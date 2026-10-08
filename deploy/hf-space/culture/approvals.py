"""
cultureqc.approvals — run-time check of model weights against approved change records.

configs/approved_changes.jsonl is a hash-chained log of `change` records
(culture/records.py, change_event), written by scripts/approve_change.py. Each
`model` record names a model id and the SHA-256 of the weights it approves;
a later record for the same id replaces an earlier one.

Before a model reads an image, check() hashes its weights file and compares
the hash with the latest approved record for that id. The file is hashed when
it is first checked and again whenever its size or modification time changes
(culture/weights.py); every reading compares that hash with the approvals log
as it is at that moment. The log's chain is verified each time it changes,
and a broken chain approves nothing.

    from culture.approvals import check
    c = check("model", "cpsam_v2", path)    # c.status: "match" | "mismatch" | ...

What it does not prove: who wrote a change record. The chain shows a record
was not edited after later records were added; the approver's identity and
signature belong to the host platform, as for reviews (docs/host_platform.md).
Profiles and configs are not checked here: their SHA-256 are recorded in every
reading (confluency_profile, config_hashes), not compared with an approved set.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass

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


_memo: dict[str, tuple[tuple, dict]] = {}


def approved(path: str | None = None) -> dict:
    """{"status", "head", "reason", "items": {(subject, id): change record}} for the log at path.

    Re-read and re-verified whenever the file's size or modification time changes.
    """
    from culture.records import verify_chain
    path = path or APPROVALS_PATH
    if not os.path.exists(path):
        return {"status": "missing_log", "head": None, "reason": f"no approvals log at {path}", "items": {}}
    st = os.stat(path)
    key = (st.st_size, st.st_mtime_ns)
    if path in _memo and _memo[path][0] == key:
        return _memo[path][1]
    res = verify_chain(path)
    out = {"status": res.status, "head": res.head_hash if res.ok else None, "reason": res.reason, "items": {}}
    if res.ok:
        with open(path) as f:
            for line in f:
                if line.strip():
                    r = json.loads(line)
                    if r.get("record_type") == "change":
                        out["items"][(r["subject"], r["after"]["id"])] = r      # later records replace earlier
    _memo[path] = (key, out)
    return out


def check(subject: str, item: str, file_path: str | None, path: str | None = None) -> Check:
    """Compare file_path's SHA-256 with the latest approved change record for (subject, item)."""
    from culture.weights import _sha
    path = path or APPROVALS_PATH
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
