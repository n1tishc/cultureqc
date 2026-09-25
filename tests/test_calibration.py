"""
culture/calibration.py tests (cultureQC_upgrade_spec.md §8.1, Phase A5), plus
replay applying the stored temperature only for the matching model_version.
"""

from __future__ import annotations

import numpy as np
import pytest
import yaml

from culture.calibration import (calibrated_probs, classwise_ece, ece, fit_temperature, nll, reliability_bins,
                                 softmax)


def _overconfident_set(true_T: float, n: int = 4000, k: int = 4, seed: int = 0):
    """Labels drawn from softmax(z); the model reports z * true_T, i.e. it is
    overconfident by exactly true_T. Fitting should recover true_T."""
    rng = np.random.default_rng(seed)
    z = rng.normal(0, 2.0, size=(n, k))
    p = softmax(z)
    labels = np.array([rng.choice(k, p=row) for row in p])
    return z * true_T, labels


def test_fit_temperature_recovers_known_overconfidence():
    logits, labels = _overconfident_set(true_T=2.5)
    T = fit_temperature(logits, labels)
    assert T == pytest.approx(2.5, rel=0.08)
    assert nll(logits, labels, T) < nll(logits, labels, 1.0)
    assert ece(softmax(logits, T), labels) < ece(softmax(logits), labels)


def test_fit_temperature_is_near_one_for_calibrated_logits():
    logits, labels = _overconfident_set(true_T=1.0, seed=1)
    assert fit_temperature(logits, labels) == pytest.approx(1.0, rel=0.08)


def test_ece_hand_computed():
    # two bins used: conf 0.9 (4 samples, 3 right) and conf 0.6 (2 samples, 2 right)
    probs = np.array([[0.9, 0.1]] * 4 + [[0.6, 0.4]] * 2)
    labels = np.array([0, 0, 0, 1, 0, 0])
    expected = 4 / 6 * abs(0.75 - 0.9) + 2 / 6 * abs(1.0 - 0.6)
    assert ece(probs, labels, n_bins=10) == pytest.approx(expected)
    bins = reliability_bins(probs, labels, n_bins=10)
    assert [b["n"] for b in bins] == [2, 4]


def test_ece_zero_when_confident_and_right():
    probs = np.eye(3)[[0, 1, 2, 1]]
    assert ece(probs, np.array([0, 1, 2, 1])) == 0.0
    assert classwise_ece(probs, np.array([0, 1, 2, 1])) == [0.0, 0.0, 0.0]


def test_classwise_ece_sees_a_miscalibrated_minority_class():
    # class 1 always gets p=0.3 but is never the label: its one-vs-rest ECE is 0.3
    probs = np.array([[0.7, 0.3]] * 10)
    labels = np.zeros(10, dtype=int)
    assert classwise_ece(probs, labels, n_bins=10)[1] == pytest.approx(0.3)


def test_calibrated_probs_only_for_matching_model_version():
    logits = np.array([3.0, 0.0, -1.0, 0.5])
    cal = {"temperature": 2.0, "model_version": "qc_v1"}
    p, ok = calibrated_probs(logits, cal, "qc_v1")
    assert ok and np.allclose(p, softmax(logits / 2.0))
    p, ok = calibrated_probs(logits, cal, "qc_v2")
    assert not ok and np.allclose(p, softmax(logits))
    p, ok = calibrated_probs(logits, None, "qc_v1")
    assert not ok and np.allclose(p, softmax(logits))


# -- replay applies it --------------------------------------------------------

from test_replay import fixture_cache  # noqa: E402,F401  (the replay fixture cache)

def _replay(fixture_cache, cal_path):
    from culture.replay import build_replay_visits
    return build_replay_visits(fixture_cache, "fixture_seq_1", "L1", "S1", "flask-1", seed=0,
                               calibration_path=str(cal_path))


def test_replay_applies_temperature_for_matching_version(fixture_cache, tmp_path):
    cal_path = tmp_path / "calibration.yaml"
    cal_path.write_text(yaml.safe_dump({"temperature": 3.0, "model_version": "qc_effnetb0_v1"}))
    raw = _replay(fixture_cache, tmp_path / "missing.yaml")
    cal = _replay(fixture_cache, cal_path)
    assert all(not v["calibrated"] for v in raw) and all(v["calibrated"] for v in cal)
    assert all("calibration.yaml" in v["config_hashes"] for v in cal)
    assert all("calibration.yaml" not in v["config_hashes"] for v in raw)
    for r, c in zip(raw, cal):
        pr, pc = np.array(list(r["class_probs"].values())), np.array(list(c["class_probs"].values()))
        logits = np.log(pr)  # softmax is shift-invariant, so log p recovers the logits up to a constant
        assert np.allclose(pc, softmax(logits / 3.0))
        assert r["class_pred"] == c["class_pred"]  # temperature never changes the argmax


def test_replay_ignores_calibration_for_other_model_version(fixture_cache, tmp_path):
    cal_path = tmp_path / "calibration.yaml"
    cal_path.write_text(yaml.safe_dump({"temperature": 3.0, "model_version": "qc_some_other"}))
    visits = _replay(fixture_cache, cal_path)
    assert all(not v["calibrated"] for v in visits)
