#!/usr/bin/env python3
"""
Generate synthetic contamination / detachment / image-quality tiles
from clean LIVECell base images + DeepBacs bacterial sprites.

Classes:
    normal                  - clean crop, untouched
    contamination_suspected - bacterial sprites in background + turbidity haze
    detachment              - synthetic mask erosion + bright floaters
    image_quality           - dust, bubbles, scratches, blur, vignette (NOT contamination)

    python scripts/synth_contamination.py \
        --base-dir /path/to/livecell_train_val_images \
        --sprite-dir data/sprites/bacteria \
        --out data/tiles \
        --tiles-per-class 1000 \
        --seed 42

Optional:
    --mask-dir /path/to/cached_cellpose_masks   (improves placement accuracy)
"""

import argparse
import glob
import os
import random

import cv2
import numpy as np
import pandas as pd
from skimage.filters import threshold_otsu
from tqdm import tqdm


TILE_SIZE = 256

SEVERITY_RANGES = {
    "early": (30, 150),
    "mid": (150, 600),
    "late": (600, 2000),
}


# ──────────────────────────────────────────────────────
# Utilities
# ──────────────────────────────────────────────────────


def load_sprites(sprite_dir):
    sprites = []
    for f in sorted(glob.glob(os.path.join(sprite_dir, "*.png"))):
        s = cv2.imread(f, cv2.IMREAD_UNCHANGED)
        if s is not None and s.ndim == 3 and s.shape[2] == 4:
            sprites.append(s)
    return sprites


def random_crop(img, mask=None, tile_size=TILE_SIZE):
    h, w = img.shape[:2]
    if h < tile_size or w < tile_size:
        return None
    y = random.randint(0, h - tile_size)
    x = random.randint(0, w - tile_size)
    crop = img[y : y + tile_size, x : x + tile_size].copy()
    crop_mask = mask[y : y + tile_size, x : x + tile_size].copy() if mask is not None else None
    return crop, crop_mask, x, y


def get_cell_mask(img, mask_dir=None, fname=None):
    """Cached cellpose mask if available, otherwise local-variance threshold."""
    if mask_dir and fname:
        for suffix in [".npy", ".tif.npy"]:
            npy_path = os.path.join(mask_dir, fname + suffix)
            if os.path.exists(npy_path):
                return np.load(npy_path) > 0
        npy_path = os.path.join(mask_dir, fname.replace(".tif", "") + ".npy")
        if os.path.exists(npy_path):
            return np.load(npy_path) > 0

    g = cv2.GaussianBlur(img.astype(np.float32), (5, 5), 0)
    mean = cv2.blur(g, (15, 15))
    sq = cv2.blur(g ** 2, (15, 15))
    var = np.clip(sq - mean ** 2, 0, None)
    try:
        t = threshold_otsu(var)
        return var > t
    except Exception:
        return np.zeros_like(img, dtype=bool)


# ──────────────────────────────────────────────────────
# Class recipes
# ──────────────────────────────────────────────────────


def add_bacteria(tile, bg_mask, sprites, severity="early", rng=None):
    """Composite bacterial sprites onto background pixels + turbidity haze."""
    if rng is None:
        rng = np.random.default_rng()

    lo, hi = SEVERITY_RANGES[severity]
    n_target = rng.integers(lo, hi)

    out = tile.astype(np.float32).copy()
    bg_coords = np.argwhere(bg_mask)
    if len(bg_coords) < 10:
        return tile, 0

    placed = 0
    for _ in range(n_target):
        sprite = sprites[rng.integers(0, len(sprites))]

        angle = rng.uniform(0, 360)
        center = (sprite.shape[1] // 2, sprite.shape[0] // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        sprite_rot = cv2.warpAffine(
            sprite, M, (sprite.shape[1], sprite.shape[0]),
            flags=cv2.INTER_LINEAR, borderValue=0,
        )

        sh, sw = sprite_rot.shape[:2]
        idx = rng.integers(0, len(bg_coords))
        cy, cx = bg_coords[idx]
        y0, x0 = cy - sh // 2, cx - sw // 2

        if y0 < 0 or x0 < 0 or y0 + sh > tile.shape[0] or x0 + sw > tile.shape[1]:
            continue

        alpha = sprite_rot[:, :, 3].astype(np.float32) / 255.0
        gray = sprite_rot[:, :, 0].astype(np.float32)

        local_region = out[y0 : y0 + sh, x0 : x0 + sw]
        local_mean = local_region[alpha < 0.1].mean() if (alpha < 0.1).sum() > 0 else local_region.mean()
        sprite_mean = gray[alpha > 0.5].mean() if (alpha > 0.5).sum() > 0 else gray.mean()
        if sprite_mean > 0:
            gray = gray * (local_mean / sprite_mean) * rng.uniform(0.5, 0.85)

        if rng.random() > 0.5:
            ksize = int(rng.choice([3, 5]))
            kernel = np.zeros((ksize, ksize))
            kernel[ksize // 2, :] = 1.0 / ksize
            gray = cv2.filter2D(gray, -1, kernel)

        out[y0 : y0 + sh, x0 : x0 + sw] = local_region * (1 - alpha) + gray * alpha
        placed += 1

    haze_strength = min(placed / 2000, 0.3)
    if haze_strength > 0.01:
        haze = rng.uniform(0.9, 1.1, size=(16, 16)).astype(np.float32)
        haze = cv2.resize(haze, (tile.shape[1], tile.shape[0]), interpolation=cv2.INTER_CUBIC)
        out = out * (1 - haze_strength) + out * haze * haze_strength
        mean_val = out.mean()
        out = mean_val + (out - mean_val) * (1 - haze_strength * 0.5)

    return np.clip(out, 0, 255).astype(np.uint8), placed


def add_image_artifact(tile, rng=None):
    """Add one of: blur, dust, bubble, scratch, vignette. NOT contamination."""
    if rng is None:
        rng = np.random.default_rng()

    out = tile.astype(np.float32).copy()
    artifact = str(rng.choice(["blur", "dust", "bubble", "scratch", "vignette"]))

    if artifact == "blur":
        out = cv2.GaussianBlur(out, (0, 0), rng.uniform(2.0, 5.0))

    elif artifact == "dust":
        for _ in range(rng.integers(3, 9)):
            cy, cx = rng.integers(10, tile.shape[0] - 10), rng.integers(10, tile.shape[1] - 10)
            r = rng.integers(2, 6)
            cv2.circle(out, (int(cx), int(cy)), int(r), float(out.mean() * rng.uniform(0.2, 0.6)), -1)

    elif artifact == "bubble":
        for _ in range(rng.integers(1, 4)):
            cy, cx = rng.integers(40, tile.shape[0] - 40), rng.integers(40, tile.shape[1] - 40)
            r = rng.integers(15, 60)
            cv2.circle(out, (int(cx), int(cy)), int(r), float(out.mean() * 1.4), 2)
            cv2.circle(out, (int(cx), int(cy)), int(r) - 3, float(out.mean() * 1.1), -1)

    elif artifact == "scratch":
        for _ in range(rng.integers(1, 3)):
            y1, x1 = rng.integers(0, tile.shape[0]), rng.integers(0, tile.shape[1])
            angle = rng.uniform(0, np.pi)
            length = rng.integers(80, 200)
            y2, x2 = int(y1 + length * np.sin(angle)), int(x1 + length * np.cos(angle))
            cv2.line(out, (x1, y1), (x2, y2), float(out.mean() * rng.uniform(1.2, 1.6)), 1)

    elif artifact == "vignette":
        h, w = tile.shape[:2]
        Y, X = np.ogrid[:h, :w]
        dist = np.sqrt((X - w / 2) ** 2 + (Y - h / 2) ** 2)
        out = out * (1.0 - 0.4 * (dist / np.sqrt((w / 2) ** 2 + (h / 2) ** 2)) ** 2)

    return np.clip(out, 0, 255).astype(np.uint8), artifact


def make_synthetic_detachment(tile, cell_mask, rng=None):
    """Erode cell mask in patches, fill with BG noise, add bright floaters."""
    if rng is None:
        rng = np.random.default_rng()

    out = tile.astype(np.float32).copy()
    h, w = tile.shape[:2]

    bg_pixels = out[~cell_mask]
    bg_mean = bg_pixels.mean() if len(bg_pixels) > 0 else out.mean()
    bg_std = bg_pixels.std() if len(bg_pixels) > 0 else 10.0

    erode_mask = cell_mask.copy()
    for _ in range(rng.integers(2, 6)):
        py, px = rng.integers(0, h), rng.integers(0, w)
        pr = rng.integers(20, 50)
        y0, y1 = max(0, py - pr), min(h, py + pr)
        x0, x1 = max(0, px - pr), min(w, px + pr)
        erode_mask[y0:y1, x0:x1] = False

    removed = cell_mask & ~erode_mask
    noise = rng.normal(bg_mean, bg_std, size=out.shape).astype(np.float32)
    out[removed] = noise[removed]

    for _ in range(rng.integers(5, 30)):
        fy, fx = rng.integers(10, h - 10), rng.integers(10, w - 10)
        fr = rng.integers(4, 10)
        brightness = float(bg_mean * rng.uniform(1.2, 1.6))
        cv2.circle(out, (int(fx), int(fy)), int(fr), brightness, -1)
        cv2.circle(out, (int(fx), int(fy)), int(fr) + 2, float(brightness * 0.8), 1)

    return np.clip(out, 0, 255).astype(np.uint8)


# ──────────────────────────────────────────────────────
# Main generator
# ──────────────────────────────────────────────────────


def generate(base_dir, sprite_dir, out_dir, mask_dir=None, tiles_per_class=1000, seed=42):
    rng = np.random.default_rng(seed)
    random.seed(seed)

    sprites = load_sprites(sprite_dir)
    assert sprites, f"No sprites in {sprite_dir}. Run extract_sprites.py first."

    base_files = sorted(glob.glob(os.path.join(base_dir, "*.tif")))
    random.shuffle(base_files)
    print(f"Base images: {len(base_files)}  |  Sprites: {len(sprites)}")

    for cls in ["normal", "contamination_suspected", "detachment", "image_quality"]:
        os.makedirs(os.path.join(out_dir, cls), exist_ok=True)

    manifest = []
    counts = {c: 0 for c in ["normal", "contamination_suspected", "detachment", "image_quality"]}
    mask_source_counts = {"cached": 0, "fallback_threshold": 0}
    sevs = ["early", "mid", "late"]

    for base_path in tqdm(base_files, desc="Generating tiles"):
        if all(c >= tiles_per_class for c in counts.values()):
            break

        img = cv2.imread(base_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            continue

        fname = os.path.basename(base_path)
        cell_line = fname.split("_")[0]

        used_cache = bool(mask_dir and os.path.exists(os.path.join(mask_dir, fname + ".npy")))
        mask_source_counts["cached" if used_cache else "fallback_threshold"] += 1

        cell_mask = get_cell_mask(img, mask_dir, fname)
        bg_mask = ~cell_mask

        for _ in range(6):
            result = random_crop(img, bg_mask)
            if result is None:
                continue
            crop_img, crop_bg, cx, cy = result
            crop_cell = ~crop_bg if crop_bg is not None else None
            base_rec = {"source_image": fname, "cell_line": cell_line, "crop_x": cx, "crop_y": cy}

            # Normal
            if counts["normal"] < tiles_per_class:
                tid = f"normal_{counts['normal']:05d}.png"
                cv2.imwrite(os.path.join(out_dir, "normal", tid), crop_img)
                manifest.append({**base_rec, "tile_id": tid, "class": "normal",
                                 "severity": "n/a", "artifact": "none"})
                counts["normal"] += 1

            # Contamination
            if counts["contamination_suspected"] < tiles_per_class and crop_bg is not None:
                sev = sevs[counts["contamination_suspected"] % 3]
                contam, n_placed = add_bacteria(crop_img, crop_bg, sprites, sev, rng)
                if n_placed > 0:
                    tid = f"contam_{counts['contamination_suspected']:05d}.png"
                    cv2.imwrite(os.path.join(out_dir, "contamination_suspected", tid), contam)
                    manifest.append({**base_rec, "tile_id": tid, "class": "contamination_suspected",
                                     "severity": sev, "n_sprites": n_placed, "artifact": "bacteria+haze"})
                    counts["contamination_suspected"] += 1

            # Image quality
            if counts["image_quality"] < tiles_per_class:
                iq, artifact = add_image_artifact(crop_img, rng)
                tid = f"imgq_{counts['image_quality']:05d}.png"
                cv2.imwrite(os.path.join(out_dir, "image_quality", tid), iq)
                manifest.append({**base_rec, "tile_id": tid, "class": "image_quality",
                                 "severity": "n/a", "artifact": artifact})
                counts["image_quality"] += 1

            # Detachment
            if counts["detachment"] < tiles_per_class and crop_cell is not None:
                if crop_cell.mean() > 0.15:
                    det = make_synthetic_detachment(crop_img, crop_cell, rng)
                    tid = f"detach_{counts['detachment']:05d}.png"
                    cv2.imwrite(os.path.join(out_dir, "detachment", tid), det)
                    manifest.append({**base_rec, "tile_id": tid, "class": "detachment",
                                     "severity": "synthetic", "artifact": "mask_erosion+floaters"})
                    counts["detachment"] += 1

    mf = pd.DataFrame(manifest)
    print(f"\nGenerated:")
    for cls, n in counts.items():
        print(f"  {cls}: {n}")
    print(f"\nCell mask source:")
    print(f"  cached Cellpose masks: {mask_source_counts['cached']}")
    print(f"  local-variance fallback: {mask_source_counts['fallback_threshold']}")

    return mf


def split_by_source(mf, seed=42):
    """Split by source image: 70/15/15, no leakage."""
    rng = np.random.default_rng(seed)
    sources = mf["source_image"].unique().tolist()
    rng.shuffle(sources)

    n = len(sources)
    n_train, n_val = int(n * 0.70), int(n * 0.15)
    train_s = set(sources[:n_train])
    val_s = set(sources[n_train : n_train + n_val])

    mf["split"] = mf["source_image"].apply(
        lambda s: "train" if s in train_s else ("val" if s in val_s else "test")
    )

    # Verify
    for s in mf["source_image"].unique():
        assert len(mf[mf["source_image"] == s]["split"].unique()) == 1, f"Leakage: {s}"
    print("No leakage.")

    print(f"\nSplit × Class:")
    print(mf.groupby(["split", "class"]).size().unstack(fill_value=0).to_string())
    return mf


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-dir", required=True, help="LIVECell train_val images (flat .tif)")
    parser.add_argument("--sprite-dir", default="data/sprites/bacteria")
    parser.add_argument("--mask-dir", default=None, help="Cached cellpose .npy masks (optional)")
    parser.add_argument("--out", default="data/tiles")
    parser.add_argument("--tiles-per-class", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    mf = generate(
        base_dir=args.base_dir,
        sprite_dir=args.sprite_dir,
        out_dir=args.out,
        mask_dir=args.mask_dir,
        tiles_per_class=args.tiles_per_class,
        seed=args.seed,
    )

    mf = split_by_source(mf, seed=args.seed)
    mf.to_csv(os.path.join(args.out, "manifest.csv"), index=False)
    print(f"\nManifest: {args.out}/manifest.csv ({len(mf)} rows)")


if __name__ == "__main__":
    main()
