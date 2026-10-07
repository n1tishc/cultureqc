"""Slice 0 smoke test: the full single-image pipeline, for real.

Unlike deploy/hf-space/test_api.py (stubbed models, fast, runs on every push),
this drives real Cellpose-SAM + EfficientNet-B0 inference end to end via
culture.pipeline.analyze(). It is the one place in the suite that proves the
shipped models actually run and produce a self-consistent, schema-shaped
record. Slow by design (~20-60s on CPU, see results/baseline_latency.csv) —
not part of the fast CI job; run manually or in a CI-optional job.

    .venv/bin/python -m pytest tests/test_smoke_pipeline.py -v
"""

from __future__ import annotations

import json
import os
import tempfile

import pytest
from conftest import require_module

require_module("torch")
require_module("cellpose")
from culture.pipeline import analyze  # noqa: E402
from culture.qc import CLASS_NAMES  # noqa: E402
from culture.records import verify_chain  # noqa: E402
from culture.rules import RULES_VERSION  # noqa: E402

FIXTURE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "test-data", "contam_00015.png")


@pytest.fixture(scope="module")
def record():
    assert os.path.exists(FIXTURE), f"fixture missing: {FIXTURE}"
    with tempfile.TemporaryDirectory() as td:
        log_path = os.path.join(td, "events.jsonl")
        result = analyze(
            FIXTURE,
            flask_id="SMOKE-TEST",
            cell_line="A172",
            log_path=log_path,
        )
        result["_log_path"] = log_path
        yield result


def test_confluency_in_range(record):
    assert 0.0 <= record["confluency_pct"] <= 100.0
    assert 0.0 <= record["confluency_confidence"] <= 1.0


def test_confluency_method_is_probmap(record):
    # pipeline.py hardcodes method="probmap" — the recommended default.
    assert record["confluency_method"] == "probmap"


def test_qc_flag_is_a_known_class(record):
    assert record["qc_flag"] in CLASS_NAMES


def test_qc_confidence_in_range(record):
    assert 0.0 <= record["qc_confidence"] <= 1.0


def test_recommended_action_is_valid(record):
    assert record["recommended_action"] in {"human_review", "passage", "feed", "continue", "reimage"}


def test_rationale_is_nonempty_and_deterministic_template(record):
    assert record["qc_rationale"]
    assert record["model_versions"]["vlm"] == "template"  # use_vlm=False in pipeline.py


def test_model_versions_present(record):
    assert record["model_versions"]["seg"] == "cpsam_v2"
    assert record["model_versions"]["qc"] == "qc_effnetb0_v1"


def test_classifier_calibrated_and_demoted(record):
    # B3 (spec v4 §2B.2): the A5 temperature is applied live; the classifier
    # is demoted (configs/qc.yaml), so it is recorded but not decided on.
    assert record["qc_calibrated"] is True
    assert record["qc_used_in_decision"] is False
    assert record["qc_evidence_bbox"] is None                     # no Grad-CAM while demoted
    assert "QC flag" not in record["action_reason"]
    assert record["qc_rationale"].startswith("Confluency ")
    assert set(record["config_hashes"]) == {"qc.yaml", "calibration.yaml", "detectability.yaml", "anomaly.yaml",
                                            "confluency_profiles.yaml", "quality.yaml", "approved_changes.jsonl",
                                            "finetuned_models.yaml"}


def test_shipped_weights_checked_against_the_approvals_log(record):
    from culture.approvals import approved
    mc = record["model_check"]
    assert mc["id"] == "cpsam_v2" and mc["status"] == "match"
    assert mc["sha256"] == mc["approved_sha256"] == record["model_weights_hash"]["seg"]
    assert mc["approvals_head"] == approved()["head"]
    assert record["finetuned_reading"] is None                    # none asked for


def test_anomaly_recorded_and_an_input_to_the_rules(record):
    # B2 + rules v0.3 on: the anomaly check is recorded, and its flag is an input to
    # the rules (it holds a passage) whenever the check ran.
    assert record["anomaly_status"] in {"ok", "unavailable"}
    assert record["anomaly_used_in_decision"] is (record["anomaly_status"] == "ok")
    assert record["decided_by"] == RULES_VERSION == "rules_v0.5"
    if record["anomaly_status"] == "ok":
        assert record["anomaly_flag"] == (record["anomaly_score"] > record["anomaly_threshold"])
        assert record["model_versions"]["dino"] == "facebook/dinov2-small"
    # the rationale mentions the anomaly check exactly when it flagged the image
    assert ("anomaly check flagged" in record["qc_rationale"]) is bool(record["anomaly_flag"])


def test_reading_names_its_profile_and_hashes_the_weights(record):
    # schema 0.4: no profile_id passed, so the uncalibrated profile: default cutoff, no band
    p = record["confluency_profile"]
    assert record["record_type"] == "reading"
    assert p["id"] == "uncalibrated" and p["band_pp"] is None and record["confluency_interval"] is None
    assert record["quality_gate"] is None                                  # no gate calibrated for the setup
    assert record["anomaly_bin_confluency_pct"] == pytest.approx(record["confluency_pct"], abs=0.01)
    assert all(len(v) == 64 for v in record["model_weights_hash"].values())
    assert "reviewed_by" not in record                                     # reviews are their own records


def test_image_hash_matches_fixture(record):
    import hashlib
    h = hashlib.sha256()
    with open(FIXTURE, "rb") as f:
        h.update(f.read())
    assert record["image_hash"] == h.hexdigest()


def test_record_is_hash_chained_and_verifies(record):
    ok, bad_line = verify_chain(record["_log_path"])
    assert ok, f"chain broken at line {bad_line}"


def test_record_matches_schema(record):
    import jsonschema

    schema_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "culture", "schema.json")
    with open(schema_path) as f:
        schema = json.load(f)

    # schema.json matches what the pipeline writes (0.3 aligned it; 0.4 added
    # record types, the profile and the host-platform fields).
    clean = {k: v for k, v in record.items() if not k.startswith("_")}
    jsonschema.validate(clean, schema)
