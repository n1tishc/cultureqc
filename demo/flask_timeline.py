"""
demo/flask_timeline.py — data + plotting for the app's "Flask Timeline" tab
(cultureQC_upgrade.md §5.4, §5.5 checkpoint: "Show a replayed flask timeline
and the raw history table").

Two separate things are "simulated" here, and the UI text in demo/app.py
says both explicitly rather than only the one the spec calls out:

  1. The visit *stream* is replay-simulated (culture/replay.py): irregular
     visit timestamps and simulated FOV repositioning sampled from cached
     frames, no new inference run. Every visit carries
     "provenance": "replay_simulated". This is the spec's own required
     label ("Replay of recorded time-lapse (simulated visits)").

  2. The underlying *images* this demo replays are also fabricated. The
     real Slice 1b compute cache (cache/) has no cached time-lapse
     sequence — none of its three sources (synthetic tiles, EVICAN,
     AutoQC-Bench) are sequences, so sequence_id/frame_idx are unset for
     all 4,246 real cached rows (see culture/replay.py's module
     docstring). Real C2C12 sequences are deferred to a future nb/03
     Colab pass. Until then, this module builds a small fixture cache
     with a hand-shaped logistic growth curve standing in for a real one,
     through the exact on-disk schema culture.cache.Cache itself writes
     (see culture/cache.py's ImageRecord / _build_seg / _build_qc /
     _write_manifest column names) so culture.replay.build_replay_visits
     runs the identical code path it will run against real sequence data
     later — only the source rows are fake, not the mechanism.

Confluency/QC/quality numbers in this tab are therefore fabricated, not
measured — never call them a result.
"""

from __future__ import annotations

import hashlib
import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from culture.cache import Cache
from culture.growth import GrowthResult, fit_growth
from culture.history import History
from culture.replay import build_replay_lineage_with_passage
from demo.theme import ACCENT, BG_CARD, BORDER, TEXT_PRIMARY, TEXT_SECONDARY

TARGET_PCT = 80.0  # §6.3 default "time to target" confluency shown in the tab

LINEAGE_ID = "demo-flask-01"
PARENT_SEGMENT_ID = "demo-flask-01-seg-A"
CHILD_SEGMENT_ID = "demo-flask-01-seg-B"
PARENT_SEQUENCE_ID = "demo_seq_parent"
CHILD_SEQUENCE_ID = "demo_seq_child"
FLASK_ID = "demo-flask-01"

QUALITY_FAIL_COLOR = "#ef4444"
CHILD_SEGMENT_COLOR = "#f59e0b"

_cache_by_key: dict[tuple, tuple] = {}


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
    anomaly_frame: int | None = None, blurry_frame: int | None = None,
) -> None:
    """Writes one fixture sequence's rows into cache_dir's parquet tables,
    appending to whatever is already there. anomaly_frame (if given) gets
    logits that argmax to "contamination_suspected" instead of "normal";
    blurry_frame (if given) gets quality metrics below configs/quality.yaml's
    blur floor, so it fails the quality gate — both exist so the demo
    timeline actually shows the app's failure-handling paths, not just a
    clean growth curve."""
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
        if anomaly_frame is not None and i == anomaly_frame:
            base_logits = np.array([-1.0, 4.5, -0.5, -1.0])  # argmax "contamination_suspected"
        noisy_logits = base_logits + rng.normal(0, 0.3, 4)
        logits_rows.append({
            "image_sha256": sha, "crop_spec": "full", "model_name": "qc", "model_version": "qc_effnetb0_v1",
            "logits": json.dumps([float(x) for x in noisy_logits]),
        })

        if blurry_frame is not None and i == blurry_frame:
            quality_rows.append({
                "blur_laplacian_var": 42.0, "exposure_mean": 128.4, "uniformity_block_std": 0.4,
                "image_sha256": sha, "model_name": "quality", "model_version": "quality_v1",
            })
        else:
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


def _plot_timeline(rows: list[dict], growth_results: dict[str, GrowthResult] | None = None) -> "plt.Figure":
    """§6.3: 'fitted curve + band, target line, ... per segment' layered onto
    the existing raw-visit plot. "band" here is a 90% fit uncertainty band on
    the fitted mean curve, not a prediction band (see culture/growth.py).
    growth_results is {segment_id: GrowthResult} (see _fit_segment_growth) —
    only OK results with a t_grid get an overlay; INSUFFICIENT_DATA/
    FIT_FAILED segments show raw visits only, same as before growth fitting
    existed."""
    plt.close("all")
    growth_results = growth_results or {}
    visits = [r for r in rows if r.get("row_type") == "visit"]
    events = [r for r in rows if r.get("row_type") == "event"]

    fig, ax = plt.subplots(figsize=(9, 4.0), dpi=140)
    fig.patch.set_facecolor(BG_CARD)
    ax.set_facecolor(BG_CARD)

    seg_colors = {PARENT_SEGMENT_ID: ACCENT, CHILD_SEGMENT_ID: CHILD_SEGMENT_COLOR}
    seg_labels = {PARENT_SEGMENT_ID: "Segment A (parent)", CHILD_SEGMENT_ID: "Segment B (post-passage)"}

    any_fit_ok = False
    for seg_id, color in seg_colors.items():
        seg_visits = sorted((v for v in visits if v["segment_id"] == seg_id), key=lambda v: v["timestamp"])
        if not seg_visits:
            continue
        times = pd.to_datetime([v["timestamp"] for v in seg_visits], format="ISO8601")
        means = [v["confluency_mean"] for v in seg_visits]
        sds = [v["confluency_sd"] for v in seg_visits]
        ax.plot(times, means, "-", color=color, linewidth=1.5, alpha=0.8, label=seg_labels[seg_id])
        ax.errorbar(times, means, yerr=sds, fmt="none", ecolor=color, alpha=0.3, capsize=2)

        result = growth_results.get(seg_id)
        if result is not None and result.status == "OK" and result.t_grid_hours:
            any_fit_ok = True
            t0 = pd.Timestamp(result.t0_timestamp)
            grid_times = t0 + pd.to_timedelta(result.t_grid_hours, unit="h")
            ax.plot(grid_times, result.y_grid["mean"], "--", color=color, linewidth=1.2, alpha=0.9, zorder=2)
            if result.y_grid["lo"] is not None:
                ax.fill_between(grid_times, result.y_grid["lo"], result.y_grid["hi"], color=color, alpha=0.13, linewidth=0, zorder=1)

        for v, t, m in zip(seg_visits, times, means):
            passed = v.get("quality", {}).get("pass", True)
            flag = v.get("class_pred")
            if not passed:
                ax.scatter([t], [m], marker="x", s=64, color=QUALITY_FAIL_COLOR, linewidth=1.8, zorder=4)
            elif flag == "contamination_suspected":
                ax.scatter([t], [m], marker="o", s=56, facecolor=color, edgecolor=QUALITY_FAIL_COLOR,
                           linewidth=2.0, zorder=4)
            else:
                ax.scatter([t], [m], marker="o", s=42, facecolor=color, edgecolor=color, zorder=3)

    for e in events:
        if e.get("event_type") == "PASSAGED":
            parent_visits = [v for v in visits if v["segment_id"] == e["segment_id"]]
            if parent_visits:
                t = pd.to_datetime(max(v["timestamp"] for v in parent_visits), format="ISO8601")
                ax.axvline(t, color=TEXT_SECONDARY, linestyle="--", linewidth=1.1, alpha=0.7)
                ax.annotate("PASSAGED", xy=(t, 96), xytext=(4, 0), textcoords="offset points",
                            color=TEXT_SECONDARY, fontsize=8.5)

    if any_fit_ok:
        ax.axhline(TARGET_PCT, color=TEXT_SECONDARY, linestyle=":", linewidth=1.0, alpha=0.55, zorder=0)
        ax.annotate(f"target {TARGET_PCT:.0f}%", xy=(1.0, TARGET_PCT), xycoords=("axes fraction", "data"),
                    xytext=(4, 2), textcoords="offset points", color=TEXT_SECONDARY, fontsize=7.5)

    ax.set_ylim(0, 100)
    ax.set_ylabel("Confluency (%)", color=TEXT_PRIMARY, fontsize=9.5)
    ax.tick_params(colors=TEXT_SECONDARY, labelsize=8.5)
    for spine in ax.spines.values():
        spine.set_color(BORDER)
    ax.grid(True, color=BORDER, alpha=0.4, linewidth=0.6)
    ax.legend(loc="lower right", frameon=False, fontsize=8.5, labelcolor=TEXT_SECONDARY)
    fig.autofmt_xdate()
    fig.tight_layout()
    return fig


def _rows_to_table(rows: list[dict]) -> pd.DataFrame:
    out = []
    for r in rows:
        if r.get("row_type") == "visit":
            q = r.get("quality", {})
            out.append({
                "row_type": "visit",
                "segment_id": r["segment_id"],
                "timestamp": r["timestamp"],
                "confluency_mean_pct": round(r["confluency_mean"], 1),
                "n_fov": r["n_fov"],
                "class_pred": r.get("class_pred"),
                "quality_pass": q.get("pass"),
                "quality_reasons": ", ".join(q.get("reasons", [])) or "-",
                "provenance": r.get("provenance", ""),
                "record_hash": (r.get("record_hash", "") or "")[:10] + "…",
            })
        else:
            out.append({
                "row_type": "event",
                "segment_id": r.get("segment_id"),
                "timestamp": "",
                "confluency_mean_pct": None,
                "n_fov": None,
                "class_pred": r.get("event_type"),
                "quality_pass": None,
                "quality_reasons": "-",
                "provenance": r.get("provenance", ""),
                "record_hash": (r.get("record_hash", "") or "")[:10] + "…",
            })
    return pd.DataFrame(out)


def _segment_trend_visits(rows: list[dict], segment_id: str) -> list[dict]:
    """Same filter culture.history.History.trend_windows() applies (quality-
    passing visits only) — growth.py itself does not re-filter (see its
    docstring), so the caller must, same as any other caller would against a
    real History."""
    return sorted(
        (r for r in rows if r.get("row_type") == "visit" and r.get("segment_id") == segment_id
         and r.get("quality", {}).get("pass", True)),
        key=lambda r: r["timestamp"],
    )


def _fit_segment_growth(rows: list[dict], segment_id: str, seed: int) -> GrowthResult:
    visits = _segment_trend_visits(rows, segment_id)
    return fit_growth(visits, target_pct=TARGET_PCT, seed=seed)


def _growth_summary_markdown(growth_results: dict[str, GrowthResult]) -> str:
    """§6.3: 'T* with interval, chosen model + AIC, area doubling time, per
    segment' as text alongside the plot's overlay."""
    seg_labels = {PARENT_SEGMENT_ID: "Segment A (parent)", CHILD_SEGMENT_ID: "Segment B (post-passage)"}
    lines = [f"**Growth model** (fabricated demo data; target {TARGET_PCT:.0f}% confluency):"]
    for seg_id, label in seg_labels.items():
        result = growth_results.get(seg_id)
        if result is None or result.status != "OK":
            status = result.status if result is not None else "NO_DATA"
            lines.append(f"- **{label}**: `{status}` — not enough trend-eligible visits yet to fit a growth curve.")
            continue

        aic_bits = ", ".join(f"{m} AIC={f['aic']:.1f}" for m, f in result.fits.items())
        if result.t_star_status == "REACHED":
            if result.t_star_interval_hours is not None:
                lo, hi = result.t_star_interval_hours
                t_star_str = f"T* = {result.t_star_hours:.0f}h, 90% CI [{lo:.0f}h, {hi:.0f}h]"
            else:
                t_star_str = f"T* = {result.t_star_hours:.0f}h (interval unavailable — too few successful bootstrap refits)"
        else:
            t_star_str = f"T* = `NOT_REACHED` (fitted carrying capacity below {TARGET_PCT:.0f}%)"
        doubling_str = (
            f"{result.area_doubling_time_hours:.1f}h" if result.area_doubling_time_hours is not None
            else "n/a (non-growing at start of window)"
        )
        lines.append(
            f"- **{label}**: **{result.chosen_model}** chosen ({aic_bits}) &middot; {t_star_str} "
            f"&middot; area doubling time (early phase) {doubling_str}"
        )
    lines.append(
        "\n*The shaded band is a 90% fit uncertainty band on the fitted curve (bootstrap), not a "
        "prediction band for a single future reading. T*'s interval covers residual-bootstrap "
        "uncertainty within the chosen model only, not uncertainty in logistic-vs-Gompertz model "
        "selection itself — see culture/growth.py's docstring and scripts/backtest_growth.py.*"
    )
    return "\n".join(lines)


def _summary_markdown(rows: list[dict], chain_ok: bool, bad_line: int | None) -> str:
    n_visits = sum(1 for r in rows if r.get("row_type") == "visit")
    n_events = sum(1 for r in rows if r.get("row_type") == "event")
    n_segments = len({r["segment_id"] for r in rows if r.get("segment_id")})
    n_failed = sum(
        1 for r in rows if r.get("row_type") == "visit" and not r.get("quality", {}).get("pass", True)
    )
    chain_note = "hash chain intact" if chain_ok else f"hash chain **BROKEN at line {bad_line}**"
    return (
        f"**{n_visits} visits** across {n_segments} segment{'s' if n_segments != 1 else ''} &middot; "
        f"**{n_events} events** &middot; **{n_failed} quality-gate failure(s)** excluded from trend "
        f"computations &middot; {chain_note}"
    )


def build_demo_timeline(work_dir: str, seed: int = 0):
    """Builds (once per (work_dir, seed) -- the History/Cache I/O, replay,
    and growth fit are cached after that, see below) a fixture cache,
    replays it through culture.replay into a culture.history.History, fits
    culture.growth per segment, and returns (fig, history_dataframe,
    summary_markdown, growth_markdown). Deterministic given seed, same
    guarantee culture.replay.build_replay_visits and culture.growth.fit_growth
    already make."""
    key = (work_dir, seed)
    if key in _cache_by_key:
        chain_ok, bad_line, rows, growth_results = _cache_by_key[key]
        return (
            _plot_timeline(rows, growth_results), _rows_to_table(rows),
            _summary_markdown(rows, chain_ok, bad_line), _growth_summary_markdown(growth_results),
        )

    rng = np.random.default_rng(seed)
    cache_dir = os.path.join(work_dir, f"flask_timeline_cache_{seed}")
    cache = Cache(cache_dir)  # real Cache -- replay.py only ever reads its parquet tables

    # Parent: seeded low, grows toward near-confluent over ~6 days, then passaged.
    _write_sequence(
        cache_dir, PARENT_SEQUENCE_ID, start="2026-06-01T08:00:00Z",
        n_frames=16, hours_apart=9.0, low=8.0, high=88.0, t_mid_frac=0.5, k=0.09,
        rng=rng, blurry_frame=6,
    )
    # Child: reseeded lower after the split, grows again; one frame near the
    # end is flagged contamination_suspected.
    _write_sequence(
        cache_dir, CHILD_SEQUENCE_ID, start="2026-06-08T08:00:00Z",
        n_frames=10, hours_apart=9.0, low=14.0, high=70.0, t_mid_frac=0.5, k=0.11,
        rng=rng, anomaly_frame=8,
    )

    visits, event = build_replay_lineage_with_passage(
        cache, lineage_id=LINEAGE_ID,
        parent_sequence_id=PARENT_SEQUENCE_ID, parent_segment_id=PARENT_SEGMENT_ID,
        child_sequence_id=CHILD_SEQUENCE_ID, child_segment_id=CHILD_SEGMENT_ID,
        flask_id=FLASK_ID, split_ratio=0.2, seed=seed,
    )

    history_dir = os.path.join(work_dir, f"flask_timeline_history_{seed}")
    h = History(history_dir)
    h.append_event(lineage_id=LINEAGE_ID, segment_id=PARENT_SEGMENT_ID, event_type="SEEDED", seeding_density=6000)
    for v in sorted((v for v in visits if v["segment_id"] == PARENT_SEGMENT_ID), key=lambda v: v["timestamp"]):
        h.append_visit(v)
    h.append_event(lineage_id=LINEAGE_ID, segment_id=event["segment_id"], event_type="PASSAGED",
                    split_ratio=event["split_ratio"], child_segment_ids=event["child_segment_ids"])
    for v in sorted((v for v in visits if v["segment_id"] == CHILD_SEGMENT_ID), key=lambda v: v["timestamp"]):
        h.append_visit(v)

    chain_ok, bad_line = h.verify_lineage(LINEAGE_ID)
    rows = h.get_lineage(LINEAGE_ID)
    growth_results = {
        seg_id: _fit_segment_growth(rows, seg_id, seed)
        for seg_id in (PARENT_SEGMENT_ID, CHILD_SEGMENT_ID)
    }

    # Cache the raw rows + growth results, not the rendered (fig, df, ...)
    # tuple: fig is a matplotlib Figure and _plot_timeline() opens with
    # plt.close("all") on every call, which would close a *previously
    # cached* Figure the next time a different seed's build reuses this code
    # path -- e.g. seed 2 (cached) -> seed 3 (built, cached) -> seed 2 again
    # (cache hit) would hand Gradio seed 2's now-closed Figure. Rebuilding
    # fig/table/summary fresh from cached rows on every call avoids that
    # entirely. growth_results ARE safe to cache directly (plain
    # dataclasses/dicts, nothing closable) -- refitting them (curve_fit +
    # 500-resample bootstrap, twice per segment) is real compute, not a
    # cheap re-render, so caching that (not just the rows) keeps a
    # cache-hit fast. History/Cache I/O and get_model_versions() also only
    # happen once per (work_dir, seed).
    _cache_by_key[key] = (chain_ok, bad_line, rows, growth_results)
    return (
        _plot_timeline(rows, growth_results), _rows_to_table(rows),
        _summary_markdown(rows, chain_ok, bad_line), _growth_summary_markdown(growth_results),
    )
