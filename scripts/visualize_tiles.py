#!/usr/bin/env python3
"""
Render a 4x6 grid per class + severity comparison for sanity checking.

    python scripts/visualize_tiles.py --tiles-dir data/tiles --out results/synth_grids
"""

import argparse
import glob
import os
import random

import cv2
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def show_grid(tile_dir, class_name, n_rows=4, n_cols=6):
    files = sorted(glob.glob(os.path.join(tile_dir, class_name, "*.png")))
    if not files:
        print(f"No tiles for {class_name}")
        return None
    random.seed(0)
    sample = random.sample(files, min(n_rows * n_cols, len(files)))

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(n_cols * 2.5, n_rows * 2.5))
    fig.suptitle(f"{class_name}  ({len(files)} total)", fontsize=14)
    for idx, ax in enumerate(axes.flatten()):
        if idx < len(sample):
            img = cv2.imread(sample[idx], cv2.IMREAD_GRAYSCALE)
            ax.imshow(img, cmap="gray", vmin=0, vmax=255)
            ax.set_title(os.path.basename(sample[idx]), fontsize=6)
        ax.axis("off")
    plt.tight_layout()
    return fig


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tiles-dir", default="data/tiles")
    parser.add_argument("--out", default="results/synth_grids")
    args = parser.parse_args()

    os.makedirs(args.out, exist_ok=True)

    # Grid per class
    for cls in ["normal", "contamination_suspected", "detachment", "image_quality"]:
        fig = show_grid(args.tiles_dir, cls)
        if fig:
            path = os.path.join(args.out, f"grid_{cls}.png")
            fig.savefig(path, dpi=150, bbox_inches="tight")
            print(f"Saved {path}")
            plt.close(fig)

    # Severity comparison
    manifest_path = os.path.join(args.tiles_dir, "manifest.csv")
    if os.path.exists(manifest_path):
        mf = pd.read_csv(manifest_path)
        contam = mf[mf["class"] == "contamination_suspected"]
        if len(contam) > 0:
            fig, axes = plt.subplots(1, 3, figsize=(12, 4))
            for i, sev in enumerate(["early", "mid", "late"]):
                sev_tiles = contam[contam.severity == sev]
                if len(sev_tiles) > 5:
                    path = os.path.join(args.tiles_dir, "contamination_suspected", sev_tiles.iloc[5].tile_id)
                    img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
                    if img is not None:
                        axes[i].imshow(img, cmap="gray", vmin=0, vmax=255)
                axes[i].set_title(f"{sev} ({len(sev_tiles)} tiles)")
                axes[i].axis("off")
            fig.suptitle("Contamination severity: early → mid → late", fontsize=13)
            plt.tight_layout()
            sev_path = os.path.join(args.out, "severity_comparison.png")
            fig.savefig(sev_path, dpi=150, bbox_inches="tight")
            print(f"Saved {sev_path}")
            plt.close(fig)

        # Split counts
        if "split" in mf.columns:
            print("\nSplit × Class:")
            print(mf.groupby(["split", "class"]).size().unstack(fill_value=0))


if __name__ == "__main__":
    main()
