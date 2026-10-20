"""
cultureqc.approvals — run-time check of model weights against approved change records.

configs/approved_changes.jsonl is a hash-chained log of `change` records
(culture/records.py, change_event), written by scripts/approve_change.py. Each
`model` record names a model id and the SHA-256 of the weights it approves;
a later effective record for the same id replaces an earlier one. Future
records do not authorize weights until their timezone-aware effective_from.

Before a model reads an image, check() hashes its weights file and compares
the hash with the latest approved record for that id. The file is hashed when
it is first checked and again whenever its size or modification time changes
(culture/weights.py); every reading compares that hash with the approvals log
as it is at that moment. Selection and chain verification use the same byte
snapshot on every check; a malformed or broken registry approves nothing.

    from culture.approvals import check
    c = check("model", "cpsam_v2", path)    # c.status: "match" | "mismatch" | ...

What it does not prove: who wrote a change record. The chain shows a record
was not edited after later records were added; the approver's identity and
signature belong to the host platform, as for reviews (docs/host_platform.md).
Configuration/profile/rules activation is host-managed, not enforced here.
Each new reading explicitly records that distinction in configuration_activation.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache

from jsonschema import Draft7Validator, FormatChecker, ValidationError

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPROVALS_PATH = os.path.join(REPO, "configs", "approved_changes.jsonl")
STATUSES = ("match", "mismatch", "missing_file", "not_approved", "approvals_unavailable")


class NotApproved(RuntimeError):
    """The weights about to be used are not the ones the latest approved change record names."""

    def __init__(self, check: "Check"):
        super().__init__(f"{check.item}: {check.reason}")
        self.check = check


@dataclass(frozen=True)
class Check:
    subject: str
    item: str
    status: str                         # one of STATUSES
    sha256: str | None                  # the file's, as hashed now
    approved_sha256: str | None         # the latest approved change record's
    approvals_head: str | None          # record_hash of the log's last record, when the chain verifies
    reason: str

    @property
    def ok(self) -> bool:
        return self.status == "match"

    def record_fields(self) -> dict:
        return {"id": self.item, "status": self.status, "sha256": self.sha256,
                "approved_sha256": self.approved_sha256, "approvals_head": self.approvals_head}


def _now():
    return datetime.now(timezone.utc)


@lru_cache(maxsize=1)
def _change_validator():
    """The packaged schema is immutable for the worker's code release."""
    with open(os.path.join(os.path.dirname(__file__), "schema.json")) as stream:
        schema = json.load(stream)
    return Draft7Validator(schema, format_checker=FormatChecker())


def approved(path: str | None = None, *, now: datetime | None = None) -> dict:
    """{"status", "head", "reason", "items": {(subject, id): change record}} for the log at path.

    Verify and select from one byte snapshot. Latest appended effective change wins.
    Selection is repeated even if the file is unchanged, so scheduled changes activate.
    """
    from culture.records import GENESIS_HASH, _canonical_json, _sha256
    path = os.fspath(path or APPROVALS_PATH)
    now = _now() if now is None else now
    if not isinstance(now, datetime) or now.utcoffset() is None:
        raise ValueError("Approval evaluation time must be timezone-aware")
    try:
        with open(path, "rb") as stream:
            raw = stream.read()
    except FileNotFoundError:
        return {"status": "missing_log", "head": None, "reason": f"no approvals log at {path}", "items": {}}
    except OSError as exc:
        return {"status": "invalid_log", "head": None, "reason": str(exc), "items": {}}
    items = {}
    head = GENESIS_HASH
    count = 0
    try:
        for line in raw.decode("utf-8").splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            stored_hash = record.pop("record_hash")
            if record["prev_record_hash"] != head or stored_hash != _sha256(_canonical_json(record)):
                raise ValueError("Approval chain hash or link mismatch")
            record["record_hash"] = stored_hash
            head = stored_hash
            count += 1
            if record.get("record_type") != "change":
                raise ValueError("Approval registry accepts change records only")
            _change_validator().validate(record)
            effective = datetime.fromisoformat(record["effective_from"])
            if effective.utcoffset() is None:
                raise ValueError("Approval effective_from must be timezone-aware")
            subject, after = record["subject"], record["after"]
            if subject not in ("model", "confluency_profile", "rules", "config"):
                raise ValueError("Unknown approval subject")
            if not isinstance(after["id"], str) or not after["id"].strip():
                raise ValueError("Approval requires an artifact id")
            if not re.fullmatch(r"[0-9a-f]{64}", after["sha256"]):
                raise ValueError("Approval requires a SHA-256 identity")
            if not all(isinstance(record["approved_by"][field], str) and record["approved_by"][field].strip()
                       for field in ("id", "name")):
                raise ValueError("Approval requires a declared approver")
            if effective <= now:
                items[(subject, after["id"])] = record
    except (ValueError, KeyError, TypeError, AttributeError, ValidationError) as exc:
        return {"status": "invalid_log", "head": None, "reason": str(exc), "items": {}}
    return {"status": "intact" if count else "empty_chain", "head": head if count else None,
            "reason": f"{count} records; effective at {now.isoformat()}", "items": items}


def check(subject: str, item: str, file_path: str | None, path: str | None = None) -> Check:
    """Compare file_path's SHA-256 with the latest effective change for (subject, item)."""
    from culture.weights import _sha
    path = os.fspath(path or APPROVALS_PATH)
    log = approved(path)
    rel = os.path.relpath(path, REPO) if path.startswith(REPO) else path
    if log["status"] != "intact":
        return Check(subject, item, "approvals_unavailable", None, None, None,
                     f"the approvals log {rel} is {log['status']}: {log['reason']}")
    rec = log["items"].get((subject, item))
    if rec is None:
        return Check(subject, item, "not_approved", None, None, log["head"],
                     f"no approved change record for {subject} {item!r} in {rel}")
    want = rec["after"]["sha256"]
    sha = _sha(file_path)
    if sha is None:
        return Check(subject, item, "missing_file", None, want, log["head"], f"weights file not found: {file_path}")
    if sha != want:
        return Check(subject, item, "mismatch", sha, want, log["head"],
                     f"weights SHA-256 {sha[:12]}… is not the approved {want[:12]}…")
    return Check(subject, item, "match", sha, want, log["head"],
                 f"weights match the change record approved by {rec['approved_by']['name']}")


def require(subject: str, item: str, file_path: str | None, path: str | None = None) -> Check:
    """check(), raising NotApproved unless the weights match."""
    c = check(subject, item, file_path, path)
    if not c.ok:
        raise NotApproved(c)
    return c
