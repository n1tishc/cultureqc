"""
culture/growth.py one-step-ahead expected value (cultureQC_upgrade_spec.md
§6.1 "Expected value for SPC", feeds A6).

Synthetic logistic streams with known truth. Noise comes from a test noise
config (sigma_fov = 1 + 0.05 * pct), not configs/noise.yaml: that file's
fit is measured almost entirely below 10% confluency (EVICAN/AutoQC crops)
and extrapolates to sigma ~ pct at 30-80%, which would make these streams
mostly clipping. These check the code, including that the predictive SD is
on the right scale when the model is right; they say nothing about real
C2C12 growth.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np
import pytest
import yaml

from culture.growth import one_step_ahead_series, predict_next

_NOISE = {"intercept": 1.0, "slope": 0.05}
_BASE = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _sigma(pct: float) -> float:
    return _NOISE["intercept"] + _NOISE["slope"] * pct


def _logistic(t, K=85.0, r=0.08, t0=45.0):
    return K / (1.0 + np.exp(-r * (t - t0)))


def _visit(t: float, fov: list[float], segment_id: str = "S1", passed: bool = True) -> dict:
    fov = np.asarray(fov, dtype=float)
    return {
        "visit_id": f"v{t:.2f}", "segment_id": segment_id,
        "timestamp": (_BASE + timedelta(hours=t)).isoformat(),
        "confluency_mean": float(fov.mean()), "confluency_sd": float(fov.std()) if len(fov) > 1 else 0.0,
        "n_fov": len(fov), "crop_specs": [f"crop_f0.25_s1_k{i}" for i in range(len(fov))],
        "quality": {"pass": passed, "reasons": [] if passed else ["blur_below_threshold"]},
    }


def _noisy_stream(rng, n_fov=3, cadence=6.0, span=84.0, stall_at=None, K=None, r=None, t0=None):
    """Logistic truth; each FOV reading = truth + N(0, sigma_fov(truth)).
    stall_at: from then on the culture advances at 10% speed."""
    K = rng.uniform(70, 95) if K is None else K
    r = rng.uniform(0.05, 0.12) if r is None else r
    t0 = rng.uniform(30, 55) if t0 is None else t0
    visits, t = [], 0.0
    while t <= span:
        tt = t if stall_at is None or t < stall_at else stall_at + 0.1 * (t - stall_at)
        truth = _logistic(tt, K, r, t0)
        visits.append(_visit(t, np.clip(truth + rng.normal(0, _sigma(truth), n_fov), 0, 100)))
        t += cadence * (1 + rng.uniform(-0.25, 0.25))
    return visits


@pytest.fixture(autouse=True)
def _test_noise_config(tmp_path, monkeypatch):
    """Point predict_next / one_step_ahead_series at the test noise config."""
    import culture.growth as growth

    path = tmp_path / "noise.yaml"
    path.write_text(yaml.safe_dump({"crop_fracs": {"0.25": dict(_NOISE), "0.5": dict(_NOISE)}}))
    for fn in ("predict_next", "one_step_ahead_series"):
        defaults = list(getattr(growth, fn).__defaults__)
        idx = getattr(growth, fn).__code__.co_varnames.index("noise_config_path") - (
            getattr(growth, fn).__code__.co_argcount - len(defaults))
        defaults[idx] = str(path)
        monkeypatch.setattr(getattr(growth, fn), "__defaults__", tuple(defaults))


def _clean_stream(hours, **kw):
    return [_visit(h, [_logistic(h, **kw)] * 3) for h in hours]


def test_insufficient_data_until_minimum_prior_visits():
    visits = _clean_stream([0, 6, 12, 18, 24, 30, 36, 42])
    preds = one_step_ahead_series(visits, n_boot=30)
    assert [p.status for p in preds[:5]] == ["INSUFFICIENT_DATA"] * 5  # < 5 priors
    assert all(p.status == "OK" for p in preds[5:])
    assert [p.n_prior for p in preds] == list(range(8))
    assert preds[0].hours_ahead is None and preds[1].hours_ahead == pytest.approx(6.0)


def test_expected_value_tracks_a_clean_curve():
    hours = list(range(0, 85, 6))
    preds = one_step_ahead_series(_clean_stream(hours), n_boot=30)
    ok = [(p, h) for p, h in zip(preds, hours) if p.status == "OK"]
    assert len(ok) >= 8
    for p, h in ok[3:]:  # after a few fits the curve is pinned down
        assert p.expected == pytest.approx(_logistic(h), abs=3.0)


def test_obs_sd_uses_expected_confluency_and_fov_count():
    prior = _clean_stream([0, 6, 12, 18, 24, 30, 36])
    t_new = 42.0
    expected_truth = _logistic(t_new)
    crashed = _visit(t_new, [2.0, 2.0, 2.0])  # a crash reading must not shrink its own SD
    p3 = predict_next(prior, crashed, n_boot=30)
    assert p3.status == "OK"
    assert p3.obs_sd == pytest.approx(_sigma(p3.expected) / np.sqrt(3))
    assert p3.expected == pytest.approx(expected_truth, abs=3.0)
    assert _sigma(p3.expected) > 2 * _sigma(2.0)  # evaluated at the observed 2%, the SD would shrink a lot
    assert p3.z == pytest.approx((2.0 - p3.expected) / p3.predictive_sd)
    assert p3.z < -5

    p_none = predict_next(prior, crashed, n_boot=30, fov_scaling="none")
    assert p_none.obs_sd == pytest.approx(_sigma(p_none.expected))
    one_fov = predict_next(prior, _visit(t_new, [2.0]), n_boot=30)
    assert one_fov.obs_sd == pytest.approx(_sigma(one_fov.expected))
    assert p3.predictive_sd == pytest.approx(np.hypot(p3.fit_sd, p3.obs_sd))


def test_quality_failed_visits_get_no_residual_and_are_not_priors():
    visits = _clean_stream([0, 6, 12, 18, 24, 30, 36, 42, 48])
    bad = dict(visits[6], confluency_mean=0.0, quality={"pass": False, "reasons": ["blur_below_threshold"]})
    worse = dict(bad, confluency_mean=99.0)
    a = one_step_ahead_series(visits[:6] + [bad] + visits[7:], n_boot=30)
    b = one_step_ahead_series(visits[:6] + [worse] + visits[7:], n_boot=30)
    assert a[6].status == "QUALITY_FAILED" and a[6].z is None
    assert [p.n_prior for p in a] == [0, 1, 2, 3, 4, 5, 6, 6, 7]
    # its reading can't move any other prediction
    for pa, pb in zip(a, b):
        if pa.status == "OK":
            assert (pa.expected, pa.predictive_sd) == (pb.expected, pb.predictive_sd)


def test_deterministic_and_seeded():
    visits = _noisy_stream(np.random.default_rng(3))
    a = one_step_ahead_series(visits, seed=7, n_boot=30)
    b = one_step_ahead_series(visits, seed=7, n_boot=30)
    c = one_step_ahead_series(visits, seed=8, n_boot=30)
    assert a == b
    assert [p.fit_sd for p in a] != [p.fit_sd for p in c]


def test_rejects_mixed_segments_and_out_of_order_visits():
    visits = _clean_stream([0, 6, 12, 18, 24, 30])
    with pytest.raises(ValueError, match="more than one segment"):
        one_step_ahead_series(visits[:3] + [dict(v, segment_id="S2") for v in visits[3:]])
    with pytest.raises(ValueError, match="not after"):
        predict_next(visits[1:], visits[0])


def test_stall_shows_in_the_first_visits_after_onset():
    """Same noise draws, with and without a stall at 45 h. The one-step
    residual only carries the stall for a few visits: after that the refit
    bends into a plateau and absorbs it (so SPC has to accumulate early,
    e.g. CUSUM). Compare the sum of z over the 4 visits after onset."""
    def post_onset_sum(stall_at):
        visits = _noisy_stream(np.random.default_rng(11), stall_at=stall_at, K=85.0, r=0.1, t0=40.0)
        preds = one_step_ahead_series(visits, seed=0, n_boot=50)
        hours = [(datetime.fromisoformat(v["timestamp"]) - _BASE).total_seconds() / 3600 for v in visits]
        after = [p.z for p, h in zip(preds, hours) if p.status == "OK" and h > 45.0][:4]
        assert len(after) == 4
        return sum(after)

    stalled, normal = post_onset_sum(45.0), post_onset_sum(None)
    assert stalled < -5
    assert stalled < normal - 5


def test_z_is_standard_scale_when_the_model_is_right():
    """Pooled one-step z over many noisy logistic streams (noise = the
    test sigma_fov, 3 FOVs, 6 h cadence ± 25%) should have SD ≈ 1.
    If predictive_sd were missing a term, SD(z) would sit well above 1 and
    an SPC false-alarm rate tuned on it would mean nothing. Measured here:
    SD 1.23, mean 0.15 over 285 predictions (slightly over-dispersed: the
    bootstrap is conditional on the AIC-chosen model). With only fit_sd the
    SD is 2.14; with only obs_sd, 1.72."""
    rng = np.random.default_rng(0)
    zs = []
    for s in range(30):
        zs += [p.z for p in one_step_ahead_series(_noisy_stream(rng), seed=s, n_boot=50) if p.status == "OK"]
    zs = np.asarray(zs)
    assert len(zs) > 200
    assert 0.8 <= zs.std(ddof=1) <= 1.3
    assert abs(zs.mean()) < 0.2
