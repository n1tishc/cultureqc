"""Slice 1 — real-image confluency validation against EVICAN's held-out eval2019 split.

Dataset: EVICAN (CC BY 4.0, Parekh et al. 2020, Bioinformatics), downloaded from
its Dataverse (Edmond/Max Planck Society) record doi:10.17617/3.AJBV1S. Verified
via the Cellpose-SAM paper (Pachitariu, Rariden & Stringer 2025, bioRxiv
2025.04.28.651001) NOT to be among its 18 training datasets (LIVECell, DeepBacs,
TissueNet, and 15 others are; EVICAN is not) — see docs/DATASETS.md.

GT confluency = union of "Cell" category COCO polygons / image area, per the
spec's rule. Sanity-checked visually on two images (one easy, one difficult
tier) before running this at scale: eval2019 crops are exhaustively annotated
(no visible unmasked cells, clean background) — see docs/DATASETS.md for the
overlay evidence, so no "restrict to fully annotated regions" sub-cropping is
needed here, unlike the general partial-annotation caveat the spec raises for
EVICAN's larger training-image set (not used here).

Methods, none retuned on this eval set except the local-contrast baseline's own
threshold (tuned on a small tuning split per the spec, then frozen — see below):
    cultureqc          culture.seg.cpsam_confluency(method="probmap") — shipped, no retuning
    threshold_baseline  culture.seg.threshold_confluency — shipped, no retuning
    local_contrast_halo  Jaccard et al. (PMC4260842) - INSPIRED, NOT a faithful
        reimplementation. The paper's halo correction is an iterative Kirsch-filter
        gradient-direction tracking algorithm (8 directional filters, per-pixel
        boundary tracking toward brighter intensities, area-ratio constraint) --
        substantial standalone engineering. What's implemented here: local
        contrast (std/mean in a sliding window) thresholded and cleaned as the
        paper describes, then halo suppression approximated by morphological
        opening sized to typical halo width, instead of the paper's directional
        tracking. Labelled "local_contrast_halo (Jaccard-et-al.-inspired,
        simplified)" everywhere it's reported — never as a reproduction of their
        method. Threshold tuned on a 6-image tuning split (excluded from the
        reported eval set), then frozen for all reported numbers.

Usage:
    .venv/bin/python scripts/eval_confluency_real.py --budget-s 2400 --seed 0

Outputs:
    results/confluency_real.csv
    results/confluency_real_summary.md
    results/confluency_real_scatter.png
    results/confluency_real_overlays/{best,median,worst}_*.png
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import statistics
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

EVICAN_DIR = os.path.join("data", "sources", "evican")
IMAGES_DIR = os.path.join(EVICAN_DIR, "eval2019_images")
TIERS = ["easy", "medium", "difficult"]

# Linear fit of Cellpose-SAM CPU seg time vs. pixel count, from Slice 0's
# results/baseline_latency.csv (256x256 -> 45s, 704x520 -> 140s): t = a + b*px
LATENCY_FIT_A = 24.28
LATENCY_FIT_B = 0.000316

# True-outlier cutoff: images above this pixel count are excluded from the
# eval subset selection (not from the dataset — just from what we budget
# local CPU time for). Chosen to drop exactly the 6 images that dominate
# total runtime (see the AskUserQuestion exchange this slice started with);
# everything else, including sizes comparable to our own 704x520 test-data
# fixtures, stays eligible — that size band is the one that matters for a
# full-flask-image use case.
SIZE_CUTOFF_PX = 500_000

TUNING_HOLD_OUT_N = 6  # excluded from the reported eval set; used only to freeze the local-contrast threshold


def load_coco_gt():
    """Returns {image_id_global: {"file_name","width","height","gt_pct","tier"}}."""
    import numpy as np
    import cv2

    out = {}
    next_id = 0
    for tier in TIERS:
        path = os.path.join(EVICAN_DIR, f"instances_eval2019_{tier}_EVICAN2.json")
        with open(path) as f:
            d = json.load(f)
        anns_by_img = {}
        for a in d["annotations"]:
            if a["category_id"] != 1:  # 1 = Cell, 2 = Nucleus; confluency wants Cell
                continue
            anns_by_img.setdefault(a["image_id"], []).append(a)
        for im in d["images"]:
            mask = np.zeros((im["height"], im["width"]), np.uint8)
            for a in anns_by_img.get(im["id"], []):
                for poly in a["segmentation"]:
                    pts = np.array(poly, dtype=np.float32).reshape(-1, 2)
                    pts = np.clip(pts, 0, None).astype(np.int32)
                    cv2.fillPoly(mask, [pts], 1)
            gt_pct = float(mask.mean() * 100)
            out[next_id] = {
                "file_name": im["file_name"],
                "width": im["width"], "height": im["height"],
                "px": im["width"] * im["height"],
                "cell_line": im["file_name"].rsplit("_", 1)[-1].split(".")[0],
                "tier": tier,
                "gt_pct": gt_pct,
            }
            next_id += 1
    return out


def select_subset(gt, budget_s: float, seed: int):
    """Deterministic stratified pick under a Cellpose-SAM CPU time budget.

    Excludes true-outlier-sized images (see SIZE_CUTOFF_PX), then round-robins
    across the three difficulty tiers (shuffled within each tier, fixed seed)
    preferring cell-line diversity, until the estimated total segmentation
    time would exceed `budget_s`.
    """
    import random

    rng = random.Random(seed)
    by_tier = {t: [k for k, v in gt.items() if v["tier"] == t and v["px"] <= SIZE_CUTOFF_PX] for t in TIERS}
    for t in TIERS:
        rng.shuffle(by_tier[t])

    def est_time(k):
        return LATENCY_FIT_A + LATENCY_FIT_B * gt[k]["px"]

    selected = []
    used_cell_lines = set()
    total_t = 0.0
    pointers = {t: 0 for t in TIERS}
    exhausted = set()
    while len(exhausted) < len(TIERS):
        for t in TIERS:
            if t in exhausted:
                continue
            pool = by_tier[t]
            # Prefer an unused cell line within this tier first (diversity),
            # falling back to the next unpicked image otherwise.
            idx = None
            for i in range(pointers[t], len(pool)):
                if gt[pool[i]]["cell_line"] not in used_cell_lines:
                    idx = i
                    break
            if idx is None:
                idx = pointers[t] if pointers[t] < len(pool) else None
            if idx is None:
                exhausted.add(t)
                continue
            k = pool[idx]
            pool[idx], pool[pointers[t]] = pool[pointers[t]], pool[idx]
            pointers[t] += 1
            t_est = est_time(k)
            if total_t + t_est > budget_s and selected:
                exhausted.add(t)
                continue
            selected.append(k)
            used_cell_lines.add(gt[k]["cell_line"])
            total_t += t_est
            if pointers[t] >= len(pool):
                exhausted.add(t)
    return selected, total_t


def local_contrast_halo_confluency(img, threshold: float, window: int = 15,
                                    fmax_frac: float = 0.0005, rmax_frac: float = 0.0005,
                                    halo_open_px: int = 7):
    """Jaccard-et-al.-INSPIRED baseline. See module docstring: this is a simplified
    approximation (morphological opening for halo suppression), not the paper's
    iterative Kirsch-filter directional tracking. Do not report as a faithful
    reproduction of PMC4260842's method.
    """
    import cv2
    import numpy as np

    if img.ndim == 3:
        img = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    g = img.astype(np.float32)
    ksize = (window, window)
    mean = cv2.blur(g, ksize)
    sq_mean = cv2.blur(g ** 2, ksize)
    var = np.clip(sq_mean - mean ** 2, 0, None)
    std = np.sqrt(var)
    contrast = std / (mean + 1e-6)  # coefficient of variation, per the paper's C = sigma/mu

    binary = (contrast > threshold).astype(np.uint8)

    area = binary.shape[0] * binary.shape[1]
    fmax = max(1, int(area * fmax_frac))
    rmax = max(1, int(area * rmax_frac))
    from skimage.morphology import remove_small_holes, remove_small_objects
    binary_bool = remove_small_holes(binary.astype(bool), max_size=fmax)
    binary_bool = remove_small_objects(binary_bool, max_size=rmax)

    # Halo suppression (simplified, see docstring): morphological opening strips
    # thin peripheral rings (typical phase-contrast halo width) that aren't part
    # of a solid contiguous cell body, in place of the paper's directional
    # gradient tracking.
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (halo_open_px, halo_open_px))
    opened = cv2.morphologyEx(binary_bool.astype(np.uint8), cv2.MORPH_OPEN, kernel)

    return float(opened.mean() * 100)


def tune_local_contrast_threshold(gt, tuning_ids, thresholds=(0.05, 0.08, 0.1, 0.12, 0.15, 0.2, 0.25, 0.3)):
    import cv2

    best_t, best_mae = None, float("inf")
    imgs = {k: cv2.imread(os.path.join(IMAGES_DIR, gt[k]["file_name"]), cv2.IMREAD_GRAYSCALE) for k in tuning_ids}
    for t in thresholds:
        errs = [abs(local_contrast_halo_confluency(imgs[k], threshold=t) - gt[k]["gt_pct"]) for k in tuning_ids]
        mae = statistics.mean(errs)
        print(f"  tuning threshold={t}: MAE={mae:.2f}pp on {len(tuning_ids)} tuning images")
        if mae < best_mae:
            best_mae, best_t = mae, t
    return best_t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget-s", type=float, default=2400.0,
                     help="Cellpose-SAM CPU time budget for the eval subset (seconds)")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    import cv2

    gt = load_coco_gt()
    print(f"Loaded GT for {len(gt)} EVICAN eval2019 images across {len(TIERS)} difficulty tiers.")

    all_ids = sorted(gt.keys())
    rng_tune = __import__("random").Random(args.seed + 1000)
    tuning_ids = rng_tune.sample(all_ids, TUNING_HOLD_OUT_N)
    print(f"Tuning split (excluded from reported eval): {[gt[k]['file_name'] for k in tuning_ids]}")
    print("Tuning local_contrast_halo threshold...")
    tuned_threshold = tune_local_contrast_threshold(gt, tuning_ids)
    print(f"Frozen local_contrast_halo threshold: {tuned_threshold}")

    eligible = {k: v for k, v in gt.items() if k not in tuning_ids}
    subset, est_t = select_subset(eligible, args.budget_s, args.seed)
    print(f"Selected {len(subset)} images, estimated Cellpose-SAM time {est_t:.0f}s ({est_t/60:.1f} min)")
    by_tier_count = {t: sum(1 for k in subset if gt[k]["tier"] == t) for t in TIERS}
    print(f"  by tier: {by_tier_count}")
    print(f"  distinct cell lines: {len(set(gt[k]['cell_line'] for k in subset))}")

    from culture.seg import cpsam_confluency, threshold_confluency, _get_model as _get_seg_model

    print("Loading Cellpose-SAM...")
    t0 = time.time()
    _get_seg_model()
    print(f"  resident in {time.time()-t0:.1f}s")

    rows = []
    t0 = time.time()
    for i, k in enumerate(subset):
        meta = gt[k]
        path = os.path.join(IMAGES_DIR, meta["file_name"])
        img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            print(f"  skip (unreadable): {path}")
            continue

        ts = time.time()
        cq = cpsam_confluency(img, method="probmap")
        t_seg = time.time() - ts

        th = threshold_confluency(img)
        lch_pct = local_contrast_halo_confluency(img, threshold=tuned_threshold)

        row = {
            "image_id": k, "file_name": meta["file_name"], "tier": meta["tier"],
            "cell_line": meta["cell_line"], "width": meta["width"], "height": meta["height"],
            "gt_pct": round(meta["gt_pct"], 3),
            "cultureqc_pct": cq.pct, "cultureqc_confidence": cq.confidence,
            "threshold_baseline_pct": th.pct,
            "local_contrast_halo_pct": round(lch_pct, 3),
            "cultureqc_seg_s": round(t_seg, 2),
        }
        rows.append(row)
        elapsed = time.time() - t0
        print(f"  [{i+1}/{len(subset)}] {meta['file_name']:20s} {meta['width']}x{meta['height']:<6} "
              f"GT={meta['gt_pct']:6.2f}  cultureqc={cq.pct:6.2f}  thresh={th.pct:6.2f}  "
              f"lch={lch_pct:6.2f}  seg={t_seg:5.1f}s  elapsed={elapsed/60:5.1f}min")

    os.makedirs("results", exist_ok=True)
    import csv
    with open("results/confluency_real.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"\nWrote results/confluency_real.csv ({len(rows)} rows)")

    # Save the frozen threshold + tuning info alongside, for the writeup.
    with open("results/confluency_real_tuning.json", "w") as f:
        json.dump({
            "local_contrast_halo_threshold": tuned_threshold,
            "tuning_image_ids": [gt[k]["file_name"] for k in tuning_ids],
            "eval_subset_n": len(rows),
            "eval_subset_by_tier": by_tier_count,
            "estimated_seg_time_s": est_t,
            "size_cutoff_px": SIZE_CUTOFF_PX,
            "seed": args.seed,
        }, f, indent=2)
    print("Wrote results/confluency_real_tuning.json")


if __name__ == "__main__":
    main()
