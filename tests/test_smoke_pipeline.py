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
    assert record["recommended_action"] in {"human_review", "passage", "feed", "hold"}


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
    assert set(record["config_hashes"]) == {"qc.yaml", "calibration.yaml", "detectability.yaml", "anomaly.yaml"}


def test_anomaly_recorded_and_an_input_to_the_rules(record):
    # B2 + rules v0.3: the anomaly check is recorded, and its flag is an input to
    # the rules (it holds a passage) whenever the check ran.
    assert record["anomaly_status"] in {"ok", "unavailable"}
    assert record["anomaly_used_in_decision"] is (record["anomaly_status"] == "ok")
    assert record["decided_by"] == "rules_v0.3"
    if record["anomaly_status"] == "ok":
        assert record["anomaly_flag"] == (record["anomaly_score"] > record["anomaly_threshold"])
        assert record["model_versions"]["dino"] == "facebook/dinov2-small"
    # the rationale mentions the anomaly check exactly when it flagged the image
    assert ("anomaly check flagged" in record["qc_rationale"]) is bool(record["anomaly_flag"])


def test_image_hash_matches_fixture(record):
    import hashlib
    h = hashlib.sha256()
    with open(FIXTURE, "rb") as f:
        h.update(f.read())
    assert record["image_hash"] == h.hexdigest()


def test_record_is_hash_chained_and_verifies(record):
    ok, bad_line = verify_chain(record["_log_path"])
    assert ok, f"chain broken at line {bad_line}"


@pytest.mark.xfail(
    reason="culture/schema.json's confluency_method enum "
           "(['cpsam_v2_probmap','cpsam_v2_instance','threshold_baseline']) doesn't match "
           "what culture/seg.py actually writes ('probmap'/'instance'/'threshold', see "
           "ConfluencyResult.method). Nothing in the repo currently validates a live record "
           "against this schema (docs/REPO_MAP.md §6) so this drift went unnoticed until this "
           "smoke test. Recon-only slice (Slice 0) — not fixed here; flagged for whoever "
           "touches schema.json/seg.py next (Slice 2's visit-summary schema is the natural "
           "place). strict=True: if this starts passing, that means the drift was fixed and "
           "this xfail should be deleted, not left stale.",
    strict=True,
)
def test_record_matches_schema(record):
    import jsonschema

    schema_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "culture", "schema.json")
    with open(schema_path) as f:
        schema = json.load(f)

    # Also excludes "record_hash": schema.json has additionalProperties: false
    # but doesn't list record_hash as a property, even though
    # RecordWriter.append() (culture/records.py) always adds it — a second,
    # separate drift from the one this test is xfail'd for above.
    clean = {k: v for k, v in record.items() if not k.startswith("_") and k != "record_hash"}
    jsonschema.validate(clean, schema)
