"""T05 fixtures exercise the live record paths without model downloads."""

import builtins
from datetime import datetime
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np
import pytest

from culture.provenance import capture_configs, capture_time, config_snapshot, load_yaml, replay_decision
from culture.records import RecordWriter
from culture.rules import LineConfig, RULES_VERSION


@pytest.fixture
def runtime(tmp_path, monkeypatch):
    from culture import anomaly, pipeline, profiles, qc, weights
    from culture.anomaly import AnomalyResult
    from culture.seg import ConfluencyResult
    from demo import analysis

    image = np.full((32, 32), 100, np.uint8)
    path = tmp_path / "frame.png"
    cv2.imwrite(str(path), image)
    profile_path = tmp_path / "profiles.yaml"
    profile_path.write_bytes(Path(profiles.PROFILES_PATH).read_bytes())
    qc_path = tmp_path / "qc.yaml"
    qc_path.write_text("classifier: {demoted: true}\n")
    anomaly_path = tmp_path / "override.yaml"
    anomaly_path.write_text("marker: consumed\n")
    monkeypatch.setenv("CULTUREQC_ANOMALY_CONFIG", str(anomaly_path))
    original_profile = profiles.get_profile
    get_profile = lambda selected=None: original_profile(selected, str(profile_path))
    monkeypatch.setattr(profiles, "get_profile", get_profile)
    monkeypatch.setattr(analysis, "get_profile", get_profile)
    state = SimpleNamespace(path=path, image=image, profile_path=profile_path, qc_path=qc_path,
                            anomaly_path=anomaly_path, during_segment=lambda: None, after_anomaly=lambda: None)
    check = {"id": "cpsam_v2", "status": "match", "sha256": "a" * 64,
             "approved_sha256": "a" * 64, "approvals_head": "c" * 64}

    def segment(*args, **kwargs):
        state.during_segment()
        if kwargs.get("on_visual"):
            kwargs["on_visual"](np.ones(image.shape), np.ones(image.shape, bool))
        return ConfluencyResult(90, .9, "probmap", "cpsam_v2", {"model_check": check, "pct_default_cutoff": 90})

    def score(*args):
        anomaly.load_anomaly_config()
        state.after_anomaly()
        return AnomalyResult(status="unavailable")

    classified = SimpleNamespace(flag="normal", confidence=.9, calibrated=False, model_version="fixture",
                                 evidence_bbox=None, evidence_bboxes=[])
    for module in (pipeline, analysis):
        monkeypatch.setattr(module, "cpsam_confluency", segment)
        monkeypatch.setattr(module, "qc_classify", lambda *args, **kwargs: classified)
        monkeypatch.setattr(module, "classifier_demoted", lambda: qc.classifier_demoted(str(qc_path)))
    for module in (weights, analysis):
        monkeypatch.setattr(module, "weights_hashes", lambda: {"seg": "a" * 64})
    for module in (anomaly, analysis):
        monkeypatch.setattr(module, "score_frame", score)

    def library(**kwargs):
        return pipeline.analyze(str(path), cell_line="MSC", profile_id="msc_phase",
                                log_path=str(tmp_path / "library.jsonl"), **kwargs)

    def console(captured_at=None, **kwargs):
        result = analysis.analyze_image(image, str(path), "MSC", 80, profile_id="msc_phase", **kwargs)
        return RecordWriter(str(tmp_path / "console.jsonl")).append(
            analysis.build_record(result, str(path), "MSC", captured_at=captured_at))

    state.library, state.console = library, console
    return state


@pytest.mark.parametrize("surface", ["library", "console"])
@pytest.mark.parametrize("timestamp", [None, "2024-01-02T03:04:05+05:30", "2024-01-02T03:04:05Z"])
def test_capture_time_is_not_analysis_time(runtime, surface, timestamp):
    record = getattr(runtime, surface)(captured_at=timestamp)
    assert record["captured_at"] == timestamp
    assert record["capture_time_source"] == ("host" if timestamp else "unknown")
    assert datetime.fromisoformat(record["analysis_started_at"]) <= datetime.fromisoformat(record["analysis_completed_at"])
    assert record["schema_version"] == "0.8"


@pytest.mark.parametrize("timestamp", ["", "not a date", "2024-01-02", "2024-01-02T03:04:05", 123, True])
def test_bad_capture_time_is_rejected(timestamp):
    with pytest.raises(ValueError):
        capture_time(timestamp)


def test_replay_has_no_io_or_inference(runtime, monkeypatch):
    record = runtime.library(hours_since_passage=48)
    expected = record["recommended_action"], record["decision"]["reason_code"]

    def forbidden(*args, **kwargs):
        raise AssertionError("Replay attempted IO or inference")

    from culture import profiles, seg
    monkeypatch.setattr(builtins, "open", forbidden)
    monkeypatch.setattr(profiles, "load_profiles", forbidden)
    monkeypatch.setattr(seg, "cpsam_confluency", forbidden)
    result = replay_decision(record, RULES_VERSION)
    assert (result.action, result.reason_code) == expected


@pytest.mark.parametrize("surface", ["library", "console"])
def test_records_identify_consumed_config_not_later_disk_contents(runtime, surface):
    initial_profile = runtime.profile_path.read_bytes()
    initial_anomaly = runtime.anomaly_path.read_bytes()

    def mutate_profile():
        runtime.profile_path.write_bytes(initial_profile.replace(b"-1.5", b"-2.5"))

    runtime.during_segment = mutate_profile
    runtime.after_anomaly = lambda: runtime.anomaly_path.write_text("marker: changed-after-consumption\n")
    record = getattr(runtime, surface)(hours_since_passage=48)
    snapshots = {entry["source_path"]: entry for entry in record["config_snapshot"]}
    for path, original in ((runtime.profile_path, initial_profile), (runtime.anomaly_path, initial_anomaly)):
        assert path.read_bytes() != original
        assert snapshots[str(path)]["text"].encode() == original
        assert record["config_hashes"][str(path)] == hashlib.sha256(original).hexdigest()
    assert record["confluency_profile"]["cutoff"] == -1.5
    assert replay_decision(record, RULES_VERSION).action == record["recommended_action"]


def test_effective_target_and_timing_are_distinct_structured_values(runtime):
    cfg = LineConfig(cell_line="MSC", target_confluency=80)
    runtime.during_segment = lambda: setattr(cfg, "target_confluency", 100)
    first = runtime.library(line_config=cfg, hours_since_passage=48)
    second = runtime.library(line_config=cfg, hours_since_passage=6)
    assert first["decision_inputs"]["values"]["line_config"]["target_confluency"] == 80
    assert second["decision_inputs"]["values"]["line_config"]["target_confluency"] == 100
    assert first["decision_inputs"]["values"]["hours_since_passage"] == 48
    assert second["decision_inputs"]["values"]["hours_since_passage"] == 6
    assert first["recommended_action"] == "human_review" and second["recommended_action"] == "continue"
    assert first["decision_inputs"]["sha256"] != second["decision_inputs"]["sha256"]


def test_library_console_share_decision_and_map_provenance(runtime):
    library = runtime.library(hours_since_passage=48, hours_since_feed=12)
    console = runtime.console(hours_since_passage=48, hours_since_feed=12)
    for key in ("decision_inputs", "decision", "config_hashes", "config_snapshot", "confluency_map_hash",
                "map_provenance", "image_hash", "captured_at", "capture_time_source"):
        assert library[key] == console[key], key


@pytest.mark.parametrize("field", ["decision_inputs", "capture_time_source", "config_snapshot", "map_provenance"])
def test_writer_rejects_missing_provenance_before_append(runtime, tmp_path, field):
    import jsonschema

    record = runtime.library()
    record.pop(field)
    path = tmp_path / "invalid.jsonl"
    with pytest.raises(jsonschema.ValidationError):
        RecordWriter(str(path)).append(record)
    assert not path.exists()


@pytest.mark.parametrize("kind", ["snapshot", "action", "reason_code", "measurement", "config_text", "profile"])
def test_inconsistent_records_are_rejected(runtime, tmp_path, kind):
    record = runtime.library(hours_since_passage=48)
    if kind == "snapshot":
        record["decision_inputs"]["values"]["hours_since_passage"] = 0
    elif kind == "action":
        record["recommended_action"] = "passage"
    elif kind == "reason_code":
        record["decision"]["reason_code"] = "passage_candidate"
    elif kind == "measurement":
        record["confluency_pct"] = 1
    elif kind == "config_text":
        record["config_snapshot"][0]["text"] += "\n"
    else:
        record["confluency_profile"]["cutoff"] = -9
    path = tmp_path / "rejected.jsonl"
    with pytest.raises(ValueError):
        RecordWriter(str(path)).append(record)
    assert not path.exists()


def test_legacy_and_unknown_policy_are_not_guessed(runtime):
    record = runtime.library()
    with pytest.raises(ValueError, match="policy"):
        replay_decision(record, "rules_v999")
    with pytest.raises(ValueError, match="Historical"):
        replay_decision({"decided_by": "rules_v0.5"}, "rules_v0.5")


def test_config_capture_is_request_local_and_pins_missing_files(tmp_path):
    path = tmp_path / "config.yaml"

    @capture_configs
    def request():
        assert load_yaml(path, optional=True) is None
        path.write_text("value: present\n")
        assert load_yaml(path, optional=True) is None
        return config_snapshot()

    assert request()[0]["status"] == "missing"
    assert config_snapshot() == []
    assert load_yaml(path) == {"value": "present"}


def test_replay_command_never_rewrites_examples(runtime, tmp_path, monkeypatch):
    from scripts import export_demo_examples as exporter

    path = tmp_path / "examples.json"
    path.write_text(json.dumps({"examples": [{"id": "fixture", "record": runtime.library()}]}))
    monkeypatch.setattr(exporter, "OUT_JSON", str(path))
    before = path.read_bytes()
    exporter.rederive("ignored-date")
    assert path.read_bytes() == before
    path.write_text(json.dumps({"examples": [{"id": "legacy", "record": {"decided_by": "rules_v0.5"}}]}))
    before = path.read_bytes()
    with pytest.raises(ValueError, match="Historical"):
        exporter.rederive("ignored-date")
    assert path.read_bytes() == before


@pytest.mark.parametrize("surface", ["library", "console"])
def test_image_hash_is_bound_before_inference(runtime, surface):
    expected = hashlib.sha256(runtime.path.read_bytes()).hexdigest()
    runtime.during_segment = lambda: runtime.path.write_bytes(b"replaced during inference")
    record = getattr(runtime, surface)()
    assert record["image_hash"] == expected


def test_capture_ignores_stale_profile_quality_and_calibration_caches(tmp_path, monkeypatch):
    from culture import profiles, quality, qc

    profile_path = tmp_path / "profiles.yaml"
    original = Path(profiles.PROFILES_PATH).read_text()
    profile_path.write_text(original)
    assert profiles.get_profile("msc_phase", str(profile_path)).cutoff == -1.5
    profile_path.write_text(original.replace("-1.5", "-2.5"))
    quality_path = tmp_path / "quality.yaml"
    quality_path.write_text("marker: fresh-quality\n")
    monkeypatch.setattr(quality, "_thresholds", {"marker": "stale"})
    monkeypatch.setattr(quality, "_thresholds_path", str(quality_path))
    monkeypatch.setattr(qc, "_calibration_loaded", True)
    monkeypatch.setattr(qc, "_calibration", {"marker": "stale"})

    @capture_configs
    def request():
        assert profiles.get_profile("msc_phase", str(profile_path)).cutoff == -2.5
        assert quality._load_thresholds(str(quality_path)) == {"marker": "fresh-quality"}
        assert qc._get_calibration() != {"marker": "stale"}
        return config_snapshot()

    assert len(request()) == 3


def test_anomaly_bank_cache_cannot_claim_a_different_config_hash(tmp_path):
    from culture.anomaly import bank_hash, load_banks

    path = tmp_path / "banks.npz"
    bank = np.ones((2, 3), dtype=np.float32)
    np.savez(path, bin_fixture=bank)
    first, reason = load_banks({"bank": {"sha256": bank_hash([bank])}}, str(path))
    assert first is not None and reason is None
    second, reason = load_banks({"bank": {"sha256": "b" * 64}}, str(path))
    assert second is None and "do not match" in reason
