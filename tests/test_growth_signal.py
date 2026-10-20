"""Offline frozen-reference regression fixtures, not biological validation."""

from datetime import datetime, timedelta, timezone
from dataclasses import asdict
import copy
import json
from pathlib import Path

import numpy as np
import pytest
import yaml

from culture.growth_signal import frozen_growth_series


def _visit(hours, observed=None, **changes):
    truth = 85.0 / (1.0 + np.exp(-0.08 * (hours - 45.0)))
    visit = {
        "visit_id": f"visit-{hours}",
        "segment_id": "segment-1",
        "timestamp": (datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(hours=hours)).isoformat(),
        "confluency_mean": float(truth if observed is None else observed),
        "confluency_sd": 0.0,
        "n_fov": 3,
        "crop_specs": ["crop_f0.25_s1_k0"],
        "quality": {"pass": True},
        "model_versions": {"confluency": "fixture-v1"},
        "config_hashes": {"quality": "fixture-quality-v1"},
        "source_dataset": "synthetic",
    }
    visit.update(changes)
    return visit


@pytest.fixture
def noise_path(tmp_path):
    destination = tmp_path / "noise.yaml"
    destination.write_text(yaml.safe_dump({"crop_fracs": {"0.25": {"intercept": 1.0, "slope": 0.05}}}))
    return str(destination)


def test_frozen_reference_does_not_absorb_a_sustained_stall(noise_path):
    healthy = [_visit(hours) for hours in range(0, 97, 6)]
    plateau = _visit(42)["confluency_mean"]
    stalled = [_visit(hours, plateau if hours > 42 else None) for hours in range(0, 97, 6)]
    settings = {"baseline_end": _visit(36)["timestamp"], "baseline_reason": "Fixed 36-hour acquisition prefix",
                "noise_config_path": noise_path}
    healthy_signals = frozen_growth_series(healthy, **settings)
    stalled_signals = frozen_growth_series(stalled, **settings)
    assert stalled_signals[-1].expected == pytest.approx(healthy_signals[-1].expected, abs=1e-8)
    assert stalled_signals[-1].expected - stalled_signals[-1].observed > 30.0
    assert stalled_signals[-1].growth_fraction == pytest.approx(0.0)
    assert healthy_signals[-1].growth_fraction == pytest.approx(1.0, abs=0.01)


def _signals(visits, noise_path, **changes):
    settings = {"baseline_end": _visit(36)["timestamp"], "baseline_reason": "Fixed 36-hour acquisition prefix",
                "noise_config_path": noise_path}
    settings.update(changes)
    return frozen_growth_series(visits, **settings)


def test_prefix_is_identical_when_future_values_and_boundaries_change(noise_path):
    visits = [_visit(hours) for hours in range(0, 85, 6)]
    prefix = _signals(visits[:10], noise_path)
    future = [_visit(hours, 0.0, model_versions={"confluency": "changed"}) for hours in range(60, 85, 6)]
    assert _signals(visits[:10] + future, noise_path)[:10] == prefix
    assert _signals(visits[:5], noise_path) == _signals(visits, noise_path)[:5]
    assert all(signal.expected is None for signal in prefix[:7])
    assert all(signal.reference_id is None for signal in prefix[:7])


def test_quality_rejection_does_not_change_reference_and_coverage_recovers(noise_path):
    visits = [_visit(hours) for hours in range(0, 85, 6)]
    visits[8] = _visit(48, 0.0, quality={"pass": False})
    original = _signals(visits, noise_path)
    visits[8]["confluency_mean"] = 99.0
    changed = _signals(visits, noise_path)
    assert original == changed
    assert original[8].status == "QUALITY_FAILED"
    assert original[8].expected is None
    assert [signal.status for signal in original[9:11]] == ["INSUFFICIENT_COVERAGE"] * 2
    assert original[11].status == "OK"
    assert all(signal.growth_fraction is None for signal in original[8:11])


def test_failed_baseline_reading_never_enters_fit(noise_path):
    visits = [_visit(hours) for hours in range(0, 73, 3)]
    visits[4] = _visit(12, 0.0, quality={"pass": False})
    original = _signals(visits, noise_path)
    visits[4]["confluency_mean"] = 100.0
    assert _signals(visits, noise_path) == original
    assert original[-1].n_baseline == 12
    assert original[-1].status == "OK"


def test_gap_suppresses_growth_until_a_full_covered_horizon(noise_path):
    visits = [_visit(hours) for hours in list(range(0, 43, 6)) + [60, 66, 72, 78]]
    signals = _signals(visits, noise_path)
    assert signals[8].status == signals[9].status == "INSUFFICIENT_COVERAGE"
    assert signals[10].status == "OK"
    assert signals[10].horizon_start == _visit(60)["timestamp"]


def test_irregular_horizon_interpolation_uses_observed_neighbors_only(noise_path):
    visits = [_visit(hours) for hours in list(range(0, 37, 6)) + [41, 46, 51]]
    signals = _signals(visits, noise_path)
    signal = signals[-1]
    expected_start = _visit(36)["confluency_mean"] + 3 / 5 * (
        _visit(41)["confluency_mean"] - _visit(36)["confluency_mean"])
    assert signal.status == "OK"
    assert signal.observed_growth_pp == pytest.approx(_visit(51)["confluency_mean"] - expected_start)
    assert signal.horizon_start == _visit(39)["timestamp"]
    assert signal.horizon_hours == 12.0


@pytest.mark.parametrize("changes", [
    {"segment_id": "new-segment"}, {"lineage_id": "new-lineage"}, {"flask_id": "new-flask"},
    {"model_versions": {"confluency": "new-model"}},
    {"config_hashes": {"quality": "new-quality"}}, {"source_dataset": "other-source"},
    {"source_sequence_id": "other-sequence"}, {"provenance": "other-origin"},
    {"n_fov": 4}, {"pixel_size_um": 0.5}, {"imager_id": "scope-2"}, {"setup_id": "setup-2"},
    {"crop_specs": ["crop_f0.5_s1_k0"]},
    {"model_versions": {}}, {"config_hashes": None},
])
def test_window_boundary_permanently_invalidates_reference(noise_path, changes):
    visits = [_visit(hours) for hours in range(0, 73, 6)]
    visits[8].update(changes)
    signals = _signals(visits, noise_path)
    assert signals[7].status == "OK"
    assert all(signal.status == "WINDOW_CHANGED" for signal in signals[8:])
    assert all(signal.expected is None for signal in signals[8:])


def test_quality_failed_boundary_still_invalidates_reference(noise_path):
    visits = [_visit(hours) for hours in range(0, 61, 6)]
    visits[8].update(quality={"pass": False}, model_versions={"confluency": "new-model"})
    signals = _signals(visits, noise_path)
    assert signals[8].status == "QUALITY_FAILED"
    assert signals[9].status == "WINDOW_CHANGED"


def test_missing_provenance_is_not_silently_accepted(noise_path):
    visits = [_visit(hours) for hours in range(0, 49, 6)]
    visits[0].pop("config_hashes")
    assert all(signal.status == "WINDOW_CHANGED" for signal in _signals(visits, noise_path))


def test_insufficient_baseline_cannot_recruit_post_cutoff_visits(noise_path):
    visits = [_visit(hours) for hours in range(0, 73, 6)]
    signals = _signals(visits, noise_path, baseline_end=_visit(12)["timestamp"])
    assert all(signal.status == "INSUFFICIENT_BASELINE" for signal in signals[3:])
    assert all(signal.n_baseline == 3 for signal in signals[3:])
    assert all(signal.expected is None for signal in signals)


def test_baseline_gap_is_explicit(noise_path):
    visits = [_visit(hours) for hours in [0, 6, 12, 24, 30, 36, 42, 48]]
    assert _signals(visits, noise_path)[-1].status == "INSUFFICIENT_BASELINE_COVERAGE"


def test_horizon_warmup_and_expected_saturation_are_unscored(noise_path):
    visits = [_visit(hours) for hours in range(0, 193, 6)]
    warmup = _signals(visits, noise_path, horizon_hours=48)
    assert warmup[7].status == "INSUFFICIENT_COVERAGE"
    saturation = _signals(visits, noise_path)[-1]
    assert saturation.status == "LOW_EXPECTED_GROWTH"
    assert saturation.growth_fraction is None
    assert saturation.expected_growth_pp < 1.0


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -1.0, 101.0, None, True, 10**400])
def test_invalid_observations_have_no_numeric_scores(noise_path, value):
    visits = [_visit(hours) for hours in range(0, 49, 6)]
    visits[-1]["confluency_mean"] = value
    signal = _signals(visits, noise_path)[-1]
    assert signal.status == "INVALID_OBSERVATION"
    assert signal.observed is None
    assert signal.expected is None
    json.dumps(asdict(signal), allow_nan=False)


def test_missing_quality_fails_closed(noise_path):
    visits = [_visit(hours) for hours in range(0, 49, 6)]
    visits[-1].pop("quality")
    assert _signals(visits, noise_path)[-1].status == "QUALITY_FAILED"


@pytest.mark.parametrize("value", [True, 10**400, 1e308])
def test_invalid_deviation_never_reaches_weighting(noise_path, value):
    visits = [_visit(hours) for hours in range(0, 49, 6)]
    visits[3]["confluency_sd"] = value
    signals = _signals(visits, noise_path)
    assert signals[3].status == "INVALID_OBSERVATION"


def test_crop_offsets_do_not_create_a_window_boundary(noise_path):
    visits = [_visit(hours) for hours in range(0, 49, 6)]
    expected = _signals(visits, noise_path)
    visits[-1]["crop_specs"] = ["crop_f0.25_s99_k7"]
    assert _signals(visits, noise_path) == expected


def test_fit_failure_is_not_a_zero_deficit(noise_path, monkeypatch):
    monkeypatch.setattr("culture.growth_signal._fit_one", lambda *args: None)
    signals = _signals([_visit(hours) for hours in range(0, 49, 6)], noise_path)
    assert signals[-1].status == "FIT_FAILED"
    assert signals[-1].growth_deficit_pp is None


def test_deterministic_serializable_and_does_not_mutate_inputs(noise_path):
    visits = [_visit(hours) for hours in range(0, 73, 6)]
    before = copy.deepcopy(visits)
    first, second = _signals(visits, noise_path), _signals(visits, noise_path)
    assert first == second
    assert visits == before
    json.dumps([asdict(signal) for signal in first], allow_nan=False)
    assert len({signal.reference_id for signal in first[7:]}) == 1


def test_fault_labels_and_onset_are_not_inputs_to_reference_selection(noise_path):
    visits = [_visit(hours) for hours in range(0, 73, 6)]
    original = _signals(visits, noise_path)
    for visit in visits:
        visit["fault"] = {"type": "stall", "onset": visit["timestamp"]}
        visit["healthy"] = False
    assert _signals(visits, noise_path) == original


def test_reference_digest_changes_with_baseline_and_fit_configuration(noise_path):
    visits = [_visit(hours) for hours in range(0, 49, 6)]
    reference = _signals(visits, noise_path)[-1].reference_id
    visits[3]["confluency_mean"] += 0.1
    assert _signals(visits, noise_path)[-1].reference_id != reference
    visits[3]["confluency_mean"] -= 0.1
    with open(noise_path, "a") as destination:
        destination.write("\n# Different artifact bytes\n")
    assert _signals(visits, noise_path)[-1].reference_id != reference


def test_config_fit_and_digest_use_the_same_single_read(noise_path, monkeypatch):
    visits = [_visit(hours) for hours in range(0, 49, 6)]
    expected = _signals(visits, noise_path)
    read_bytes = Path.read_bytes
    reads = []

    def replace_noise_after_read(config_file):
        content = read_bytes(config_file)
        reads.append(str(config_file))
        if str(config_file) == noise_path:
            config_file.write_bytes(content + b"\n# Concurrent file replacement\n")
        return content

    monkeypatch.setattr(Path, "read_bytes", replace_noise_after_read)
    assert _signals(visits, noise_path) == expected
    assert reads.count(noise_path) == 1
    assert len(reads) == 2


@pytest.mark.parametrize("changes", [
    {"baseline_reason": ""}, {"horizon_hours": 0}, {"max_gap_hours": -1},
    {"min_expected_growth_pp": float("nan")}, {"baseline_end": "2026-01-01"},
    {"horizon_hours": True}, {"max_gap_hours": False}, {"min_expected_growth_pp": True},
    {"horizon_hours": 10**400}, {"max_gap_hours": 10**400},
])
def test_invalid_settings_raise(noise_path, changes):
    with pytest.raises(ValueError):
        _signals([_visit(0)], noise_path, **changes)


@pytest.mark.parametrize("visits", [[_visit(6), _visit(0)], [_visit(0), _visit(0)]])
def test_rejects_out_of_order_and_duplicate_times(noise_path, visits):
    with pytest.raises(ValueError, match="strictly chronological"):
        _signals(visits, noise_path)
