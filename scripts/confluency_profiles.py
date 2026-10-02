"""
Confluency calibration profiles: one Cellpose-SAM cutoff and one error band per
imaging setup, fitted on labelled images from that setup and tested on others.

The method, splits and acceptance criteria are pre-registered in
results/confluency_profiles.md and committed before any image is scored here.

    .venv/bin/python scripts/confluency_profiles.py maps --setup livecell
    .venv/bin/python scripts/confluency_profiles.py maps --setup c2c12      # the pre-registered crops; no labels read
    .venv/bin/python scripts/confluency_profiles.py robust --setup evican
    .venv/bin/python scripts/confluency_profiles.py labelpage --out ~/Desktop/projs/c2c12_label
    .venv/bin/python scripts/confluency_profiles.py score [--labels path] [--msc-dir path]

`maps` and `robust` run Cellpose-SAM only (CULTUREQC_DEVICE=mps for Apple's
GPU) and never read ground truth. `score` reads the maps, fits each profile on
its calibration images, and appends the results section to the .md once.

Outputs: cache/confluency_profiles/ (readings, gitignored),
results/confluency_profiles.csv, results/confluency_profiles.md (results
section), results/confluency_profiles.json (the fitted profiles).
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import csv
import json
import math
import os
import sys
from datetime import datetime, timezone

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "scripts"))
os.chdir(REPO)

GRID = [round(-4.0 + 0.5 * i, 1) for i in range(11)]
I0 = GRID.index(0.0)
BAND = 1.0            # culture.seg.cpsam_confluency's ambiguity band
FLOOR = 0.30          # culture.rules confidence floor (boundary ambiguity 0.70)
ALPHA = 0.10          # 90% band
TARGETS = (80.0, 70.0)
GT_BANDS = [(0, 20), (20, 40), (40, 60), (60, 90), (90, 100.0001)]
MAPS = os.path.join("cache", "probmaps_full")
WORK = os.path.join("cache", "confluency_profiles")
LIVECELL = os.path.join("data", "sources", "livecell")
C2C12_PNG = os.path.expanduser("~/Desktop/projs/c2c12_prepared/content/data/c2c12/png")
CROP = 160            # C2C12 label crop, px at 1.3 µm/px
N_CROPS = 20          # per split
OUT_MD = os.path.join("results", "confluency_profiles.md")
OUT_CSV = os.path.join("results", "confluency_profiles.csv")
OUT_JSON = os.path.join("results", "confluency_profiles.json")
LABELS = os.path.join("results", "c2c12_confluency_labels.json")   # the owner's painted C2C12 crops, tracked
PROFILE = {"evican": "evican_mixed", "livecell": "livecell_incucyte", "msc": "msc_phase", "c2c12": "c2c12_ker2018"}


# ── maps ────────────────────────────────────────────────────────────────────

def prob_map(src: str, name: str, path: str | None = None, img: np.ndarray | None = None) -> np.ndarray:
    """Full-resolution flows[2] of the call culture.seg.cpsam_confluency makes, cached as float16."""
    dst = os.path.join(MAPS, src, name + ".npz")
    if not os.path.exists(dst):
        import cv2
        from culture.seg import _get_model
        if img is None:
            img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                raise FileNotFoundError(path)
        _, flows, _ = _get_model().eval(img, diameter=None, channels=[0, 0])
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        np.savez_compressed(dst, prob=flows[2].astype(np.float16))
    return np.load(dst)["prob"].astype(np.float32)


def curve(p: np.ndarray) -> list[float]:
    return [float((p > t).mean() * 100) for t in GRID]


def conf0(p: np.ndarray) -> float:
    return float(np.clip(1 - 4 * (np.abs(p) < BAND).mean(), 0, 1))


# ── setups: name, split, unit (left out together), image path, ground truth loader ──

def evican_items() -> list[dict]:
    from eval_confluency_real import IMAGES_DIR, load_coco_gt
    gt = {v["file_name"]: v for v in load_coco_gt().values()}
    ev = {r["file_name"] for r in csv.DictReader(open(os.path.join("results", "confluency_real.csv")))}
    out = [{"setup": "evican", "name": n, "split": "test" if n in ev else "calib", "unit": n,
            "path": os.path.join(IMAGES_DIR, n), "group": gt[n]["cell_line"], "_gt": gt[n]["gt_pct"]} for n in sorted(gt)]
    assert sum(i["split"] == "test" for i in out) == 33 and len(out) == 98
    return out


def _livecell_field(name: str) -> tuple[str, str]:
    line, _, well, field = name.split("_")[:4]
    return line, f"{line}_{well}_{field}"


def livecell_items() -> list[dict]:
    names = sorted(os.listdir(os.path.join(LIVECELL, "images", "livecell_test_images")))
    fields: dict[str, list[str]] = {}
    for n in names:
        line, f = _livecell_field(n)
        fields.setdefault(line, [])
        if f not in fields[line]:
            fields[line].append(f)
    rng = np.random.default_rng(0)
    calib = set()
    for line in sorted(fields):
        fs = sorted(fields[line])
        order = rng.permutation(len(fs))
        calib |= {fs[i] for i in order[: len(fs) // 2]}
    out = []
    for n in names:
        line, f = _livecell_field(n)
        out.append({"setup": "livecell", "name": n, "split": "calib" if f in calib else "test", "unit": f,
                    "path": os.path.join(LIVECELL, "images", "livecell_test_images", n), "group": line})
    return out


def livecell_gt(items: list[dict]) -> None:
    import cv2
    want = {i["name"]: i for i in items}
    seen = set()
    for f in sorted(os.listdir(os.path.join(LIVECELL, "annotations"))):
        if not f.endswith("_test.json"):
            continue
        d = json.load(open(os.path.join(LIVECELL, "annotations", f)))
        by = {}
        for a in d["annotations"]:
            by.setdefault(a["image_id"], []).append(a)
        for im in d["images"]:
            n = im["file_name"]
            if n not in want or n in seen:
                continue
            m = np.zeros((im["height"], im["width"]), np.uint8)
            for a in by.get(im["id"], []):
                for poly in a["segmentation"]:
                    pts = np.clip(np.array(poly, dtype=np.float32).reshape(-1, 2), 0, None).astype(np.int32)
                    cv2.fillPoly(m, [pts], 1)
            want[n]["_gt"] = float(m.mean() * 100)
            seen.add(n)
    missing = [n for n in want if n not in seen]
    assert not missing, f"no LIVECell annotation for {len(missing)} images, e.g. {missing[:3]}"


def c2c12_crops() -> list[dict]:
    """The pre-registered crop choice: no model output involved."""
    import pandas as pd
    im = pd.read_parquet(os.path.join("cache", "images.parquet"))
    split = pd.read_csv(os.path.join("results", "replay_fleet_split.csv"))
    base = split[split.kind == "base"]
    rng = np.random.default_rng(0)
    out = []
    for sp in ("tuning", "heldout"):
        seqs = sorted(base[base.split == sp].sequence_id)
        combos = [(s, k) for s in seqs for k in range(5)]
        order = rng.permutation(len(combos))[:N_CROPS]
        for j, ci in enumerate(order):
            s, k = combos[ci]
            fr = im[(im.dataset == "c2c12") & (im.sequence_id == s)].sort_values("frame_idx").reset_index(drop=True)
            lo, hi = len(fr) * k // 5, len(fr) * (k + 1) // 5
            r = fr.iloc[int(rng.integers(lo, hi))]
            y0 = int(rng.integers(0, int(r.height) - CROP + 1))
            x0 = int(rng.integers(0, int(r.width) - CROP + 1))
            png = os.path.join(C2C12_PNG, s, os.path.basename(r.source_path).rsplit(".", 1)[0] + ".png")
            out.append({"setup": "c2c12", "name": f"{'t' if sp == 'tuning' else 'h'}{j:02d}",
                        "split": "calib" if sp == "tuning" else "test", "unit": s, "group": s,
                        "frame_sha": r.image_sha256, "frame_idx": int(r.frame_idx), "path": png, "y0": y0, "x0": x0})
    return out


def c2c12_items(labels_path: str | None) -> list[dict]:
    if not labels_path or not os.path.exists(labels_path):
        return []
    labels = json.load(open(labels_path))["crops"]
    out = []
    for c in c2c12_crops():
        lab = labels.get(c["name"])
        if not lab or lab.get("skip") or not lab.get("done"):
            continue
        m = rle_decode(lab["rle"], CROP, CROP)
        out.append({**c, "_gt": float(m.mean() * 100)})
    return out


def rle_decode(rle: list[int], h: int, w: int) -> np.ndarray:
    """Runs alternate background, cell, background, ... over the row-major crop."""
    flat = np.zeros(h * w, np.uint8)
    pos, val = 0, 0
    for run in rle:
        flat[pos: pos + run] = val
        pos += run
        val ^= 1
    assert pos == h * w, (pos, h * w)
    return flat.reshape(h, w)


MSC = os.path.join("data", "sources", "msc")


def msc_items(msc_dir: str | None = None) -> list[dict]:
    """Solopov et al. 2025 (Kaggle maximsolopov/msu-smooth-1-20): images/<pop>_part_<p>_tile_<t>.png and
    masks/<same>_mask.png (0/255). Leave one population out: every image is a test image of the fold that
    leaves its population out, and a calibration image of the other folds."""
    msc_dir = msc_dir or MSC
    if not os.path.isdir(os.path.join(msc_dir, "images")):
        return []
    out = []
    for n in sorted(os.listdir(os.path.join(msc_dir, "images"))):
        out.append({"setup": "msc", "name": n, "split": "lopo", "unit": n.split("_part_")[0],
                    "group": n.split("_part_")[0], "path": os.path.join(msc_dir, "images", n),
                    "mask": os.path.join(msc_dir, "masks", n.replace(".png", "_mask.png"))})
    return out


def msc_gt(items: list[dict]) -> None:
    import cv2
    for i in items:
        m = cv2.imread(i["mask"], cv2.IMREAD_GRAYSCALE)
        assert m is not None, i["mask"]
        i["_gt"] = float((m > 0).mean() * 100)


def item_map(i: dict) -> np.ndarray:
    if i["setup"] == "c2c12":
        p = prob_map("c2c12", i["frame_sha"], i["path"])
        return p[i["y0"]: i["y0"] + CROP, i["x0"]: i["x0"] + CROP]
    return prob_map(i["setup"], i["name"], i["path"])


# ── profile fitting ─────────────────────────────────────────────────────────

def pick(R: np.ndarray, gt: np.ndarray) -> int:
    """Index of the grid cutoff with the lowest MAE; ties go to the value closest to 0.0."""
    mae = np.abs(R - gt[:, None]).mean(0)
    best = np.flatnonzero(np.isclose(mae, mae.min()))
    return int(min(best, key=lambda j: abs(GRID[j])))


def band(R: np.ndarray, gt: np.ndarray, units: np.ndarray) -> tuple[float | None, np.ndarray]:
    res = np.empty(len(gt))
    for u in np.unique(units):
        out = units == u
        if out.all():
            return None, res
        j = pick(R[~out], gt[~out])
        res[out] = np.abs(R[out, j] - gt[out])
    n = len(gt)
    k = math.ceil((1 - ALPHA) * (n + 1))
    return (float(np.sort(res)[k - 1]) if n >= 9 and k <= n else None), res


def call(reading, q, T):
    if q is None:
        return np.where(reading >= T, "passage", "continue")
    return np.where(reading - q >= T, "passage", np.where(reading + q < T, "continue", "review"))


def shipped_call(reading0, c0, T):
    return np.where(c0 < FLOOR, "review", np.where(reading0 >= T, "passage", "continue"))


def agreement(calls, gt, T):
    keep = calls != "review"
    if not keep.any():
        return None, 0
    ok = (calls[keep] == "passage") == (gt[keep] >= T)
    return float(ok.mean()), int(keep.sum())


def stats(r: np.ndarray, gt: np.ndarray) -> dict:
    e = r - gt
    out = {"n": len(gt), "mae": float(np.abs(e).mean()) if len(e) else None,
           "median_ae": float(np.median(np.abs(e))) if len(e) else None,
           "bias": float(e.mean()) if len(e) else None, "over10": int((np.abs(e) > 10).sum())}
    if len(gt) >= 3:
        slope, icpt = np.polyfit(gt, r, 1)
        out.update(slope=float(slope), intercept=float(icpt), r2=float(np.corrcoef(gt, r)[0, 1] ** 2))
    return out


# ── commands ────────────────────────────────────────────────────────────────

def load_items(setup: str, labels: str | None = None, msc_dir: str | None = None) -> list[dict]:
    if setup == "evican":
        return evican_items()
    if setup == "livecell":
        return livecell_items()
    if setup == "c2c12":
        return c2c12_crops() if labels is None else c2c12_items(labels)
    if setup == "msc":
        return msc_items(msc_dir)
    raise ValueError(setup)


def cmd_maps(a):
    items = load_items(a.setup, msc_dir=a.msc_dir)
    if a.setup == "c2c12":
        items = list({i["frame_sha"]: i for i in items}.values())
    todo = [i for i in items if not os.path.exists(os.path.join(MAPS, a.setup, (i.get("frame_sha") or i["name"]) + ".npz"))]
    print(f"{a.setup}: {len(items)} maps, {len(todo)} to compute", flush=True)
    for k, i in enumerate(todo):
        if a.setup == "c2c12":
            prob_map("c2c12", i["frame_sha"], i["path"])
        else:
            prob_map(a.setup, i["name"], i["path"])
        if (k + 1) % 25 == 0:
            print(f"  {k + 1}/{len(todo)}", flush=True)
    print("done", flush=True)


def perturb(img: np.ndarray, kind: str) -> np.ndarray:
    import cv2
    if kind == "dim":
        return np.clip(img.astype(np.float32) * 0.7, 0, 255).astype(np.uint8)
    if kind == "bright":
        return np.clip(img.astype(np.float32) * 1.3, 0, 255).astype(np.uint8)
    if kind == "blur":
        return cv2.GaussianBlur(img, (0, 0), 2)
    raise ValueError(kind)


def cmd_robust(a):
    """Readings on perturbed copies of up to 40 test images; no ground truth read."""
    import cv2
    items = [i for i in load_items(a.setup, msc_dir=a.msc_dir) if i["split"] in ("test", "lopo")]
    rng = np.random.default_rng(0)
    pick_ = sorted(rng.permutation(len(items))[:40]) if len(items) > 40 else range(len(items))
    os.makedirs(WORK, exist_ok=True)
    out = os.path.join(WORK, f"robust_{a.setup}.json")
    done = json.load(open(out)) if os.path.exists(out) else {}
    from culture.seg import _get_model
    for k, j in enumerate(pick_):
        i = items[j]
        if i["name"] in done:
            continue
        img = cv2.imread(i["path"], cv2.IMREAD_GRAYSCALE)
        row = {}
        for kind in ("dim", "bright", "blur"):
            _, flows, _ = _get_model().eval(perturb(img, kind), diameter=None, channels=[0, 0])
            p = flows[2]
            if i["setup"] == "c2c12":
                p = p[i["y0"]: i["y0"] + CROP, i["x0"]: i["x0"] + CROP]
            row[kind] = curve(p)
        done[i["name"]] = row
        json.dump(done, open(out, "w"))
        print(f"  {k + 1}/{len(pick_)}", flush=True)
    print("done", out)


def readings(setup: str, items: list[dict]) -> list[dict]:
    rows = []
    for i in items:
        p = item_map(i)
        rows.append({k: v for k, v in i.items() if not k.startswith("_") and k != "path"} |
                    {"gt": i["_gt"], "curve": curve(p), "conf0": conf0(p)})
    return rows


def folds(rows: list[dict]) -> list[tuple[list[int], list[int]]]:
    """(calibration, test) row indices: one fold for a fixed split; for MSC one fold per left-out population."""
    if all(r["split"] == "lopo" for r in rows):
        units = sorted({r["unit"] for r in rows})
        return [([k for k, r in enumerate(rows) if r["unit"] != u], [k for k, r in enumerate(rows) if r["unit"] == u])
                for u in units]
    return [([k for k, r in enumerate(rows) if r["split"] == "calib"], [k for k, r in enumerate(rows) if r["split"] == "test"])]


def fit(rows: list[dict], idx: list[int] | None = None) -> dict:
    cal = [rows[k] for k in idx] if idx is not None else [r for r in rows if r["split"] in ("calib", "lopo")]
    R = np.array([r["curve"] for r in cal])
    gt = np.array([r["gt"] for r in cal])
    j = pick(R, gt)
    q, _ = band(R, gt, np.array([r["unit"] for r in cal]))
    return {"cutoff": GRID[j], "j": j, "band_pp": q, "n_calib": len(cal), "calib_mae": float(np.abs(R[:, j] - gt).mean())}


def evaluate(rows, prof, all_profiles, robust):
    """Every test image is read at the cutoff and band of the fold it is held out of."""
    fs = folds(rows)
    test_idx, J, Q = [], [], []
    fold_fits = []
    for cal, test in fs:
        f = fit(rows, cal)
        fold_fits.append(f)
        test_idx += test
        J += [f["j"]] * len(test)
        Q += [np.nan if f["band_pp"] is None else f["band_pp"]] * len(test)
    test = [rows[k] for k in test_idx]
    R = np.array([r["curve"] for r in test])
    gt = np.array([r["gt"] for r in test])
    c0 = np.array([r["conf0"] for r in test])
    J, Q = np.array(J), np.array(Q)
    rp = R[np.arange(len(test)), J]                      # reading at the fold's cutoff
    has_q = not np.isnan(Q).any()
    within = np.abs(rp - gt) <= Q
    out = {"folds": [{k: v for k, v in f.items() if k != "j"} for f in fold_fits], "n_test": len(test),
           "shipped": stats(R[:, I0], gt), "profile": stats(rp, gt), "bands": [], "calls": {}, "transfer": {}}
    for lo, hi in GT_BANDS:
        m = (gt >= lo) & (gt < hi)
        out["bands"].append({"band": f"{lo}-{min(hi, 100):.0f}%", "n": int(m.sum()),
                             "mae0": float(np.abs(R[m, I0] - gt[m]).mean()) if m.any() else None,
                             "bias0": float((R[m, I0] - gt[m]).mean()) if m.any() else None,
                             "mae": float(np.abs(rp[m] - gt[m]).mean()) if m.any() else None,
                             "bias": float((rp[m] - gt[m]).mean()) if m.any() else None,
                             "coverage": float(within[m].mean()) if (has_q and m.any()) else None})
    out["coverage"] = float(within.mean()) if has_q else None
    for T in TARGETS:
        cp = np.where(rp - Q >= T, "passage", np.where(rp + Q < T, "continue", "review")) if has_q \
            else call(rp, None, T)
        cs = shipped_call(R[:, I0], c0, T)
        ap, np_ = agreement(cp, gt, T)
        as_, ns = agreement(cs, gt, T)
        out["calls"][T] = {"profile_review": float((cp == "review").mean()), "profile_agree": ap, "profile_n": np_,
                           "shipped_review": float((cs == "review").mean()), "shipped_agree": as_, "shipped_n": ns}
    for name, other in all_profiles.items():
        out["transfer"][name] = float(np.abs(R[:, other["j"]] - gt).mean())
    # learning curve: per fold, the cutoff picked from k random calibration images; MAE over all test images
    rng = np.random.default_rng(0)
    out["learning"] = {}
    for k in (2, 5, 10, 20):
        if any(k > len(cal) for cal, _ in fs):
            continue
        maes = []
        for _ in range(20):
            err = []
            for cal, tst in fs:
                s_ = rng.choice(cal, k, replace=False)
                jj = pick(np.array([rows[i]["curve"] for i in s_]), np.array([rows[i]["gt"] for i in s_]))
                err += [abs(rows[i]["curve"][jj] - rows[i]["gt"]) for i in tst]
            maes.append(float(np.mean(err)))
        out["learning"][k] = (float(np.median(maes)), float(np.quantile(maes, 0.9)))
    if robust:
        pos = {r["name"]: n for n, r in enumerate(test)}
        out["robust"] = {}
        for kind in ("dim", "bright", "blur"):
            d = [abs(v[kind][J[pos[nm]]] - test[pos[nm]]["curve"][J[pos[nm]]]) for nm, v in robust.items() if nm in pos]
            out["robust"][kind] = (float(np.median(d)), len(d)) if d else None
    # acceptance
    m6090 = (gt >= 60) & (gt < 90)
    near = int(((gt >= 60) & (gt <= 100)).sum())
    A = {}
    A["A1"] = ("pass" if out["profile"]["mae"] <= 5 else "fail", f"{out['profile']['mae']:.2f} pp")
    if m6090.sum() >= 10:
        e = rp[m6090] - gt[m6090]
        A["A2"] = ("pass" if np.abs(e).mean() <= 5 else "fail", f"{np.abs(e).mean():.2f} pp, n = {int(m6090.sum())}")
        A["A3"] = ("pass" if abs(e.mean()) <= 3 else "fail", f"{e.mean():+.2f} pp, n = {int(m6090.sum())}")
    else:
        A["A2"] = A["A3"] = ("not measurable", f"n = {int(m6090.sum())}")
    c80 = out["calls"][80.0]
    if near >= 10 and c80["profile_agree"] is not None:
        A["A4"] = ("pass" if c80["profile_agree"] >= 0.95 else "fail",
                   f"{c80['profile_agree']:.1%} of {c80['profile_n']}, review {c80['profile_review']:.1%}")
    else:
        A["A4"] = ("not measurable", f"{near} test images at 60–100%")
    cov6090 = float(within[m6090].mean()) if (has_q and m6090.any()) else None
    A["A5"] = (("pass" if out["coverage"] >= 0.85 else "fail",
                f"{out['coverage']:.1%}; at 60–90%: " + (f"{cov6090:.0%} of {int(m6090.sum())}" if cov6090 is not None
                                                          else "no images")) if has_q
               else ("not measurable", "no band"))
    out["acceptance"] = A
    out["_rows"] = [{"name": r["name"], "gt": r["gt"], "reading": float(x), "cutoff": GRID[j], "band": float(q)}
                    for r, x, j, q in zip(test, rp, J, Q)]
    return out


def fmt(v, spec=".2f", none="—"):
    return none if v is None else format(v, spec)


def cmd_score(a):
    setups = {"evican": evican_items(), "livecell": livecell_items()}
    livecell_gt(setups["livecell"])
    msc = msc_items(a.msc_dir)
    if msc:
        msc_gt(msc)
        setups["msc"] = msc
    labels = a.labels or (LABELS if os.path.exists(LABELS) else None)
    c2 = c2c12_items(labels)
    if c2:
        setups["c2c12"] = c2
    for s, items in setups.items():
        missing = [i for i in items if not os.path.exists(os.path.join(MAPS, s, (i.get("frame_sha") or i["name"]) + ".npz"))]
        assert not missing, f"{s}: {len(missing)} maps missing; run `maps --setup {s}` first"
    rows = {s: readings(s, items) for s, items in setups.items()}
    profiles = {PROFILE[s]: fit(r) for s, r in rows.items()}
    robust = {s: json.load(open(os.path.join(WORK, f"robust_{s}.json")))
              for s in rows if os.path.exists(os.path.join(WORK, f"robust_{s}.json"))}
    res = {s: evaluate(r, profiles[PROFILE[s]], profiles, robust.get(s)) for s, r in rows.items()}

    os.makedirs(WORK, exist_ok=True)
    json.dump(rows, open(os.path.join(WORK, "readings.json"), "w"))
    with open(OUT_CSV, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["setup", "name", "unit", "gt_pct", "pct_cut0", "conf_cut0", "test_cutoff", "pct_test", "band_pp"])
        for s, rr in rows.items():
            byname = {r["name"]: r for r in rr}
            for t in res[s]["_rows"]:
                r = byname[t["name"]]
                w.writerow([s, r["name"], r["unit"], round(r["gt"], 3), round(r["curve"][I0], 2), round(r["conf0"], 3),
                            t["cutoff"], round(t["reading"], 2), None if np.isnan(t["band"]) else round(t["band"], 3)])
    status = {"evican": "held-out", "livecell": "in-domain check", "msc": "held-out",
              "c2c12": "held-out; non-specialist labels"}
    json.dump({"generated_by": "scripts/confluency_profiles.py", "grid": GRID,
               "profiles": {k: {kk: vv for kk, vv in v.items() if kk != "j"} for k, v in profiles.items()},
               "results": {PROFILE[s_]: {"status": status[s_], **{k: v for k, v in r.items() if k != "_rows"},
                                         "calls": {str(int(T)): c for T, c in r["calls"].items()},
                                         "learning": {str(k): v for k, v in r["learning"].items()}}
                           for s_, r in res.items()}},
              open(OUT_JSON, "w"), indent=1, default=float)
    write_md(rows, profiles, res)


def write_md(rows, profiles, res):
    src = open(OUT_MD).read().split("\n## Results\n")[0].rstrip() + "\n"
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    L = ["", "## Results", "",
         f"Generated {stamp} by `scripts/confluency_profiles.py score`, with the method and rules above unchanged. "
         "EVICAN: Parekh et al., *Bioinformatics* 36(12):3863 (2020), CC BY 4.0. LIVECell: Edlund et al., "
         "*Nat Methods* 18:1038 (2021), CC BY-NC 4.0. MSC: Solopov et al., *Int J Mol Sci* 26:2338 (2025), "
         "Kaggle copy CC BY-NC-SA 4.0. C2C12: Ker et al., *Sci Data* 5:180237 (2018), CC BY 4.0"
         + (f"; crop labels `{LABELS}`, SHA-256 `{hashlib.sha256(open(LABELS, 'rb').read()).hexdigest()}`"
            if "c2c12" in rows and os.path.exists(LABELS) else "") + ".", ""]
    L += ["### Profiles", "",
          "| profile | images (calibration / test) | cutoff (logit) | calibration MAE (pp) | 90% band (± pp) | status |",
          "|---|---|---|---|---|---|"]
    status = {"evican": "held-out", "livecell": "in-domain check; test fields are other positions, mostly in the same well",
              "msc": "held-out, leave one population out", "c2c12": "held-out sequences; non-specialist labels on 160 px crops"}
    for s, rr in rows.items():
        p = profiles[PROFILE[s]]
        nt = res[s]["n_test"]
        L.append(f"| `{PROFILE[s]}` | {p['n_calib']} / {nt} | {p['cutoff']:+.1f} | {p['calib_mae']:.2f} | "
                 f"{fmt(p['band_pp'])} | {status[s]} |")
    L += ["", "### Acceptance (each profile on its own test images)", "",
          "| profile | A1 MAE ≤ 5 | A2 MAE ≤ 5 at 60–90% | A3 \\|bias\\| ≤ 3 at 60–90% | A4 passage call ≥ 95% at 80% | A5 band covers ≥ 85% |",
          "|---|---|---|---|---|---|"]
    for s in rows:
        A = res[s]["acceptance"]
        L.append(f"| `{PROFILE[s]}` | " + " | ".join(f"**{A[k][0]}** ({A[k][1]})" for k in ("A1", "A2", "A3", "A4", "A5")) + " |")
    for s, r in res.items():
        p = profiles[PROFILE[s]]
        L += ["", f"### `{PROFILE[s]}` ({status[s]})", ""]
        if len(r["folds"]) > 1:
            L += ["Leave one population out: " + "; ".join(
                f"fold {k + 1} cutoff {f['cutoff']:+.1f}, band ± {fmt(f['band_pp'])} pp ({f['n_calib']} calibration images)"
                for k, f in enumerate(r["folds"])) + ".", ""]
        L += [
              "| | shipped, cutoff 0.0 | profile, cutoff %+.1f |" % p["cutoff"], "|---|---|---|"]
        for k, lab in [("mae", "MAE (pp)"), ("median_ae", "median absolute error (pp)"), ("bias", "mean signed error (pp)"),
                       ("over10", "off by more than 10 pp"), ("slope", "slope, reading on ground truth"),
                       ("intercept", "intercept (pp)"), ("r2", "R²")]:
            a0, a1 = r["shipped"].get(k), r["profile"].get(k)
            L.append(f"| {lab} | {a0} of {r['shipped']['n']} | {a1} of {r['profile']['n']} |" if k == "over10"
                     else f"| {lab} | {fmt(a0)} | {fmt(a1)} |")
        L += ["", "| ground truth | n | MAE at 0.0 | bias at 0.0 | MAE at profile | bias at profile | band coverage |",
              "|---|---|---|---|---|---|---|"]
        for b in r["bands"]:
            L.append(f"| {b['band']} | {b['n']} | {fmt(b['mae0'])} | {fmt(b['bias0'], '+.2f')} | {fmt(b['mae'])} | "
                     f"{fmt(b['bias'], '+.2f')} | {fmt(b['coverage'], '.0%')} |")
        L.append(f"\nBand coverage, all test images: {fmt(r['coverage'], '.1%')}.\n")
        L += ["| target | rule | sent to review | agrees with ground truth (of the rest) |", "|---|---|---|---|"]
        for T, c in r["calls"].items():
            L.append(f"| {T:.0f}% | profile band | {c['profile_review']:.1%} | {fmt(c['profile_agree'], '.1%')} (n = {c['profile_n']}) |")
            L.append(f"| {T:.0f}% | shipped | {c['shipped_review']:.1%} | {fmt(c['shipped_agree'], '.1%')} (n = {c['shipped_n']}) |")
        L += ["", "Learning curve (reported only): test MAE of the cutoff picked from k random calibration images, 20 draws.", "",
              "| k | median MAE (pp) | 90th percentile (pp) |", "|---|---|---|"]
        for k, (med, p90) in r["learning"].items():
            L.append(f"| {k} | {med:.2f} | {p90:.2f} |")
        if r.get("robust"):
            L += ["", "Robustness (reported only): median |change in reading| at the profile's cutoff.", "",
                  "| perturbation | median change (pp) | images |", "|---|---|---|"]
            for kind, lab in [("dim", "intensity × 0.7"), ("bright", "intensity × 1.3"), ("blur", "Gaussian blur σ = 2 px")]:
                v = r["robust"].get(kind)
                if v:
                    L.append(f"| {lab} | {v[0]:.2f} | {v[1]} |")
    L += ["", "### Transfer: test MAE under each profile's cutoff", "",
          "| test images ↓ / profile → | " + " | ".join(f"`{n}` ({profiles[n]['cutoff']:+.1f})" for n in profiles) + " |",
          "|---|" + "---|" * len(profiles)]
    for s, r in res.items():
        L.append(f"| {PROFILE[s]} | " + " | ".join(f"{r['transfer'][n]:.2f}" for n in profiles) + " |")
    L.append("")
    open(OUT_MD, "w").write(src + "\n".join(L) + "\n")
    print("wrote", OUT_MD, OUT_CSV, OUT_JSON)


# ── figure ──────────────────────────────────────────────────────────────────

OUT_PNG = os.path.join("results", "confluency_profiles.png")


def cmd_figure(a):
    """Reading vs ground truth per setup on its test images: shipped cutoff (grey) and the
    setup's own profile (colour), with the 90% band and the 80% target. From results/confluency_profiles.csv."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import pandas as pd
    df = pd.read_csv(OUT_CSV)
    doc = json.load(open(OUT_JSON))
    setups = [s for s in ("livecell", "msc", "evican", "c2c12") if s in set(df.setup)]
    fig, axes = plt.subplots(1, len(setups), figsize=(4.2 * len(setups), 4.4), squeeze=False)
    for ax, s in zip(axes[0], setups):
        d = df[df.setup == s]
        res = doc["results"][PROFILE[s]]
        q = doc["profiles"][PROFILE[s]]["band_pp"]
        x = np.linspace(0, 100, 2)
        if q is not None:
            ax.fill_between(x, x - q, x + q, color="#3b82f6", alpha=0.12, lw=0, label=f"90% band ±{q:.1f} pp")
        ax.plot(x, x, color="#111", lw=0.8)
        ax.scatter(d.gt_pct, d.pct_cut0, s=7, color="#9ca3af", alpha=0.6,
                   label=f"shipped cutoff 0: MAE {res['shipped']['mae']:.1f} pp")
        ax.scatter(d.gt_pct, d.pct_test, s=7, color="#2563eb", alpha=0.7,
                   label=f"own profile: MAE {res['profile']['mae']:.1f} pp")
        ax.axhline(80, color="#f59e0b", lw=0.8, ls="--"); ax.axvline(80, color="#f59e0b", lw=0.8, ls="--")
        ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.set_aspect("equal")
        ax.set_xlabel("expert ground truth (%)"); ax.set_ylabel("reading (%)")
        ax.set_title(f"{PROFILE[s]}\n{res['status']}, n = {len(d)} test images", fontsize=10)
        ax.legend(loc="upper left", fontsize=7, frameon=False)
    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=140)
    print("wrote", OUT_PNG)


# ── C2C12 label page ────────────────────────────────────────────────────────

def cmd_labelpage(a):
    import cv2
    crops = c2c12_crops()
    order = np.random.default_rng(1).permutation(len(crops))     # interleave the splits for the labeller
    data = []
    for k in order:
        c = crops[k]
        img = cv2.imread(c["path"], cv2.IMREAD_GRAYSCALE)
        assert img is not None, c["path"]
        y0, x0 = c["y0"], c["x0"]
        crop = img[y0: y0 + CROP, x0: x0 + CROP]
        cy0, cx0 = max(0, y0 - CROP), max(0, x0 - CROP)
        ctx = img[cy0: y0 + 2 * CROP, cx0: x0 + 2 * CROP]
        enc = lambda m: "data:image/png;base64," + base64.b64encode(cv2.imencode(".png", m)[1].tobytes()).decode()
        data.append({"id": c["name"], "img": enc(crop), "ctx": enc(ctx), "ctx_off": [y0 - cy0, x0 - cx0]})
    tpl = open(os.path.join(REPO, "scripts", "label_page.html")).read()
    os.makedirs(os.path.expanduser(a.out), exist_ok=True)
    dst = os.path.join(os.path.expanduser(a.out), "label.html")
    open(dst, "w").write(tpl.replace("/*__CROPS__*/[]", json.dumps(data)).replace("__SIZE__", str(CROP)))
    print("wrote", dst, len(data), "crops")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("maps", "robust"):
        p = sub.add_parser(name)
        p.add_argument("--setup", required=True, choices=["evican", "livecell", "msc", "c2c12"])
        p.add_argument("--labels")
        p.add_argument("--msc-dir")
    p = sub.add_parser("score")
    p.add_argument("--labels")
    p.add_argument("--msc-dir")
    sub.add_parser("figure")
    p = sub.add_parser("labelpage")
    p.add_argument("--out", default="~/Desktop/projs/c2c12_label")
    a = ap.parse_args()
    {"maps": cmd_maps, "robust": cmd_robust, "score": cmd_score, "labelpage": cmd_labelpage,
     "figure": cmd_figure}[a.cmd](a)


if __name__ == "__main__":
    main()
