"""Offline experimental growth deficits against a predeclared frozen prefix.

This module neither establishes that a baseline is healthy nor emits alerts,
calibrated probabilities or uncertainty. Its inputs must be one chronological
acquisition window. A caller must choose the baseline cutoff and analysis
settings independently of fault labels and onset, before evaluating outcomes.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from numbers import Real
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from culture.growth import (
    MODEL_FNS,
    PARAM_NAMES,
    _CROP_FRAC_RE,
    _DEFAULT_CONFIG_PATH,
    _NOISE_CONFIG_PATH,
    _fit_one,
    _weights,
)


@dataclass(frozen=True)
class FrozenGrowthSignal:
    visit_id: str | None
    timestamp: str
    status: str
    baseline_end: str
    baseline_reason: str
    n_baseline: int = 0
    reference_id: str | None = None
    chosen_model: str | None = None
    observed: float | None = None
    expected: float | None = None
    level_deficit_pp: float | None = None
    horizon_start: str | None = None
    horizon_hours: float | None = None
    expected_growth_pp: float | None = None
    observed_growth_pp: float | None = None
    growth_deficit_pp: float | None = None
    growth_fraction: float | None = None


def _timestamp(value: str) -> pd.Timestamp:
    timestamp = pd.Timestamp(value)
    if pd.isna(timestamp) or timestamp.tzinfo is None:
        raise ValueError("timestamps must be valid and timezone-aware")
    return timestamp.tz_convert("UTC")


def _provenance(visit: dict) -> str | None:
    if not visit.get("segment_id"):
        return None
    for field in ("model_versions", "config_hashes"):
        if not isinstance(visit.get(field), dict) or not visit[field]:
            return None
    metadata = {field: visit.get(field) for field in (
        "lineage_id", "segment_id", "flask_id", "model_versions", "config_hashes",
        "source_dataset", "source_sequence_id", "provenance",
        "n_fov", "pixel_size_um", "imager_id", "setup_id",
    )}
    crop_fractions = set()
    for spec in visit.get("crop_specs") or []:
        match = _CROP_FRAC_RE.search(spec)
        crop_fractions.add(match.group(1) if match else "unmeasured")
    metadata["crop_fractions"] = sorted(crop_fractions)
    return json.dumps(metadata, sort_keys=True, allow_nan=False)


def _finite_number(value) -> bool:
    if isinstance(value, bool) or not isinstance(value, Real):
        return False
    try:
        return math.isfinite(value)
    except (OverflowError, TypeError, ValueError):
        return False


def _observation_status(visit: dict) -> str | None:
    quality = visit.get("quality")
    if not isinstance(quality, dict) or quality.get("pass") is not True:
        return "QUALITY_FAILED"
    value = visit.get("confluency_mean")
    deviation = visit.get("confluency_sd", 0.0)
    if not _finite_number(value) or not 0 <= value <= 100:
        return "INVALID_OBSERVATION"
    if deviation is not None and (
        not _finite_number(deviation) or not 0 <= deviation <= 100
    ):
        return "INVALID_OBSERVATION"
    return None


def frozen_growth_series(
    visits: list[dict],
    *,
    baseline_end: str,
    baseline_reason: str,
    horizon_hours: float = 12.0,
    max_gap_hours: float = 6.0,
    min_expected_growth_pp: float = 1.0,
    config_path: str = _DEFAULT_CONFIG_PATH,
    noise_config_path: str = _NOISE_CONFIG_PATH,
) -> list[FrozenGrowthSignal]:
    """Return one serializable dataclass per input visit, without mutation.

    Baseline observations at or before ``baseline_end`` are never scored.
    The first later visit freezes an AIC-selected logistic/Gompertz fit using
    only eligible baseline observations. Missing provenance or any acquisition
    window change permanently invalidates that reference for this call, even
    if a later visit restores the original metadata. Start a new, explicitly
    chosen baseline in a separate call for a new window.

    Growth uses the exact trailing horizon, linearly interpolating its start
    only between eligible, already observed neighbors. Any rejected visit or
    gap exceeding ``max_gap_hours`` in that interval suppresses growth scores.
    ``min_expected_growth_pp`` is an explicit exploratory denominator guard,
    not a biological stall cutoff. No ratio is emitted below that guard.
    """
    if not isinstance(baseline_reason, str) or not baseline_reason.strip():
        raise ValueError("baseline_reason must record a predeclared selection rationale")
    for name, value in (("horizon_hours", horizon_hours), ("max_gap_hours", max_gap_hours),
                        ("min_expected_growth_pp", min_expected_growth_pp)):
        if not _finite_number(value) or value <= 0:
            raise ValueError(f"{name} must be a finite positive number, not a boolean")
    cutoff = _timestamp(baseline_end)
    times = [_timestamp(visit["timestamp"]) for visit in visits]
    if any(current <= previous for previous, current in zip(times, times[1:])):
        raise ValueError("visits must be strictly chronological with no duplicate timestamps")
    if not visits:
        return []
    config_bytes = {"growth": Path(config_path).read_bytes(), "noise": Path(noise_config_path).read_bytes()}
    cfg, noise_cfg = yaml.safe_load(config_bytes["growth"]), yaml.safe_load(config_bytes["noise"])
    config_hashes = {name: hashlib.sha256(content).hexdigest() for name, content in config_bytes.items()}
    origin = times[0]
    hours = np.array([(timestamp - origin).total_seconds() / 3600.0 for timestamp in times])
    signature = _provenance(visits[0])
    invalid_window = False
    baseline_indices = []
    statuses = []
    fit_status = None
    reference = None
    model = None
    parameters = None
    results = []

    for index, visit in enumerate(visits):
        provenance = _provenance(visit)
        invalid_window = invalid_window or provenance is None or provenance != signature
        observation_status = _observation_status(visit)
        statuses.append(observation_status)
        base = {
            "visit_id": visit.get("visit_id"), "timestamp": visit["timestamp"],
            "baseline_end": baseline_end, "baseline_reason": baseline_reason,
            "observed": float(visit["confluency_mean"]) if observation_status is None else None,
        }
        if times[index] <= cutoff:
            if observation_status is None and not invalid_window:
                baseline_indices.append(index)
            status = observation_status or ("WINDOW_CHANGED" if invalid_window else "BASELINE_WARMUP")
            results.append(FrozenGrowthSignal(**base, status=status, n_baseline=len(baseline_indices)))
            continue
        if invalid_window:
            results.append(FrozenGrowthSignal(**base, status=observation_status or "WINDOW_CHANGED",
                                              n_baseline=len(baseline_indices)))
            continue
        if fit_status is None:
            fit_status = "INSUFFICIENT_BASELINE"
            minimum = cfg["minimum_data"]
            baseline_hours = hours[baseline_indices]
            if (len(baseline_indices) >= minimum["min_visits"] and
                    baseline_hours[-1] - baseline_hours[0] >= minimum["min_hours"]):
                fit_status = "INSUFFICIENT_BASELINE_COVERAGE"
                if (np.all(np.diff(baseline_hours) <= max_gap_hours) and
                        (cutoff - times[baseline_indices[-1]]).total_seconds() / 3600 <= max_gap_hours):
                    baseline = [visits[position] for position in baseline_indices]
                    observed = np.array([entry["confluency_mean"] for entry in baseline], dtype=float)
                    weights = _weights(baseline, noise_cfg, cfg["fallback_crop_frac"])
                    candidates = {}
                    for candidate in MODEL_FNS:
                        fitted = _fit_one(candidate, baseline_hours, observed, weights, cfg["bounds"])
                        if fitted is not None and np.isfinite(fitted["aic"]):
                            candidates[candidate] = fitted
                    fit_status = "FIT_FAILED"
                    if candidates:
                        model = min(candidates, key=lambda candidate: candidates[candidate]["aic"])
                        parameters = candidates[model]["params"]
                        payload = {
                            "baseline_end": baseline_end, "baseline_reason": baseline_reason,
                            "provenance": signature, "config_hashes": config_hashes,
                            "baseline": [{"timestamp": entry["timestamp"],
                                          "confluency_mean": entry["confluency_mean"],
                                          "weight": float(weight)}
                                         for entry, weight in zip(baseline, weights)],
                            "model": model, "parameters": parameters,
                        }
                        reference = hashlib.sha256(json.dumps(payload, sort_keys=True,
                                                               allow_nan=False).encode()).hexdigest()
                        fit_status = "OK"
        base.update(n_baseline=len(baseline_indices), reference_id=reference, chosen_model=model)
        if observation_status is not None or fit_status != "OK":
            results.append(FrozenGrowthSignal(**base, status=observation_status or fit_status))
            continue
        model_parameters = [parameters[name] for name in PARAM_NAMES[model]]
        expected = float(MODEL_FNS[model](np.array([hours[index]]), *model_parameters)[0])
        base.update(expected=expected, level_deficit_pp=expected - base["observed"])
        start_hours = hours[index] - horizon_hours
        anchor = int(np.searchsorted(hours[:index + 1], start_hours, side="right")) - 1
        if anchor < 0:
            results.append(FrozenGrowthSignal(**base, status="INSUFFICIENT_COVERAGE"))
            continue
        interval_hours = hours[anchor:index + 1]
        if (any(statuses[position] is not None for position in range(anchor, index + 1)) or
                np.any(np.diff(interval_hours) > max_gap_hours)):
            results.append(FrozenGrowthSignal(**base, status="INSUFFICIENT_COVERAGE"))
            continue
        interval_values = [visits[position]["confluency_mean"] for position in range(anchor, index + 1)]
        start_observed = float(np.interp(start_hours, interval_hours, interval_values))
        start_expected = float(MODEL_FNS[model](np.array([start_hours]), *model_parameters)[0])
        expected_growth = expected - start_expected
        observed_growth = base["observed"] - start_observed
        base.update(horizon_start=(origin + pd.Timedelta(hours=start_hours)).isoformat(),
                    horizon_hours=float(horizon_hours), expected_growth_pp=expected_growth,
                    observed_growth_pp=observed_growth, growth_deficit_pp=expected_growth - observed_growth)
        if expected_growth < min_expected_growth_pp:
            results.append(FrozenGrowthSignal(**base, status="LOW_EXPECTED_GROWTH"))
            continue
        results.append(FrozenGrowthSignal(**base, status="OK", growth_fraction=observed_growth / expected_growth))
    return results
