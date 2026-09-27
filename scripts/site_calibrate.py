"""
Site calibration for the per-image anomaly check (cultureQC_upgrade_specv4.md
§2B.4): rebuild the banks and per-bin thresholds from known-good images of a new
instrument, so the flag is calibrated for that site instead of for C2C12.

    python scripts/site_calibrate.py --normals DIR --out-dir OUT [--confluency-csv CSV | --single-bin]

Method, the same as scripts/eval_anomaly.py (read from configs/anomaly.yaml):
DINOv2-small patches of each image's 256 px centre tile; banks = greedy
k-center coresets per confluency bin; image score = mean of the top 1% patch
distances; threshold = the (1 − fpr) quantile of normal scores. No image is
ever scored against a bank that contains it: a seeded split puts half the
images in the banks and scores the other half to set the thresholds.

Binning needs each image's full-frame Cellpose-SAM confluency:
  --confluency-csv CSV   columns filename,pct (e.g. from an earlier run)
  (default)              run Cellpose-SAM on every image (minutes per image on CPU;
                         use a GPU for more than a few images)
  --single-bin           one bin for all confluencies (no Cellpose)
Bins with too few images on either side of the split merge into a neighbour.

Writes OUT/banks.npz and OUT/anomaly.yaml (same layout as configs/anomaly.yaml);
never touches configs/. To use them:
    CULTUREQC_ANOMALY_CONFIG=OUT/anomaly.yaml CULTUREQC_ANOMALY_BANKS=OUT/banks.npz python demo/app.py
Aim for dozens of images per bin: with n calibration images the 5% threshold
is set by about n/20 of them.
"""

from __future__ import annotations

import argparse
import glob
import math
import os
import sys
import time

import numpy as np
import yaml

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from culture.anomaly import (EPS, bank_hash, bin_index, bin_label, greedy_coreset, image_score,  # noqa: E402
                             load_anomaly_config, merge_bins, nn_distance)

EXTS = (".png", ".jpg", ".jpeg", ".tif", ".tiff")
MIN_PER_SIDE = 3


def list_images(folder: str) -> list[str]:
    return sorted(p for p in glob.glob(os.path.join(folder, "*")) if p.lower().endswith(EXTS))


def _embed(img: np.ndarray) -> np.ndarray:
    from culture.cache import dino_embed, qc_tile_from

    x = dino_embed(qc_tile_from(img))["patches"].astype(np.float32)   # float16 as the cache stores it
    return x / (np.linalg.norm(x, axis=1, keepdims=True) + EPS)


def _confluency(img: np.ndarray) -> float:
    from culture.seg import cpsam_confluency

    return float(cpsam_confluency(img, method="probmap").pct)


def calibrate(patches: list[np.ndarray], pct: list[float], base: dict, fpr: float, seed: int,
              single_bin: bool) -> tuple[dict, dict, list[str]]:
    """(banks, config, warnings) from per-image patch arrays and confluencies."""
    n = len(patches)
    if n < 2 * MIN_PER_SIDE:
        raise SystemExit(f"need at least {2 * MIN_PER_SIDE} images, got {n}")
    rng = np.random.default_rng(seed)
    order = rng.permutation(n)
    bank_idx, cal_idx = set(order[: n // 2].tolist()), set(order[n // 2:].tolist())

    edges = [0.0, 100.0] if single_bin else list(base["bins"]["configured_edges"])
    if not single_bin:
        per_bin = [min(sum(bin_index(pct[i], edges) == b for i in side) for side in (bank_idx, cal_idx))
                   for b in range(len(edges) - 1)]
        edges = merge_bins(edges, per_bin, MIN_PER_SIDE)
    method = base["method"]
    banks, cal, warnings = {}, {"bins": {}}, []
    for b in range(len(edges) - 1):
        label = bin_label(b, edges)
        bank_imgs = [i for i in sorted(bank_idx) if bin_index(pct[i], edges) == b]
        cal_imgs = [i for i in sorted(cal_idx) if bin_index(pct[i], edges) == b]
        if not bank_imgs or not cal_imgs:
            raise SystemExit(f"bin {label}: {len(bank_imgs)} bank / {len(cal_imgs)} calibration images; "
                             "add images or use --single-bin")
        x = np.concatenate([patches[i] for i in bank_imgs])
        keep = greedy_coreset(x, max(1, int(math.ceil(method["coreset_frac"] * len(x)))), seed=seed,
                              proj_dim=method["proj_dim"])
        banks[f"bin_{label}"] = x[keep]
        scores = np.array([image_score(nn_distance(patches[i], banks[f"bin_{label}"]), method["top_frac"])
                           for i in cal_imgs])
        cal["bins"][label] = {"lo": edges[b], "hi": edges[b + 1], "n_bank_images": len(bank_imgs),
                              "n_calibration_images": len(cal_imgs), "mean": round(float(scores.mean()), 6),
                              "sd": round(float(scores.std(ddof=1)) if len(scores) > 1 else 0.0, 6),
                              "threshold": round(float(np.quantile(scores, 1 - fpr)), 6)}
        if len(cal_imgs) < 20:
            warnings.append(f"bin {label}: only {len(cal_imgs)} calibration images; its {fpr:.0%} threshold "
                            "is a rough estimate")
    config = {
        "method": method,
        "bins": {"edges": edges, "bin_by": "single bin" if single_bin else base["bins"]["bin_by"]},
        "fpr": fpr,
        "calibration": cal,
        "bank": {"source": "site calibration (scripts/site_calibrate.py)", "split_seed": seed,
                 "sha256": bank_hash([banks[k] for k in sorted(banks)]),
                 "sizes": {k: int(len(v)) for k, v in banks.items()}},
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    return banks, config, warnings


def main():
    import cv2
    import pandas as pd

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--normals", required=True, help="folder of known-good images from the new instrument")
    ap.add_argument("--out-dir", required=True)
    src = ap.add_mutually_exclusive_group()
    src.add_argument("--confluency-csv")
    src.add_argument("--single-bin", action="store_true")
    ap.add_argument("--fpr", type=float, default=None, help="default: configs/anomaly.yaml's fpr")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    base = load_anomaly_config()
    paths = list_images(args.normals)
    known = {}
    if args.confluency_csv:
        df = pd.read_csv(args.confluency_csv)
        known = dict(zip(df.filename, df.pct))
    patches, pct = [], []
    for k, p in enumerate(paths, 1):
        img = cv2.imread(p, cv2.IMREAD_GRAYSCALE)
        if img is None:
            raise SystemExit(f"could not read {p}")
        patches.append(_embed(img))
        name = os.path.basename(p)
        pct.append(0.0 if args.single_bin else float(known[name]) if args.confluency_csv else _confluency(img))
        print(f"[{k}/{len(paths)}] {name}", flush=True)
    banks, config, warnings = calibrate(patches, pct, base, args.fpr if args.fpr is not None else base["fpr"],
                                        args.seed, args.single_bin)
    os.makedirs(args.out_dir, exist_ok=True)
    np.savez(os.path.join(args.out_dir, "banks.npz"), **banks)
    with open(os.path.join(args.out_dir, "anomaly.yaml"), "w") as f:
        yaml.safe_dump(config, f, sort_keys=False)
    for w in warnings:
        print("warning:", w)
    for label, c in config["calibration"]["bins"].items():
        print(f"bin {label}: {c['n_bank_images']} bank / {c['n_calibration_images']} calibration images, "
              f"threshold {c['threshold']:.4f}")
    print(f"wrote {args.out_dir}/banks.npz and {args.out_dir}/anomaly.yaml")


if __name__ == "__main__":
    main()
