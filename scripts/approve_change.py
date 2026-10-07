"""
Append an approved `model` change record to configs/approved_changes.jsonl (culture/approvals.py).

The record names the model id and its weights' SHA-256 (hashed here from the file), the record it
replaces, the reason, the evidence files with their SHA-256, and who approved it. Refuses to write
when the log's chain does not verify.

    .venv/bin/python scripts/approve_change.py cpsam_v2 --weights ~/.cellpose/models/cpsam_v2 \\
        --reason "..." --evidence results/confluency_profiles.md --approved-by "repository owner"

`check` prints each configured model's run-time check without writing anything:

    .venv/bin/python scripts/approve_change.py check [--weights PATH]
"""

from __future__ import annotations

import argparse
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from culture.approvals import APPROVALS_PATH, approved, check  # noqa: E402
from culture.records import RecordWriter, change_event, hash_file  # noqa: E402


def cmd_check(a):
    from culture import finetuned
    log = approved()
    print(f"approvals log {os.path.relpath(APPROVALS_PATH, REPO)}: {log['status']} ({log['reason']})")
    rows = [("cpsam_v2", a.weights if a.model == "cpsam_v2" else _cellpose_path())]
    for mid, e in finetuned.load_config().items():
        rows.append((mid, a.weights if a.model == mid else finetuned.weights_file(e)))
    for mid, path in rows:
        c = check("model", mid, path)
        print(f"  {mid}: {c.status} — {c.reason}\n    file {path}")


def _cellpose_path() -> str | None:
    from culture.weights import _cellpose_path as p
    return p()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("model", help="model id, or `check`")
    ap.add_argument("--weights", help="weights file to hash (for check: the file to check for --model)")
    ap.add_argument("--for", dest="for_model", help="check only: the model id --weights stands in for")
    ap.add_argument("--reason")
    ap.add_argument("--evidence", nargs="+", default=[])
    ap.add_argument("--approved-by")
    a = ap.parse_args()
    if a.model == "check":
        a.model = a.for_model
        cmd_check(a)
        return
    if not (a.weights and a.reason and a.evidence and a.approved_by):
        ap.error("approving needs --weights, --reason, --evidence and --approved-by")
    log = approved()
    if log["status"] not in ("intact", "missing_log"):
        sys.exit(f"refusing to append: the approvals log is {log['status']} ({log['reason']})")
    prev = log["items"].get(("model", a.model))
    evidence = [{"path": p, "sha256": hash_file(os.path.join(REPO, p))} for p in a.evidence]
    rec = change_event("model", None if prev is None else dict(prev["after"]),
                       {"id": a.model, "sha256": hash_file(os.path.expanduser(a.weights))},
                       a.reason, evidence, "owner", a.approved_by)
    out = RecordWriter(APPROVALS_PATH).append(rec)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
