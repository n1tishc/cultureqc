"""
cultureqc.calibration — temperature scaling for the QC classifier
(cultureQC_upgrade_spec.md §8.1, Phase A5).

Class probabilities get trended over time (A6's failure-class residual), so
they have to be calibrated. One scalar temperature T divides the cached
logits before the softmax; it's fit on the synthetic val split by
minimising negative log-likelihood (scripts/calibrate_classifier.py) and
stored in configs/calibration.yaml together with the qc model_version it
was fit for. It is only applied to logits from that model_version: new
weights need a new fit.

ECE here is the usual top-label ECE with equal-width confidence bins.
classwise_ece() is the one-vs-rest version per class, which is what matters
for trending a single class's probability.

Usage:
    from culture.calibration import load_calibration, calibrated_probs
    cal = load_calibration()                  # None if no config
    probs = calibrated_probs(logits, cal, model_version="qc_effnetb0_v1")
"""

from __future__ import annotations

import os

import numpy as np
import yaml
from scipy.optimize import minimize_scalar

DEFAULT_CALIBRATION_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "configs", "calibration.yaml"
)
N_BINS = 15
_LOG_T_BOUNDS = (np.log(0.05), np.log(20.0))


def softmax(logits: np.ndarray, temperature: float = 1.0) -> np.ndarray:
    z = np.asarray(logits, dtype=np.float64) / temperature
    z = z - z.max(axis=-1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=-1, keepdims=True)


def nll(logits: np.ndarray, labels: np.ndarray, temperature: float = 1.0) -> float:
    z = np.asarray(logits, dtype=np.float64) / temperature
    z = z - z.max(axis=1, keepdims=True)
    log_probs = z - np.log(np.exp(z).sum(axis=1, keepdims=True))
    return float(-log_probs[np.arange(len(labels)), labels].mean())


def fit_temperature(logits: np.ndarray, labels: np.ndarray) -> float:
    """T minimising NLL on (logits, labels), searched over log T in
    [log 0.05, log 20]. Deterministic (bounded Brent)."""
    res = minimize_scalar(lambda lt: nll(logits, labels, np.exp(lt)), bounds=_LOG_T_BOUNDS, method="bounded",
                          options={"xatol": 1e-6})
    return float(np.exp(res.x))


def _binned_gap(conf: np.ndarray, correct: np.ndarray, n_bins: int) -> tuple[float, list[dict]]:
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    # bin i holds (edges[i], edges[i+1]]; confidence 0 goes in the first bin
    idx = np.clip(np.searchsorted(edges, conf, side="left") - 1, 0, n_bins - 1)
    total, bins = 0.0, []
    for i in range(n_bins):
        m = idx == i
        if not m.any():
            continue
        acc, mean_conf = float(correct[m].mean()), float(conf[m].mean())
        total += m.sum() / len(conf) * abs(acc - mean_conf)
        bins.append({"lo": float(edges[i]), "hi": float(edges[i + 1]), "n": int(m.sum()),
                     "accuracy": acc, "confidence": mean_conf})
    return float(total), bins


def ece(probs: np.ndarray, labels: np.ndarray, n_bins: int = N_BINS) -> float:
    """Top-label expected calibration error."""
    probs = np.asarray(probs)
    return _binned_gap(probs.max(axis=1), (probs.argmax(axis=1) == labels).astype(float), n_bins)[0]


def reliability_bins(probs: np.ndarray, labels: np.ndarray, n_bins: int = N_BINS) -> list[dict]:
    probs = np.asarray(probs)
    return _binned_gap(probs.max(axis=1), (probs.argmax(axis=1) == labels).astype(float), n_bins)[1]


def classwise_ece(probs: np.ndarray, labels: np.ndarray, n_bins: int = N_BINS) -> list[float]:
    """One-vs-rest ECE per class: bins p(class k) against 'label == k'."""
    probs = np.asarray(probs)
    return [_binned_gap(probs[:, k], (labels == k).astype(float), n_bins)[0] for k in range(probs.shape[1])]


def load_calibration(path: str = DEFAULT_CALIBRATION_PATH) -> dict | None:
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return yaml.safe_load(f)


def calibration_config_hash(path: str = DEFAULT_CALIBRATION_PATH) -> str:
    from culture.records import hash_file
    return hash_file(path)


def calibrated_probs(logits, calibration: dict | None, model_version: str) -> tuple[np.ndarray, bool]:
    """(probabilities, calibrated?). Temperature-scaled only when a
    calibration exists for this exact model_version; otherwise the plain
    softmax and False."""
    if calibration is not None and calibration.get("model_version") == model_version:
        return softmax(logits, float(calibration["temperature"])), True
    return softmax(logits), False
