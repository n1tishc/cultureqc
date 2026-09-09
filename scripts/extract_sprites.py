#!/usr/bin/env python3
"""
Extract individual bacterial sprites from DeepBacs brightfield images.

Each sprite is saved as a small RGBA PNG: bacterium visible, background transparent.
These get composited onto clean cell culture tiles by synth_contamination.py.

    python scripts/extract_sprites.py \
        --input data/sources/deepbacs \
        --out data/sprites/bacteria \
        --max-sprites 100
"""

import argparse
import glob
import json
import os

import cv2
import numpy as np
from tqdm import tqdm


def extract_sprites_from_image(img_path, mask_path, min_area=15, max_area=3000, pad=4):
    """
    Given a brightfield image and its mask, extract individual bacteria
    as small RGBA crops. Returns list of (sprite_rgba, area_px).
    """
    img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
    mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)

    if img is None or mask is None:
        return []

    if mask.max() > 1:
        _, mask = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)

    n_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)

    sprites = []
    for i in range(1, n_labels):
        area = stats[i, cv2.CC_STAT_AREA]
        if area < min_area or area > max_area:
            continue

        x = stats[i, cv2.CC_STAT_LEFT]
        y = stats[i, cv2.CC_STAT_TOP]
        w = stats[i, cv2.CC_STAT_WIDTH]
        h = stats[i, cv2.CC_STAT_HEIGHT]

        x0 = max(0, x - pad)
        y0 = max(0, y - pad)
        x1 = min(img.shape[1], x + w + pad)
        y1 = min(img.shape[0], y + h + pad)

        crop = img[y0:y1, x0:x1].copy()
        crop_mask = (labels[y0:y1, x0:x1] == i).astype(np.uint8)
        crop_mask = cv2.dilate(crop_mask, np.ones((3, 3), np.uint8), iterations=1)

        alpha = (crop_mask * 255).astype(np.uint8)
        rgba = np.zeros((crop.shape[0], crop.shape[1], 4), dtype=np.uint8)
        rgba[:, :, 0] = crop
        rgba[:, :, 1] = crop
        rgba[:, :, 2] = crop
        rgba[:, :, 3] = alpha

        sprites.append((rgba, area))

    return sprites


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/sources/deepbacs")
    parser.add_argument("--out", default="data/sprites/bacteria")
    parser.add_argument("--max-sprites", type=int, default=None,
                        help="Cap total sprites. Default: no cap, use everything found.")
    parser.add_argument("--splits", nargs="+", default=["train", "test"],
                        help="Which DeepBacs splits to pull source images from (default: train + test — "
                             "unrelated to any ML train/test split, just more sprite variety).")
    args = parser.parse_args()

    os.makedirs(args.out, exist_ok=True)

    # DeepBacs layout: <input>/<split>/brightfield/*.tif + <input>/<split>/masks_binary/*.tif
    pairs = []  # list of (src_path, gt_dir)
    for split in args.splits:
        src_dir = os.path.join(args.input, split, "brightfield")
        gt_dir = os.path.join(args.input, split, "masks_binary")
        if os.path.isdir(src_dir) and os.path.isdir(gt_dir):
            for f in sorted(glob.glob(os.path.join(src_dir, "*.tif"))):
                pairs.append((f, gt_dir))
            print(f"{split}: {len(glob.glob(os.path.join(src_dir, '*.tif')))} images")

    if not pairs:
        # Fallback: generic source/GT name search
        src_files = []
        gt_dir = None
        for root, dirs, files in os.walk(args.input):
            tifs = [f for f in files if f.lower().endswith(".tif")]
            dirname = os.path.basename(root).lower()
            if dirname in ("source", "input", "images", "brightfield") and tifs:
                src_files = [os.path.join(root, f) for f in sorted(tifs)]
            if dirname in ("gt", "target", "masks", "labels", "masks_binary") and tifs:
                gt_dir = root
        if src_files and gt_dir:
            pairs = [(f, gt_dir) for f in src_files]

    if not pairs:
        print("Could not auto-detect source/GT directories. Structure found:")
        for root, dirs, files in os.walk(args.input):
            level = root.replace(args.input, "").count(os.sep)
            if level < 3:
                tifs = [f for f in files if f.lower().endswith(".tif")]
                print(f"{'  ' * level}{os.path.basename(root)}/  ({len(tifs)} tifs)")
        return

    print(f"Total source images: {len(pairs)}")

    all_sprites = []
    for src_path, gt_dir in tqdm(pairs, desc="Extracting sprites"):
        basename = os.path.basename(src_path)
        mask_path = None
        for ext in [".tif", ".png", ".TIF", ".PNG"]:
            candidate = os.path.join(gt_dir, os.path.splitext(basename)[0] + ext)
            if os.path.exists(candidate):
                mask_path = candidate
                break
        if mask_path is None:
            continue

        sprites = extract_sprites_from_image(src_path, mask_path)
        all_sprites.extend(sprites)
        if args.max_sprites and len(all_sprites) >= args.max_sprites:
            all_sprites = all_sprites[: args.max_sprites]
            break

    manifest = []
    for i, (rgba, area) in enumerate(all_sprites):
        fname = f"bact_{i:04d}.png"
        cv2.imwrite(os.path.join(args.out, fname), rgba)
        manifest.append({"file": fname, "area_px": int(area), "h": rgba.shape[0], "w": rgba.shape[1]})

    with open(os.path.join(args.out, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"\nExtracted {len(manifest)} sprites to {args.out}/")
    if manifest:
        areas = [s["area_px"] for s in manifest]
        print(f"Area range: {min(areas)}-{max(areas)} px, median {np.median(areas):.0f}")


if __name__ == "__main__":
    main()
