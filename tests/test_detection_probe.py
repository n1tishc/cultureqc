"""Offline command safety and machine-readable output, with no model downloads."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import subprocess
import sys

import cv2
import numpy as np

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/probe_detection_signals.py"


def run_probe(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)],
                          capture_output=True, text=True, timeout=30)


def test_coverage_command_defaults_to_plan_without_models(tmp_path):
    source = tmp_path / "frame.png"
    cv2.imwrite(str(source), np.zeros((1040, 1392), np.uint8))
    before = source.read_bytes()
    process = run_probe("coverage", source)
    assert process.returncode == 0, process.stderr
    result = json.loads(process.stdout)
    assert result["status"] == "plan_only"
    assert result["tile_count"] == 35 and result["coverage_fraction"] == 1.0
    assert result["used_in_decision"] is False
    assert source.read_bytes() == before
    assert list(tmp_path.iterdir()) == [source]


def test_scoring_needs_explicit_local_inputs(tmp_path):
    source = tmp_path / "frame.png"
    cv2.imwrite(str(source), np.zeros((224, 224), np.uint8))
    process = run_probe("coverage", source, "--score")
    assert process.returncode == 1
    assert "requires --model-dir" in json.loads(process.stdout)["reason"]


def test_high_bit_depth_image_is_not_silently_darkened(tmp_path):
    source = tmp_path / "frame.png"
    cv2.imwrite(str(source), np.full((224, 224), 4095, np.uint16))
    process = run_probe("coverage", source)
    assert process.returncode == 1
    assert "uint8" in json.loads(process.stdout)["reason"]


def test_bad_growth_packet_is_structured_error(tmp_path):
    source = tmp_path / "visits.json"
    source.write_text("{}")
    process = run_probe("growth", source)
    assert process.returncode == 1
    assert json.loads(process.stdout)["status"] == "error"


def test_growth_command_returns_frozen_signals_without_mutating_input(tmp_path):
    origin = datetime(2026, 1, 1, tzinfo=timezone.utc)
    visits = [{
        "timestamp": (origin + timedelta(hours=hours)).isoformat(),
        "segment_id": "fixture-segment",
        "model_versions": {"seg": "fixture"},
        "config_hashes": {"quality": "fixture"},
        "quality": {"pass": True},
        "confluency_mean": float(85 / (1 + np.exp(-0.08 * (hours - 45)))),
        "confluency_sd": 0,
    } for hours in range(0, 97, 6)]
    source = tmp_path / "visits.json"
    source.write_text(json.dumps({
        "visits": visits, "baseline_end": visits[6]["timestamp"],
        "baseline_reason": "Predeclared synthetic 36-hour prefix",
        "horizon_hours": 12, "max_gap_hours": 6, "min_expected_growth_pp": 1,
    }))
    before = source.read_bytes()
    process = run_probe("growth", source)
    assert process.returncode == 0, process.stderr
    result = json.loads(process.stdout)
    assert result["used_in_decision"] is False
    assert result["status"] == "experimental_uncalibrated"
    assert len(result["signals"]) == len(visits)
    assert all(signal["reference_id"] is None for signal in result["signals"][:7])
    assert len({signal["reference_id"] for signal in result["signals"][7:]}) == 1
    assert result["signals"][-1]["status"] == "OK"
    assert abs(result["signals"][-1]["growth_fraction"] - 1) < 0.01
    assert source.read_bytes() == before
    assert list(tmp_path.iterdir()) == [source]


def test_empty_image_is_structured_error(tmp_path):
    source = tmp_path / "empty.png"
    source.write_bytes(b"")
    process = run_probe("coverage", source)
    assert process.returncode == 1
    assert json.loads(process.stdout)["reason"] == "image is empty"
    assert not process.stderr


def test_malformed_yaml_is_rejected_before_model_loading(tmp_path):
    source = tmp_path / "frame.png"
    cv2.imwrite(str(source), np.zeros((224, 224), np.uint8))
    config = tmp_path / "broken.yaml"
    config.write_text("method: [broken")
    process = run_probe("coverage", source, "--score", "--model-dir", tmp_path,
                        "--config", config, "--banks", tmp_path / "nonexistent.npz", "--confluency", 30)
    assert process.returncode == 1
    assert "not valid YAML" in json.loads(process.stdout)["reason"]
    assert not process.stderr
