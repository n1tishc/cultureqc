from datetime import datetime, timedelta, timezone
import builtins
import hashlib
import json

import pytest

from culture import approvals
from culture.records import RecordWriter, change_event, verify_chain


def _append(log, model_id, digest, effective_from, before=None):
    return RecordWriter(str(log)).append(change_event(
        "model", before, {"id": model_id, "sha256": digest}, "timed approval",
        [{"path": "results/validation.md", "sha256": "0" * 64}],
        "owner", "Repository owner", effective_from=effective_from,
    ))


@pytest.mark.parametrize("field", ["evidence", "reason", "before"])
def test_structurally_incomplete_change_fails_closed(tmp_path, field):
    from culture.records import _canonical_json, _sha256
    log = tmp_path / "approvals.jsonl"
    record = _append(log, "m", "a" * 64, "2026-10-01T00:00:00+00:00")
    record.pop(field)
    record.pop("record_hash")
    record["record_hash"] = _sha256(_canonical_json(record))
    log.write_text(json.dumps(record) + "\n")
    result = approvals.approved(str(log), now=datetime(2026, 10, 20, tzinfo=timezone.utc))
    assert result["status"] == "invalid_log"
    assert not result["items"]


def test_future_approval_activates_at_inclusive_boundary(tmp_path):
    log = tmp_path / "approvals.jsonl"
    _append(log, "m", "a" * 64, "2026-10-20T12:00:00+00:00")

    before = approvals.approved(str(log), now=datetime(2026, 10, 20, 11, 59, 59, tzinfo=timezone.utc))
    boundary = approvals.approved(str(log), now=datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc))

    assert before["status"] == "intact"
    assert ("model", "m") not in before["items"]
    assert boundary["items"][("model", "m")]["after"]["sha256"] == "a" * 64


def test_future_record_does_not_supersede_active_record_until_boundary(tmp_path):
    log = tmp_path / "approvals.jsonl"
    old = _append(log, "m", "a" * 64, "2026-10-19T00:00:00+00:00")
    future = _append(log, "m", "b" * 64, "2026-10-20T12:00:00+00:00",
                     before={"id": "m", "sha256": "a" * 64})

    before = approvals.approved(str(log), now=datetime(2026, 10, 20, 11, 59, tzinfo=timezone.utc))
    boundary = approvals.approved(str(log), now=datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc))

    assert before["items"][("model", "m")]["record_hash"] == old["record_hash"]
    assert boundary["items"][("model", "m")]["record_hash"] == future["record_hash"]


def test_check_re_evaluates_injected_clock_without_log_changes(tmp_path, monkeypatch):
    log = tmp_path / "approvals.jsonl"
    weights = tmp_path / "m.weights"
    weights.write_bytes(b"version one")
    first = hashlib.sha256(weights.read_bytes()).hexdigest()
    _append(log, "m", first, "2026-10-19T00:00:00+00:00")
    _append(log, "m", "b" * 64, "2026-10-20T12:00:00+00:00",
            before={"id": "m", "sha256": first})
    moments = iter((datetime(2026, 10, 20, 11, 59, tzinfo=timezone.utc),
                    datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc)))
    monkeypatch.setattr(approvals, "_now", lambda: next(moments))

    before = approvals.check("model", "m", str(weights), str(log))
    at_boundary = approvals.check("model", "m", str(weights), str(log))

    assert before.status == "match"
    assert at_boundary.status == "mismatch"
    assert at_boundary.approved_sha256 == "b" * 64


def test_effective_time_compares_instants_across_timezone_offsets(tmp_path):
    log = tmp_path / "approvals.jsonl"
    _append(log, "m", "a" * 64, "2026-10-20T05:00:00-07:00")

    exact_instant = approvals.approved(str(log), now=datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc))
    one_second_early = approvals.approved(str(log), now=datetime(2026, 10, 20, 7, 59, 59,
                                                               tzinfo=timezone(timedelta(hours=-4))))

    assert exact_instant["items"][("model", "m")]["after"]["sha256"] == "a" * 64
    assert ("model", "m") not in one_second_early["items"]


def test_approval_uses_one_byte_snapshot_if_registry_changes_after_read(tmp_path, monkeypatch):
    log = tmp_path / "approvals.jsonl"
    _append(log, "m", "a" * 64, "2026-10-19T00:00:00+00:00")
    replacement = tmp_path / "replacement.jsonl"
    _append(replacement, "m", "b" * 64, "2026-10-19T00:00:00+00:00")
    replacement_bytes = replacement.read_bytes()
    real_open = builtins.open
    reads = 0

    class ReplaceAfterRead:
        def __init__(self, stream):
            self.stream = stream

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return self.stream.__exit__(*args)

        def read(self, *args):
            nonlocal reads
            data = self.stream.read(*args)
            reads += 1
            self.stream.close()
            with real_open(log, "wb") as target:
                target.write(replacement_bytes)
            return data

    def swapping_open(path, *args, **kwargs):
        stream = real_open(path, *args, **kwargs)
        if os.fspath(path) == str(log) and args and args[0] == "rb":
            return ReplaceAfterRead(stream)
        return stream

    import os
    monkeypatch.setattr(builtins, "open", swapping_open)
    result = approvals.approved(str(log), now=datetime(2026, 10, 20, tzinfo=timezone.utc))

    assert reads == 1
    assert result["status"] == "intact"
    assert result["items"][("model", "m")]["after"]["sha256"] == "a" * 64
    assert log.read_bytes() == replacement_bytes


def test_rollback_requires_a_new_effective_approval_and_keeps_history(tmp_path):
    log = tmp_path / "approvals.jsonl"
    first = _append(log, "m", "a" * 64, "2026-10-01T00:00:00+00:00")
    second = _append(log, "m", "b" * 64, "2026-10-02T00:00:00+00:00",
                     before={"id": "m", "sha256": "a" * 64})
    at_second = approvals.approved(str(log), now=datetime(2026, 10, 3, tzinfo=timezone.utc))
    assert at_second["items"][("model", "m")]["after"]["sha256"] == "b" * 64

    rollback = _append(log, "m", "a" * 64, "2026-10-04T00:00:00+00:00",
                       before={"id": "m", "sha256": "b" * 64})
    before_rollback = approvals.approved(str(log), now=datetime(2026, 10, 3, 23, 59, tzinfo=timezone.utc))
    after_rollback = approvals.approved(str(log), now=datetime(2026, 10, 4, tzinfo=timezone.utc))

    assert before_rollback["items"][("model", "m")]["record_hash"] == second["record_hash"]
    assert after_rollback["items"][("model", "m")]["record_hash"] == rollback["record_hash"]
    assert verify_chain(str(log)).n_records == 3
    assert first["record_hash"] != rollback["record_hash"]


@pytest.mark.parametrize("effective_from", ["2026-10-20T12:00:00", "not-a-date"])
def test_naive_or_malformed_effective_timestamp_fails_closed(tmp_path, effective_from):
    log = tmp_path / "approvals.jsonl"
    record = change_event(
        "model", None, {"id": "m", "sha256": "a" * 64}, "invalid time",
        [{"path": "results/validation.md", "sha256": "0" * 64}],
        "owner", "Repository owner", effective_from=effective_from,
    )
    record["record_id"] = "invalid-time"
    record["recorded_at"] = "2026-10-19T00:00:00+00:00"
    record["prev_record_hash"] = "0" * 64
    from culture.records import _canonical_json, _sha256
    record["record_hash"] = _sha256(_canonical_json(record))
    log.write_text(json.dumps(record, sort_keys=True) + "\n")

    result = approvals.approved(str(log), now=datetime(2026, 10, 21, tzinfo=timezone.utc))

    assert result["status"] == "invalid_log"
    assert result["items"] == {}


@pytest.mark.parametrize("bad_value", ["not-a-digest", 17, None])
def test_invalid_approval_identity_fails_closed(tmp_path, bad_value):
    from culture.records import _canonical_json, _sha256

    log = tmp_path / "approvals.jsonl"
    record = _append(log, "m", "a" * 64, "2026-10-19T00:00:00+00:00")
    record["after"]["sha256"] = bad_value
    unsigned = {key: value for key, value in record.items() if key != "record_hash"}
    record["record_hash"] = _sha256(_canonical_json(unsigned))
    log.write_text(json.dumps(record, sort_keys=True) + "\n")

    result = approvals.approved(str(log), now=datetime(2026, 10, 20, tzinfo=timezone.utc))

    assert result["status"] == "invalid_log"
    assert result["items"] == {}


def test_check_rejects_naive_injected_clock(tmp_path, monkeypatch):
    log = tmp_path / "approvals.jsonl"
    monkeypatch.setattr(approvals, "_now", lambda: datetime(2026, 10, 20))

    with pytest.raises(ValueError, match="timezone-aware"):
        approvals.check("model", "m", None, str(log))
