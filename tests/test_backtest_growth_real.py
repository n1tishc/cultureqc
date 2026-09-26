"""
scripts/backtest_growth.py --source c2c12 (A1) on the tiny replay-fleet
fixture: truth crossings, the no-repositioning arm, and that every crossing
sequence is counted in every cell (no outcome dropped).
"""

from __future__ import annotations

import importlib.util
import os
import sys

import numpy as np
import pandas as pd

from test_replay_fleet import _fleet_cache, _run

_SPEC = importlib.util.spec_from_file_location(
    "backtest_growth", os.path.join(os.path.dirname(__file__), "..", "scripts", "backtest_growth.py"))
bg = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(bg)


def test_truth_crossing_interpolates_and_reports_fragility():
    s = pd.DataFrame({"hours": [0.0, 1.0, 2.0, 3.0], "pct": [40.0, 48.0, 52.0, 49.0]})
    tr = bg.truth_crossing(s, 50.0)
    assert np.isclose(tr["true_hours"], 1.5)
    assert tr["frames_after"] == 2 and tr["frames_after_at_or_above"] == 1 and np.isclose(tr["margin_pct"], 2.0)
    assert bg.truth_crossing(s, 60.0) is None


def test_without_repositioning_reads_the_full_frame():
    v = {"image_sha256": ["a", "a", "a"], "fov_confluency": [1.0, 2.0, 3.0], "confluency_mean": 2.0,
         "confluency_sd": 0.8, "n_fov": 3, "crop_specs": ["crop_f0.25_s0_k0"] * 3}
    (w,) = bg._without_repositioning([v], {"a": 42.0})
    assert w["confluency_mean"] == 42.0 and w["n_fov"] == 1 and w["crop_specs"] == ["full"] and w["confluency_sd"] == 0


def _grow(cache):
    """Replace the fixture's random confluency with logistic growth (K 70%, midpoint 50 h)."""
    images = pd.read_parquet(os.path.join(cache, "images.parquet"))
    conf = pd.read_parquet(os.path.join(cache, "confluency.parquet"))
    rng = np.random.default_rng(0)
    frame = dict(zip(images.image_sha256, images.frame_idx))
    hours = conf.image_sha256.map(frame).astype(float) * 2.0
    full = 70.0 / (1.0 + np.exp(-0.08 * (hours - 50.0)))
    noise = np.where(conf.crop_spec == "full", 0.0, rng.normal(0, 1.0, len(conf)))
    conf["pct"] = np.clip(full + noise, 0, 100)
    conf.to_parquet(os.path.join(cache, "confluency.parquet"), index=False)


def test_real_backtest_counts_every_crossing_sequence(tmp_path, monkeypatch):
    cache = _fleet_cache(tmp_path)
    _grow(cache)
    _run(monkeypatch, cache, str(tmp_path / "results"), str(tmp_path / "visits"))
    split = str(tmp_path / "results" / "replay_fleet_split.csv")
    df, truths, held = bg.run_real_backtest(cache, split, n_boot=20, check_jsonl=False)

    assert set(held) == set(pd.read_csv(split).query("kind == 'base' and split == 'heldout'").sequence_id)
    assert len(truths) == len(held) * len(bg.REAL_TARGETS)
    allowed = {"predicted", "not_reached", "cut_not_reached", "cut_at_or_after_crossing",
               "fit_insufficient_data", "fit_fit_failed"}
    assert set(df.outcome) <= allowed
    n_cells = 3 * len(bg.CUT_OFFSETS)  # 1 crop, 3 crops, full frame
    for (sid, target), g in df.groupby(["sequence_id", "target_pct"]):
        assert truths[(truths.sequence_id == sid) & (truths.target_pct == target)].crosses.item()
        assert len(g) == n_cells * 2  # x 2 cadences
    crossing = truths[truths.crosses]
    assert len(crossing) and (df.outcome == "predicted").any()
    assert len(df) == len(crossing) * n_cells * 2
