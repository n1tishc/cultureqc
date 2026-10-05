"""
Confluency in the passage range on dense regions of held-out MSC images.

The method and the pass rules are pre-registered in
results/confluency_dense_tiles.md and committed before any map is read here.

    .venv/bin/python scripts/confluency_dense_tiles.py count    # expert masks only; no map read
    .venv/bin/python scripts/confluency_dense_tiles.py score    # reads the cached maps once

`score` crops the full-frame maps cached by scripts/confluency_profiles.py
(cache/probmaps_full/msc/) to each quarter, reads it at the cutoff and band of
the fold that leaves its population out (results/confluency_profiles.json),
and appends the results section to the .md once.

Outputs: results/confluency_dense_tiles.md (results section),
results/confluency_dense_tiles.csv (one row per included region),
results/confluency_dense_tiles.json.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone

import cv2
import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))
os.chdir(REPO)

from confluency_profiles import msc_items, prob_map, stats  # noqa: E402

LO, HI = 60.0, 90.0
T = 80.0
MIN_IMAGES = 10
N_BOOT = 10_000
MAE_MAX, BIAS_MAX = 5.0, 3.0
SHIPPED = 0.0
POPS = ["218-4", "218-5", "218-6"]       # sorted units: the fold order of confluency_profiles.folds
OUT_MD = os.path.join("results", "confluency_dense_tiles.md")
OUT_CSV = os.path.join("results", "confluency_dense_tiles.csv")
OUT_JSON = os.path.join("results", "confluency_dense_tiles.json")
PROFILES = os.path.join("results", "confluency_profiles.json")


def mask(i: dict) -> np.ndarray:
    m = cv2.imread(i["mask"], cv2.IMREAD_GRAYSCALE)
    assert m is not None, i["mask"]
    return m > 0


def cells(shape, g: int):
    h, w = shape
    th, tw = h // g, w // g
    for a in range(g):
        for b in range(g):
            yield a * g + b, slice(a * th, (a + 1) * th), slice(b * tw, (b + 1) * tw)


def regions(items, g: int, lo: float, hi: float) -> list[dict]:
    """Every grid cell whose expert-mask confluency is in [lo, hi]; masks only."""
    out = []
    for i in items:
        m = mask(i)
        for k, ys, xs in cells(m.shape, g):
            gt = float(m[ys, xs].mean() * 100)
            if lo <= gt <= hi:
                out.append({"name": i["name"], "pop": i["group"], "grid": g, "cell": k, "gt": gt,
                            "ys": ys, "xs": xs, "item": i})
    return out


def fold_profiles() -> dict:
    folds = json.load(open(PROFILES))["results"]["msc_phase"]["folds"]
    assert len(folds) == len(POPS)
    return {p: f for p, f in zip(POPS, folds)}


def boot(rows: list[dict], fn, rng) -> tuple[float, float]:
    names = sorted({r["name"] for r in rows})
    by = {n: [r for r in rows if r["name"] == n] for n in names}
    vals = []
    for _ in range(N_BOOT):
        pick = rng.choice(len(names), len(names), replace=True)
        vals.append(fn([r for j in pick for r in by[names[j]]]))
    return float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))


def mae(rows, key="reading"):
    return float(np.mean([abs(r[key] - r["gt"]) for r in rows]))


def bias(rows, key="reading"):
    return float(np.mean([r[key] - r["gt"] for r in rows]))


def cmd_count(a):
    items = msc_items()
    for g in (2, 4):
        rs = regions(items, g, LO, HI)
        pops = {p: sum(r["pop"] == p for r in rs) for p in POPS}
        print(f"{g}x{g}: {len(rs)} regions at {LO:.0f}-{HI:.0f}% from {len({r['name'] for r in rs})} images; {pops}")


def read(rs: list[dict], prof: dict) -> None:
    cache = {}
    for r in rs:
        i = r["item"]
        if i["name"] not in cache:
            cache.clear()
            p = prob_map("msc", i["name"], i["path"])
            assert p.shape == mask(i).shape, (i["name"], p.shape)
            cache[i["name"]] = p
        p = cache[i["name"]][r["ys"], r["xs"]]
        f = prof[r["pop"]]
        r["cutoff"], r["band"] = f["cutoff"], f["band_pp"]
        r["reading"] = float((p > f["cutoff"]).mean() * 100)
        r["reading0"] = float((p > SHIPPED).mean() * 100)


def summary(rs: list[dict], rng, key="reading") -> dict:
    n_img = len({r["name"] for r in rs})
    out = {"n_regions": len(rs), "n_images": n_img,
           "per_population": {p: sum(r["pop"] == p for r in rs) for p in POPS},
           "measurable": n_img >= MIN_IMAGES}
    if not rs:
        return out
    out.update(mae=mae(rs, key), bias=bias(rs, key),
               mae_ci=boot(rs, lambda x: mae(x, key), rng), bias_ci=boot(rs, lambda x: bias(x, key), rng),
               stats=stats(np.array([r[key] for r in rs]), np.array([r["gt"] for r in rs])),
               by_population={p: {"n": sum(r["pop"] == p for r in rs),
                                  "mae": mae([r for r in rs if r["pop"] == p], key),
                                  "bias": bias([r for r in rs if r["pop"] == p], key)}
                              for p in POPS if any(r["pop"] == p for r in rs)})
    return out


def passage(rs: list[dict]) -> dict:
    calls = ["passage" if r["reading"] - r["band"] >= T else "continue" if r["reading"] + r["band"] < T else "review"
             for r in rs]
    kept = [(c, r) for c, r in zip(calls, rs) if c != "review"]
    agree = sum((c == "passage") == (r["gt"] >= T) for c, r in kept)
    return {"n": len(rs), "n_images": len({r["name"] for r in rs}), "review": calls.count("review"),
            "passage": calls.count("passage"), "continue": calls.count("continue"),
            "decided": len(kept), "agree": agree, "agreement": (agree / len(kept)) if kept else None,
            "gt_at_or_above_T": sum(r["gt"] >= T for r in rs)}


def f2(v, spec=".2f"):
    return "—" if v is None else format(v, spec)


def write_md(res: dict) -> None:
    text = open(OUT_MD).read()
    if "\n## Results" in text:
        sys.exit("results section already present; the test is scored once")
    p, s0, s4, cov, pc = res["primary"], res["shipped"], res["grid4"], res["coverage"], res["passage_80"]
    d2 = "pass" if p["mae"] <= MAE_MAX else "fail"
    d3 = "pass" if abs(p["bias"]) <= BIAS_MAX else "fail"
    if not p["measurable"]:
        d2 = d3 = "not measurable"
    pops = ", ".join(f"{k}: n = {v['n']}, MAE {v['mae']:.2f}, bias {v['bias']:+.2f}" for k, v in p["by_population"].items())
    lines = [
        "", "## Results", "",
        f"Scored {res['scored_at']} by `scripts/confluency_dense_tiles.py score`; one row per region in "
        f"`{OUT_CSV}`.", "",
        f"Included: {p['n_regions']} quarters (500 × 500 px) with ground truth {LO:.0f}–{HI:.0f}%, from "
        f"{p['n_images']} images (populations 218-4 / 218-5 / 218-6: "
        f"{' / '.join(str(p['per_population'][k]) for k in POPS)}).", "",
        "| # | measure | result (95% interval, images resampled) | limit | verdict |",
        "|---|---|---|---|---|",
        f"| D2 | MAE | {p['mae']:.2f} pp ({p['mae_ci'][0]:.2f}–{p['mae_ci'][1]:.2f}) | ≤ {MAE_MAX:.0f} pp | {d2} |",
        f"| D3 | mean signed error | {p['bias']:+.2f} pp ({p['bias_ci'][0]:+.2f} to {p['bias_ci'][1]:+.2f}) | "
        f"\\|bias\\| ≤ {BIAS_MAX:.0f} pp | {d3} |", "",
        f"Per population, at the fold cutoff: {pops}. Median absolute error {p['stats']['median_ae']:.2f} pp; "
        f"{p['stats']['over10']} of {p['n_regions']} off by more than 10 pp.", "",
        "Secondary (not judged):", "",
        f"- Shipped cutoff 0.0 on the same quarters: MAE {s0['mae']:.2f} pp ({s0['mae_ci'][0]:.2f}–"
        f"{s0['mae_ci'][1]:.2f}), bias {s0['bias']:+.2f} pp.",
        f"- Band coverage: {cov['covered']} of {cov['n']} quarters ({100 * cov['share']:.1f}%) read within their "
        "fold's band (bands measured on whole images; a quarter is a smaller, noisier field).",
        f"- Passage call at T = 80% on quarters with ground truth 60–100% ({pc['n']} from {pc['n_images']} images, "
        f"{pc['gt_at_or_above_T']} at or above 80%): passage {pc['passage']}, continue {pc['continue']}, "
        f"review {pc['review']}; of the {pc['decided']} not sent to review, {pc['agree']} agree with ground truth"
        + (f" ({100 * pc['agreement']:.1f}%)." if pc["agreement"] is not None else "."),
        f"- Field size, 4 × 4 grid (250 × 250 px): {s4['n_regions']} tiles from {s4['n_images']} images, "
        f"MAE {s4['mae']:.2f} pp ({s4['mae_ci'][0]:.2f}–{s4['mae_ci'][1]:.2f}), bias {s4['bias']:+.2f} pp "
        f"({s4['bias_ci'][0]:+.2f} to {s4['bias_ci'][1]:+.2f}).", "",
    ]
    with open(OUT_MD, "a") as fh:
        fh.write("\n".join(lines))


def cmd_score(a):
    if "\n## Results" in open(OUT_MD).read():
        sys.exit("results section already present; the test is scored once")
    items = msc_items()
    assert len(items) == 320, len(items)
    prof = fold_profiles()
    for p in POPS:
        n_pop = sum(i["group"] == p for i in items)
        assert prof[p]["n_calib"] == len(items) - n_pop, (p, prof[p]["n_calib"], n_pop)
    rng = np.random.default_rng(0)
    q2 = regions(items, 2, LO, HI)
    a4 = regions(items, 2, LO, 100.0)
    q4 = regions(items, 4, LO, HI)
    for rs in (q2, a4, q4):
        read(rs, prof)
    covered = sum(abs(r["reading"] - r["gt"]) <= r["band"] for r in q2)
    res = {"generated_by": "scripts/confluency_dense_tiles.py score",
           "scored_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
           "primary": summary(q2, rng), "shipped": summary(q2, rng, key="reading0"),
           "grid4": summary(q4, rng),
           "coverage": {"n": len(q2), "covered": covered, "share": covered / len(q2) if q2 else None},
           "passage_80": passage(a4)}
    with open(OUT_CSV, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["name", "population", "grid", "cell", "gt_pct", "cutoff", "reading_pct", "reading_cut0_pct", "band_pp"])
        for r in q2 + q4:
            w.writerow([r["name"], r["pop"], r["grid"], r["cell"], round(r["gt"], 3), r["cutoff"],
                        round(r["reading"], 3), round(r["reading0"], 3), round(r["band"], 4)])
    json.dump(res, open(OUT_JSON, "w"), indent=1)
    write_md(res)
    print(json.dumps({k: res[k] for k in ("primary", "coverage", "passage_80")}, indent=1, default=str)[:3000])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("count")
    sub.add_parser("score")
    a = ap.parse_args()
    {"count": cmd_count, "score": cmd_score}[a.cmd](a)


if __name__ == "__main__":
    main()
