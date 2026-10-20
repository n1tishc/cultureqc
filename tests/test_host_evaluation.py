"""Offline host boundary tests; all model measurements here are synthetic stubs."""

import json
from dataclasses import replace
import sys
import time

import pytest

from scripts.host_evaluation import assess_record, evaluate, main, run_bounded, worker, write_json
from test_decision_provenance import runtime


def test_current_record_has_non_actuating_missing_check_outcome(runtime):
    record = runtime.library()
    result = assess_record(record)
    assert result["status"] == "required_check_unavailable"
    assert result["record"] == record
    assert result["host_actionable"] is False
    assert result["host_next_step"] == "operator_review"
    assert result["retry_automatically"] is False


@pytest.mark.parametrize("passed", [False, True])
def test_quality_outcome_never_schedules(runtime, monkeypatch, passed):
    from culture import quality, profiles
    from culture.quality import QualityResult

    original = profiles.get_profile
    monkeypatch.setattr(profiles, "get_profile", lambda selected: replace(original(selected), quality="synthetic"))
    monkeypatch.setattr(quality, "quality_gate", lambda *args, **kwargs: QualityResult(
        blur=1, mean_intensity=100, uniformity=1, passed=passed,
        reasons=[] if passed else ["synthetic_blur"]))
    record = runtime.library()
    result = assess_record(record)
    assert result["status"] == ("advisory_reading" if passed else "check_failed")
    if not passed:
        assert record["recommended_action"] == "reimage"
    assert result["host_next_step"] == "operator_review"


@pytest.mark.parametrize("mutation", ["hash", "schema", "policy", "actionable", "provenance", "record_id", "previous_hash"])
def test_corrupt_and_historical_records_are_refused(runtime, mutation):
    from culture.records import _canonical_json, _sha256

    record = runtime.library()
    if mutation == "hash":
        record["confluency_pct"] += 1
    else:
        if mutation == "schema":
            record["schema_version"] = "0.4"
        elif mutation == "policy":
            record["decided_by"] = "rules_v0.5"
        elif mutation == "actionable":
            record["decision"]["host_actionable"] = True
        elif mutation == "record_id":
            record.pop("record_id")
        elif mutation == "previous_hash":
            record["prev_record_hash"] = 123
        else:
            record["preprocessing"]["source_sha256"] = "0" * 64
        record["record_hash"] = _sha256(_canonical_json({key: value for key, value in record.items() if key != "record_hash"}))
    with pytest.raises(Exception):
        assess_record(record)


def test_record_evaluation_runs_in_worker_without_models(runtime, tmp_path):
    record = runtime.library()
    source = tmp_path / "reading.json"
    write_json(source, record)
    original = source.read_bytes()
    directory = tmp_path / "run"
    result = evaluate(source, directory, timeout_seconds=30)
    assert result["record"] == record
    assert source.read_bytes() == original
    assert not (directory / "evaluation.jsonl").exists()
    manifest = json.loads((directory / "manifest.json").read_text())
    assert manifest["mode"] == "record"
    assert "culture/schema.json" in manifest["source_sha256"]
    assert "outcome.json" in manifest["output_sha256"]
    assert manifest["installed_packages"]
    assert manifest["git_head"]
    with pytest.raises(FileExistsError):
        evaluate(source, directory)


def test_missing_input_has_no_implicit_continue(tmp_path):
    result = evaluate(tmp_path / "absent.png", tmp_path / "run", mode="live")
    assert result["status"] == "input_or_dependency_missing"
    assert result["record"] is None
    assert result["host_actionable"] is False


def test_worker_refuses_legacy_record(tmp_path):
    source, request, result = [tmp_path / name for name in ("record.json", "request.json", "result.json")]
    write_json(source, {"schema_version": "0.4"})
    write_json(request, {"mode": "record", "input_path": str(source)})
    worker(request, result)
    assert json.loads(result.read_text())["status"] == "refused"


def test_live_invalid_image_is_refused_before_models(tmp_path):
    source = tmp_path / "invalid.png"
    source.write_bytes(b"not an image")
    result = evaluate(source, tmp_path / "run", mode="live", timeout_seconds=30)
    assert result["record"] is None
    assert result["status"] == "refused"
    assert not (tmp_path / "run" / "evaluation.jsonl").exists()


def test_timeout_kills_worker_before_late_write(tmp_path):
    late = tmp_path / "late"
    command = [sys.executable, "-c", f"import time; from pathlib import Path; time.sleep(.6); Path({str(late)!r}).touch()"]
    assert run_bounded(command, tmp_path, .1) is None
    time.sleep(.7)
    assert not late.exists()


def test_timeout_outcome_never_uses_partial_result(tmp_path, monkeypatch):
    from scripts import host_evaluation

    monkeypatch.setattr(host_evaluation, "run_bounded", lambda *args: None)
    source = tmp_path / "reading.json"
    source.write_text("{}")
    result = evaluate(source, tmp_path / "run")
    assert result["status"] == "timeout"
    assert result["record"] is None
    assert result["retry_automatically"] is False


@pytest.mark.parametrize("timeout", [0, -1, float("nan"), float("inf"), True])
def test_bad_timeouts_do_not_launch(tmp_path, timeout):
    with pytest.raises(ValueError):
        run_bounded([sys.executable, "-c", "raise AssertionError"], tmp_path, timeout)


def test_external_log_and_optional_finetune_not_accepted(tmp_path):
    for options in ({"log_path": "production.jsonl"}, {"finetuned_id": "anything"}):
        with pytest.raises(ValueError, match="Unsupported"):
            evaluate("missing", tmp_path / "run", mode="live", options=options)


def test_manifest_failure_is_recorded(tmp_path, monkeypatch):
    from scripts import host_evaluation

    def fail():
        raise OSError("inventory unavailable")

    monkeypatch.setattr(host_evaluation, "manifest", fail)
    result = evaluate("unused", tmp_path / "run")
    assert result["status"] == "manifest_failed"
    assert result["record"] is None
    assert (tmp_path / "run" / "outcome.json").exists()


def test_changed_source_inventory_invalidates_result(runtime, tmp_path, monkeypatch):
    from scripts import host_evaluation

    source = tmp_path / "reading.json"
    write_json(source, runtime.library())
    calls = iter([{"first": "hash"}, {"changed": "hash"}])
    monkeypatch.setattr(host_evaluation, "source_inventory", lambda: next(calls))
    result = evaluate(source, tmp_path / "run", timeout_seconds=30)
    assert result["status"] == "source_changed"
    assert result["record"] is None


def test_timeout_exit_race_stays_a_timeout(tmp_path, monkeypatch):
    from scripts import host_evaluation
    import subprocess

    class ExitingProcess:
        pid = 123

        def wait(self, timeout=None):
            if timeout is not None:
                raise subprocess.TimeoutExpired("synthetic", timeout)
            return 0

    def gone(*args):
        raise ProcessLookupError("already exited")

    monkeypatch.setattr(host_evaluation.subprocess, "Popen", lambda *args, **kwargs: ExitingProcess())
    monkeypatch.setattr(host_evaluation.os, "killpg", gone)
    assert run_bounded(["synthetic-not-executed"], tmp_path, 1) is None


def test_non_object_request_has_cli_error(tmp_path):
    request = tmp_path / "request.json"
    request.write_text("null")
    with pytest.raises(SystemExit) as error:
        main(["--live-request", str(request), "--output-dir", str(tmp_path / "run")])
    assert error.value.code == 2
    assert not (tmp_path / "run").exists()
