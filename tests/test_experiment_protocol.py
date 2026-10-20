"""E0 checks need no models, images, network or scientific-result rewrites."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from check_experiment_protocol import REQUIRED_TEXT, SPLITS, check_files, validate


@pytest.fixture
def packet():
    protocol = {field: f"fixture {field}" for field in REQUIRED_TEXT}
    protocol.update(
        schema_version=1, status="approved", workstream="E1", pixel_size_um=1.3,
        cadence_hours=6, max_false_alerts_per_100=5, false_alert_denominator="images",
        max_detection_delay_hours=12, final_test_custodian="fixture custodian",
        split_assignment_reference="fixture allocation", manifest_sha256="a" * 64,
        minimum_independent_groups={split: {"control": 1, "case": 1} for split in SPLITS},
    )
    samples = []
    for split in SPLITS:
        for label in ("control", "case"):
            identity = f"{split}-{label}"
            samples.append({
                "sample_id": identity, "split": split, "label": label,
                "culture_id": identity, "sequence_id": identity, "session_id": identity,
                "lineage_id": identity, "image_sha256": hashlib.sha256(identity.encode()).hexdigest(),
                "label_reference": "fixture label", "label_origin": "confirmed", "prior_use": "unseen",
            })
    return protocol, {"schema_version": 1, "protocol_id": protocol["protocol_id"], "samples": samples}


def test_complete_fixture_is_structurally_ready(packet):
    assert validate(*packet) == []


@pytest.mark.parametrize("field", ["culture_id", "sequence_id", "session_id", "lineage_id", "image_sha256"])
def test_cross_split_leakage_is_blocked(packet, field):
    protocol, manifest = packet
    manifest["samples"][-1][field] = manifest["samples"][0][field]
    assert any(f"{field} crosses splits" in error for error in validate(protocol, manifest))


def test_frames_do_not_count_as_independent_cultures(packet):
    protocol, manifest = packet
    protocol["minimum_independent_groups"]["final_test"]["case"] = 2
    duplicate = dict(manifest["samples"][-1], sample_id="another-frame", image_sha256="b" * 64)
    manifest["samples"].append(duplicate)
    assert any("1 independent cultures, requires 2" in error for error in validate(protocol, manifest))


def test_duplicate_images_cannot_inflate_group_counts(packet):
    protocol, manifest = packet
    duplicate = dict(manifest["samples"][-1], sample_id="duplicate", culture_id="another-culture")
    manifest["samples"].append(duplicate)
    assert any("duplicate image_sha256" in error for error in validate(protocol, manifest))


@pytest.mark.parametrize("field,value", [
    ("status", "draft"), ("final_test_custodian", "fixture owner"),
    ("minimum_independent_groups", {}), ("schema_version", True),
    ("pixel_size_um", 0), ("cadence_hours", float("nan")),
])
def test_unready_protocol_is_blocked(packet, field, value):
    protocol, manifest = packet
    protocol[field] = value
    assert validate(protocol, manifest)


@pytest.mark.parametrize("prior_use", ["development", "historical_evaluation", None])
def test_reused_final_test_data_is_blocked(packet, prior_use):
    protocol, manifest = packet
    manifest["samples"][-1]["prior_use"] = prior_use
    assert any("final_test must be unseen" in error for error in validate(protocol, manifest))


@pytest.mark.parametrize("value", [None, True, -1, 101, 10**400, float("nan"), float("inf"), "5"])
def test_invalid_alert_budgets_are_blocked(packet, value):
    protocol, manifest = packet
    protocol["max_false_alerts_per_100"] = value
    assert any("max_false_alerts_per_100" in error for error in validate(protocol, manifest))


@pytest.mark.parametrize("field", REQUIRED_TEXT)
def test_required_protocol_fields(packet, field):
    protocol, manifest = packet
    protocol[field] = " "
    assert any(field in error for error in validate(protocol, manifest))


def test_manifest_hash_binds_exact_bytes(packet, tmp_path):
    protocol, manifest = packet
    manifest_path = tmp_path / "manifest.json"
    protocol_path = tmp_path / "protocol.json"
    manifest_path.write_text(json.dumps(manifest))
    protocol["manifest_sha256"] = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    protocol_path.write_text(json.dumps(protocol))
    assert check_files(protocol_path, manifest_path)["ready"]
    manifest_path.write_text(json.dumps(manifest) + "\n")
    result = check_files(protocol_path, manifest_path)
    assert not result["ready"]
    assert "manifest bytes do not match protocol manifest_sha256" in result["blockers"]


def test_draft_cli_fails_without_modifying_inputs():
    folder = REPO / "docs/specs/detection-experiments"
    paths = [folder / "protocol.draft.json", folder / "manifest.draft.json"]
    before = [path.read_bytes() for path in paths]
    result = subprocess.run(
        [sys.executable, str(REPO / "scripts/check_experiment_protocol.py"), *map(str, paths)],
        capture_output=True, text=True,
    )
    assert result.returncode == 1
    assert not json.loads(result.stdout)["ready"]
    assert before == [path.read_bytes() for path in paths]


def test_cli_returns_blockers_for_large_json_numbers(packet, tmp_path):
    protocol, manifest = packet
    protocol["pixel_size_um"] = 10**400
    protocol_path = tmp_path / "protocol.json"
    manifest_path = tmp_path / "manifest.json"
    protocol_path.write_text(json.dumps(protocol))
    manifest_path.write_text(json.dumps(manifest))
    result = subprocess.run(
        [sys.executable, str(REPO / "scripts/check_experiment_protocol.py"),
         str(protocol_path), str(manifest_path)], capture_output=True, text=True,
    )
    assert result.returncode == 1
    assert not json.loads(result.stdout)["ready"]
    assert "pixel_size_um" in result.stdout
    assert not result.stderr


@pytest.mark.parametrize("value", [None, [], "invalid"])
def test_invalid_document_shapes(value):
    assert validate(value, {})
    assert validate({}, value)


def test_malformed_row_fields_return_blockers(packet):
    protocol, manifest = packet
    manifest["samples"][0].update(sample_id=[], culture_id={}, image_sha256=False)
    manifest["samples"].append(None)
    assert validate(protocol, manifest)
