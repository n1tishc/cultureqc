"""Slice 1 — scatter plot + overlay gallery from results/confluency_real.csv.

Run after scripts/eval_confluency_real.py.

    .venv/bin/python scripts/plot_confluency_real.py

Outputs:
    results/confluency_real_scatter.png
    results/confluency_real_overlays/{best,median,worst}_<file>.png
"""

from __future__ import annotations

import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

IMAGES_DIR = os.path.join("data", "sources", "evican", "eval2019_images")


def load_rows():
    with open("results/confluency_real.csv") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        for k in ("gt_pct", "cultureqc_pct", "threshold_baseline_pct", "local_contrast_halo_pct",
                   "cultureqc_confidence", "cultureqc_seg_s"):
            r[k] = float(r[k])
        r["width"], r["height"] = int(r["width"]), int(r["height"])
        r["abs_err_cultureqc"] = abs(r["cultureqc_pct"] - r["gt_pct"])
    return rows


def make_scatter(rows):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 3, figsize=(15, 5), sharex=True, sharey=True)
    methods = [
        ("cultureqc_pct", "cultureQC (cpsam_v2, probmap)"),
        ("threshold_baseline_pct", "Global-threshold baseline"),
        ("local_contrast_halo_pct", "Local-contrast + halo (Jaccard-inspired, simplified)"),
    ]
    colors = {"easy": "#2a9d8f", "medium": "#e9c46a", "difficult": "#e76f51"}
    for ax, (col, title) in zip(axes, methods):
        for tier, color in colors.items():
            xs = [r["gt_pct"] for r in rows if r["tier"] == tier]
            ys = [r[col] for r in rows if r["tier"] == tier]
            ax.scatter(xs, ys, c=color, label=tier, alpha=0.8, edgecolors="none", s=40)
        ax.plot([0, 100], [0, 100], "k--", linewidth=1, alpha=0.5)
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 100)
        ax.set_xlabel("GT confluency (%)")
        ax.set_title(title, fontsize=10)
    axes[0].set_ylabel("Predicted confluency (%)")
    axes[0].legend(loc="upper left", fontsize=8, title="EVICAN tier")
    fig.suptitle("cultureQC real-image confluency validation — EVICAN eval2019 subset (Slice 1)")
    fig.tight_layout()
    fig.savefig("results/confluency_real_scatter.png", dpi=150)
    print("Wrote results/confluency_real_scatter.png")


def make_overlay_gallery(rows):
    import cv2
    import numpy as np

    out_dir = "results/confluency_real_overlays"
    os.makedirs(out_dir, exist_ok=True)

    ranked = sorted(rows, key=lambda r: r["abs_err_cultureqc"])
    picks = {
        "best": ranked[:3],
        "median": ranked[len(ranked) // 2 - 1: len(ranked) // 2 + 2],
        "worst": ranked[-3:],
    }

    from culture.seg import cpsam_confluency

    for label, group in picks.items():
        for r in group:
            path = os.path.join(IMAGES_DIR, r["file_name"])
            img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                continue
            visuals = {}
            def cb(prob, mask, visuals=visuals):
                visuals["mask"] = mask
            cpsam_confluency(img, method="probmap", on_visual=cb)
            pred_mask = visuals.get("mask")

            rgb = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
            if pred_mask is not None:
                edge = cv2.morphologyEx(pred_mask.astype(np.uint8), cv2.MORPH_GRADIENT, np.ones((2, 2), np.uint8))
                rgb[edge > 0] = (0, 0, 255)  # red = cultureQC predicted boundary
            text = (f"{r['file_name']}  GT={r['gt_pct']:.1f}%  "
                    f"cultureQC={r['cultureqc_pct']:.1f}%  |err|={r['abs_err_cultureqc']:.1f}pp")
            banner = np.full((24, rgb.shape[1], 3), 255, np.uint8)
            cv2.putText(banner, text, (4, 17), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1, cv2.LINE_AA)
            canvas = np.vstack([banner, rgb])
            out_path = os.path.join(out_dir, f"{label}_{r['file_name']}.png")
            cv2.imwrite(out_path, canvas)
            print(f"  wrote {out_path}")


def main():
    rows = load_rows()
    print(f"Loaded {len(rows)} rows")
    make_scatter(rows)
    make_overlay_gallery(rows)


if __name__ == "__main__":
    main()
