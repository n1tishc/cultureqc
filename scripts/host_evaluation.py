"""Local, non-actuating host contract exercise; not a serving endpoint."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import platform
import signal
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
REQUEST_FIELDS = {
    "image_path", "flask_id", "cell_line", "profile_id", "setup_id", "captured_at",
    "hours_since_passage", "hours_since_feed", "imager_id", "fov", "lineage",
    "environment", "protocol_stage", "pixel_size_um", "check_policy", "line_config",
}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def outcome(status, reason, record=None):
    return {"status": status, "reason": reason, "host_actionable": False,
            "host_next_step": "operator_review", "retry_automatically": False,
            "record": record}


def assess_record(record):
    import jsonschema
    from culture.records import RecordWriter, SCHEMA_VERSION
    from culture.rules import RULES_VERSION

    if (not isinstance(record, dict) or record.get("record_type") != "reading"
            or record.get("schema_version") != SCHEMA_VERSION
            or record.get("decided_by") != RULES_VERSION):
        raise ValueError("Requires a current schema 0.8 / rules_v0.7 reading; no legacy migration")
    payload = {key: value for key, value in record.items() if key != "record_hash"}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    if hashlib.sha256(canonical.encode()).hexdigest() != record.get("record_hash"):
        raise ValueError("Record hash mismatch")
    schema = json.loads((ROOT / "culture" / "schema.json").read_text())
    jsonschema.validate(record, schema, format_checker=jsonschema.FormatChecker())
    RecordWriter._prepare(record)
    decision = record["decision"]
    if decision["host_actionable"] is not False or decision["mode"] != "advisory":
        raise ValueError("Unexpected actionable policy output")
    checks = decision["checks"]
    if any(check["status"] == "failed" for check in checks.values()):
        status = "check_failed"
    elif any(check["requirement"] == "required" and check["status"] == "unavailable"
             for check in checks.values()):
        status = "required_check_unavailable"
    else:
        status = "advisory_reading"
    return outcome(status, decision["reason_code"], record)


def worker(request_path, result_path):
    from culture.approvals import NotApproved

    try:
        request = json.loads(Path(request_path).read_text())
        if request["mode"] == "record":
            record = json.loads(Path(request["input_path"]).read_text())
        else:
            from culture.pipeline import analyze
            from culture.records import verify_chain
            from culture.rules import CheckPolicy, LineConfig

            options = request["options"].copy()
            for name, factory in (("check_policy", CheckPolicy), ("line_config", LineConfig)):
                if name in options:
                    options[name] = factory(**options[name])
            record = analyze(request["input_path"], log_path=request["log_path"], **options)
            if not verify_chain(request["log_path"])[0]:
                raise ValueError("Evaluation audit log did not verify")
            if record["image_hash"] != request["input_sha256"]:
                raise ValueError("Analyzed input differs from the evaluation snapshot")
        result = assess_record(record)
    except FileNotFoundError as error:
        result = outcome("input_or_dependency_missing", str(error))
    except NotApproved as error:
        result = outcome("model_not_approved", str(error))
    except ImportError as error:
        result = outcome("dependency_unavailable", str(error))
    except (ValueError, TypeError, KeyError) as error:
        result = outcome("refused", f"{type(error).__name__}: {error}")
    except Exception as error:
        result = outcome("evaluation_error", f"{type(error).__name__}: {error}")
    write_json(result_path, result)


def run_bounded(command, directory, timeout_seconds):
    if (isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float))
            or not math.isfinite(timeout_seconds) or timeout_seconds <= 0):
        raise ValueError("timeout_seconds must be finite and positive")
    if os.name != "posix":
        raise ValueError("This evaluation harness requires POSIX process-group termination")
    with (directory / "worker.stdout").open("wb") as stdout, (directory / "worker.stderr").open("wb") as stderr:
        process = subprocess.Popen(command, cwd=ROOT, stdout=stdout, stderr=stderr, start_new_session=True)
        try:
            return process.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
            return None


def source_inventory():
    paths = [path for folder in ("culture", "demo", "configs", "config", "scripts")
             for path in (ROOT / folder).rglob("*")
             if path.is_file() and path.suffix in (".py", ".json", ".jsonl", ".yaml", ".yml")]
    paths += list(ROOT.glob("requirements*.txt"))
    return {str(path.relative_to(ROOT)): digest(path) for path in sorted(paths)}


def manifest():
    return {
        "python": sys.version, "platform": platform.platform(),
        "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, timeout=10).strip(),
        "git_status": subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True, timeout=10),
        "source_sha256": source_inventory(),
        "installed_packages": dict(sorted((package.metadata["Name"], package.version)
                                          for package in importlib.metadata.distributions())),
        "scope": "offline host contract evaluation; no actuation, deployment or scientific acceptance",
        "performance": "single cold worker elapsed time only; p95, queue and batch capacity unmeasured",
    }


def evaluate(input_path, output_dir, *, mode="record", options=None, timeout_seconds=120):
    if mode not in ("record", "live"):
        raise ValueError("mode must be record or live")
    options = dict(options or {})
    if set(options) - (REQUEST_FIELDS - {"image_path"}):
        raise ValueError("Unsupported live request fields")
    if (isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float))
            or not math.isfinite(timeout_seconds) or timeout_seconds <= 0):
        raise ValueError("timeout_seconds must be finite and positive")
    directory = Path(output_dir).resolve()
    directory.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    inventory = {"manifest_status": "unavailable"}
    phase = "manifest"
    try:
        inventory = manifest()
        inventory["manifest_status"] = "captured"
        phase = "evaluation"
        source = Path(input_path).resolve()
        snapshot = directory / ("input" + source.suffix)
        snapshot.write_bytes(source.read_bytes())
        request = {"mode": mode, "original_input": str(source), "input_path": str(snapshot),
                   "input_sha256": digest(snapshot), "options": options,
                   "log_path": str(directory / "evaluation.jsonl")}
        write_json(directory / "request.json", request)
        command = [sys.executable, "-m", "scripts.host_evaluation", "--worker",
                   str(directory / "request.json"), str(directory / "worker-result.json")]
        code = run_bounded(command, directory, timeout_seconds)
        if code is None:
            result = outcome("timeout", "Worker killed; preserve partial log and reconcile before any new attempt")
        elif code != 0 or not (directory / "worker-result.json").exists():
            result = outcome("worker_failed", "Worker did not return a complete result; preserve diagnostic files")
        else:
            result = json.loads((directory / "worker-result.json").read_text())
        inventory["source_changed_during_run"] = source_inventory() != inventory["source_sha256"]
        if inventory["source_changed_during_run"]:
            result = outcome("source_changed", "Source/config inventory changed; freeze the bundle before a new evaluation")
    except FileNotFoundError as error:
        result = outcome("manifest_failed" if phase == "manifest" else "input_or_dependency_missing", str(error))
    except Exception as error:
        result = outcome("manifest_failed" if phase == "manifest" else "evaluation_error",
                         f"{type(error).__name__}: {error}")
    inventory["elapsed_seconds"] = time.monotonic() - started
    inventory["timeout_seconds"] = timeout_seconds
    inventory["mode"] = mode
    if result["record"] is not None:
        inventory["reading_identity"] = {name: result["record"].get(name) for name in (
            "record_hash", "schema_version", "decided_by", "model_versions", "model_weights_hash",
            "model_check", "config_hashes", "configuration_activation", "image_hash")}
    write_json(directory / "outcome.json", result)
    inventory["output_sha256"] = {path.name: digest(path) for path in sorted(directory.iterdir()) if path.is_file()}
    write_json(directory / "manifest.json", inventory)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sources = parser.add_mutually_exclusive_group(required=True)
    sources.add_argument("--record", help="One current reading JSON; no inference or model downloads")
    sources.add_argument("--live-request", help="Explicit live Python-library request JSON; models required")
    sources.add_argument("--worker", nargs=2, help=argparse.SUPPRESS)
    parser.add_argument("--output-dir")
    parser.add_argument("--timeout-seconds", type=float, default=120)
    args = parser.parse_args(argv)
    if args.worker:
        worker(*args.worker)
        return 0
    if not args.output_dir:
        parser.error("--output-dir is required and must not already exist")
    try:
        options = json.loads(Path(args.live_request).read_text()) if args.live_request else {}
        if not isinstance(options, dict):
            raise ValueError("Live request must be a JSON object")
        source = options.pop("image_path") if args.live_request else args.record
        result = evaluate(source, args.output_dir, mode="live" if args.live_request else "record",
                          options=options, timeout_seconds=args.timeout_seconds)
    except (OSError, ValueError, TypeError, KeyError) as error:
        parser.exit(2, f"Evaluation not started/completed: {error}\n")
    print(json.dumps({key: value for key, value in result.items() if key != "record"}, indent=2))
    return 0 if result["record"] is not None else 1


if __name__ == "__main__":
    raise SystemExit(main())
