"""
culture/anomaly.py and scripts/eval_anomaly.py's scoring loop: coreset
determinism, the bin-merge rule, and that no frame is ever scored against a
bank holding its own base sequence's patches.
"""

from __future__ import annotations

import importlib.util
import os

import numpy as np
import pandas as pd

from culture.anomaly import bin_index, greedy_coreset, image_score, merge_bins, nn_distance

_SPEC = importlib.util.spec_from_file_location(
    "eval_anomaly", os.path.join(os.path.dirname(__file__), "..", "scripts", "eval_anomaly.py"))
ea = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(ea)


def _unit(x):
    return (x / np.linalg.norm(x, axis=1, keepdims=True)).astype(np.float32)


def test_coreset_is_deterministic_and_covers_outliers():
    rng = np.random.default_rng(0)
    x = _unit(np.r_[rng.normal(0, 0.01, (500, 16)) + 1.0, -np.ones((1, 16))])  # one far point
    a, b = greedy_coreset(x, 20, seed=3, proj_dim=8), greedy_coreset(x, 20, seed=3, proj_dim=8)
    assert np.array_equal(a, b) and len(set(a)) == 20
    assert 500 in set(greedy_coreset(x, 5, seed=0, proj_dim=8))
    assert len(greedy_coreset(x, 10_000, seed=0)) == len(x)


def test_nn_distance_and_image_score():
    bank = _unit(np.eye(4)[:2])
    q = _unit(np.array([[1.0, 0, 0, 0], [0, 0, 1.0, 0]]))
    assert np.allclose(nn_distance(q, bank), [0.0, 1.0], atol=1e-6)
    assert image_score(np.arange(200, dtype=float), top_frac=0.01) == 198.5  # mean of the top 2


def test_bins_merge_until_each_has_enough_sequences():
    edges = [0.0, 20.0, 40.0, 60.0, 80.0, 100.0]
    assert merge_bins(edges, [10, 10, 6, 1, 0], 3) == [0.0, 20.0, 40.0, 100.0]
    assert merge_bins(edges, [1, 10, 10, 10, 10], 3) == [0.0, 40.0, 60.0, 80.0, 100.0]
    assert merge_bins(edges, [5] * 5, 3) == edges
    assert [bin_index(p, [0.0, 20.0, 40.0, 100.0]) for p in (0.0, 19.9, 20.0, 57.0, 100.0)] == [0, 0, 1, 2, 2]


def test_no_frame_is_scored_against_its_own_sequence():
    rng = np.random.default_rng(0)
    rows, patches = [], {}
    for k, (seq, split) in enumerate([("t0", "tuning"), ("t1", "tuning"), ("t2", "tuning"), ("h0", "heldout")]):
        centre = rng.normal(size=32)
        for i in range(4):
            sha = f"{seq}_{i}"
            # every frame of a sequence is (almost) the same patch set: its own sequence would score ~0
            patches[sha] = _unit(centre + rng.normal(0, 1e-3, (8, 32))).astype(np.float16)
            rows.append({"image_sha256": sha, "base_sequence_id": seq, "split": split, "kind": "normal",
                         "pct": 10.0 + 25 * (i % 2)})
    frames = pd.DataFrame(rows)
    cfg = {**ea.DEFAULTS, "coreset_frac": 1.0, "proj_dim": 8}
    edges = [0.0, 20.0, 100.0]
    scored, banks = ea.score_frames(frames, patches, edges, cfg)
    assert (scored.score_binned > 0.05).all() and (scored.score_global > 0.05).all()
    assert sum(len(v) for k, v in banks.items() if k != "global") == 3 * 4 * 8  # full bank: all tuning patches
