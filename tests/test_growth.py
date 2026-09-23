"""
culture/growth.py tests (cultureQC_upgrade.md §6.1, §6.4 acceptance:
"NOT_REACHED / INSUFFICIENT_DATA / multi-segment unit tests").

Synthetic, hand-constructed visit windows with known ground-truth logistic
parameters — these test that the fitting/prediction *code* is correct
(recovers a known curve, returns the right status in each edge case,
deterministic given a seed), not a claim about real growth data. See
scripts/backtest_growth.py for the (also synthetic, explicitly labeled)
harness-correctness backtest — real C2C12 numbers are still pending real
cached sequences (culture/replay.py's own docstring).
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import numpy as np
import yaml

from culture.growth import GrowthResult, _sigma_fov_for_visit, fit_growth, growth_config_hash

_NOISE_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "configs", "noise.yaml"
)


def _make_visit(t_hours: float, confluency: float, segment_id: str = "S1", sd: float = 1.0, crop_frac: str = "0.25") -> dict:
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    ts = (base + timedelta(hours=t_hours)).isoformat()
    return {
        "segment_id": segment_id,
        "timestamp": ts,
        "confluency_mean": confluency,
        "confluency_sd": sd,
        "crop_specs": [f"crop_f{crop_frac}_s1_k{i}" for i in range(3)],
    }


def _logistic_series(K: float, r: float, t0: float, hours: list[float]) -> list[float]:
    return [float(K / (1.0 + np.exp(-r * (h - t0)))) for h in hours]


def _visits(K: float, r: float, t0: float, hours: list[float], segment_id: str = "S1") -> list[dict]:
    y = _logistic_series(K, r, t0, hours)
    return [_make_visit(h, c, segment_id=segment_id) for h, c in zip(hours, y)]


# -- sigma_fov / weighting: reuses the measured noise.yaml model, not a guess --

def test_sigma_fov_uses_measured_noise_config():
    noise_cfg = yaml.safe_load(open(_NOISE_CONFIG_PATH))
    visit = {"crop_specs": ["crop_f0.25_s1_k0", "crop_f0.25_s1_k1"], "confluency_mean": 50.0}
    sigma = _sigma_fov_for_visit(visit, noise_cfg, fallback_frac=0.5)
    entry = noise_cfg["crop_fracs"]["0.25"]
    assert abs(sigma - (entry["intercept"] + entry["slope"] * 50.0)) < 1e-9


def test_sigma_fov_falls_back_for_unparseable_crop_spec():
    noise_cfg = yaml.safe_load(open(_NOISE_CONFIG_PATH))
    visit = {"crop_specs": ["full"], "confluency_mean": 30.0}
    sigma = _sigma_fov_for_visit(visit, noise_cfg, fallback_frac=0.5)
    entry = noise_cfg["crop_fracs"]["0.5"]
    assert abs(sigma - (entry["intercept"] + entry["slope"] * 30.0)) < 1e-9


# -- fit correctness --------------------------------------------------------

def test_fit_recovers_logistic_shape_and_predicts_target_crossing():
    hours = list(range(0, 145, 12))  # 13 visits, 144h span
    visits = _visits(K=90, r=0.05, t0=60, hours=hours)
    result = fit_growth(visits, target_pct=80.0, seed=0, n_boot=50)

    assert result.status == "OK"
    assert result.chosen_model in ("logistic", "gompertz")
    assert "logistic" in result.fits and "gompertz" in result.fits  # "report both"
    assert result.t_star_status == "REACHED"
    assert result.t_star_hours is not None

    true_t_star = 60 - np.log(90 / 80 - 1) / 0.05
    assert abs(result.t_star_hours - true_t_star) < 15  # sanity tolerance, not precision claim

    assert result.t_star_interval_hours is not None
    lo, hi = result.t_star_interval_hours
    assert lo <= result.t_star_hours <= hi

    assert result.area_doubling_time_hours is not None and result.area_doubling_time_hours > 0
    assert result.y_grid is not None and result.y_grid["lo"] is not None and result.y_grid["hi"] is not None


def test_not_reached_when_target_above_carrying_capacity():
    hours = list(range(0, 145, 12))
    visits = _visits(K=40, r=0.05, t0=60, hours=hours)  # plateaus well under target
    result = fit_growth(visits, target_pct=80.0, seed=0, n_boot=50)

    assert result.status == "OK"
    assert result.t_star_status == "NOT_REACHED"
    assert result.t_star_hours is None
    assert result.t_star_interval_hours is None


def test_insufficient_data_too_few_visits():
    hours = [0, 12, 24]  # 3 < min_visits=5
    visits = _visits(K=90, r=0.05, t0=30, hours=hours)
    result = fit_growth(visits, seed=0)
    assert result.status == "INSUFFICIENT_DATA"
    assert result.n_visits == 3


def test_insufficient_data_too_short_span():
    hours = [0, 2, 4, 6, 8]  # 5 visits, span 8h < min_hours=12
    visits = _visits(K=90, r=0.05, t0=30, hours=hours)
    result = fit_growth(visits, seed=0)
    assert result.status == "INSUFFICIENT_DATA"


def test_insufficient_data_empty():
    result = fit_growth([], seed=0)
    assert result.status == "INSUFFICIENT_DATA"
    assert result.n_visits == 0


def test_multi_segment_independent():
    hours = list(range(0, 145, 12))
    good = _visits(K=90, r=0.06, t0=50, hours=hours, segment_id="A")
    poor = _visits(K=90, r=0.015, t0=100, hours=hours, segment_id="B")

    ra = fit_growth(good, target_pct=80.0, seed=0, n_boot=50)
    rb = fit_growth(poor, target_pct=80.0, seed=0, n_boot=50)

    assert ra.segment_id == "A" and rb.segment_id == "B"
    assert ra.status == "OK" and rb.status == "OK"
    if rb.t_star_status == "REACHED":
        assert rb.t_star_hours > ra.t_star_hours  # slower grower crosses later


def test_deterministic_given_seed():
    hours = list(range(0, 145, 12))
    visits = _visits(K=90, r=0.05, t0=60, hours=hours)
    r1 = fit_growth(visits, target_pct=80.0, seed=7, n_boot=50)
    r2 = fit_growth(visits, target_pct=80.0, seed=7, n_boot=50)
    assert r1.t_star_interval_hours == r2.t_star_interval_hours
    assert r1.y_grid == r2.y_grid
    assert r1.n_bootstrap_success == r2.n_bootstrap_success


def test_different_seed_bootstrap_interval_differs():
    # A perfectly noiseless synthetic curve fits exactly (residuals ~0), so
    # the bootstrap has nothing to resample and both seeds degenerate to the
    # same point interval — that's correct behavior, not what this test is
    # after. Add small fixed noise so real residuals (and seed-dependent
    # bootstrap variance) exist, same as any real fit would have.
    hours = list(range(0, 145, 12))
    y = _logistic_series(K=90, r=0.05, t0=60, hours=hours)
    noise_rng = np.random.default_rng(123)
    y_noisy = [c + n for c, n in zip(y, noise_rng.normal(0, 2.0, len(y)))]
    visits = [_make_visit(h, c) for h, c in zip(hours, y_noisy)]

    r1 = fit_growth(visits, target_pct=80.0, seed=1, n_boot=50)
    r2 = fit_growth(visits, target_pct=80.0, seed=2, n_boot=50)
    assert r1.t_star_interval_hours != r2.t_star_interval_hours


def test_growth_config_hash_is_stable_sha256():
    h1 = growth_config_hash()
    h2 = growth_config_hash()
    assert h1 == h2
    assert len(h1) == 64


def test_result_is_growth_result_dataclass():
    hours = list(range(0, 145, 12))
    visits = _visits(K=90, r=0.05, t0=60, hours=hours)
    result = fit_growth(visits, seed=0, n_boot=20)
    assert isinstance(result, GrowthResult)
