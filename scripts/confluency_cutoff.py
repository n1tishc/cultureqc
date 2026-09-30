"""
Cellpose-SAM cell-probability cutoff, calibrated on EVICAN images outside the
reported evaluation subset.

Question: results/confluency_real_summary.md found cultureQC under-reads real
confluency on 30 of 33 EVICAN images (mean signed error -8.32 pp) and named the
probability cutoff (culture/seg.py, thr=0.0, the Cellpose default) as the
likeliest cause. Does a cutoff chosen on other images remove the bias on the 33?

Rule, fixed in this file before the full-resolution maps were scored:
    grid        -4.0, -3.5, ..., +1.0 (logit)
    calibration the 65 eval2019 images not in results/confluency_real.csv
                (includes the 6-image tuning split and 15_Caco-2.jpg)
    pick        the grid value with the lowest calibration MAE; no tie rule
    evaluation  the 33 images of results/confluency_real.csv, reported at 0.0
                and at the pick; the full evaluation curve is printed for
                disclosure and not used to choose

Disclosure: the cutoff hypothesis came from the error analysis on the 33, and a
quarter-resolution sweep over the cached maps (the same grid, calibration and
evaluation curves) was looked at before this script existed.

Maps: full-resolution flows[2] from the call culture.seg.cpsam_confluency
makes, stored as float16 under cache/probmaps_full/ (gitignored) and computed
if missing. CULTUREQC_DEVICE=mps runs it on Apple's GPU.

Downstream (context, no decision): the held-out C2C12 frames scored from the
cache's quarter-resolution maps at 0.0 and at the pick, to show what changing
the default would move (anomaly bins, confidence floor, frames reaching a
target).

    .venv/bin/python scripts/confluency_cutoff.py

Outputs: results/confluency_cutoff.csv, results/confluency_cutoff.md
"""

from __future__ import annotations

import csv
import json
import os
import sys
from datetime import datetime, timezone

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from eval_confluency_real import IMAGES_DIR, load_coco_gt  # noqa: E402

GRID = [round(-4.0 + 0.5 * i, 1) for i in range(11)]
BAND = 1.0          # culture.seg.cpsam_confluency default
FLOOR = 0.30        # culture.rules default confidence floor
MAPS = os.path.join("cache", "probmaps_full")
LIVECELL_DIR = os.path.join("data", "sources", "livecell")
# Dense LIVECell test frames (70/80/90% GT, two lines). LIVECell is in
# Cellpose-SAM's training set, so these only show over-read risk at high
# density; they are not a held-out accuracy estimate.
LIVECELL_DENSE = [
    ("a172", "A172_Phase_C7_2_01d16h00m_2.tif"), ("a172", "A172_Phase_C7_2_02d00h00m_3.tif"),
    ("a172", "A172_Phase_C7_1_03d00h00m_4.tif"), ("skov3", "SKOV3_Phase_E4_2_01d16h00m_4.tif"),
    ("skov3", "SKOV3_Phase_E4_1_01d16h00m_2.tif"), ("skov3", "SKOV3_Phase_F4_2_02d08h00m_1.tif"),
]
OUT_CSV = os.path.join("results", "confluency_cutoff.csv")
OUT_MD = os.path.join("results", "confluency_cutoff.md")


def prob_map(src: str, name: str, path: str) -> np.ndarray:
    dst = os.path.join(MAPS, src, name + ".npz")
    if not os.path.exists(dst):
        import cv2
        from culture.seg import _get_model
        img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        _, flows, _ = _get_model().eval(img, diameter=None, channels=[0, 0])
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        np.savez_compressed(dst, prob=flows[2].astype(np.float16))
    return np.load(dst)["prob"].astype(np.float32)


def pct(p, t):
    return float((p > t).mean() * 100)


def confidence(p, t):
    return float(np.clip(1 - 4 * (np.abs(p - t) < BAND).mean(), 0, 1))


def mae(rows, t):
    return float(np.mean([abs(pct(r["p"], t) - r["gt"]) for r in rows]))


def summary(rows, t):
    e = np.array([pct(r["p"], t) - r["gt"] for r in rows])
    return {"mae": float(np.abs(e).mean()), "median_ae": float(np.median(np.abs(e))), "bias": float(e.mean()),
            "over10": int((np.abs(e) > 10).sum()), "over15": int((np.abs(e) > 15).sum()), "n": len(rows)}


def livecell_gt(line: str, name: str) -> float | None:
    """Union of the image's polygons, rasterised as load_coco_gt does for EVICAN
    (cv2.fillPoly, boundary pixels included), so both GTs are the same measure."""
    import cv2
    ann = os.path.join(LIVECELL_DIR, "annotations", f"{line}_test.json")
    if not os.path.exists(ann):
        return None
    d = json.load(open(ann))
    img = next(i for i in d["images"] if i["file_name"] == name)
    m = np.zeros((img["height"], img["width"]), np.uint8)
    for a in d["annotations"]:
        if a["image_id"] == img["id"]:
            for poly in a["segmentation"]:
                pts = np.clip(np.array(poly, dtype=np.float32).reshape(-1, 2), 0, None).astype(np.int32)
                cv2.fillPoly(m, [pts], 1)
    return float(m.mean() * 100)


def c2c12_downstream(t_pick):
    import pandas as pd
    im = pd.read_parquet("cache/images.parquet")
    split = pd.read_csv("results/replay_fleet_split.csv")
    held = set(split[(split.kind == "base") & (split.split == "heldout")].sequence_id)
    frames = im[(im.dataset == "c2c12") & im.sequence_id.isin(held)]
    bin_of = lambda v: 0 if v < 20 else (1 if v < 40 else 2)  # anomaly banks: 0-20, 20-40, 40-100
    out = {t: {"pct": [], "conf": []} for t in (0.0, t_pick)}
    for sha in frames.image_sha256:
        p = np.load(f"cache/probmaps/{sha}.npz")["prob_x1000"].astype(np.float32) / 1000
        for t in out:
            out[t]["pct"].append(pct(p, t))
            out[t]["conf"].append(confidence(p, t))
    a, b = np.array(out[0.0]["pct"]), np.array(out[t_pick]["pct"])
    rows = []
    for t in out:
        v, c = np.array(out[t]["pct"]), np.array(out[t]["conf"])
        rows.append({"t": t, "median": float(np.median(v)), "max": float(v.max()), "below_floor": int((c < FLOOR).sum()),
                     "ge50": int((v >= 50).sum()), "ge80": int((v >= 80).sum())})
    moved = int(sum(bin_of(x) != bin_of(y) for x, y in zip(a, b)))
    return {"n": len(frames), "sequences": int(frames.sequence_id.nunique()), "rows": rows, "moved": moved,
            "shift_median": float(np.median(b - a)), "shift_p90": float(np.quantile(b - a, 0.9))}


def main():
    gt = {v["file_name"]: v for v in load_coco_gt().values()}
    evald = {r["file_name"] for r in csv.DictReader(open(os.path.join("results", "confluency_real.csv")))}
    rows = []
    for name in sorted(gt):
        rows.append({"file": name, "gt": gt[name]["gt_pct"], "tier": gt[name]["tier"],
                     "split": "eval33" if name in evald else "calib65",
                     "p": prob_map("evican", name, os.path.join(IMAGES_DIR, name))})
    cal = [r for r in rows if r["split"] == "calib65"]
    ev = [r for r in rows if r["split"] == "eval33"]
    assert len(cal) == 65 and len(ev) == 33, (len(cal), len(ev))

    curve = [(t, mae(cal, t), mae(ev, t)) for t in GRID]
    t_pick = min(curve, key=lambda c: c[1])[0]
    print("cutoff  calib65 MAE  eval33 MAE")
    for t, mc, me in curve:
        print(f"{t:+5.1f}   {mc:6.2f}       {me:6.2f}{'   <- pick' if t == t_pick else ''}")

    s_ev = {t: summary(ev, t) for t in (0.0, t_pick)}
    s_cal = {t: summary(cal, t) for t in (0.0, t_pick)}
    bands = [(0, 20), (20, 40), (40, 70)]
    band_rows = []
    for lo, hi in bands:
        g = [r for r in ev if lo <= r["gt"] < hi]
        if g:
            band_rows.append((f"{lo}-{hi}%", len(g), mae(g, 0.0), mae(g, t_pick)))

    with open(OUT_CSV, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["file_name", "split", "tier", "gt_pct", "pct_cut0", "conf_cut0", f"pct_cut{t_pick}", f"conf_cut{t_pick}"])
        for r in rows:
            w.writerow([r["file"], r["split"], r["tier"], round(r["gt"], 3), round(pct(r["p"], 0.0), 2),
                        round(confidence(r["p"], 0.0), 3), round(pct(r["p"], t_pick), 2), round(confidence(r["p"], t_pick), 3)])

    worst = sorted(ev, key=lambda r: -abs(pct(r["p"], t_pick) - r["gt"]))[:6]
    swing = sorted(rows, key=lambda r: -abs(pct(r["p"], t_pick) - pct(r["p"], 0.0)))[:5]
    caco = next(r for r in rows if r["file"] == "15_Caco-2.jpg")
    ht29 = next(r for r in rows if r["file"] == "48_HT29.jpg")

    dense = []
    for line, name in LIVECELL_DENSE:
        path = os.path.join(LIVECELL_DIR, "images", "livecell_test_images", name)
        g = livecell_gt(line, name)
        if g is None or not os.path.exists(path):
            continue
        p = prob_map("livecell", name, path)
        dense.append((name, g, pct(p, 0.0), pct(p, t_pick), confidence(p, 0.0), confidence(p, t_pick)))

    down = c2c12_downstream(t_pick)

    L = []
    L.append("# Cellpose-SAM probability cutoff, calibrated off the evaluation subset\n")
    L.append(f"Generated {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')} by `scripts/confluency_cutoff.py`. "
             "EVICAN eval2019 (Parekh et al., *Bioinformatics* 36(12):3863, 2020; CC BY 4.0), 98 images with expert `Cell` masks; "
             "GT confluency as in `results/confluency_real_summary.md`. Full-resolution Cellpose-SAM (cpsam_v2) probability maps, "
             "the call `culture/seg.py::cpsam_confluency` makes. Nothing here changes the shipped default (cutoff 0.0).\n")
    L.append("## Rule\n")
    L.append("Fixed in the script before the full-resolution maps were scored: grid -4.0 to +1.0 logit in 0.5 steps; "
             "calibration = the 65 eval2019 images not in `results/confluency_real.csv` (includes the 6-image tuning split and 15_Caco-2.jpg); "
             "pick = lowest calibration MAE, no tie rule; evaluation = the 33 images of `results/confluency_real.csv`.\n")
    L.append("Disclosure: the cutoff hypothesis came from the error analysis on the 33, and a quarter-resolution sweep of the cached maps, "
             "showing the evaluation curve too, was seen before the rule was written. The 33 are all under 500,000 px "
             "(the original subset's time budget); 28 of the 65 calibration images are larger. "
             "The same scratch sweep also tried a linear correction fitted on the 65 (evaluation MAE 6.76 pp, quarter resolution); "
             "it is not part of this rule.\n")
    L.append("## Curve\n")
    L.append("| cutoff (logit) | calibration MAE, n=65 (pp) | evaluation MAE, n=33 (pp) |\n|---|---:|---:|")
    for t, mc, me in curve:
        L.append(f"| {t:+.1f}{' (pick)' if t == t_pick else (' (shipped)' if t == 0.0 else '')} | {mc:.2f} | {me:.2f} |")
    L.append("")
    L.append("## Result on the 33 held-out images\n")
    L.append("| | shipped, cutoff 0.0 | calibrated, cutoff %+.1f |\n|---|---:|---:|" % t_pick)
    for k, lab in [("mae", "MAE (pp)"), ("median_ae", "median absolute error (pp)"), ("bias", "mean signed error (pp)"),
                   ("over10", "images off by more than 10 pp"), ("over15", "images off by more than 15 pp")]:
        f0, f1 = s_ev[0.0][k], s_ev[t_pick][k]
        L.append(f"| {lab} | {f0:.2f} | {f1:.2f} |" if isinstance(f0, float) else f"| {lab} | {f0} of 33 | {f1} of 33 |")
    L.append("")
    L.append("By ground-truth band (evaluation images):\n")
    L.append("| GT band | n | MAE at 0.0 (pp) | MAE at pick (pp) |\n|---|---:|---:|---:|")
    for b, n, m0, m1 in band_rows:
        L.append(f"| {b} | {n} | {m0:.2f} | {m1:.2f} |")
    L.append("")
    L.append(f"Calibration set, in-sample: MAE {s_cal[0.0]['mae']:.2f} → {s_cal[t_pick]['mae']:.2f} pp, "
             f"off by more than 10 pp {s_cal[0.0]['over10']} → {s_cal[t_pick]['over10']} of 65.\n")
    L.append("Largest remaining errors on the 33 at the pick:\n")
    L.append("| image | GT (%) | at 0.0 (%) | at pick (%) |\n|---|---:|---:|---:|")
    for r in worst:
        L.append(f"| {r['file']} | {r['gt']:.1f} | {pct(r['p'], 0.0):.1f} | {pct(r['p'], t_pick):.1f} |")
    L.append("")
    L.append("Largest swings between the two cutoffs, all 98 (the reading depends on the cutoff most where the map sits between them):\n")
    L.append("| image | split | GT (%) | at 0.0 (%) | at pick (%) |\n|---|---|---:|---:|---:|")
    for r in swing:
        L.append(f"| {r['file']} | {r['split']} | {r['gt']:.1f} | {pct(r['p'], 0.0):.1f} | {pct(r['p'], t_pick):.1f} |")
    L.append("")
    L.append("## What the cutoff does not fix\n")
    L.append(f"- 15_Caco-2.jpg (GT {caco['gt']:.1f}%, the only eval2019 image above 60%): {pct(caco['p'], 0.0):.1f}% at 0.0, "
             f"{pct(caco['p'], t_pick):.1f}% at the pick; the map's highest logit is {caco['p'].max():.2f}, so no cutoff in the grid finds these cells.")
    L.append(f"- 48_HT29.jpg, the site's error case (GT {ht29['gt']:.1f}%): {pct(ht29['p'], 0.0):.1f}% at confidence {confidence(ht29['p'], 0.0):.3f} at 0.0; "
             f"{pct(ht29['p'], t_pick):.1f}% at confidence {confidence(ht29['p'], t_pick):.3f} at the pick (floor {FLOOR}).")
    L.append("- The passage range stays untested on held-out real images: eval2019 has no image at or above 66%.\n")
    if dense:
        L.append("## Dense LIVECell frames (in Cellpose-SAM's training set; over-read check only)\n")
        L.append("GT is the union of the polygons rasterised with cv2.fillPoly, as for EVICAN. The first run of this script used "
                 "pycocotools' annToMask, which gave GT 2-4 pp lower (a larger apparent over-read); it was switched to match the "
                 "EVICAN measure after that output was seen.\n")
        L.append("| frame | GT (%) | at 0.0 (%) | at pick (%) | confidence at 0.0 | at pick |\n|---|---:|---:|---:|---:|---:|")
        for name, g, a0, a1, c0, c1 in dense:
            L.append(f"| {name} | {g:.1f} | {a0:.1f} | {a1:.1f} | {c0:.3f} | {c1:.3f} |")
        L.append("")
    L.append("## What changing the default would move (held-out C2C12, context)\n")
    L.append(f"{down['n']} held-out frames, {down['sequences']} sequences, scored from the cache's quarter-resolution maps "
             "(Ker et al., *Sci Data* 5:180237, 2018; CC BY 4.0). No C2C12 ground truth exists, so this says what moves, not what is right.\n")
    L.append("| cutoff | median confluency (%) | max (%) | below the confidence floor | at or above 50% | at or above 80% |\n|---|---:|---:|---:|---:|---:|")
    for r in down["rows"]:
        L.append(f"| {r['t']:+.1f} | {r['median']:.1f} | {r['max']:.1f} | {r['below_floor']} | {r['ge50']} | {r['ge80']} |")
    L.append("")
    L.append(f"Shift per frame: median {down['shift_median']:+.1f} pp, 90th percentile {down['shift_p90']:+.1f} pp. "
             f"{down['moved']} of {down['n']} frames change anomaly bank (0-20 / 20-40 / 40-100%), whose thresholds were set at cutoff 0.0. "
             f"Confidence is 1 − 4 × the share of pixels within ±{BAND} logit of the cutoff, and the floor ({FLOOR}) was set at 0.0.\n")
    with open(OUT_MD, "w") as f:
        f.write("\n".join(L))
    print(f"pick {t_pick:+.1f}; wrote {OUT_CSV}, {OUT_MD}")


if __name__ == "__main__":
    main()
