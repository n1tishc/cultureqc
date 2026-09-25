#!/usr/bin/env python3
"""
Temperature-scale the QC classifier from cached logits (cultureQC_upgrade_spec.md
§8.1, Phase A5). CPU only: reads cache/logits.parquet, no inference.

Joins the synthetic tiles' cached logits with data/tiles/manifest.csv (split +
class), fits one temperature on the val split by NLL (culture.calibration),
and reports accuracy, NLL, top-label ECE and one-vs-rest ECE per class before
and after, on val (where T was fit, the V8 number) and test (held out).

    python scripts/calibrate_classifier.py --cache-dir cache

Writes configs/calibration.yaml, results/calibration.csv,
results/calibration_summary.md, results/calibration_reliability.png.
All numbers are synthetic (data/tiles/).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np
import pandas as pd
import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from culture.calibration import (N_BINS, classwise_ece, ece, fit_temperature, nll,  # noqa: E402
                                 reliability_bins, softmax)
from culture.qc import CLASS_NAMES  # noqa: E402


def load_tile_logits(cache_dir: str, manifest_path: str) -> pd.DataFrame:
    images = pd.read_parquet(os.path.join(cache_dir, "images.parquet"))
    tiles = images[images.dataset == "synth_tiles"].copy()
    tiles["tile_id"] = tiles["source_path"].apply(os.path.basename)
    tiles["class_dir"] = tiles["source_path"].apply(lambda p: os.path.basename(os.path.dirname(p)))
    manifest = pd.read_csv(manifest_path)

    merged = tiles.merge(manifest[["tile_id", "class", "split", "severity"]], on="tile_id", how="inner")
    if len(merged) != len(tiles) or len(merged) != len(manifest):
        raise SystemExit(f"join mismatch: {len(tiles)} cached tiles, {len(manifest)} manifest rows, "
                         f"{len(merged)} joined")
    bad = merged[merged.class_dir != merged["class"]]
    if len(bad):
        raise SystemExit(f"{len(bad)} tiles sit in a class directory that disagrees with the manifest, "
                         f"e.g. {bad.source_path.iloc[0]}")

    logits = pd.read_parquet(os.path.join(cache_dir, "logits.parquet"))
    logits = logits[logits.model_name == "qc"]
    merged = merged.merge(logits[["image_sha256", "model_version", "logits"]], on="image_sha256", how="inner")
    if len(merged) != len(tiles):
        raise SystemExit(f"{len(tiles) - len(merged)} tiles have no cached qc logits")
    versions = merged.model_version.unique().tolist()
    if len(versions) != 1:
        raise SystemExit(f"cached logits come from more than one qc model_version: {versions}")
    merged["logits"] = merged["logits"].apply(lambda s: np.array(json.loads(s), dtype=np.float64))
    merged["label"] = merged["class"].map({c: i for i, c in enumerate(CLASS_NAMES)})
    if merged.label.isna().any():
        raise SystemExit(f"unknown classes: {sorted(set(merged['class']) - set(CLASS_NAMES))}")
    return merged


def metrics(logits: np.ndarray, labels: np.ndarray, T: float) -> dict:
    p = softmax(logits, T)
    out = {"n": len(labels), "accuracy": float((p.argmax(1) == labels).mean()), "nll": nll(logits, labels, T),
           "ece": ece(p, labels), "mean_confidence": float(p.max(1).mean())}
    for name, v in zip(CLASS_NAMES, classwise_ece(p, labels)):
        out[f"ece_{name}"] = v
    return out


def plot_reliability(splits: dict, T: float, path: str) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, len(splits), figsize=(5 * len(splits), 4.6))
    for ax, (split, (logits, labels)) in zip(np.atleast_1d(axes), splits.items()):
        ax.plot([0, 1], [0, 1], color="0.6", lw=1, ls="--")
        for temp, label, colour in [(1.0, "before (T=1)", "#c0504d"), (T, f"after (T={T:.3f})", "#1f77b4")]:
            bins = reliability_bins(softmax(logits, temp), labels)
            ax.plot([b["confidence"] for b in bins], [b["accuracy"] for b in bins], "-", color=colour, lw=1,
                    label=f"{label}, ECE {ece(softmax(logits, temp), labels):.3f}")
            ax.scatter([b["confidence"] for b in bins], [b["accuracy"] for b in bins], color=colour, zorder=3,
                       s=[12 + 6 * np.sqrt(b["n"]) for b in bins])
            if temp != 1.0:
                for b in bins:
                    ax.annotate(str(b["n"]), (b["confidence"], b["accuracy"]), textcoords="offset points",
                                xytext=(4, -10), fontsize=7, color=colour)
        ax.set_xlim(0, 1.02)
        ax.set_ylim(0, 1.02)
        ax.set_xlabel("confidence (top-label, mean per bin)")
        ax.set_ylabel("accuracy in bin")
        ax.set_title(f"{split} split (n={len(labels)}), synthetic tiles\nmarker size and labels: tiles per bin (after)", fontsize=10)
        ax.legend(loc="lower right", fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache-dir", default="cache")
    ap.add_argument("--manifest", default="data/tiles/manifest.csv")
    ap.add_argument("--config-out", default="configs/calibration.yaml")
    ap.add_argument("--results-dir", default="results")
    args = ap.parse_args()

    df = load_tile_logits(args.cache_dir, args.manifest)
    model_version = df.model_version.iloc[0]
    data = {s: (np.stack(g.logits.to_numpy()), g.label.to_numpy().astype(int)) for s, g in df.groupby("split")}
    T = fit_temperature(*data["val"])

    rows = []
    for split in ("val", "test", "train"):
        for stage, temp in (("before", 1.0), ("after", T)):
            rows.append({"split": split, "stage": stage, "temperature": temp, **metrics(*data[split], temp)})
    res = pd.DataFrame(rows)
    os.makedirs(args.results_dir, exist_ok=True)
    res.to_csv(os.path.join(args.results_dir, "calibration.csv"), index=False)
    plot_reliability({"val": data["val"], "test": data["test"]}, T,
                     os.path.join(args.results_dir, "calibration_reliability.png"))

    from culture.model_versions import get_model_versions
    qc_version = get_model_versions().get("qc", {})
    if qc_version.get("version") not in (None, model_version):
        raise SystemExit(f"cached logits are {model_version}, local qc weights are {qc_version.get('version')}")

    def r(split, stage):
        return res[(res.split == split) & (res.stage == stage)].iloc[0]

    config = {
        "temperature": round(T, 6),
        "model_name": "qc",
        "model_version": model_version,
        "weights_sha256": qc_version.get("weights_sha256"),
        "fit": {
            "method": "temperature scaling, NLL minimised over log T in [log 0.05, log 20]",
            "split": "val",
            "n": int(r("val", "before")["n"]),
            "source": f"{args.cache_dir}/logits.parquet joined with {args.manifest}",
            "provenance": "synthetic",
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        },
        "ece_bins": N_BINS,
        "ece_val": {"before": round(float(r("val", "before")["ece"]), 4), "after": round(float(r("val", "after")["ece"]), 4)},
        "ece_test": {"before": round(float(r("test", "before")["ece"]), 4), "after": round(float(r("test", "after")["ece"]), 4)},
    }
    header = ("# QC classifier temperature (cultureQC_upgrade_spec.md §8.1, Phase A5).\n"
              "# Written by scripts/calibrate_classifier.py; do not edit by hand.\n"
              "# Applied only to logits from the model_version below (culture/calibration.py).\n")
    with open(args.config_out, "w") as f:
        f.write(header)
        yaml.safe_dump(config, f, sort_keys=False)

    fmt = lambda x: f"{x:.4f}"  # noqa: E731
    lines = [
        "# QC classifier calibration (Phase A5)",
        "",
        f"Generated by `scripts/calibrate_classifier.py` from `{args.cache_dir}/logits.parquet` "
        f"(model `{model_version}`), joined with `{args.manifest}`. **Provenance: synthetic** "
        "(data/tiles/, the classifier's own synthetic tile set).",
        "",
        f"Temperature fit on **val** (n={int(r('val', 'before')['n'])}) by NLL: **T = {T:.4f}** "
        "(stored in `configs/calibration.yaml`).",
        "",
        f"ECE: top-label, {N_BINS} equal-width bins. Per-class ECE: one-vs-rest, p(class) against "
        "'label is that class' (the quantity A6's failure-class residual trends).",
        "",
        "| split | stage | n | accuracy | NLL | ECE | " + " | ".join(f"ECE {c}" for c in CLASS_NAMES) + " |",
        "|---|---|---|---|---|---|" + "---|" * len(CLASS_NAMES),
    ]
    for _, x in res.iterrows():
        lines.append(f"| {x.split} | {x.stage} | {int(x.n)} | {fmt(x.accuracy)} | {fmt(x.nll)} | {fmt(x.ece)} | "
                     + " | ".join(fmt(x[f'ece_{c}']) for c in CLASS_NAMES) + " |")
    val_after, test_after = float(r("val", "after")["ece"]), float(r("test", "after")["ece"])
    top = {s: reliability_bins(softmax(data[s][0], T), data[s][1])[-1] for s in ("val", "test")}
    lines += [
        "",
        "Bins are sparse below the top one: after scaling, "
        + ", ".join(f"{top[s]['n']}/{len(data[s][1])} {s} tiles are in the top bin "
                    f"(confidence > {top[s]['lo']:.3f})" for s in ("val", "test"))
        + ". The lower bins hold a handful of tiles each, so their points in the diagram are noisy.",
    ]
    lines += [
        "",
        f"**V8 (ECE on val after temperature scaling ≤ 0.05): {'pass' if val_after <= 0.05 else 'fail'}** "
        f"({val_after:.4f}). This is in-sample: T was fit on val. Test ({test_after:.4f}) is the held-out figure.",
        "",
        "What this does and doesn't show: calibration on the classifier's own synthetic tiles. The tiles "
        "share generators and backgrounds with the training set and accuracy on them is high, so a low "
        "ECE here says little about calibration on real C2C12 frames or on shifted backgrounds (B3). "
        "Train-split rows are for reference only (the classifier was trained on them).",
        "",
        "![reliability](calibration_reliability.png)",
    ]
    with open(os.path.join(args.results_dir, "calibration_summary.md"), "w") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
