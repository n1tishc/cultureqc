#!/usr/bin/env python3
"""
Three example segments for the §6.4 checkpoint ("Backtest table + 3 example
segments (good, poor, plateau)"). SYNTHETIC fixture sequences — same
fixture-through-real-Cache pattern as scripts/backtest_growth.py;
culture/growth.py and culture/replay.py run
their real code paths against fabricated data. Never a claim about real
growth.

Usage:
    python scripts/growth_examples.py
Outputs:
    results/growth_examples.png
    results/growth_examples.md
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from culture.cache import Cache
from culture.growth import fit_growth
from culture.replay import build_replay_visits
from demo.theme import ACCENT, BG_CARD, BORDER, TEXT_PRIMARY, TEXT_SECONDARY

RESULTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
TARGET_PCT = 80.0

EXAMPLES = [
    {
        "tag": "good", "title": "Good — healthy growth, target reached with a tight interval",
        "low": 6.0, "high": 92.0, "t_mid_frac": 0.40, "k": 0.10, "n_frames": 14, "hours_apart": 9.0,
    },
    {
        "tag": "poor", "title": "Poor — slow, late-inflecting growth: reached, but late and wide",
        "low": 8.0, "high": 90.0, "t_mid_frac": 0.85, "k": 0.028, "n_frames": 16, "hours_apart": 10.0,
    },
    {
        "tag": "plateau", "title": "Plateau — carrying capacity below target: NOT_REACHED",
        "low": 10.0, "high": 45.0, "t_mid_frac": 0.40, "k": 0.09, "n_frames": 14, "hours_apart": 9.0,
    },
]


def _fake_sha(tag: str) -> str:
    return hashlib.sha256(tag.encode()).hexdigest()


def _logistic(t_hours, t_mid_hours, k, low, high):
    return low + (high - low) / (1.0 + np.exp(-k * (t_hours - t_mid_hours)))


def _append_parquet(cache_dir: str, name: str, rows: list[dict]) -> None:
    path = os.path.join(cache_dir, name)
    new_df = pd.DataFrame(rows)
    if os.path.exists(path):
        new_df = pd.concat([pd.read_parquet(path), new_df], ignore_index=True)
    new_df.to_parquet(path, index=False)


def _write_sequence(
    cache_dir: str, sequence_id: str, start: str, n_frames: int, hours_apart: float,
    low: float, high: float, t_mid_frac: float, k: float, rng: np.random.Generator,
) -> None:
    """Writes one fixture sequence's rows (a noisy logistic, every frame
    "normal" and passing the quality gate) into cache_dir's parquet tables,
    appending to whatever is already there."""
    base = pd.Timestamp(start)
    t_mid = t_mid_frac * (n_frames - 1) * hours_apart
    shas = [_fake_sha(f"{sequence_id}-{i}") for i in range(n_frames)]

    images_rows, conf_rows, logits_rows, quality_rows = [], [], [], []
    for i, sha in enumerate(shas):
        t_hours = i * hours_apart
        images_rows.append({
            "image_sha256": sha, "dataset": "demo_fixture", "source_path": f"/demo/{sequence_id}/{i}.png",
            "sequence_id": sequence_id, "frame_idx": i,
            "timestamp": (base + pd.Timedelta(hours=t_hours)).isoformat(),
            "height": 256, "width": 256, "bit_depth": "uint8", "normalization": "grayscale_imread",
        })

        full_pct = float(np.clip(_logistic(t_hours, t_mid, k, low, high) + rng.normal(0, 1.5), 0, 100))
        conf_rows.append({
            "image_sha256": sha, "crop_spec": "full", "model_name": "seg", "model_version": "cpsam_v2",
            "pct": full_pct, "confidence": 0.82, "extra": json.dumps({}),
        })
        for c in range(4):
            crop_pct = float(np.clip(full_pct + rng.normal(0, 3.5), 0, 100))
            conf_rows.append({
                "image_sha256": sha, "crop_spec": f"crop_f0.25_s1_k{c}", "model_name": "seg",
                "model_version": "cpsam_v2", "pct": crop_pct, "confidence": 0.78,
                "extra": json.dumps({"frac": 0.25}),
            })

        base_logits = np.array([4.0, -1.0, -1.0, -1.0])  # argmax "normal"
        noisy_logits = base_logits + rng.normal(0, 0.3, 4)
        logits_rows.append({
            "image_sha256": sha, "crop_spec": "full", "model_name": "qc", "model_version": "qc_effnetb0_v1",
            "logits": json.dumps([float(x) for x in noisy_logits]),
        })

        quality_rows.append({
            "blur_laplacian_var": float(rng.uniform(250, 700)),
            "exposure_mean": float(rng.uniform(128.0, 128.8)),
            "uniformity_block_std": float(rng.uniform(0.15, 0.9)),
            "image_sha256": sha, "model_name": "quality", "model_version": "quality_v1",
        })

    _append_parquet(cache_dir, "images.parquet", images_rows)
    _append_parquet(cache_dir, "confluency.parquet", conf_rows)
    _append_parquet(cache_dir, "logits.parquet", logits_rows)
    _append_parquet(cache_dir, "quality.parquet", quality_rows)


def build_and_fit(example: dict, seed: int = 0):
    sequence_id = f"growth_example_{example['tag']}"
    work_dir = tempfile.mkdtemp(prefix=f"growth_example_{example['tag']}_")
    cache_dir = os.path.join(work_dir, "cache")
    cache = Cache(cache_dir)  # creates cache_dir -- must run before _write_sequence
    rng = np.random.default_rng(seed)
    _write_sequence(
        cache_dir, sequence_id, start="2026-01-01T00:00:00Z",
        n_frames=example["n_frames"], hours_apart=example["hours_apart"],
        low=example["low"], high=example["high"], t_mid_frac=example["t_mid_frac"], k=example["k"],
        rng=rng,
    )
    visits = build_replay_visits(cache, sequence_id, lineage_id=f"L_{sequence_id}",
                                  segment_id=f"S_{sequence_id}", flask_id="example-flask", seed=seed)
    visits.sort(key=lambda v: v["timestamp"])
    result = fit_growth(visits, target_pct=TARGET_PCT, seed=seed)
    return visits, result


def plot_example(ax, example, visits, result):
    times = pd.to_datetime([v["timestamp"] for v in visits], format="ISO8601")
    means = [v["confluency_mean"] for v in visits]
    sds = [v["confluency_sd"] for v in visits]

    ax.set_facecolor(BG_CARD)
    ax.plot(times, means, "-o", color=ACCENT, linewidth=1.5, markersize=4, alpha=0.9)
    ax.errorbar(times, means, yerr=sds, fmt="none", ecolor=ACCENT, alpha=0.3, capsize=2)

    if result.status == "OK" and result.t_grid_hours:
        t0 = pd.Timestamp(result.t0_timestamp)
        grid_times = t0 + pd.to_timedelta(result.t_grid_hours, unit="h")
        ax.plot(grid_times, result.y_grid["mean"], "--", color="#f59e0b", linewidth=1.3)
        if result.y_grid["lo"] is not None:
            ax.fill_between(grid_times, result.y_grid["lo"], result.y_grid["hi"], color="#f59e0b", alpha=0.15, linewidth=0)
        ax.axhline(TARGET_PCT, color=TEXT_SECONDARY, linestyle=":", linewidth=1.0, alpha=0.6)

    ax.set_ylim(0, 105)
    ax.set_title(example["title"], color=TEXT_PRIMARY, fontsize=9.5, loc="left")
    ax.tick_params(colors=TEXT_SECONDARY, labelsize=7.5)
    for spine in ax.spines.values():
        spine.set_color(BORDER)
    ax.grid(True, color=BORDER, alpha=0.4, linewidth=0.5)
    for label in ax.get_xticklabels():
        label.set_rotation(20)
        label.set_ha("right")


def status_line(result) -> str:
    if result.status != "OK":
        return f"status: `{result.status}`"
    aic_bits = ", ".join(f"{m} AIC={f['aic']:.1f}" for m, f in result.fits.items())
    if result.t_star_status == "REACHED":
        lo, hi = result.t_star_interval_hours or (None, None)
        interval = f", 90% CI [{lo:.0f}h, {hi:.0f}h]" if lo is not None else " (interval unavailable)"
        t_star = f"T* = {result.t_star_hours:.0f}h{interval}"
    else:
        t_star = "T* = `NOT_REACHED`"
    doubling = f"{result.area_doubling_time_hours:.1f}h" if result.area_doubling_time_hours is not None else "n/a"
    return f"**{result.chosen_model}** chosen ({aic_bits}) &middot; {t_star} &middot; doubling (early) {doubling}"


def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)
    fig, axes = plt.subplots(1, 3, figsize=(14, 3.6), dpi=140)
    fig.patch.set_facecolor(BG_CARD)

    md_lines = [
        "# Growth model — 3 example segments (SYNTHETIC, §6.4 checkpoint)",
        "",
        "Fabricated fixture sequences replayed through the real culture/replay.py + culture/growth.py",
        "code path (same pattern as scripts/backtest_growth.py) — never a claim",
        "about real cell growth.",
        "",
    ]
    for ax, example in zip(axes, EXAMPLES):
        visits, result = build_and_fit(example, seed=0)
        plot_example(ax, example, visits, result)
        md_lines.append(f"- **{example['tag']}** ({example['title']}): {status_line(result)}")

    md_lines += [
        "",
        "Note the doubling-time pair above: **plateau** reports a *faster* early doubling time than",
        "**poor** even though plateau never reaches the target and poor eventually does. That's",
        "expected, not a bug — doubling time is a rate (how fast growth is happening right now),",
        "independent of the fitted ceiling K (how high it will ever get). Plateau's generating curve",
        "rises steeply to a low ceiling; poor's rises slowly throughout to a much higher one. See",
        "culture/growth.py:_area_doubling_time's docstring.",
    ]

    fig.tight_layout()
    png_path = os.path.join(RESULTS_DIR, "growth_examples.png")
    fig.savefig(png_path, facecolor=BG_CARD)

    md_path = os.path.join(RESULTS_DIR, "growth_examples.md")
    with open(md_path, "w") as f:
        f.write("\n".join(md_lines) + "\n")

    print("\n".join(md_lines))
    print(f"\nwrote {png_path}")
    print(f"wrote {md_path}")


if __name__ == "__main__":
    main()
