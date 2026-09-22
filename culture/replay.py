"""
cultureqc.replay — build realistic visit streams from cached time-lapse
sequences, entirely from the compute cache, no model inference at replay
time (cultureQC_upgrade.md §5.4).

Reads confluency/logits/quality rows straight from a culture.cache.Cache —
no image ever touched, no model ever loaded — so replay runs on CPU in
seconds. Every visit this module produces carries
`"provenance": "replay_simulated"` so downstream consumers (the app's Flask
timeline tab, any report) can label it correctly; the spec requires the UI
say "Replay of recorded time-lapse (simulated visits)" wherever this feeds
it.

**Requires** the source sequence's cached images to have real `sequence_id`
and `frame_idx` set (culture.cache.ImageRecord's own fields) — the actual
Slice 1b Colab pass built every ImageRecord without them (all blank/-1),
since none of its three image sets (synthetic tiles, EVICAN, AutoQC-Bench)
are sequences. That's fine for those sets; it means replay cannot run
against the current real cache at all, only against a cache built with
sequence_id/frame_idx populated — a fixture for now (tests/test_replay.py),
real C2C12/CTC sequences once nb/03 caches them with these fields set
correctly (see docs/DATASETS.md).

Usage:
    from culture.replay import build_replay_visits
    visits = build_replay_visits(cache, sequence_id="c2c12_seq_04",
                                  lineage_id="L1", segment_id="S1",
                                  flask_id="flask-1", seed=0)
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import yaml

from culture.model_versions import get_model_versions
from culture.quality import config_hash as quality_config_hash
from culture.quality import evaluate_thresholds

_DEFAULT_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "configs", "replay.yaml"
)


def _load_config(config_path: str) -> dict:
    with open(config_path) as f:
        return yaml.safe_load(f)


def replay_config_hash(config_path: str = _DEFAULT_CONFIG_PATH) -> str:
    from culture.records import hash_file
    return hash_file(config_path)


def _sequence_frames(cache, sequence_id: str) -> pd.DataFrame:
    """The sequence's cached frames, ordered by frame_idx, with real
    timestamps (required — see module docstring)."""
    images = pd.read_parquet(os.path.join(cache.dir, "images.parquet"))
    frames = images[images.sequence_id == sequence_id].copy()
    if len(frames) == 0:
        raise ValueError(f"no cached frames with sequence_id={sequence_id!r}")
    if (frames.frame_idx < 0).any() or (frames.timestamp == "").any():
        raise ValueError(
            f"sequence_id={sequence_id!r} has frames with unset frame_idx/timestamp — "
            "replay needs both (see module docstring)"
        )
    return frames.sort_values("frame_idx").reset_index(drop=True)


def _sample_visit_timestamps(frames: pd.DataFrame, config: dict, rng: np.random.Generator, n_visits: int | None) -> list[pd.Timestamp]:
    """Irregular visit times (§5.4: 'sample visit times with jitter ...,
    not every frame'), within the sequence's actual time span."""
    frame_times = pd.to_datetime(frames["timestamp"])
    t0, t1 = frame_times.min(), frame_times.max()
    mean_gap = timedelta(hours=config["timing"]["mean_interval_hours"])
    jitter = timedelta(hours=config["timing"]["jitter_hours"])

    times = []
    t = t0
    while t <= t1 and (n_visits is None or len(times) < n_visits):
        times.append(t)
        gap_hours = config["timing"]["mean_interval_hours"] + rng.uniform(-1, 1) * config["timing"]["jitter_hours"]
        t = t + timedelta(hours=max(0.1, gap_hours))
    return times


def _nearest_frame(frames: pd.DataFrame, visit_time: pd.Timestamp) -> pd.Series:
    frame_times = pd.to_datetime(frames["timestamp"])
    idx = (frame_times - visit_time).abs().idxmin()
    return frames.loc[idx]


def _sample_crops_for_frame(cache, image_sha: str, config: dict, rng: np.random.Generator) -> pd.DataFrame:
    """1..N of the frame's cached crops (§5.4: 'simulated repositioning:
    each visit samples 1-N of the cached crops for that frame')."""
    conf = cache.load_confluency()
    crops = conf[(conf.image_sha256 == image_sha) & (conf.model_name == "seg") & (conf.crop_spec != "full")]
    if len(crops) == 0:
        # No crops cached for this frame (crop_fracs=() at build time) —
        # fall back to the full-frame row alone, one simulated "reposition."
        full = conf[(conf.image_sha256 == image_sha) & (conf.model_name == "seg") & (conf.crop_spec == "full")]
        return full.iloc[:1]
    lo, hi = config["repositioning"]["min_crops_per_visit"], config["repositioning"]["max_crops_per_visit"]
    n = int(rng.integers(lo, min(hi, len(crops)) + 1))
    idx = rng.choice(crops.index, size=n, replace=False)
    return crops.loc[idx]


def _class_probs_and_pred(cache, image_sha: str) -> tuple[dict | None, str | None]:
    from culture.qc import CLASS_NAMES

    logits_df = cache.load_logits()
    row = logits_df[(logits_df.image_sha256 == image_sha) & (logits_df.model_name == "qc")]
    if len(row) == 0:
        return None, None
    logits = np.array(row.iloc[0]["logits"], dtype=np.float64)
    exp = np.exp(logits - logits.max())
    probs = exp / exp.sum()
    class_probs = {name: float(p) for name, p in zip(CLASS_NAMES, probs)}
    class_pred = CLASS_NAMES[int(np.argmax(probs))]
    return class_probs, class_pred


def _quality_for_frame(cache, image_sha: str) -> dict:
    q = cache.load_quality()
    row = q[q.image_sha256 == image_sha]
    if len(row) == 0:
        return {"blur": 0.0, "mean_intensity": 0.0, "uniformity": 0.0, "pass": False, "reasons": ["no_cached_quality_metrics"]}
    r = row.iloc[0]
    result = evaluate_thresholds(r["blur_laplacian_var"], r["exposure_mean"], r["uniformity_block_std"])
    return result.to_dict()


def build_replay_visits(
    cache,
    sequence_id: str,
    lineage_id: str,
    segment_id: str,
    flask_id: str,
    seed: int = 0,
    n_visits: int | None = None,
    config_path: str = _DEFAULT_CONFIG_PATH,
) -> list[dict]:
    """Deterministic given `seed` (and the underlying cache's contents, which
    don't change): the same inputs always produce the same visit stream —
    same sampled timestamps, same sampled crops. Returns a list of
    visit_summary dicts (schemas/visit_summary.v1.json-shaped, plus a
    'provenance' field the schema permits but doesn't require)."""
    config = _load_config(config_path)
    rng = np.random.default_rng(seed)

    frames = _sequence_frames(cache, sequence_id)
    visit_times = _sample_visit_timestamps(frames, config, rng, n_visits)
    model_versions = get_model_versions()
    cfg_hashes = {"quality.yaml": quality_config_hash(), "replay.yaml": replay_config_hash(config_path)}

    visits = []
    for visit_time in visit_times:
        frame = _nearest_frame(frames, visit_time)
        sha = frame["image_sha256"]

        sampled_crops = _sample_crops_for_frame(cache, sha, config, rng)
        fov_confluency = [float(p) for p in sampled_crops["pct"]]
        crop_specs = list(sampled_crops["crop_spec"])
        n_fov = len(fov_confluency)

        class_probs, class_pred = _class_probs_and_pred(cache, sha)
        quality = _quality_for_frame(cache, sha)

        visits.append({
            "visit_id": str(uuid.uuid4()),
            "lineage_id": lineage_id,
            "segment_id": segment_id,
            "flask_id": flask_id,
            "timestamp": visit_time.tz_localize("UTC").isoformat() if visit_time.tzinfo is None else visit_time.isoformat(),
            "image_sha256": [sha] * n_fov,  # all sampled crops are sub-regions of this one cached frame
            "fov_confluency": fov_confluency,
            "confluency_mean": float(np.mean(fov_confluency)) if fov_confluency else 0.0,
            "confluency_sd": float(np.std(fov_confluency)) if len(fov_confluency) > 1 else 0.0,
            "n_fov": n_fov,
            "class_probs": class_probs,
            "class_pred": class_pred,
            "calibrated": False,
            "anomaly_score": None,
            "anomaly_score_density_bin": None,
            "quality": quality,
            "model_versions": model_versions,
            "config_hashes": cfg_hashes,
            # Extra, schema-permitted (not required) provenance fields:
            "provenance": "replay_simulated",
            "source_sequence_id": sequence_id,
            "source_frame_idx": int(frame["frame_idx"]),
            "crop_specs": crop_specs,
        })
    return visits


def build_replay_lineage_with_passage(
    cache,
    lineage_id: str,
    parent_sequence_id: str,
    parent_segment_id: str,
    child_sequence_id: str,
    child_segment_id: str,
    flask_id: str,
    split_ratio: float = 0.2,
    seed: int = 0,
    n_visits_parent: int | None = None,
    n_visits_child: int | None = None,
    config_path: str = _DEFAULT_CONFIG_PATH,
) -> tuple[list[dict], dict]:
    """§5.4: 'simulated passage: optionally end a segment at a target
    confluency and start a child segment from an earlier frame of another
    sequence (labelled simulated).' Composes two build_replay_visits() runs
    (parent sequence, child sequence — an EARLIER frame of a *different*
    cached sequence, standing in for 'the culture was split and one part
    kept growing') with a PASSAGED event between them, both segments in the
    same lineage. Returns (all_visits_in_order, passaged_event_dict) — the
    caller appends both to a History."""
    parent_visits = build_replay_visits(
        cache, parent_sequence_id, lineage_id, parent_segment_id, flask_id,
        seed=seed, n_visits=n_visits_parent, config_path=config_path,
    )
    child_visits = build_replay_visits(
        cache, child_sequence_id, lineage_id, child_segment_id, flask_id,
        seed=seed + 1, n_visits=n_visits_child, config_path=config_path,
    )
    event = {
        "row_type": "event",
        "lineage_id": lineage_id,
        "segment_id": parent_segment_id,
        "event_type": "PASSAGED",
        "split_ratio": split_ratio,
        "child_segment_ids": [child_segment_id],
        "provenance": "replay_simulated",
    }
    return parent_visits + child_visits, event
