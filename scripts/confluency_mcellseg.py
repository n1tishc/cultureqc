"""
Sealed test on a dense, held-out dataset: mCellSeg (Alam et al. 2026, Zenodo 10.5281/zenodo.20174259, CC BY 4.0).

The method, the split and the pass rules are pre-registered in results/confluency_mcellseg.md and committed
before any probability map of these images is computed. GPU steps run on Colab (nb/06_confluency_evidence.ipynb):

    python scripts/confluency_mcellseg.py count     # expert masks only: checks the committed split
    python scripts/confluency_mcellseg.py maps      # zero-shot and rescaled maps, every image
    python scripts/confluency_mcellseg.py train     # fine-tune: two cross-fit folds, then the final model
    python scripts/confluency_mcellseg.py ftmaps    # fine-tuned maps (out-of-fold for calibration, final for test)
    python scripts/confluency_mcellseg.py curves    # readings at every cutoff -> results/confluency_mcellseg_curves.json

CPU, on the Mac, once:

    .venv/bin/python scripts/confluency_mcellseg.py score     # reads the curves file only; appends the results section
    .venv/bin/python scripts/confluency_mcellseg.py figure    # results/confluency_mcellseg.png from the scored files

Data: data/sources/mcellseg/mCellSeg/labeled/{images,masks} (gitignored; not redistributed here).
Maps and weights: cache/ (gitignored, on the Colab disk).
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))
os.chdir(REPO)

DATA = os.path.join("data", "sources", "mcellseg", "mCellSeg", "labeled")
ZENODO_MD5 = "ed06d6e4c10e93b81703984cef852246"      # mCellSeg.zip, from the Zenodo record
GRID = [round(-4.0 + 0.5 * i, 1) for i in range(11)]  # as scripts/confluency_profiles.py
ALPHA = 0.10
MIN_CALIB = 9          # a band needs >= 9 calibration images (confluency_profiles.band)
MIN_IMAGES = 10        # a criterion on a subset is measurable with >= 10 test images in it
T = 80.0
LO, HI = 60.0, 90.0
N_BOOT = 10_000
MAE_MAX, BIAS_MAX, AGREE_MIN, COVER_MIN = 5.0, 3.0, 0.95, 0.85
TARGET_DIAM = 30.0     # Cellpose's nominal cell diameter for the rescaled arm
MAPS = os.path.join("cache", "probmaps_mcellseg")
OUT_MD = os.path.join("results", "confluency_mcellseg.md")
OUT_CSV = os.path.join("results", "confluency_mcellseg.csv")
OUT_JSON = os.path.join("results", "confluency_mcellseg.json")
SPLIT_JSON = os.path.join("results", "confluency_mcellseg_split.json")


# ── setups and split units (file names and image sizes only) ────────────────

def setup_of(name: str, shape: tuple[int, int]) -> str:
    """Acquisition group. The TIFFs carry no instrument tags, so a group is an image format plus a file family."""
    if name.startswith("HUVEC_"):
        return "cd7_huvec_dic"
    if name.startswith(("CellsOnly_Polymer", "Polymer_Test")):
        return "polymer_lowmag"
    if name.startswith("BF-HUVEC"):
        return "huvec_bf_2752"
    if shape == (2048, 2048):
        return "jp_bf_2048"
    if shape == (3440, 3440):
        return "bf_20x_3440"
    if "oir" in name:
        return "oir_1024"
    if re.search(r"_C004[ZT]\d{3}$", name[:-4]):
        return "lsm_hek_1024"
    if shape == (2796, 2796):
        return "lsm_2796"
    return "other"


_DROP = re.compile(r"^(\d+|z\d|C\d{3}[ZT]\d{3}|\d+x|\d+h|\d+czi|\d+xoir|C|BF|DIC|S\d+|\d+Speed|\d{8}|CD7|xoir|czi)$", re.I)


def unit_of(name: str, setup: str) -> str:
    """Images that may share a field, well or z-stack share a unit; units never straddle the split.

    cd7_huvec_dic: condition + well (one image per well; the two frames of well 09 share it).
    Everything else: the condition with positions, z-planes, frames, channels, magnifications and time points
    stripped, so every image of a condition is one unit (conservative where positions might repeat)."""
    stem = name[:-4]
    if setup == "cd7_huvec_dic":
        m = re.match(r"HUVEC_([A-Za-z]+)(?:_CD7)?_(\d+)", stem)
        return f"{m.group(1).lower()}|{int(m.group(2)):02d}"
    toks = [t for t in re.split(r"[_\-\s]+", stem) if t and not _DROP.match(t)]
    return "|".join(t.lower() for t in toks)


def items() -> list[dict]:
    import tifffile
    out = []
    for n in sorted(os.listdir(os.path.join(DATA, "images"))):
        if not n.endswith(".tif"):
            continue
        m = tifffile.imread(os.path.join(DATA, "masks", n[:-4] + "_mask.tif"))
        s = setup_of(n, m.shape)
        out.append({"name": n, "setup": s, "unit": unit_of(n, s), "gt": float((m > 0).mean() * 100),
                    "path": os.path.join(DATA, "images", n), "mask": os.path.join(DATA, "masks", n[:-4] + "_mask.tif")})
    return out


def split(its: list[dict]) -> None:
    """Within a setup, units ranked by mean expert confluency (then name) alternate calibration, test,
    calibration, ... so both halves span the density range. Uses the masks only."""
    by = defaultdict(lambda: defaultdict(list))
    for i in its:
        by[i["setup"]][i["unit"]].append(i)
    for s, units in by.items():
        order = sorted(units, key=lambda u: (np.mean([i["gt"] for i in units[u]]), u))
        for k, u in enumerate(order):
            for i in units[u]:
                i["split"] = "calib" if k % 2 == 0 else "test"


def calibrated_setups(its: list[dict]) -> list[str]:
    n = defaultdict(int)
    for i in its:
        n[i["setup"]] += i["split"] == "calib"
    return sorted(s for s, k in n.items() if k >= MIN_CALIB)


def cmd_count(a):
    its = items()
    assert len(its) == 200, len(its)
    split(its)
    cal = calibrated_setups(its)
    rows = []
    for s in sorted({i["setup"] for i in its}):
        g = [i for i in its if i["setup"] == s]
        for part in ("calib", "test"):
            h = [i for i in g if i["split"] == part]
            gt = np.array([i["gt"] for i in h])
            rows.append((s, part, len(h), len({i["unit"] for i in h}), int(((gt >= LO) & (gt <= HI)).sum()),
                         int((gt >= LO).sum()), int((gt >= T).sum())))
    print(f"{'setup':16s} {'part':6s} {'n':>3s} {'units':>5s} {'60-90':>5s} {'60-100':>6s} {'>=80':>4s}")
    for r in rows:
        print(f"{r[0]:16s} {r[1]:6s} {r[2]:3d} {r[3]:5d} {r[4]:5d} {r[5]:6d} {r[6]:4d}" + ("  *" if r[0] in cal else ""))
    test = [i for i in its if i["split"] == "test" and i["setup"] in cal]
    gt = np.array([i["gt"] for i in test])
    print(f"\ncalibrated setups (* , >= {MIN_CALIB} calibration images): {cal}")
    print(f"test images in calibrated setups: {len(test)}; 60-90%: {int(((gt >= LO) & (gt <= HI)).sum())}; "
          f"60-100%: {int((gt >= LO).sum())}; >=80%: {int((gt >= T).sum())}")
    doc = {"generated_by": "scripts/confluency_mcellseg.py count", "calibrated_setups": cal,
           "images": [{k: i[k] for k in ("name", "setup", "unit", "split", "gt")} for i in its]}
    if os.path.exists(SPLIT_JSON):                    # committed with the pre-registration: check, never rewrite
        saved = json.load(open(SPLIT_JSON))
        same = saved["calibrated_setups"] == cal and [
            {k: r[k] for k in ("name", "setup", "unit", "split")} for r in saved["images"]] == [
            {k: r[k] for k in ("name", "setup", "unit", "split")} for r in doc["images"]] and all(
            abs(r["gt"] - s["gt"]) < 1e-9 for r, s in zip(doc["images"], saved["images"]))
        print("split matches the committed", SPLIT_JSON if same else "SPLIT DIFFERS from the committed file")
        if not same:
            sys.exit(1)
    else:
        json.dump(doc, open(SPLIT_JSON, "w"), indent=1)


# ── maps ────────────────────────────────────────────────────────────────────

def gray(path: str) -> np.ndarray:
    import tifffile
    im = tifffile.imread(path)
    return im[..., 0] if im.ndim == 3 else im


def instance_mask(path: str) -> np.ndarray:
    import tifffile
    return tifffile.imread(path).astype(np.int32)


def eq_diameters(mask: np.ndarray) -> np.ndarray:
    ids, area = np.unique(mask[mask > 0], return_counts=True)
    return 2 * np.sqrt(area / np.pi)


def setup_diameter(its: list[dict], setup: str) -> float:
    """Median equivalent diameter of the expert cells in the setup's calibration images (masks only)."""
    d = np.concatenate([eq_diameters(instance_mask(i["mask"])) for i in its if i["setup"] == setup and i["split"] == "calib"])
    return float(np.median(d))


def cached(arm: str, name: str, fn) -> np.ndarray:
    dst = os.path.join(MAPS, arm, name + ".npz")
    if not os.path.exists(dst):
        p = fn()
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        np.savez_compressed(dst, prob=p.astype(np.float16))
    return np.load(dst)["prob"].astype(np.float32)


def loaded() -> list[dict]:
    """Items with the committed split; refuses to run if the split on disk was not produced by `count`."""
    its = items()
    split(its)
    saved = {r["name"]: r for r in json.load(open(SPLIT_JSON))["images"]}
    for i in its:
        assert saved[i["name"]]["split"] == i["split"] and saved[i["name"]]["unit"] == i["unit"], i["name"]
    return its


def cmd_maps(a):
    from confluency_finetune import model
    its = loaded()
    cal = calibrated_setups(its)
    diam = {s: setup_diameter(its, s) for s in cal}
    print("rescaled arm, diameter per setup (px, calibration masks):", {s: round(d, 1) for s, d in diam.items()})
    mdl = model("base")
    for k, i in enumerate(its):
        cached("zero", i["name"], lambda: mdl.eval(gray(i["path"]), diameter=None, channels=[0, 0], compute_masks=False)[1][2])
        if i["setup"] in cal:
            cached("rescaled", i["name"], lambda: mdl.eval(gray(i["path"]), diameter=diam[i["setup"]], channels=[0, 0], compute_masks=False)[1][2])
        if k % 10 == 0:
            print(k, len(its), flush=True)
    for i in lazy_items():
        cached("lazy_zero", i["name"], lambda: mdl.eval(i["img"](), diameter=None, channels=[0, 0], compute_masks=False)[1][2])


# ── fine-tuning: two cross-fit folds over calibration units, then the final model ──

def ft_folds(its: list[dict]) -> None:
    """Calibration units of each calibrated setup, ranked by mean expert confluency, alternate folds A and B."""
    cal = calibrated_setups(its)
    by = defaultdict(lambda: defaultdict(list))
    for i in its:
        if i["setup"] in cal and i["split"] == "calib":
            by[i["setup"]][i["unit"]].append(i)
    for s, units in by.items():
        order = sorted(units, key=lambda u: (np.mean([i["gt"] for i in units[u]]), u))
        for k, u in enumerate(order):
            for i in units[u]:
                i["fold"] = "A" if k % 2 == 0 else "B"


FT_RUNS = {"mcellseg_ftA": "B", "mcellseg_ftB": "A", "mcellseg_ftF": None}   # run -> fold it is trained on (None: all)


def cmd_train(a):
    from confluency_finetune import train_run, RUNS
    its = loaded()
    ft_folds(its)
    for run, fold in FT_RUNS.items():
        if os.path.exists(os.path.join(RUNS, run, "manifest.json")):
            continue
        pool = [i for i in its if "fold" in i and (fold is None or i["fold"] == fold)]
        man = train_run(run, pool, label_fn=instance_mask)
        print(json.dumps({k: man[k] for k in ("run", "n", "weights_sha256", "seconds")}), flush=True)


def cmd_ftmaps(a):
    from confluency_finetune import model
    its = loaded()
    ft_folds(its)
    cal = calibrated_setups(its)
    jobs = {"mcellseg_ftA": [i for i in its if i.get("fold") == "A"],
            "mcellseg_ftB": [i for i in its if i.get("fold") == "B"],
            "mcellseg_ftF": [i for i in its if i["setup"] in cal and i["split"] == "test"]}
    for run, todo in jobs.items():
        mdl = model(run)
        for i in todo:
            cached("ft", i["name"], lambda: mdl.eval(gray(i["path"]), diameter=None, channels=[0, 0], compute_masks=False)[1][2])
        print(run, len(todo), flush=True)


# ── supplementary: MSC on an incubator imager (Joas et al. 2025, Zenodo 15421541, CC BY 4.0) ──

LAZY = os.path.join("data", "sources", "msc_lazy", "livecell", "LC_GENERALPREP_LAZY", "Instance_prep")


def lazy_items() -> list[dict]:
    import cv2
    out = {}
    for sub in ("", "test"):
        d = os.path.join(LAZY, sub)
        for n in sorted(os.listdir(os.path.join(d, "masks"))) if os.path.isdir(os.path.join(d, "masks")) else []:
            if not n.endswith("_mask.png"):
                continue
            stem = n[:-9]
            img = os.path.join(d, "imgs", stem + ".jpg")
            m = cv2.imread(os.path.join(d, "masks", n), cv2.IMREAD_GRAYSCALE)
            out.setdefault(stem, {"name": stem, "setup": "cytosmart_msc", "unit": stem, "gt": float((m > 0).mean() * 100),
                                  "path": img, "img": (lambda p=img: cv2.imread(p, cv2.IMREAD_GRAYSCALE))})
    its = sorted(out.values(), key=lambda i: i["name"])
    order = sorted(its, key=lambda i: (i["gt"], i["name"]))
    for k, i in enumerate(order):
        i["split"] = "calib" if k % 2 == 0 else "test"
    return its


# ── scoring (once) ──────────────────────────────────────────────────────────

ARMS = {"Z": "zero-shot, shipped cutoff 0.0, no band (uncalibrated)",
        "C": "zero-shot + per-setup calibration (the shipped method)",
        "F": "fine-tuned on the calibration images + per-setup calibration",
        "R": "zero-shot, rescaled by the calibration cells' diameter + per-setup calibration"}


def curve(p: np.ndarray) -> np.ndarray:
    return np.array([float((p > c).mean() * 100) for c in GRID])


CURVES = os.path.join("results", "confluency_mcellseg_curves.json")
MAP_DIRS = {"zero": "zero", "rescaled": "rescaled", "ft": "ft", "lazy_zero": "lazy_zero"}


def cmd_curves(a):
    """GPU-side last step: the reading at every grid cutoff, per image and map set, plus the fine-tuned runs'
    manifests, to one small file. score reads only this file."""
    from confluency_finetune import RUNS, environment
    its = loaded()
    cal = calibrated_setups(its)
    out = {"generated_by": "scripts/confluency_mcellseg.py curves", "environment": environment(), "grid": GRID,
           "diameters": {s: setup_diameter(its, s) for s in cal}, "maps": {}, "manifests": {}}
    for key, sub in MAP_DIRS.items():
        names = [i["name"] for i in (lazy_items() if key == "lazy_zero" else its)]
        rows = {}
        for n in names:
            p = os.path.join(MAPS, sub, n + ".npz")
            if os.path.exists(p):
                rows[n] = [float(x) for x in curve(np.load(p)["prob"].astype(np.float32))]
        out["maps"][key] = rows
        print(key, len(rows), "of", len(names), flush=True)
    for run in FT_RUNS:
        mp = os.path.join(RUNS, run, "manifest.json")
        if os.path.exists(mp):
            out["manifests"][run] = json.load(open(mp))
    json.dump(out, open(CURVES, "w"))
    print("wrote", CURVES)


def curve_of(C: dict, arm: str, name: str) -> np.ndarray:
    key = {"Z": "zero", "C": "zero", "R": "rescaled", "F": "ft", "S": "lazy_zero"}[arm]
    if name not in C["maps"][key]:
        sys.exit(f"no {key} reading for {name}: run maps / ftmaps / curves on Colab first; score computes nothing new")
    return np.array(C["maps"][key][name])


def uncalibrated_call(reading: float) -> str:
    return "review" if reading >= T else "continue"            # rules_v0.5: no band, at or above T goes to a person


def cal_call(reading: float, q: float | None) -> str:
    if q is None:
        return uncalibrated_call(reading)
    return "passage" if reading - q >= T else "continue" if reading + q < T else "review"


def fit_setup(rows: list[dict]) -> dict:
    from confluency_profiles import band, pick
    R = np.array([r["curve"] for r in rows])
    gt = np.array([r["gt"] for r in rows])
    j = pick(R, gt)
    q, _ = band(R, gt, np.array([r["unit"] for r in rows]))
    return {"cutoff": GRID[j], "j": j, "band_pp": q, "n_calib": len(rows),
            "calib_mae": float(np.abs(R[:, j] - gt).mean())}


def clustered(rows: list[dict], fn, rng) -> tuple[float, float]:
    keys = sorted({r["cluster"] for r in rows})
    by = {k: [r for r in rows if r["cluster"] == k] for k in keys}
    vals = []
    for _ in range(N_BOOT):
        pick = rng.choice(len(keys), len(keys), replace=True)
        vals.append(fn([r for j in pick for r in by[keys[j]]]))
    vals = [v for v in vals if v is not None and not math.isnan(v)]
    return float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))


def mae(rows, arm):
    return float(np.mean([abs(r[arm] - r["gt"]) for r in rows])) if rows else float("nan")


def bias(rows, arm):
    return float(np.mean([r[arm] - r["gt"] for r in rows])) if rows else float("nan")


def dense(rows):
    return [r for r in rows if LO <= r["gt"] <= HI]


def criteria(test: list[dict], arm: str, rng) -> dict:
    d = dense(test)
    a4 = [r for r in test if r["gt"] >= LO]
    calls = [r[f"{arm}_call"] for r in a4]
    kept = [(c, r) for c, r in zip(calls, a4) if c != "review"]
    agree = sum((c == "passage") == (r["gt"] >= T) for c, r in kept)
    has_band = [r for r in test if r[f"{arm}_band"] is not None]
    cover = sum(abs(r[arm] - r["gt"]) <= r[f"{arm}_band"] for r in has_band)
    out = {"n": len(test), "n_60_90": len(d), "n_60_100": len(a4), "n_ge_T": sum(r["gt"] >= T for r in a4),
           "B1_mae": mae(test, arm), "B1_ci": clustered(test, lambda x: mae(x, arm), rng),
           "B2_mae": mae(d, arm), "B2_ci": clustered(d, lambda x: mae(x, arm), rng) if d else None,
           "B3_bias": bias(d, arm), "B3_ci": clustered(d, lambda x: bias(x, arm), rng) if d else None,
           "B4_passage": calls.count("passage"), "B4_continue": calls.count("continue"),
           "B4_review": calls.count("review"), "B4_decided": len(kept), "B4_agree": agree,
           "B4_agreement": agree / len(kept) if kept else None,
           "B4_ready_called_continue": sum(c == "continue" and r["gt"] >= T for c, r in zip(calls, a4)),
           "B5_n": len(has_band), "B5_covered": cover, "B5_coverage": cover / len(has_band) if has_band else None,
           "review_share": sum(r[f"{arm}_call"] == "review" for r in test) / len(test)}
    m2 = len(d) >= MIN_IMAGES
    m4 = len(a4) >= MIN_IMAGES
    out["verdicts"] = {
        "B1": "pass" if out["B1_mae"] <= MAE_MAX else "fail",
        "B2": ("pass" if out["B2_mae"] <= MAE_MAX else "fail") if m2 else "not measurable",
        "B3": ("pass" if abs(out["B3_bias"]) <= BIAS_MAX else "fail") if m2 else "not measurable",
        "B4": ("pass" if out["B4_agreement"] is not None and out["B4_agreement"] >= AGREE_MIN else "fail") if m4 else "not measurable",
        "B5": ("pass" if out["B5_coverage"] >= COVER_MIN else "fail") if has_band else "no band"}
    return out


def cmd_score(a):
    if "\n## Results" in open(OUT_MD).read():
        sys.exit("results section already present; the test is scored once")
    its = loaded()
    ft_folds(its)
    cal = calibrated_setups(its)
    C = json.load(open(CURVES))
    assert C["grid"] == GRID
    rows = []
    for i in its:
        r = {k: i[k] for k in ("name", "setup", "unit", "split", "gt")} | {"fold": i.get("fold"), "cluster": i["setup"] + "/" + i["unit"]}
        r["curve_Z"] = curve_of(C, "Z", i["name"])
        if i["setup"] in cal:
            r["curve_R"] = curve_of(C, "R", i["name"])
            r["curve_F"] = curve_of(C, "F", i["name"])
        rows.append(r)
    profiles = {}
    for s in cal:
        calib = [r for r in rows if r["setup"] == s and r["split"] == "calib"]
        for arm, key in (("C", "curve_Z"), ("R", "curve_R"), ("F", "curve_F")):
            profiles[(arm, s)] = fit_setup([{"curve": r[key], "gt": r["gt"], "unit": r["unit"]} for r in calib])
    j0 = GRID.index(0.0)
    for r in rows:
        r["Z"], r["Z_band"] = float(r["curve_Z"][j0]), None
        r["Z_call"] = uncalibrated_call(r["Z"])
        if r["setup"] in cal:
            for arm, key in (("C", "curve_Z"), ("R", "curve_R"), ("F", "curve_F")):
                pr = profiles[(arm, r["setup"])]
                r[arm], r[f"{arm}_band"] = float(r[key][pr["j"]]), pr["band_pp"]
                r[f"{arm}_call"] = cal_call(r[arm], pr["band_pp"])
    test = [r for r in rows if r["split"] == "test" and r["setup"] in cal]
    rng = np.random.default_rng(0)
    res = {"generated_by": "scripts/confluency_mcellseg.py score",
           "scored_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"), "computed_on": C["environment"],
           "fine_tuned_runs": {k: {f: m.get(f) for f in ("run", "n", "weights_sha256", "seconds")}
                               for k, m in C["manifests"].items()},
           "calibrated_setups": cal,
           "profiles": {f"{arm}/{s}": {k: v for k, v in p.items() if k != "j"} for (arm, s), p in profiles.items()},
           "criteria": {arm: criteria(test, arm, rng) for arm in ("Z", "C", "F", "R")}}
    d = dense(test)
    res["contrasts"] = {}
    for arm in ("F", "R"):
        diff = mae(d, "C") - mae(d, arm)
        res["contrasts"][f"C-{arm}"] = {"mae_60_90_diff": diff,
                                        "ci": clustered(d, lambda x: mae(x, "C") - mae(x, arm), rng),
                                        "mae_all_diff": mae(test, "C") - mae(test, arm),
                                        "ci_all": clustered(test, lambda x: mae(x, "C") - mae(x, arm), rng)}
    res["per_setup"] = {s: {arm: {"n": len(g := [r for r in test if r["setup"] == s]), "mae": mae(g, arm), "bias": bias(g, arm),
                                  "n_60_90": len(dense(g)), "mae_60_90": mae(dense(g), arm) if dense(g) else None,
                                  "bias_60_90": bias(dense(g), arm) if dense(g) else None}
                            for arm in ("Z", "C", "F", "R")} for s in cal}
    small = [r for r in rows if r["setup"] not in cal and r["split"] == "test"]
    res["uncalibrated_setups"] = {"n": len(small), "mae": mae(small, "Z"), "bias": bias(small, "Z"),
                                  "n_60_90": len(dense(small)), "mae_60_90": mae(dense(small), "Z") if dense(small) else None,
                                  "bias_60_90": bias(dense(small), "Z") if dense(small) else None,
                                  "calls": {c: sum(r["Z_call"] == c for r in small) for c in ("continue", "review")}}
    lz = lazy_items()
    lrows = [{"name": i["name"], "unit": i["unit"], "split": i["split"], "gt": i["gt"], "cluster": i["unit"],
              "curve": curve_of(C, "S", i["name"])} for i in lz]
    lp = fit_setup([r for r in lrows if r["split"] == "calib"])
    for r in lrows:
        r["S"] = float(r["curve"][lp["j"]])
        r["S0"] = float(r["curve"][j0])
    lt = [r for r in lrows if r["split"] == "test"]
    res["supplementary_cytosmart"] = {"profile": {k: v for k, v in lp.items() if k != "j"}, "n_test": len(lt),
                                      "mae": mae(lt, "S"), "bias": bias(lt, "S"), "mae_cut0": mae(lt, "S0"),
                                      "bias_cut0": bias(lt, "S0"),
                                      "covered": sum(abs(r["S"] - r["gt"]) <= lp["band_pp"] for r in lt) if lp["band_pp"] else None,
                                      "n_60_90": len(dense(lt))}
    with open(OUT_CSV, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["name", "setup", "unit", "split", "fold", "gt_pct"] + [f"{a}_{k}" for a in ("Z", "C", "F", "R") for k in ("reading", "band", "call")])
        for r in rows:
            w.writerow([r["name"], r["setup"], r["unit"], r["split"], r["fold"] or "", round(r["gt"], 3)] +
                       [("" if r.get(f"{a}{k}") is None else (round(r[f"{a}{k}"], 3) if isinstance(r[f"{a}{k}"], float) else r[f"{a}{k}"]))
                        for a in ("Z", "C", "F", "R") for k in ("", "_band", "_call")])
    json.dump(res, open(OUT_JSON, "w"), indent=1, default=float)
    write_md(res)
    print(json.dumps({k: res[k] for k in ("criteria", "contrasts")}, indent=1, default=float)[:6000])


def fmt(v, s=".2f"):
    return "—" if v is None else format(v, s)


def write_md(res: dict) -> None:
    c = res["criteria"]
    lines = ["", "## Results", "",
             f"Scored {res['scored_at']} by `scripts/confluency_mcellseg.py score`; one row per image in `{OUT_CSV}`.", "",
             f"Test images in the calibrated setups ({', '.join(res['calibrated_setups'])}): {c['C']['n']}; "
             f"{c['C']['n_60_90']} at 60–90%, {c['C']['n_60_100']} at 60–100%, {c['C']['n_ge_T']} at or above 80%.", "",
             "| | " + " | ".join(f"{a}: {ARMS[a]}" for a in ("Z", "C", "F", "R")) + " |",
             "|---|---|---|---|---|"]

    def row(label, f):
        lines.append(f"| {label} | " + " | ".join(f(c[a]) for a in ("Z", "C", "F", "R")) + " |")

    row("B1 MAE, all test images (95% interval)", lambda x: f"{x['B1_mae']:.2f} ({x['B1_ci'][0]:.2f}–{x['B1_ci'][1]:.2f}) **{x['verdicts']['B1']}**")
    row("B2 MAE, 60–90%", lambda x: f"{x['B2_mae']:.2f} ({x['B2_ci'][0]:.2f}–{x['B2_ci'][1]:.2f}) **{x['verdicts']['B2']}**")
    row("B3 mean signed error, 60–90%", lambda x: f"{x['B3_bias']:+.2f} ({x['B3_ci'][0]:+.2f} to {x['B3_ci'][1]:+.2f}) **{x['verdicts']['B3']}**")
    row("B4 calls at T = 80 on 60–100% (passage / continue / review; agree of decided)",
        lambda x: f"{x['B4_passage']} / {x['B4_continue']} / {x['B4_review']}; {x['B4_agree']} of {x['B4_decided']} **{x['verdicts']['B4']}**")
    row("B5 band coverage, all test images", lambda x: (f"{x['B5_covered']} of {x['B5_n']} ({100 * x['B5_coverage']:.1f}%) **{x['verdicts']['B5']}**"
                                                      if x["B5_coverage"] is not None else "no band"))
    row("ready (≥ 80%) called continue", lambda x: str(x["B4_ready_called_continue"]))
    row("share of test images sent to a person", lambda x: f"{100 * x['review_share']:.1f}%")
    lines += ["", "Contrasts on the same test images (positive = the second arm reads closer to the experts; 95% interval, units resampled):", ""]
    for k, v in res["contrasts"].items():
        lines.append(f"- MAE({k.split('-')[0]}) − MAE({k.split('-')[1]}): 60–90% {v['mae_60_90_diff']:+.2f} pp "
                     f"({v['ci'][0]:+.2f} to {v['ci'][1]:+.2f}); all test images {v['mae_all_diff']:+.2f} pp "
                     f"({v['ci_all'][0]:+.2f} to {v['ci_all'][1]:+.2f}).")
    lines += ["", "Profiles fitted on the calibration images (cutoff, band, n):", ""]
    for k, p in res["profiles"].items():
        lines.append(f"- {k}: cutoff {p['cutoff']:+.1f}, band ±{fmt(p['band_pp'])} pp, n = {p['n_calib']}, calibration MAE {p['calib_mae']:.2f}")
    lines += ["", "Per setup (test images; MAE / bias, then the same at 60–90%):", "",
              "| setup | n | Z | C | F | R | n 60–90 | Z | C | F | R |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for s, v in res["per_setup"].items():
        lines.append(f"| {s} | {v['C']['n']} | " + " | ".join(f"{v[a]['mae']:.2f} / {v[a]['bias']:+.2f}" for a in ("Z", "C", "F", "R")) +
                     f" | {v['C']['n_60_90']} | " + " | ".join(
                         (f"{v[a]['mae_60_90']:.2f} / {v[a]['bias_60_90']:+.2f}" if v[a]["mae_60_90"] is not None else "—") for a in ("Z", "C", "F", "R")) + " |")
    u = res["uncalibrated_setups"]
    lines += ["", f"Uncalibrated setups (too few calibration images; read at 0.0, no band): {u['n']} test images, "
              f"MAE {u['mae']:.2f}, bias {u['bias']:+.2f}; {u['n_60_90']} at 60–90%"
              + (f" (MAE {u['mae_60_90']:.2f}, bias {u['bias_60_90']:+.2f})" if u["mae_60_90"] is not None else "")
              + f"; calls {u['calls']['continue']} continue, {u['calls']['review']} review.", ""]
    s = res["supplementary_cytosmart"]
    lines += [f"Supplementary, MSC on an incubator imager (lazy masks): {s['n_test']} test images, calibrated cutoff "
              f"{s['profile']['cutoff']:+.1f}: MAE {s['mae']:.2f}, bias {s['bias']:+.2f} (at 0.0: {s['mae_cut0']:.2f}, "
              f"{s['bias_cut0']:+.2f}); band ±{fmt(s['profile']['band_pp'])} covers {fmt(s['covered'], 'd') if s['covered'] is not None else '—'} "
              f"of {s['n_test']}; {s['n_60_90']} test images at 60–90%.", ""]
    with open(OUT_MD, "a") as fh:
        fh.write("\n".join(lines))


OUT_PNG = os.path.join("results", "confluency_mcellseg.png")
SHORT = {"Z": "zero-shot, cutoff 0.0", "C": "zero-shot + calibration", "F": "fine-tuned + calibration",
         "R": "rescaled + calibration"}


def cmd_figure(a):
    """Reading vs expert confluency on the test images of the calibrated setups, one panel per arm, with the
    60–90% range shaded and the 80% target. From results/confluency_mcellseg.{csv,json}; computes nothing."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import pandas as pd
    df = pd.read_csv(OUT_CSV)
    res = json.load(open(OUT_JSON))
    d = df[(df.split == "test") & df.setup.isin(res["calibrated_setups"])]
    colours = {"cd7_huvec_dic": "#2563eb", "lsm_hek_1024": "#dc2626", "oir_1024": "#059669", "lsm_2796": "#9333ea"}
    fig, axes = plt.subplots(1, 4, figsize=(16.5, 4.6))
    x = np.linspace(0, 100, 2)
    for ax, arm in zip(axes, ("Z", "C", "F", "R")):
        c = res["criteria"][arm]
        ax.axvspan(LO, HI, color="#f59e0b", alpha=0.08, lw=0)
        ax.plot(x, x, color="#111", lw=0.8)
        for s, g in d.groupby("setup"):
            ax.scatter(g.gt_pct, g[f"{arm}_reading"], s=14, color=colours.get(s, "#555"), alpha=0.8, label=s)
        ax.axhline(T, color="#f59e0b", lw=0.8, ls="--")
        ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.set_aspect("equal")
        ax.set_xlabel("expert confluency (%)")
        ax.set_title(f"{arm}: {SHORT[arm]}\nall: MAE {c['B1_mae']:.1f} pp   60–90%: MAE {c['B2_mae']:.1f}, bias {c['B3_bias']:+.1f}",
                     fontsize=8.5)
    axes[0].set_ylabel("reading (%)")
    axes[0].legend(loc="upper left", fontsize=7, frameon=False)
    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=140)
    print("wrote", OUT_PNG)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for c in ("count", "maps", "train", "ftmaps", "curves", "score", "figure"):
        sub.add_parser(c)
    a = ap.parse_args()
    {"count": cmd_count, "maps": cmd_maps, "train": cmd_train, "ftmaps": cmd_ftmaps, "curves": cmd_curves,
     "score": cmd_score, "figure": cmd_figure}[a.cmd](a)


if __name__ == "__main__":
    main()
