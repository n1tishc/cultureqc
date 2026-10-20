"""Records retain the inference's model identity, not a later on-disk replacement."""

from types import SimpleNamespace

import cv2
import numpy as np
import pytest

from culture.anomaly import AnomalyResult
from culture.profiles import get_profile
from culture.seg import ConfluencyResult


@pytest.fixture
def reading(tmp_path):
    path = tmp_path / "frame.png"
    cv2.imwrite(str(path), np.full((32, 32), 100, np.uint8))
    check = {"id": "cpsam_v2", "status": "match", "sha256": "a" * 64,
             "approved_sha256": "a" * 64, "approvals_head": "c" * 64}
    confluency = ConfluencyResult(30.0, 0.9, "probmap", "cpsam_v2",
                                 {"model_check": check, "pct_default_cutoff": 30.0})
    quality = SimpleNamespace(flag="normal", confidence=0.9, evidence_bbox=None,
                              calibrated=False, model_version="fixture-qc")
    return path, confluency, quality


def test_pipeline_uses_per_inference_hash(reading, tmp_path, monkeypatch):
    from culture import anomaly, pipeline, weights

    path, confluency, quality = reading
    monkeypatch.setattr(pipeline, "cpsam_confluency", lambda *args, **kwargs: confluency)
    monkeypatch.setattr(pipeline, "qc_classify", lambda *args, **kwargs: quality)
    monkeypatch.setattr(anomaly, "score_frame", lambda *args: AnomalyResult(status="unavailable"))
    monkeypatch.setattr(weights, "weights_hashes", lambda: {"seg": "b" * 64, "dino": None, "qc": None})
    record = pipeline.analyze(str(path), flask_id="fixture", cell_line="fixture",
                              profile_id="uncalibrated", log_path=str(tmp_path / "events.jsonl"))
    assert record["model_weights_hash"]["seg"] == record["model_check"]["sha256"] == "a" * 64


@pytest.mark.parametrize("has_check", [True, False])
def test_console_does_not_substitute_current_file_hash(reading, monkeypatch, has_check):
    from demo import analysis
    from culture.provenance import recorded_decision

    path, confluency, quality = reading
    if not has_check:
        confluency.extra.pop("model_check")
    _, inputs = recorded_decision(confluency_pct=confluency.pct,
                                  confluency_confidence=confluency.confidence,
                                  qc_flag=None, qc_confidence=None)
    result = SimpleNamespace(
        confluency=confluency, qc=quality, quality=None, interval=None,
        profile=get_profile("uncalibrated"), probmap_x1000=None, demoted=True,
        anomaly=AnomalyResult(status="unavailable"), action="continue", reason="fixture",
        rationale={"rationale": "fixture", "method": "template"}, finetuned=None,
        passage_eligibility=None, decision=None, decision_inputs=inputs, config_snapshot=[],
        image_hash="d" * 64, preprocessing=None, analysis_started_at=None, analysis_completed_at=None,
    )
    monkeypatch.setattr(analysis, "weights_hashes", lambda: {"seg": "b" * 64, "dino": None, "qc": None})
    record = analysis.build_record(result, str(path), "fixture")
    assert record["model_weights_hash"]["seg"] == ("a" * 64 if has_check else None)
