#!/usr/bin/env python3
"""
Calibrate culture/quality.py's thresholds (cultureQC_upgrade.md §5.2) against
real cached quality metrics — no recompute, no GPU, reads cache/quality.parquet
directly.

Thresholds are set from data/tiles/'s 1,000 "normal" synthetic tiles' own
distribution (1st/99th percentile per metric — "calibrated on normal tiles"
per the spec), then measured against the 1,000 "image_quality" tiles as the
should-fail set, reporting the real false-positive/recall numbers rather than
assuming the percentile choice works.

    python scripts/calibrate_quality_gate.py --cache-dir cache

Writes configs/quality.yaml.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from collections import Counter

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

METRICS = ["blur_laplacian_var", "exposure_mean", "uniformity_block_std"]


def load_tile_quality(cache_dir: str) -> pd.DataFrame:
    q = pd.read_parquet(os.path.join(cache_dir, "quality.parquet"))
    images = pd.read_parquet(os.path.join(cache_dir, "images.parquet"))
    tiles = images[images.dataset == "synth_tiles"].copy()
    tiles["tile_id"] = tiles["source_path"].apply(os.path.basename)
    manifest = pd.read_csv("data/tiles/manifest.csv")
    merged = tiles.merge(manifest[["tile_id", "class"]], on="tile_id", how="inner")
    merged = merged.merge(q[METRICS + ["image_sha256"]], on="image_sha256", how="inner")
    return merged


def fails(row: pd.Series, thresholds: dict) -> list[str]:
    reasons = []
    if row["blur_laplacian_var"] < thresholds["blur_laplacian_var"]["floor"]:
        reasons.append("blur_below_threshold")
    lo, hi = thresholds["exposure_mean"]["low"], thresholds["exposure_mean"]["high"]
    if not (lo <= row["exposure_mean"] <= hi):
        reasons.append("exposure_out_of_range")
    if row["uniformity_block_std"] > thresholds["uniformity_block_std"]["ceiling"]:
        reasons.append("uniformity_above_threshold")
    return reasons


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache-dir", default="cache")
    parser.add_argument("--percentile-low", type=float, default=1.0)
    parser.add_argument("--percentile-high", type=float, default=99.0)
    parser.add_argument("--out", default="configs/quality.yaml")
    args = parser.parse_args()

    merged = load_tile_quality(args.cache_dir)
    normal = merged[merged["class"] == "normal"]
    iq = merged[merged["class"] == "image_quality"]
    if len(normal) == 0 or len(iq) == 0:
        raise SystemExit(
            f"Need both 'normal' and 'image_quality' tiles in {args.cache_dir}/quality.parquet "
            "joined against data/tiles/manifest.csv — got "
            f"{len(normal)} normal, {len(iq)} image_quality."
        )

    lo_q, hi_q = args.percentile_low / 100, args.percentile_high / 100
    thresholds = {
        "blur_laplacian_var": {"floor": round(float(normal["blur_laplacian_var"].quantile(lo_q)), 2)},
        "exposure_mean": {
            "low": round(float(normal["exposure_mean"].quantile(lo_q)), 2),
            "high": round(float(normal["exposure_mean"].quantile(hi_q)), 2),
        },
        "uniformity_block_std": {"ceiling": round(float(normal["uniformity_block_std"].quantile(hi_q)), 3)},
    }

    results = {}
    for name, df in [("normal", normal), ("image_quality", iq)]:
        reason_lists = df.apply(lambda r: fails(r, thresholds), axis=1)
        any_fail = reason_lists.apply(len).gt(0)
        reason_counts = Counter(r for rs in reason_lists for r in rs)
        results[name] = {
            "n": len(df),
            "fail_rate_pct": round(float(any_fail.mean() * 100), 1),
            "n_fail": int(any_fail.sum()),
            "reason_breakdown": dict(reason_counts),
        }
        print(f"{name}: fail rate = {results[name]['fail_rate_pct']}%  "
              f"({results[name]['n_fail']}/{results[name]['n']})  {dict(reason_counts)}")

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    import yaml
    doc = {
        **thresholds,
        "calibration": {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "source": f"{args.cache_dir}/quality.parquet joined with data/tiles/manifest.csv",
            "percentile": [args.percentile_low, args.percentile_high],
            "normal_false_positive_rate_pct": results["normal"]["fail_rate_pct"],
            "image_quality_recall_pct": results["image_quality"]["fail_rate_pct"],
            "n_normal": results["normal"]["n"],
            "n_image_quality": results["image_quality"]["n"],
            "note": (
                "blur alone barely separates the classes here -- data/tiles/'s "
                "'image_quality' class bundles several distinct defect types "
                "(dust, bubbles, scratches, blur, vignette per "
                "scripts/synth_contamination.py), most of which don't move "
                "Laplacian variance; exposure and uniformity are much cleaner "
                "single-metric separators. Recall is a union-of-3-checks number."
            ),
        },
    }
    with open(args.out, "w") as f:
        yaml.safe_dump(doc, f, sort_keys=False)
    print(f"\nWrote {args.out}")


if __name__ == "__main__":
    main()
