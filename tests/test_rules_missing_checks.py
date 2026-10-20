import pytest

from conftest import synthetic_passage_profile
from culture.rules import CheckPolicy, LineConfig, decide, evaluate_decision


def inputs(**overrides):
    profile, context = synthetic_passage_profile()
    return dict(confluency_pct=95, confluency_confidence=.9, qc_flag=None, qc_confidence=None,
                band_pp=5, profile=profile, setup_context=context, hours_since_passage=48,
                hours_since_feed=12, quality_passed=True, anomaly_flag=False) | overrides


def test_missing_quality_cannot_authorize_passage():
    assert decide(**inputs(quality_passed=None))[0] == "human_review"


def test_unknown_passage_time_cannot_authorize_passage():
    assert decide(**inputs(hours_since_passage=None))[0] == "human_review"


def test_recent_passage_reason_is_factual():
    action, reason = decide(**inputs(hours_since_passage=6))
    assert action == "continue"
    assert "below target" not in reason
    assert "6h" in reason and "24h" in reason


@pytest.mark.parametrize("value", [-1, float("nan"), float("inf"), True])
@pytest.mark.parametrize("field", ["hours_since_passage", "hours_since_feed"])
def test_invalid_times_are_rejected(field, value):
    with pytest.raises(ValueError):
        decide(**inputs(**{field: value}))


@pytest.mark.parametrize("requirement,action,status", [
    ("optional", "passage", "unavailable"), ("required", "human_review", "unavailable"),
    ("not_applicable", "passage", "not_applicable"),
])
@pytest.mark.parametrize("name", ["anomaly", "qc"])
def test_absent_check_requirement_is_explicit(name, requirement, action, status):
    policy = CheckPolicy(**{name: requirement})
    decision = evaluate_decision(**inputs(anomaly_flag=None), check_policy=policy)
    assert decision.action == action
    assert decision.checks[name] == {"requirement": requirement, "status": status}
    assert not decision.record_fields()["host_actionable"]
    assert decision.record_fields()["mode"] == "advisory"
    if requirement == "required":
        assert decision.reason_code == "required_check_unavailable"
        assert name in decision.reason


@pytest.mark.parametrize("policy,overrides", [
    (CheckPolicy(anomaly="not_applicable"), {"anomaly_flag": False}),
    (CheckPolicy(qc="not_applicable"), {"qc_flag": "normal", "qc_confidence": .9}),
    (CheckPolicy(qc="not_applicable"), {"qc_confidence": .9}),
    (CheckPolicy(anomaly="typo"), {}),
])
def test_contradictory_or_invalid_check_policy_is_rejected(policy, overrides):
    with pytest.raises(ValueError):
        evaluate_decision(**inputs(**overrides), check_policy=policy)


@pytest.mark.parametrize("overrides,action,code", [
    ({"quality_passed": False, "qc_flag": "detachment", "qc_confidence": .9}, "human_review", "qc_flagged"),
    ({"quality_passed": False, "anomaly_flag": True}, "reimage", "quality_failed"),
    ({"quality_passed": False, "hours_since_passage": None}, "reimage", "quality_failed"),
    ({"anomaly_flag": True}, "human_review", "anomaly_flagged"),
    ({"quality_passed": None}, "human_review", "required_check_unavailable"),
    ({"qc_flag": "detachment", "qc_confidence": None}, "human_review", "qc_incomplete"),
    ({"confluency_pct": 84.9}, "human_review", "target_within_error_band"),
    ({"confluency_pct": 85, "hours_since_passage": 24}, "passage", "passage_candidate"),
    ({"confluency_pct": 85, "hours_since_passage": 23.999}, "continue", "passage_interval_hold"),
    ({"confluency_pct": 75}, "human_review", "target_within_error_band"),
    ({"confluency_pct": 74.999}, "continue", "monitor_advisory"),
    ({"confluency_pct": 40, "hours_since_feed": 24}, "feed", "feed_due"),
    ({"confluency_pct": 40, "hours_since_feed": 23.999}, "continue", "monitor_advisory"),
    ({"hours_since_passage": 6, "hours_since_feed": 24}, "feed", "feed_due"),
])
def test_failure_precedence_and_boundaries(overrides, action, code):
    decision = evaluate_decision(**inputs(**overrides))
    assert (decision.action, decision.reason_code) == (action, code)
    assert "Advisory only" in decision.reason
    if overrides.get("hours_since_passage") == 6:
        assert "6h < 24h" in decision.reason and "below target" not in decision.reason


def test_low_unsupported_reading_is_not_no_action_clearance():
    decision = evaluate_decision(**inputs(confluency_pct=20, profile=None, band_pp=None,
                                          quality_passed=None, hours_since_passage=None, hours_since_feed=None))
    assert decision.action == "continue"
    assert "not proof that no action is needed" in decision.reason
    assert "culture-health clearance" in decision.reason
    assert "Passage timing is unknown" in decision.reason
    assert "Feed timing is unknown" in decision.reason
    assert decision.timing["passage"]["status"] == decision.timing["feed"]["status"] == "unknown"
    assert "unsupported_action_scope" in decision.warnings


@pytest.mark.parametrize("field", ["min_hours_since_passage", "feed_interval_h", "qc_review_threshold"])
@pytest.mark.parametrize("value", [-1, float("nan"), float("inf"), True])
def test_invalid_line_configuration_is_rejected(field, value):
    with pytest.raises(ValueError):
        evaluate_decision(**inputs(line_config=LineConfig(**{field: value})))


@pytest.mark.parametrize("field", ["confluency_confidence", "qc_confidence"])
@pytest.mark.parametrize("value", [-1, 1.001, float("nan"), float("inf"), True])
def test_invalid_confidence_is_rejected(field, value):
    with pytest.raises(ValueError):
        evaluate_decision(**inputs(**{field: value}))


@pytest.mark.parametrize("overrides", [{"quality_passed": 1}, {"anomaly_flag": "false"},
                                      {"qc_flag": "typo"}, {"quality_reasons": "blur"}])
def test_invalid_check_values_are_not_coerced(overrides):
    with pytest.raises(ValueError):
        evaluate_decision(**inputs(**overrides))


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_nonfinite_unused_model_values_cannot_be_written(tmp_path, value):
    from culture.records import RecordWriter, verify_chain

    path = tmp_path / "records.jsonl"
    writer = RecordWriter(str(path))
    writer.append({"fixture": 1})
    before = path.read_bytes()
    with pytest.raises(ValueError):
        writer.append({"unused_model_output": {"confidence": value}})
    assert path.read_bytes() == before
    writer.append({"fixture": 2})
    assert verify_chain(str(path)).ok


def test_runtime_rationale_uses_authoritative_decision_reason():
    from culture.rationale import generate_rationale

    decision = evaluate_decision(**inputs(hours_since_passage=6))
    rationale = generate_rationale("normal", .9, None, 95, action="continue", decision_reason=decision.reason)
    assert rationale["rationale"] == decision.reason
    assert "below target" not in rationale["rationale"]
    assert not rationale["vlm_attempted"]


def test_incomplete_qc_template_does_not_crash_or_claim_health():
    from culture.rationale import generate_rationale

    rationale = generate_rationale("detachment", None, None, 95, action="human_review")["rationale"]
    assert "confidence unavailable" in rationale
    normal = generate_rationale("normal", .9, None, 80)["rationale"]
    assert "at or above target" in normal
    assert "culture appears healthy" not in normal


def test_verifier_reports_nonfinite_json_as_broken(tmp_path):
    import json
    from culture.records import GENESIS_HASH, verify_chain

    path = tmp_path / "bad.jsonl"
    path.write_text(json.dumps({"prev_record_hash": GENESIS_HASH, "value": float("nan")}))
    result = verify_chain(str(path))
    assert result.status == "broken" and "nonfinite" in result.reason


@pytest.mark.parametrize("confidence,action", [(.6999, "passage"), (.7, "human_review")])
def test_qc_threshold_boundary(confidence, action):
    assert evaluate_decision(**inputs(qc_flag="detachment", qc_confidence=confidence)).action == action
