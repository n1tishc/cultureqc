#!/usr/bin/env python3
"""Check E0 protocol readiness without reading images or running a model."""

import argparse
import hashlib
import json
import math
import re
from pathlib import Path


SPLITS = ("development", "tuning", "final_test")
HASH = re.compile(r"[0-9a-f]{64}")
REQUIRED_TEXT = (
    "protocol_id", "owner", "approval_reference", "setup_id", "microscope",
    "objective", "cell_type", "fov_strategy", "label_method", "primary_endpoint",
    "acceptance_rule", "sample_size_justification", "candidate_plan",
    "gate_rejection_policy", "analysis_plan", "artifact_retention_plan",
)


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _number(value, minimum, maximum=math.inf):
    try:
        return (type(value) in (int, float) and math.isfinite(value)
                and minimum <= value <= maximum)
    except OverflowError:
        return False


def _digest(value):
    return isinstance(value, str) and HASH.fullmatch(value) is not None


def validate(protocol, manifest):
    """Return structural blockers; approvals and unseen-data claims are attestations."""
    errors = []
    if not isinstance(protocol, dict) or not isinstance(manifest, dict):
        return ["protocol and manifest must be JSON objects"]
    if any(type(document.get("schema_version")) is not int or document["schema_version"] != 1
           for document in (protocol, manifest)):
        errors.append("protocol and manifest schema_version must be 1")
    if protocol.get("status") != "approved":
        errors.append("protocol status must be approved by the owner")
    if protocol.get("workstream") not in ("E1", "E2", "E3"):
        errors.append("workstream must be E1, E2 or E3")
    for field in REQUIRED_TEXT:
        if not _text(protocol.get(field)):
            errors.append(f"{field} is required")
    for field in ("pixel_size_um", "cadence_hours"):
        if not _number(protocol.get(field), 0) or protocol.get(field) == 0:
            errors.append(f"{field} must be finite and positive")
    if not _number(protocol.get("max_false_alerts_per_100"), 0, 100):
        errors.append("max_false_alerts_per_100 must be between 0 and 100")
    if protocol.get("false_alert_denominator") not in ("images", "visits", "decisions"):
        errors.append("false_alert_denominator must be images, visits or decisions")
    if not _number(protocol.get("max_detection_delay_hours"), 0):
        errors.append("max_detection_delay_hours must be finite and nonnegative")
    if protocol.get("final_test_custodian") in (None, protocol.get("owner")) or not _text(protocol.get("final_test_custodian")):
        errors.append("final_test_custodian must name a separate custodian")
    if not _text(protocol.get("split_assignment_reference")):
        errors.append("split_assignment_reference is required")
    if manifest.get("protocol_id") != protocol.get("protocol_id"):
        errors.append("manifest protocol_id must match the protocol")
    if not _digest(protocol.get("manifest_sha256")):
        errors.append("manifest_sha256 must be a lowercase SHA-256 digest")

    minimums = protocol.get("minimum_independent_groups")
    if not isinstance(minimums, dict) or set(minimums) != set(SPLITS):
        errors.append("minimum_independent_groups must specify all three splits")
        minimums = {}
    for split, labels in minimums.items():
        if not isinstance(labels, dict) or set(labels) != {"control", "case"}:
            errors.append(f"{split} must specify control and case minimums")
        elif any(type(count) is not int or count < 1 for count in labels.values()):
            errors.append(f"{split} group minimums must be positive integers")

    rows = manifest.get("samples")
    if not isinstance(rows, list) or not rows:
        return errors + ["manifest samples must be a nonempty list"]
    assignments = {key: {} for key in ("culture_id", "sequence_id", "session_id", "lineage_id", "image_sha256")}
    sample_ids = set()
    image_hashes = set()
    groups = {(split, label): set() for split in SPLITS for label in ("control", "case")}
    for index, row in enumerate(rows):
        prefix = f"sample {index}"
        if not isinstance(row, dict):
            errors.append(f"{prefix} must be an object")
            continue
        split, label = row.get("split"), row.get("label")
        if split not in SPLITS or label not in ("control", "case"):
            errors.append(f"{prefix} requires a valid split and control/case label")
            continue
        for field in ("sample_id", "label_reference", *assignments):
            if not _text(row.get(field)):
                errors.append(f"{prefix}: {field} is required")
        sample_id = row.get("sample_id")
        if _text(sample_id):
            if sample_id in sample_ids:
                errors.append(f"{prefix}: duplicate sample_id")
            sample_ids.add(sample_id)
        if not _digest(row.get("image_sha256")):
            errors.append(f"{prefix}: image_sha256 must be a lowercase SHA-256 digest")
        else:
            if row["image_sha256"] in image_hashes:
                errors.append(f"{prefix}: duplicate image_sha256")
            image_hashes.add(row["image_sha256"])
        for field, seen in assignments.items():
            value = row.get(field)
            if not _text(value):
                continue
            if value in seen and seen[value] != split:
                errors.append(f"{prefix}: {field} crosses splits")
            seen[value] = split
        if row.get("label_origin") not in ("confirmed", "simulated"):
            errors.append(f"{prefix}: label_origin must be confirmed or simulated")
        if row.get("prior_use") not in ("unseen", "development", "historical_evaluation"):
            errors.append(f"{prefix}: prior_use is invalid")
        if split == "final_test" and row.get("prior_use") != "unseen":
            errors.append(f"{prefix}: final_test must be unseen, not recycled evidence")
        if _text(row.get("culture_id")):
            groups[(split, label)].add(row["culture_id"])
    for split, labels in minimums.items():
        if not isinstance(labels, dict):
            continue
        for label, count in labels.items():
            if (split, label) in groups and type(count) is int and count > 0:
                actual = len(groups[(split, label)])
                if actual < count:
                    errors.append(f"{split}/{label}: {actual} independent cultures, requires {count}")
    return errors


def check_files(protocol_path, manifest_path):
    protocol_bytes = Path(protocol_path).read_bytes()
    manifest_bytes = Path(manifest_path).read_bytes()
    protocol = json.loads(protocol_bytes)
    manifest = json.loads(manifest_bytes)
    errors = validate(protocol, manifest)
    manifest_hash = hashlib.sha256(manifest_bytes).hexdigest()
    if isinstance(protocol, dict) and protocol.get("manifest_sha256") != manifest_hash:
        errors.append("manifest bytes do not match protocol manifest_sha256")
    return {
        "ready": not errors,
        "blockers": errors,
        "protocol_sha256": hashlib.sha256(protocol_bytes).hexdigest(),
        "manifest_sha256": manifest_hash,
        "scope": "Structural readiness only; not approval authentication or scientific validation.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("protocol", type=Path)
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    try:
        result = check_files(args.protocol, args.manifest)
    except (OSError, ValueError) as error:
        result = {"ready": False, "blockers": [str(error)]}
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0 if result["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
