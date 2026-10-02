"""scripts/confluency_profiles.py on synthetic numbers: the pre-registered pick,
band, fold and call rules (results/confluency_profiles.md), with no images."""

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
cp = pytest.importorskip("confluency_profiles")


def rows_with_offset(n, offset_logit, split, unit=lambda k: f"u{k}", seed=0):
    """Readings whose best cutoff is `offset_logit`: reading(t) = gt - 4*(t - offset) + noise."""
    rng = np.random.default_rng(seed)
    out = []
    for k in range(n):
        gt = float(rng.uniform(5, 95))
        noise = float(rng.normal(0, 1.0))
        curve = [float(np.clip(gt - 4 * (t - offset_logit) + noise, 0, 100)) for t in cp.GRID]
        out.append({"name": f"{split}{k}", "split": split, "unit": unit(k), "gt": gt, "curve": curve, "conf0": 0.9})
    return out


def test_pick_finds_the_offset_and_breaks_ties_towards_zero():
    rows = rows_with_offset(60, -2.0, "calib")
    R = np.array([r["curve"] for r in rows]); gt = np.array([r["gt"] for r in rows])
    assert cp.GRID[cp.pick(R, gt)] == -2.0
    flat = np.ones((5, len(cp.GRID))) * 50.0
    assert cp.GRID[cp.pick(flat, np.full(5, 50.0))] == 0.0


def test_band_is_the_conformal_quantile_and_needs_nine_images():
    rows = rows_with_offset(40, -1.0, "calib")
    R = np.array([r["curve"] for r in rows]); gt = np.array([r["gt"] for r in rows])
    q, res = cp.band(R, gt, np.array([r["unit"] for r in rows]))
    k = int(np.ceil(0.9 * 41))
    assert q == pytest.approx(np.sort(res)[k - 1])
    q8, _ = cp.band(R[:8], gt[:8], np.arange(8))
    assert q8 is None


def test_fixed_split_and_leave_one_population_out():
    rows = rows_with_offset(30, -1.5, "calib") + rows_with_offset(30, -1.5, "test", seed=1)
    (cal, test), = cp.folds(rows)
    assert len(cal) == 30 and len(test) == 30
    lopo = [dict(r, split="lopo", unit=f"pop{k % 3}") for k, r in enumerate(rows)]
    fs = cp.folds(lopo)
    assert len(fs) == 3 and sorted(i for _, t in fs for i in t) == list(range(60))
    for cal, test in fs:
        assert not set(cal) & set(test)


def test_evaluate_reports_every_criterion():
    rows = rows_with_offset(60, -1.0, "calib") + rows_with_offset(60, -1.0, "test", seed=2)
    prof = cp.fit(rows)
    out = cp.evaluate(rows, prof, {"x": prof}, None)
    assert set(out["acceptance"]) == {"A1", "A2", "A3", "A4", "A5"}
    assert out["acceptance"]["A1"][0] == "pass" and out["profile"]["mae"] < out["shipped"]["mae"]
    c = out["calls"][80.0]
    assert 0 <= c["profile_review"] <= 1 and c["profile_agree"] >= 0.95


def test_call_rule():
    calls = cp.call(np.array([90.0, 82.0, 74.0]), 5.0, 80.0)
    assert list(calls) == ["passage", "review", "continue"]


def test_rle_round_trip():
    m = np.zeros((cp.CROP, cp.CROP), np.uint8); m[10:20, 30:90] = 1
    flat = m.ravel(); runs, v, n = [], 0, 0
    for x in flat:
        if x == v: n += 1
        else: runs.append(n); v ^= 1; n = 1
    runs.append(n)
    assert (cp.rle_decode(runs, cp.CROP, cp.CROP) == m).all()
