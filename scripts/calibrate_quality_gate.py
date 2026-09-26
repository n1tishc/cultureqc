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

Writes configs/quality.yaml (top level; any `entries` are kept).

    python scripts/calibrate_quality_gate.py --cache-dir cache --entry c2c12

Writes `entries.c2c12` only: thresholds from the frames of the *tuning* C2C12
base sequences (results/replay_fleet_split.csv), same percentiles. There are
no real should-fail frames, so it reports the fail rate on held-out normal
frames (out of sample) and on held-out simulated fault frames (lamp dimming
by severity, contamination), and writes results/quality_gate_<entry>.md.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from collections import Counter

import numpy as np
import pandas as pd
import yaml

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


def percentile_thresholds(normal: pd.DataFrame, lo_pct: float, hi_pct: float) -> dict:
    lo_q, hi_q = lo_pct / 100, hi_pct / 100
    return {
        "blur_laplacian_var": {"floor": round(float(normal["blur_laplacian_var"].quantile(lo_q)), 2)},
        "exposure_mean": {
            "low": round(float(normal["exposure_mean"].quantile(lo_q)), 2),
            "high": round(float(normal["exposure_mean"].quantile(hi_q)), 2),
        },
        "uniformity_block_std": {"ceiling": round(float(normal["uniformity_block_std"].quantile(hi_q)), 3)},
    }


def _fail_stats(df: pd.DataFrame, thresholds: dict) -> dict:
    reasons = df.apply(lambda r: fails(r, thresholds), axis=1) if len(df) else pd.Series(dtype=object)
    failed = reasons.apply(len).gt(0) if len(df) else pd.Series(dtype=bool)
    out = {"n": int(len(df)), "n_fail": int(failed.sum()),
           "fail_rate_pct": round(float(failed.mean() * 100), 1) if len(df) else None,
           "reason_breakdown": dict(Counter(r for rs in reasons for r in rs))}
    if "sequence_id" in df and len(df):
        per_seq = failed.groupby(df["sequence_id"].to_numpy()).mean() * 100
        out["n_sequences"] = int(len(per_seq))
        out["per_sequence_fail_pct"] = {k: round(float(v), 1) for k, v in per_seq.items()}
    return out


def calibrate_entry(args):
    cache = args.cache_dir
    q = pd.read_parquet(os.path.join(cache, "quality.parquet")).drop_duplicates("image_sha256")
    images = pd.read_parquet(os.path.join(cache, "images.parquet"))
    split = pd.read_csv(args.split)
    base = split[split.kind == "base"].set_index("sequence_id").split
    frames = images[images.dataset.isin(args.datasets)].merge(q[METRICS + ["image_sha256"]], on="image_sha256")
    frames["split"] = frames.sequence_id.map(base)
    if frames.split.isna().any():
        raise SystemExit(f"{int(frames.split.isna().sum())} frames belong to no sequence in {args.split}")
    tuning, held = frames[frames.split == "tuning"], frames[frames.split == "heldout"]
    thresholds = percentile_thresholds(tuning, args.percentile_low, args.percentile_high)

    man = pd.read_parquet(os.path.join(cache, "sidecars", "fault_manifest.parquet"))
    fsplit = split[split.kind == "fault"].set_index("sequence_id").split
    mod = man[man.is_modified & (man.fault_sequence_id.map(fsplit) == "heldout")]
    mod = mod.merge(q[METRICS + ["image_sha256"]], on="image_sha256").rename(
        columns={"fault_sequence_id": "sequence_id_fault"})
    mod["sequence_id"] = mod["sequence_id_fault"]

    results = {"tuning_normal": _fail_stats(tuning, thresholds), "heldout_normal": _fail_stats(held, thresholds)}
    for ftype, g in mod.groupby("fault_type"):
        results[f"heldout_{ftype}"] = _fail_stats(g, thresholds)
    dim = mod[mod.fault_type == "lamp_dimming"].copy()
    dim_bins = []
    if len(dim):
        dim["bin"] = pd.cut(dim.severity, [0, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0], include_lowest=True)
        for b, g in dim.groupby("bin", observed=True):
            dim_bins.append((str(b), _fail_stats(g, thresholds)))

    with open(args.out) as f:
        doc = yaml.safe_load(f)
    entry = {
        **thresholds,
        "datasets": list(args.datasets),
        "calibration": {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "source": f"{cache}/quality.parquet, frames of the tuning base sequences in {args.split}",
            "percentile": [args.percentile_low, args.percentile_high],
            "n_frames": results["tuning_normal"]["n"],
            "n_sequences": results["tuning_normal"]["n_sequences"],
            "tuning_fail_rate_pct": results["tuning_normal"]["fail_rate_pct"],
            "heldout_normal_fail_rate_pct": results["heldout_normal"]["fail_rate_pct"],
            "note": ("No real should-fail frames exist for this source; fail rates on held-out normal frames "
                     "and held-out simulated fault frames are in results/quality_gate_" + args.entry + ".md."),
        },
    }
    doc.setdefault("entries", {})[args.entry] = entry
    with open(args.out, "w") as f:
        yaml.safe_dump(doc, f, sort_keys=False)

    lines = [f"# Quality gate thresholds for `{args.entry}`", "",
             f"Generated {entry['calibration']['generated_at']} by `scripts/calibrate_quality_gate.py --entry "
             f"{args.entry}`. Datasets: {', '.join(args.datasets)}. C2C12 images: Ker et al., *Sci Data* 5:180237 "
             "(2018), CC BY 4.0; fault frames are simulated from them.", "",
             f"Thresholds = percentiles {args.percentile_low:g} and {args.percentile_high:g} of each metric over "
             f"the {results['tuning_normal']['n']} frames of the {results['tuning_normal']['n_sequences']} *tuning* "
             "base sequences, the same rule as the synthetic-tile thresholds. Frames within a sequence are not "
             "independent; n sequences is the sample size.", "",
             "| metric | synthetic tiles (top level) | this entry |", "|---|---|---|",
             f"| blur floor | {doc['blur_laplacian_var']['floor']} | {thresholds['blur_laplacian_var']['floor']} |",
             f"| exposure range | {doc['exposure_mean']['low']}–{doc['exposure_mean']['high']} | "
             f"{thresholds['exposure_mean']['low']}–{thresholds['exposure_mean']['high']} |",
             f"| uniformity ceiling | {doc['uniformity_block_std']['ceiling']} | "
             f"{thresholds['uniformity_block_std']['ceiling']} |", "",
             "## Fail rates", "",
             "| frames | sequences | frames | fail rate | reasons |", "|---|---|---|---|---|"]
    labels = {"tuning_normal": "tuning normal (in sample)", "heldout_normal": "held-out normal"}
    for key, r in results.items():
        label = labels.get(key, key.replace("heldout_", "held-out ") + " (modified frames)")
        reasons = ", ".join(f"{k} {v}" for k, v in sorted(r["reason_breakdown"].items())) or "—"
        lines.append(f"| {label} | {r.get('n_sequences', 0)} | {r['n']} | {r['n_fail']} ({r['fail_rate_pct']}%) "
                     f"| {reasons} |")
    if dim_bins:
        lines += ["", "Held-out lamp dimming by severity (intensity factor; 1.0 = undimmed):", "",
                  "| factor | frames | fail rate |", "|---|---|---|"]
        for b, r in dim_bins:
            lines.append(f"| {b} | {r['n']} | {r['n_fail']} ({r['fail_rate_pct']}%) |")
    per = results["heldout_normal"].get("per_sequence_fail_pct", {})
    if per:
        lines += ["", "Held-out normal fail rate per sequence: " + ", ".join(
            f"{k.replace('c2c12_', '')} {v:g}%" for k, v in sorted(per.items())) + "."]
    lines += ["", "Contamination is not an image-quality defect; its row shows only whether the gate reacts to it.",
              ""]
    md = os.path.join(args.results, f"quality_gate_{args.entry}.md")
    with open(md, "w") as f:
        f.write("\n".join(lines))
    print("\n".join(lines))
    print(f"wrote {args.out} (entries.{args.entry}) and {md}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache-dir", default="cache")
    parser.add_argument("--percentile-low", type=float, default=1.0)
    parser.add_argument("--percentile-high", type=float, default=99.0)
    parser.add_argument("--out", default="configs/quality.yaml")
    parser.add_argument("--entry", default=None, help="write entries.<name> instead of the top level")
    parser.add_argument("--datasets", nargs="+", default=["c2c12"], help="with --entry")
    parser.add_argument("--split", default="results/replay_fleet_split.csv", help="with --entry")
    parser.add_argument("--results", default="results", help="with --entry")
    args = parser.parse_args()
    if args.entry:
        calibrate_entry(args)
        return

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
    entries = None
    if os.path.exists(args.out):
        with open(args.out) as f:
            entries = (yaml.safe_load(f) or {}).get("entries")
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
    if entries:
        doc["entries"] = entries
    with open(args.out, "w") as f:
        yaml.safe_dump(doc, f, sort_keys=False)
    print(f"\nWrote {args.out}")


if __name__ == "__main__":
    main()
