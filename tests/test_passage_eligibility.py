"""Synthetic policy fixtures are not biological validation."""

import copy
from dataclasses import replace
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml
from conftest import synthetic_passage_profile

from culture.profiles import get_profile, load_profiles
from culture.rules import LineConfig, decide


def test_msc_measurement_band_does_not_authorize_passage():
    profile = get_profile("msc_phase")
    assert profile.band_pp == 7.11
    assert profile.cutoff == -1.5
    action, reason = decide(90, .9, None, None, LineConfig(target_confluency=80),
                            48, 12, False, profile.band_pp)
    assert action == "human_review"
    assert "passage eligibility" in reason


@pytest.mark.parametrize("profile_id", ["msc_phase", "evican_mixed", "livecell_incucyte", "c2c12_ker2018", None])
def test_shipped_profiles_do_not_have_action_approval(profile_id):
    profile = get_profile(profile_id)
    assert not profile.passage_eligibility(90, 80)["eligible"]


def test_synthetic_approved_scope_permits_passage():
    profile, context = synthetic_passage_profile()
    assert profile.passage_eligibility(90, 80, context)["eligible"]
    assert decide(90, .9, None, None, hours_since_passage=48, band_pp=5,
                  profile=profile, setup_context=context, quality_passed=True)[0] == "passage"


@pytest.mark.parametrize("field", ["setup_id", "cell_line", "model_sha256"])
@pytest.mark.parametrize("value", [None, "wrong"])
def test_context_must_match_approved_scope(field, value):
    profile, context = synthetic_passage_profile()
    context[field] = value
    result = profile.passage_eligibility(90, 80, context)
    assert not result["eligible"] and field in result["reason"]
    assert decide(90, .9, None, None, band_pp=5, profile=profile, setup_context=context)[0] == "human_review"


@pytest.mark.parametrize("reading,target", [(84.9, 80), (95.1, 80), (90, 79.9), (90, 80.1)])
def test_reading_and_target_must_be_in_validated_range(reading, target):
    profile, context = synthetic_passage_profile()
    profile.entry["validated_scope"]["reading_range_pct"] = [85, 95]
    assert not profile.passage_eligibility(reading, target, context)["eligible"]
    assert profile.passage_eligibility(85, 80, context)["eligible"]
    assert profile.passage_eligibility(95, 80, context)["eligible"]


@pytest.mark.parametrize("field,value", [
    ("status", "typo"), ("status", "failed"), ("cutoff", float("nan")),
    ("band_pp", -1), ("band_pp", float("inf")), ("band_pp", True), ("band_pp", None),
    ("action_eligibility", {"status": "eligible", "reason": "missing approval"}),
    ("action_eligibility", {"status": "unsupported", "reason": "contradictory scope"}),
    ("validated_scope", None), ("acceptance", {"A1": "pass", "A5": "pass"}),
    ("acceptance", {"A1": "fail"}), ("acceptance", {"A1": []}), ("status", []),
])
def test_invalid_profile_combinations_rejected_on_load(tmp_path, field, value):
    profile, _ = synthetic_passage_profile()
    entry = copy.deepcopy(profile.entry)
    entry[field] = value
    path = tmp_path / "profiles.yaml"
    path.write_text(yaml.safe_dump({"version": 2, "profiles": {
        "uncalibrated": get_profile().entry, "synthetic": entry}}))
    with pytest.raises(ValueError):
        load_profiles(str(path))


@pytest.mark.parametrize("bounds", [[90, 80], [-1, 100], [0, float("nan")], [0], "0-100"])
def test_invalid_scope_ranges_rejected(tmp_path, bounds):
    profile, _ = synthetic_passage_profile()
    profile.entry["validated_scope"]["reading_range_pct"] = bounds
    path = tmp_path / "profiles.yaml"
    path.write_text(yaml.safe_dump({"version": 2, "profiles": {
        "uncalibrated": get_profile().entry, "synthetic": profile.entry}}))
    with pytest.raises(ValueError):
        load_profiles(str(path))


def test_legacy_profile_is_measurement_only_and_unknown_request_errors(tmp_path):
    entry = {key: value for key, value in get_profile("msc_phase").entry.items()
             if key not in {"validated_scope", "action_eligibility"}}
    path = tmp_path / "legacy.yaml"
    path.write_text(yaml.safe_dump({"version": 1, "profiles": {"uncalibrated": get_profile().entry, "msc": entry}}))
    assert get_profile("msc", str(path)).calibrated
    assert not get_profile("msc", str(path)).passage_eligibility(90, 80)["eligible"]
    for requested in ("misspelled", ""):
        with pytest.raises(ValueError, match="Unknown confluency profile"):
            get_profile(requested, str(path))


def test_band_cannot_be_substituted():
    profile, context = synthetic_passage_profile()
    with pytest.raises(ValueError, match="band must match"):
        decide(90, .9, None, None, band_pp=1, profile=profile, setup_context=context)


@pytest.mark.parametrize("value", [-1, 101, float("nan"), float("inf"), True])
@pytest.mark.parametrize("field", ["confluency_pct", "band_pp", "target_confluency"])
def test_invalid_decision_measurements_are_rejected(field, value):
    kwargs = dict(confluency_pct=90, confluency_confidence=.9, qc_flag=None, qc_confidence=None, band_pp=5)
    if field == "target_confluency":
        kwargs["line_config"] = LineConfig(target_confluency=value)
    else:
        kwargs[field] = value
    with pytest.raises(ValueError):
        decide(**kwargs)


@pytest.mark.parametrize("approved,setup_matches,quality_available,passage_hours,anomaly_required", [
    (False, False, True, 48, False), (True, False, True, 48, False), (True, True, True, 48, False),
    (True, True, False, 48, False), (True, True, True, None, False), (True, True, True, 6, False),
    (True, True, True, 48, True),
])
def test_library_and_console_record_same_eligibility(tmp_path, monkeypatch, approved, setup_matches,
                                                    quality_available, passage_hours, anomaly_required):
    import cv2
    import numpy as np
    import jsonschema
    from culture import anomaly, pipeline, profiles, quality, weights
    from culture.anomaly import AnomalyResult
    from culture.records import RecordWriter
    from culture.seg import ConfluencyResult
    from culture.rules import CheckPolicy
    from demo import analysis

    profile, context = synthetic_passage_profile() if approved else (get_profile("msc_phase"), {})
    profile = replace(profile, quality="synthetic-quality" if quality_available else None)
    check_policy = CheckPolicy(qc="not_applicable", anomaly="required" if anomaly_required else "optional")
    setup_id = context.get("setup_id") if setup_matches else None
    cell_line = context.get("cell_line", "MSC")
    monkeypatch.setattr(profiles, "get_profile", lambda *args: profile)
    monkeypatch.setattr(analysis, "get_profile", lambda *args: profile)
    image = np.full((32, 32), 100, np.uint8)
    image_path = tmp_path / "frame.png"
    cv2.imwrite(str(image_path), image)
    check = {"id": "cpsam_v2", "status": "match", "sha256": "a" * 64,
             "approved_sha256": "a" * 64, "approvals_head": "c" * 64}

    def segment(*args, **kwargs):
        if kwargs.get("on_visual"):
            kwargs["on_visual"](np.ones(image.shape), np.ones(image.shape, bool))
        return ConfluencyResult(90, .9, "probmap", "cpsam_v2", {"model_check": check, "pct_default_cutoff": 90})

    qc = SimpleNamespace(flag="normal", confidence=.9, calibrated=False, model_version="fixture",
                         evidence_bbox=None, evidence_bboxes=[])
    for module in (pipeline, analysis):
        monkeypatch.setattr(module, "cpsam_confluency", segment)
        monkeypatch.setattr(module, "qc_classify", lambda *args, **kwargs: qc)
        monkeypatch.setattr(module, "classifier_demoted", lambda: True)
    for module in (weights, analysis):
        monkeypatch.setattr(module, "weights_hashes", lambda: {"seg": "a" * 64})
    for module in (anomaly, analysis):
        monkeypatch.setattr(module, "score_frame", lambda *args: AnomalyResult(status="unavailable"))
    for module in (quality, analysis):
        monkeypatch.setattr(module, "quality_gate", lambda *args, **kwargs: SimpleNamespace(
            passed=True, reasons=[], thresholds="synthetic", blur=1., mean_intensity=100., uniformity=1.))
    timing_inputs = {} if passage_hours is None else {"hours_since_passage": passage_hours, "hours_since_feed": 12}
    library_record = pipeline.analyze(str(image_path), cell_line=cell_line, setup_id=setup_id,
                                      check_policy=check_policy, **timing_inputs,
                                      log_path=str(tmp_path / "library.jsonl"))
    result = analysis.analyze_image(image, str(image_path), cell_line, 80, setup_id=setup_id,
                                    check_policy=check_policy, **timing_inputs)
    console_record = RecordWriter(str(tmp_path / "console.jsonl")).append(
        analysis.build_record(result, str(image_path), cell_line))
    assert library_record["passage_eligibility"] == console_record["passage_eligibility"]
    assert library_record["decision"] == console_record["decision"]
    assert library_record["decision_inputs"] == console_record["decision_inputs"]
    assert library_record["confluency_map_hash"] == console_record["confluency_map_hash"]
    assert library_record["config_snapshot"] == console_record["config_snapshot"]
    assert not library_record["decision"]["host_actionable"]
    if passage_hours is None:
        assert all(value["status"] == "unknown" and value["hours"] is None
                   for value in library_record["decision"]["timing"].values())
    expected_action = ("continue" if passage_hours == 6 else
                       "passage" if approved and setup_matches and quality_available and passage_hours == 48
                       and not anomaly_required else "human_review")
    assert library_record["recommended_action"] == console_record["recommended_action"] == (
        expected_action)
    schema = json.loads(Path("culture/schema.json").read_text())
    for record in (library_record, console_record):
        assert record["qc_rationale"] == record["action_reason"]
        jsonschema.validate(record, schema)
        for required in ("passage_eligibility", "decision"):
            missing = {key: value for key, value in record.items() if key != required}
            with pytest.raises(jsonschema.ValidationError):
                jsonschema.validate(missing, schema)
        actionable = copy.deepcopy(record)
        actionable["decision"]["host_actionable"] = True
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(actionable, schema)
