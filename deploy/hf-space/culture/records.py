"""
cultureqc.records — Hash-chained, append-only JSONL record writer.

Each record is:
  1. Serialized as canonical JSON (sorted keys, compact separators)
  2. SHA-256 hashed
  3. Linked to the previous record's hash via prev_record_hash
  4. Appended to an append-only JSONL log

This is the GMP audit-trail pattern mapped to 21 CFR Part 11 §11.10(e):
computer-generated, time-stamped, model-versioned records with a human
reviewer field (docs/audit_mapping.md).

What the chain proves on its own: editing a record breaks its own hash or,
if that hash is recomputed, the next record's link; inserting or reordering
records breaks a link. What it can't prove on its own: someone who rewrites a
record and recomputes every later hash, or deletes the newest records, leaves
a chain that still verifies. Those two are caught only against a checkpoint
(record count + head hash) kept outside the log's trust boundary: see
checkpoint() and verify_chain(..., checkpoint=...).

Usage:
    from culture.records import RecordWriter, checkpoint, verify_chain

    writer = RecordWriter("events.jsonl")
    writer.append(record_dict)

    result = verify_chain("events.jsonl")          # result.ok, result.status, ...
    ok, bad_line = verify_chain("events.jsonl")    # the older form still works

    cp = checkpoint("events.jsonl")                # store this somewhere else
    verify_chain("events.jsonl", checkpoint=cp)    # also catches rewrites, truncation

    python -m culture.records verify events.jsonl [--checkpoint cp.json]
    python -m culture.records checkpoint events.jsonl -o cp.json [--sign]
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import sys
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone


GENESIS_HASH = "0" * 64
SCHEMA_VERSION = "0.3"  # culture/schema.json; stamped by culture/pipeline.py and demo/analysis.py


def _canonical_json(record: dict) -> str:
    """Deterministic JSON: sorted keys, compact separators, no trailing whitespace."""
    return json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _sha256(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def hash_file(path: str) -> str:
    """SHA-256 of a file's raw bytes. Used for image_hash and model_weights_hash."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


class RecordWriter:
    """
    Append-only, hash-chained JSONL writer.

    Each call to append() adds record_id, analysed_at, prev_record_hash,
    and record_hash, then writes one JSON line. The file is opened in
    append mode — never overwritten.
    """

    def __init__(self, log_path: str):
        self.log_path = log_path
        self._prev_hash = self._read_last_hash()

    def _read_last_hash(self) -> str:
        """Read the hash of the last record in the log, or GENESIS_HASH if empty/new."""
        if not os.path.exists(self.log_path):
            return GENESIS_HASH
        last_hash = GENESIS_HASH
        with open(self.log_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    last_hash = rec.get("record_hash", GENESIS_HASH)
                except json.JSONDecodeError:
                    pass
        return last_hash

    def append(self, record: dict) -> dict:
        """
        Finalize and append a record. Adds:
          - record_id (if not present)
          - analysed_at (if not present)
          - prev_record_hash
          - record_hash

        Returns the finalized record.
        """
        record = dict(record)  # don't mutate the caller's dict

        if "record_id" not in record or not record["record_id"]:
            record["record_id"] = str(uuid.uuid4())

        if "analysed_at" not in record or not record["analysed_at"]:
            record["analysed_at"] = datetime.now(timezone.utc).isoformat()

        record["prev_record_hash"] = self._prev_hash

        # Remove record_hash if present (will be recomputed)
        record.pop("record_hash", None)

        # Compute hash over everything except record_hash itself
        canonical = _canonical_json(record)
        record_hash = _sha256(canonical)
        record["record_hash"] = record_hash

        # Append to log
        with open(self.log_path, "a") as f:
            f.write(json.dumps(record, sort_keys=True) + "\n")

        self._prev_hash = record_hash
        return record

    @property
    def record_count(self) -> int:
        if not os.path.exists(self.log_path):
            return 0
        with open(self.log_path, "r") as f:
            return sum(1 for line in f if line.strip())



# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

CHECKPOINT_SCHEMA = "1"
CHECKPOINT_KEY_ENV = "CULTUREQC_CHECKPOINT_KEY"


@dataclass(frozen=True)
class ChainResult:
    """What verify_chain found.

    status is one of:
      intact       every hash and link checks (and the checkpoint, if given)
      broken       a record's hash or link fails, or a line isn't JSON;
                   first_bad_index is that record (0-based)
      missing_log  no file at the path
      empty_chain  the file has no records
      truncated    fewer records than the checkpoint counted
      rewritten    the record at checkpoint.count - 1 doesn't hash to
                   checkpoint.head_hash
      checkpoint_invalid  the checkpoint is malformed, or its signature
                   fails or can't be checked
    """
    ok: bool
    status: str
    n_records: int
    head_hash: str | None
    first_bad_index: int | None
    reason: str
    first_bad_line: int | None = None  # 1-indexed line of first_bad_index

    def __iter__(self):
        # The older API returned (ok, bad_line); call sites still unpack that.
        return iter((self.ok, self.first_bad_line))

    def as_dict(self) -> dict:
        return asdict(self)


def _signature(cp: dict, key: str) -> str:
    body = _canonical_json({k: v for k, v in cp.items() if k != "hmac_sha256"})
    return hmac.new(key.encode("utf-8"), body.encode("utf-8"), hashlib.sha256).hexdigest()


def _check_checkpoint(cp: dict, key: str | None) -> str | None:
    """None if the checkpoint can be used, else why not."""
    count, head = cp.get("count"), cp.get("head_hash")
    if not isinstance(count, int) or isinstance(count, bool) or count < 1:
        return "checkpoint has no positive integer count"
    if not isinstance(head, str) or len(head) != 64:
        return "checkpoint has no 64-character head_hash"
    if cp.get("hash_alg", "sha256") != "sha256":
        return f"unsupported hash_alg {cp.get('hash_alg')!r}"
    if "hmac_sha256" in cp:
        key = key if key is not None else os.environ.get(CHECKPOINT_KEY_ENV)
        if not key:
            return f"checkpoint is signed but no key was given (set {CHECKPOINT_KEY_ENV})"
        if not hmac.compare_digest(str(cp["hmac_sha256"]), _signature(cp, key)):
            return "checkpoint signature does not match: the checkpoint was edited or the key is wrong"
    return None


def verify_chain(log_path: str, checkpoint: dict | None = None,
                 key: str | None = None) -> ChainResult:
    """
    Verify the hash chain of a JSONL log, and optionally against a checkpoint.

    Without a checkpoint this catches an edited, inserted or reordered record,
    but a full rewrite (every later hash recomputed) or a deleted tail still
    verifies. With one, fewer records than checkpoint["count"] is `truncated`,
    and a record at checkpoint["count"] - 1 that doesn't hash to
    checkpoint["head_hash"] is `rewritten`; records appended after the
    checkpoint are allowed. A missing or empty log never counts as intact.

    Returns a ChainResult; `ok, bad_line = verify_chain(path)` still works.
    """
    def result(status, n=0, head=None, bad=None, line=None, reason=""):
        return ChainResult(status == "intact", status, n, head, bad, reason, line)

    if checkpoint is not None:
        why = _check_checkpoint(checkpoint, key)
        if why:
            return result("checkpoint_invalid", reason=why)

    if not os.path.exists(log_path):
        return result("missing_log", reason=f"no log at {log_path}")

    prev_hash = GENESIS_HASH
    hashes: list[str] = []

    with open(log_path, "r") as f:
        for line_num, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            idx = len(hashes)

            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                return result("broken", idx, prev_hash, idx, line_num, f"record {idx} is not valid JSON")

            # Check prev_record_hash links to the previous record
            if record.get("prev_record_hash") != prev_hash:
                return result("broken", idx, prev_hash, idx, line_num,
                              f"record {idx}'s prev_record_hash doesn't match record {idx - 1}'s hash"
                              if idx else "record 0 doesn't link to the genesis hash")

            # Recompute the record's own hash
            stored_hash = record.pop("record_hash", None)
            if stored_hash != _sha256(_canonical_json(record)):
                return result("broken", idx, prev_hash, idx, line_num,
                              f"record {idx}'s contents don't hash to its record_hash")

            hashes.append(stored_hash)
            prev_hash = stored_hash

    n = len(hashes)
    head = hashes[-1] if hashes else None
    if not n:
        return result("empty_chain", reason="the log has no records")

    if checkpoint is not None:
        count = checkpoint["count"]
        if n < count:
            return result("truncated", n, head, None, None,
                          f"{n} records, but the checkpoint counted {count}")
        if hashes[count - 1] != checkpoint["head_hash"]:
            return result("rewritten", n, head, count - 1, None,
                          f"record {count - 1} doesn't match the checkpoint's head hash")

    return result("intact", n, head,
                  reason=f"{n} records" + (f"; the first {checkpoint['count']} match the checkpoint"
                                           if checkpoint is not None else ""))


def checkpoint(log_path: str, scope: str | None = None, sign: bool = False,
               key: str | None = None) -> dict:
    """
    A checkpoint of the log as it is now: its record count and head hash.

    It is only an anchor if it is stored outside the log's trust boundary: in
    the platform's own audit trail, WORM storage, or an RFC 3161 timestamp.
    A copy next to the log can be rewritten along with it.

    sign=True adds an HMAC-SHA256 over the checkpoint with `key` (or the
    CULTUREQC_CHECKPOINT_KEY environment variable), so an edited checkpoint is
    rejected. It doesn't help against anyone who holds the key.

    Raises ValueError if the chain doesn't verify, or if sign=True has no key.
    """
    res = verify_chain(log_path)
    if not res.ok:
        raise ValueError(f"won't checkpoint a chain that doesn't verify ({res.status}: {res.reason})")
    cp = {
        "scope": scope or os.path.basename(log_path),
        "count": res.n_records,
        "head_hash": res.head_hash,
        "schema_version": CHECKPOINT_SCHEMA,
        "hash_alg": "sha256",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    if sign:
        key = key if key is not None else os.environ.get(CHECKPOINT_KEY_ENV)
        if not key:
            raise ValueError(f"sign=True needs a key (set {CHECKPOINT_KEY_ENV})")
        cp["hmac_sha256"] = _signature(cp, key)
    return cp


# ---------------------------------------------------------------------------
# CLI: verify, checkpoint
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    import argparse

    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] not in ("verify", "checkpoint", "-h", "--help"):
        argv.insert(0, "verify")  # the older form: python -m culture.records <log>

    parser = argparse.ArgumentParser(prog="python -m culture.records",
                                     description="Verify or checkpoint a cultureQC hash-chained log.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("verify", help="verify the chain, optionally against a checkpoint")
    v.add_argument("log", help="path to the JSONL log")
    v.add_argument("--checkpoint", help="checkpoint JSON written by the checkpoint command")
    c = sub.add_parser("checkpoint", help="write the log's record count and head hash")
    c.add_argument("log", help="path to the JSONL log")
    c.add_argument("-o", "--out", help="write the checkpoint here (default: stdout)")
    c.add_argument("--scope", help="label stored in the checkpoint (default: the log's file name)")
    c.add_argument("--sign", action="store_true",
                   help=f"add an HMAC-SHA256 with the key in ${CHECKPOINT_KEY_ENV}")
    args = parser.parse_args(argv)

    if args.cmd == "checkpoint":
        try:
            cp = checkpoint(args.log, scope=args.scope, sign=args.sign)
        except ValueError as e:
            print(f"No checkpoint written: {e}")
            return 1
        text = json.dumps(cp, indent=1, sort_keys=True) + "\n"
        if args.out:
            with open(args.out, "w") as f:
                f.write(text)
            print(f"Checkpoint written to {args.out}: {cp['count']} records, head {cp['head_hash'][:12]}…")
        else:
            sys.stdout.write(text)
        return 0

    cp = None
    if args.checkpoint:
        with open(args.checkpoint) as f:
            cp = json.load(f)
    res = verify_chain(args.log, checkpoint=cp)
    if res.ok:
        print(f"Chain intact: {res.reason}." + ("" if cp else " No checkpoint given, so a full"
              " rewrite or a deleted tail would not show."))
        return 0
    where = f" at line {res.first_bad_line}" if res.first_bad_line else ""
    print(f"CHAIN NOT VERIFIED ({res.status}{where}): {res.reason}.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
