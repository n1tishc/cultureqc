#!/usr/bin/env python3
"""
FOV noise floor (cultureQC_upgrade.md §4.3): repositioning noise — how much
confluency swings just from re-imaging the same flask at a slightly different
field of view, with nothing biologically different happening. This is the
measurement noise the temporal layer (Slices 2-5) must exceed before it's
allowed to flag a real change.

Reads cached crop confluency — **no GPU, no recompute**. Built entirely from
Slice 1b's compute cache (culture/cache.py, produced by
nb/02_compute_cache.ipynb): for each image, K deterministic random sub-crops
were taken at each configured crop_frac (default fracs {0.25, 0.5}, K=8) and
confluency was computed on each, already stored in confluency.parquet keyed
by crop_spec. This script only reads that table.

Method: for each real image (excludes data/tiles/ synthetic tiles — they're
already fixed-scale 256x256 composites, not a real repositioning scenario)
and each crop_frac, treat the K crop confluencies as K simulated repositions
of the same flask/FOV. mean = the density regime, SD = the noise at that
density and crop size. Fit sigma_fov(confluency_pct) with a plain linear
regression **per crop_frac** (not a joint 2D surface) — the cache only has
two discrete crop_frac values by default, not a continuous range, so a
2-parameter-per-frac linear fit is the honest amount of model this data
supports; fitting anything fancier would be extrapolating past what's here.

    python scripts/fov_noise.py --cache-dir cache_slim

Outputs:
    results/fov_noise.csv         — one row per (image, crop_frac): mean/SD/n
    results/fov_noise_summary.md  — headline numbers + the fit
    results/fov_noise_plot.png    — mean vs SD scatter, one series per crop_frac, fit line overlaid
    configs/noise.yaml            — sigma_fov(confluency_pct) per crop_frac, for Slices 2-5 to import

With --entry NAME (e.g. `--datasets c2c12 --entry c2c12`) the fit is written to
noise.yaml's `entries.NAME` instead, leaving the top-level `crop_fracs` (what
culture/growth.py reads) untouched, and the results files get a `_NAME` suffix.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# data/tiles/'s dataset tag (from nb/00 / nb/02's ImageRecord(dataset=...)) —
# excluded because a 256x256 synthetic composite has no real "repositioning"
# to simulate; only real acquisitions carry genuine FOV noise.
# The fault frames (scripts/make_fault_set.py) are simulated too.
SYNTHETIC_DATASETS = {"synth_tiles", "c2c12_fault_dim", "c2c12_fault_contam"}


def load_images_table(cache_dir: str) -> pd.DataFrame:
    """Cache doesn't expose a public load_images() (only downstream loaders
    that key off image_sha256 the caller already has) — this script needs
    the sha->dataset mapping itself, so it reads the parquet directly rather
    than adding a new method to culture/cache.py while a Colab run may still
    be writing to a cache built from the currently-pinned commit."""
    return pd.read_parquet(os.path.join(cache_dir, "images.parquet"))


def collect_crop_stats(cache_dir: str, real_datasets: set[str] | None) -> pd.DataFrame:
    from culture.cache import Cache

    cache = Cache(cache_dir)
    images = load_images_table(cache_dir)
    conf = cache.load_confluency()  # all crop_specs, all models
    conf = conf[conf.model_name == "seg"]

    real_shas = set(images.image_sha256)
    if real_datasets:
        real_shas = set(images[images.dataset.isin(real_datasets)].image_sha256)
    else:
        real_shas = set(images[~images.dataset.isin(SYNTHETIC_DATASETS)].image_sha256)

    conf = conf[conf.image_sha256.isin(real_shas)]
    crop_rows = conf[conf.crop_spec != "full"].copy()
    if len(crop_rows) == 0:
        raise SystemExit(
            f"No crop rows found in {cache_dir} for the selected real datasets. "
            "Was the cache built with crop_fracs=() (crops disabled)? "
            "nb/02_compute_cache.ipynb's default full pass uses crop_fracs=(0.25, 0.5)."
        )

    def frac_of(extra_json: str) -> float:
        return json.loads(extra_json)["frac"]

    crop_rows["frac"] = crop_rows["extra"].apply(frac_of)

    out = (
        crop_rows.groupby(["image_sha256", "frac"])["pct"]
        .agg(mean_pct="mean", sd_pct="std", n_crops="count")
        .reset_index()
    )
    out = out[out.n_crops >= 3]  # SD off fewer than 3 crops isn't a real estimate
    out = out.merge(images[["image_sha256", "dataset", "sequence_id"]], on="image_sha256", how="left")
    return out


def fit_linear_noise_model(df: pd.DataFrame) -> dict:
    """sigma_fov(confluency_pct) = intercept + slope * confluency_pct, fit
    separately per crop_frac. Reports R^2 alongside so a bad fit is visible
    rather than silently trusted."""
    model = {}
    for frac, g in df.groupby("frac"):
        x, y = g["mean_pct"].to_numpy(), g["sd_pct"].to_numpy()
        if len(x) < 3:
            model[str(frac)] = {"n_points": len(x), "note": "too few points to fit"}
            continue
        slope, intercept = np.polyfit(x, y, 1)
        pred = intercept + slope * x
        ss_res = float(np.sum((y - pred) ** 2))
        ss_tot = float(np.sum((y - y.mean()) ** 2))
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else float("nan")
        model[str(frac)] = {
            "slope": round(float(slope), 5),
            "intercept": round(float(intercept), 5),
            "n_points": int(len(x)),
            "r2": round(r2, 3),
            "mean_sd_pct": round(float(y.mean()), 3),
            "max_sd_pct": round(float(y.max()), 3),
        }
    return model


def make_plot(df: pd.DataFrame, model: dict, out_path: str):
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7, 5))
    colors = plt.cm.tab10.colors
    for i, (frac, g) in enumerate(sorted(df.groupby("frac"), key=lambda kv: kv[0])):
        c = colors[i % len(colors)]
        ax.scatter(g["mean_pct"], g["sd_pct"], s=14, alpha=0.6, color=c, label=f"crop_frac={frac}")
        m = model.get(str(frac), {})
        if "slope" in m:
            xs = np.linspace(g["mean_pct"].min(), g["mean_pct"].max(), 50)
            ys = m["intercept"] + m["slope"] * xs
            ax.plot(xs, ys, color=c, linewidth=2)
    ax.set_xlabel("mean confluency across K repositioned crops (%)")
    ax.set_ylabel("SD of confluency across K crops (pp) — the FOV noise floor")
    ax.set_title("FOV repositioning noise vs. confluency (cultureQC_upgrade.md §4.3)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def write_summary_md(df: pd.DataFrame, model: dict, cache_dir: str, out_path: str, entry: str | None = None):
    n_images = df["image_sha256"].nunique()
    n_seq = df["sequence_id"].nunique()
    sfx = f"_{entry}" if entry else ""
    saved = (f"Saved to `configs/noise.yaml` under `entries.{entry}`; the top-level fit that "
             "culture/growth.py reads is unchanged." if entry else
             "Saved to `configs/noise.yaml` for Slices 2-5 to import directly.")
    datasets = sorted(df["dataset"].unique())
    lines = [
        "# FOV noise floor — Slice 1b (`cultureQC_upgrade.md` §4.3)",
        "",
        f"**Source:** cached crop confluency in `{cache_dir}`, no GPU/recompute. "
        f"{n_images} real images ({', '.join(datasets)}), excluding synthetic tiles."
        + (f" They come from {n_seq} time-lapse sequences, so frames of one sequence are not "
           "independent samples." if df["sequence_id"].notna().all() and n_seq < n_images else ""),
        "",
        "**Method:** for each image and each configured `crop_frac`, K deterministic "
        "random sub-crops simulate K repositions of the same FOV. Mean confluency "
        "across those crops is the density regime; SD across them is the noise floor "
        "at that density — the swing the temporal layer must exceed before flagging "
        "a real change, not measurement noise.",
        "",
        "| crop_frac | n points (images) | mean SD (pp) | max SD (pp) | linear fit R² |",
        "|---:|---:|---:|---:|---:|",
    ]
    for frac in sorted(model.keys(), key=float):
        m = model[frac]
        if "slope" not in m:
            lines.append(f"| {frac} | {m['n_points']} | — | — | too few points |")
            continue
        lines.append(f"| {frac} | {m['n_points']} | {m['mean_sd_pct']} | {m['max_sd_pct']} | {m['r2']} |")
    lines += [
        "",
        "**Fit:** `sigma_fov(confluency_pct) = intercept + slope * confluency_pct`, "
        "per `crop_frac` — a plain linear fit, not a joint 2D surface over "
        "(confluency, crop_frac). The cache only has two discrete crop_frac values "
        "by default (0.25, 0.5), not a continuous range, so a 2-parameter-per-frac "
        "linear model is the honest amount of structure this data supports — a "
        "fancier joint model would be extrapolating past what's actually here. " + saved,
        "",
        f"See `results/fov_noise{sfx}_plot.png` for the scatter + fit lines, "
        f"`results/fov_noise{sfx}.csv` for every (image, crop_frac) point.",
    ]
    with open(out_path, "w") as f:
        f.write("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache-dir", default="cache_slim")
    parser.add_argument(
        "--datasets", nargs="+", default=None,
        help="Restrict to these dataset tags (default: everything except data/tiles/'s "
        "synthetic tiles — see SYNTHETIC_DATASETS).",
    )
    parser.add_argument("--out", default="results")
    parser.add_argument("--configs-out", default="configs")
    parser.add_argument("--entry", default=None,
                        help="Write the fit to noise.yaml's entries.<ENTRY> and suffix the results files, "
                        "instead of replacing the top-level crop_fracs.")
    args = parser.parse_args()

    t0 = time.time()
    df = collect_crop_stats(args.cache_dir, set(args.datasets) if args.datasets else None)
    print(f"{len(df)} (image, crop_frac) points from {df['image_sha256'].nunique()} images "
          f"in {time.time()-t0:.1f}s")

    model = fit_linear_noise_model(df)
    for frac, m in sorted(model.items(), key=lambda kv: float(kv[0])):
        if "slope" in m:
            print(f"  crop_frac={frac}: sigma_fov = {m['intercept']:.3f} + {m['slope']:.4f}*pct  "
                  f"(n={m['n_points']}, R²={m['r2']}, mean SD={m['mean_sd_pct']}pp)")
        else:
            print(f"  crop_frac={frac}: {m['note']} (n={m['n_points']})")

    os.makedirs(args.out, exist_ok=True)
    os.makedirs(args.configs_out, exist_ok=True)

    sfx = f"_{args.entry}" if args.entry else ""
    df.to_csv(os.path.join(args.out, f"fov_noise{sfx}.csv"), index=False)
    print(f"Wrote {args.out}/fov_noise{sfx}.csv ({len(df)} rows)")

    make_plot(df, model, os.path.join(args.out, f"fov_noise{sfx}_plot.png"))
    print(f"Wrote {args.out}/fov_noise{sfx}_plot.png")

    write_summary_md(df, model, args.cache_dir, os.path.join(args.out, f"fov_noise{sfx}_summary.md"),
                     args.entry)
    print(f"Wrote {args.out}/fov_noise{sfx}_summary.md")

    import yaml
    fit = {
        "source_cache": args.cache_dir,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "datasets": sorted(df["dataset"].unique()),
        "n_images": int(df["image_sha256"].nunique()),
        "n_sequences": int(df["sequence_id"].nunique()),
        "crop_fracs": model,
    }
    path = os.path.join(args.configs_out, "noise.yaml")
    prev = {}
    if os.path.exists(path):
        with open(path) as f:
            prev = yaml.safe_load(f) or {}
    if args.entry:
        noise_yaml = prev
        noise_yaml.setdefault("entries", {})[args.entry] = fit
    else:
        noise_yaml = {"model": "sigma_fov(confluency_pct) = intercept + slope * confluency_pct, fit per crop_frac",
                      **fit}
        if "entries" in prev:  # keep the separately measured entries
            noise_yaml["entries"] = prev["entries"]
    with open(path, "w") as f:
        yaml.safe_dump(noise_yaml, f, sort_keys=False)
    print(f"Wrote {path}" + (f" (entries.{args.entry})" if args.entry else ""))


if __name__ == "__main__":
    main()
