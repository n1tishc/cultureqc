"""Schema 0.4: a review is its own record, linked to the reading's hash (the
reading is never edited), and a change under change control is a record too.
All three types share one chain and the schema."""

import json
import os

import pytest

from culture.records import RecordWriter, change_event, review_event, reviews_for, verify_chain

SCHEMA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "culture", "schema.json")


def reading(**kw):
    r = {"schema_version": "0.4", "record_type": "reading", "flask_id": "F-1", "cell_line": "C2C12",
         "protocol_stage": None, "lineage": {"passage_number": 7, "parent_flask_id": "F-0"}, "imager_id": "imager-1",
         "fov": {"index": 3, "x_mm": None, "y_mm": None}, "environment": {"temperature_c": 37.0},
         "captured_at": "2026-10-02T10:00:00+00:00", "image_ref": "x.png", "image_hash": "0" * 64,
         "pixel_size_um": 1.3, "confluency_pct": 82.0, "confluency_interval": [77.0, 87.0],
         "confluency_profile": {"id": "p", "sha256": "1" * 64, "status": "validated", "cutoff": -1.0, "band_pp": 5.0},
         "confluency_confidence": 0.8, "confluency_method": "probmap", "quality_gate": None, "recovery_request": None,
         "qc_flag": "normal", "qc_confidence": 0.9, "recommended_action": "human_review",
         "action_reason": "within its error band", "decided_by": "rules_v0.5", "model_versions": {"seg": "cpsam_v2"}}
    r.update(kw)
    return r


def test_review_links_to_the_reading_without_editing_it(tmp_path):
    log = str(tmp_path / "events.jsonl")
    w = RecordWriter(log)
    r = w.append(reading())
    before = open(log).read()
    w.append(review_event(r, "u-17", "Reviewer A", "approval", "override", "passage",
                          reason="Checked under the microscope: above 80%.", host_signature_ref="sig-123"))
    assert open(log).read().startswith(before)          # the reading's line is untouched
    assert verify_chain(log).ok
    (rev,) = reviews_for(log)[r["record_hash"]]
    assert rev["final_action"] == "passage" and rev["recorded_at"] and "analysed_at" not in rev


def test_review_rules():
    r = {**reading(), "record_id": "a", "record_hash": "f" * 64}
    with pytest.raises(ValueError):
        review_event(r, "u", "U", "approval", "override", "passage")              # no reason
    with pytest.raises(ValueError):
        review_event(r, "u", "U", "approval", "accept", "passage")                # accept keeps the action
    with pytest.raises(ValueError):
        review_event(r, "u", "U", "authorship-ish", "accept", "human_review")      # meaning
    with pytest.raises(ValueError):
        review_event({**r, "record_hash": None}, "u", "U", "review", "accept", "human_review")


def test_change_event_needs_evidence():
    with pytest.raises(ValueError):
        change_event("confluency_profile", None, {"id": "p", "sha256": "1" * 64}, "why", [], "u", "U")


def test_all_three_types_match_the_schema(tmp_path):
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.load(open(SCHEMA))
    log = str(tmp_path / "events.jsonl")
    w = RecordWriter(log)
    r = w.append(reading())
    rv = w.append(review_event(r, "u-17", "Reviewer A", "review", "accept", "human_review"))
    ch = w.append(change_event("confluency_profile", {"id": "uncalibrated", "sha256": "2" * 64},
                               {"id": "p", "sha256": "1" * 64}, "Profile passed its pre-registered criteria.",
                               [{"path": "results/confluency_profiles.md", "sha256": "3" * 64}], "u-2", "Approver B"))
    for rec in (r, rv, ch):
        jsonschema.validate(rec, schema)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({**r, "reviewed_by": "someone"}, schema)            # no review fields on a reading
    assert verify_chain(log).n_records == 3
