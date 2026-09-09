"""
cultureqc.records — Hash-chained, append-only JSONL record writer.

Each record is:
  1. Serialized as canonical JSON (sorted keys, compact separators)
  2. SHA-256 hashed
  3. Linked to the previous record's hash via prev_record_hash
  4. Appended to an immutable JSONL log

This is the GMP audit-trail pattern mapped to 21 CFR Part 11 §11.10(e):
computer-generated, time-stamped, non-modifiable, model-versioned records
with a human reviewer field.

Usage:
    from cultureqc.records import RecordWriter, verify_chain

    writer = RecordWriter("events.jsonl")
    writer.append(record_dict)

    ok, bad_line = verify_chain("events.jsonl")
"""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from datetime import datetime, timezone


GENESIS_HASH = "0" * 64


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


def verify_chain(log_path: str) -> tuple[bool, int | None]:
    """
    Verify the hash chain of a JSONL log.

    Returns:
        (True, None) if the chain is intact.
        (False, line_number) if a mismatch is found (1-indexed).
    """
    if not os.path.exists(log_path):
        return True, None

    prev_hash = GENESIS_HASH

    with open(log_path, "r") as f:
        for line_num, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                return False, line_num

            # Check prev_record_hash links to the previous record
            if record.get("prev_record_hash") != prev_hash:
                return False, line_num

            # Recompute the record's own hash
            stored_hash = record.pop("record_hash", None)
            canonical = _canonical_json(record)
            expected_hash = _sha256(canonical)

            if stored_hash != expected_hash:
                return False, line_num

            prev_hash = stored_hash

    return True, None


# ---------------------------------------------------------------------------
# CLI: verify_chain
# ---------------------------------------------------------------------------

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Verify the hash chain of a cultureQC event log.")
    parser.add_argument("log", help="Path to the JSONL event log")
    args = parser.parse_args()

    ok, bad_line = verify_chain(args.log)
    if ok:
        # Count records
        with open(args.log) as f:
            n = sum(1 for line in f if line.strip())
        print(f"Chain intact. {n} records verified.")
    else:
        print(f"CHAIN BROKEN at line {bad_line}.")
        exit(1)


if __name__ == "__main__":
    main()
