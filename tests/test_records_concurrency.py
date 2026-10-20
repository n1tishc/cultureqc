"""Regression tests for concurrent and fail-closed RecordWriter appends."""

import json
import multiprocessing
import os
import stat
import threading
import time

import pytest

from culture.records import RecordWriter, checkpoint, verify_chain


def _append_records_in_process(log_path, worker_id, count, barrier, results):
    try:
        writer = RecordWriter(log_path)
        barrier.wait(timeout=15)
        for index in range(count):
            writer.append({"record_id": f"worker-{worker_id}-{index}"})
        results.put(None)
    except BaseException as exc:
        results.put(f"{type(exc).__name__}: {exc}")


def _record_ids(path):
    with open(path, "r", encoding="utf-8") as log:
        return [json.loads(line)["record_id"] for line in log]


def test_constructed_writers_interleaved_on_one_path_keep_chain(tmp_path):
    path = str(tmp_path / "records.jsonl")
    first = RecordWriter(path)
    second = RecordWriter(path)

    first.append({"record_id": "first"})
    second.append({"record_id": "second"})

    result = verify_chain(path)
    assert result.ok
    assert result.n_records == 2
    assert _record_ids(path) == ["first", "second"]


def test_one_writer_serializes_threaded_appends(tmp_path):
    path = str(tmp_path / "records.jsonl")
    writer = RecordWriter(path)
    count = 12
    errors = []
    barrier = threading.Barrier(count)

    def append_record(record_id):
        try:
            barrier.wait(timeout=10)
            writer.append({"record_id": record_id})
        except BaseException as exc:
            errors.append(exc)

    threads = [threading.Thread(target=append_record, args=(f"thread-{index}",), daemon=True)
               for index in range(count)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    assert all(not thread.is_alive() for thread in threads)
    assert not errors
    result = verify_chain(path)
    assert result.ok
    assert result.n_records == count
    assert set(_record_ids(path)) == {f"thread-{index}" for index in range(count)}


def test_spawned_process_writers_append_unique_records_and_restart_cleanly(tmp_path):
    path = str(tmp_path / "records.jsonl")
    context = multiprocessing.get_context("spawn")
    results = context.Queue()
    barrier = context.Barrier(4)
    processes = [context.Process(target=_append_records_in_process,
                                 args=(path, worker_id, 8, barrier, results))
                 for worker_id in range(4)]
    try:
        for process in processes:
            process.start()
        for process in processes:
            process.join(timeout=30)

        assert all(not process.is_alive() for process in processes)
        assert [process.exitcode for process in processes] == [0] * 4
        assert [results.get(timeout=5) for _ in processes] == [None] * 4

        result = verify_chain(path)
        assert result.ok
        assert result.n_records == 32
        ids = _record_ids(path)
        assert len(ids) == len(set(ids)) == 32

        restarted = RecordWriter(path)
        restarted.append({"record_id": "after-restart"})
        result = verify_chain(path)
        assert result.ok
        assert result.n_records == 33
        assert _record_ids(path)[-1] == "after-restart"
    finally:
        for process in processes:
            if process.is_alive():
                process.terminate()
                process.join(timeout=5)
        results.close()
        results.join_thread()


@pytest.mark.parametrize("tail", [b'{"partial":', b'{"valid_json_but_unhashed":true}\n'])
def test_corrupt_or_partial_tail_refuses_append_without_changing_bytes(tmp_path, tail):
    path = tmp_path / "records.jsonl"
    RecordWriter(str(path)).append({"record_id": "good"})
    with path.open("ab") as log:
        log.write(tail)
    original = path.read_bytes()

    with pytest.raises(ValueError):
        RecordWriter(str(path)).append({"record_id": "must-not-append"})

    assert path.read_bytes() == original


def test_valid_json_record_without_newline_is_rejected_as_torn_framing(tmp_path):
    path = tmp_path / "records.jsonl"
    RecordWriter(str(path)).append({"record_id": "good"})
    content = path.read_bytes().removesuffix(b"\n")
    path.write_bytes(content)

    with pytest.raises(ValueError):
        RecordWriter(str(path)).append({"record_id": "must-not-append"})

    assert path.read_bytes() == content


@pytest.mark.parametrize("tail", [b"null\n", b"[]\n", b"\xff\n"])
def test_malformed_record_values_report_broken_and_refuse_append(tmp_path, tail):
    path = tmp_path / "records.jsonl"
    RecordWriter(str(path)).append({"record_id": "good"})
    with path.open("ab") as log:
        log.write(tail)
    original = path.read_bytes()

    result = verify_chain(str(path))
    assert not result.ok
    assert result.status == "broken"
    with pytest.raises(ValueError):
        RecordWriter(str(path)).append({"record_id": "must-not-append"})

    assert path.read_bytes() == original


def test_short_os_write_leaves_partial_tail_that_blocks_future_append(tmp_path, monkeypatch):
    path = tmp_path / "records.jsonl"
    writer = RecordWriter(str(path))
    writer.append({"record_id": "good"})
    original = path.read_bytes()
    real_write = os.write

    def short_write(descriptor, payload):
        return real_write(descriptor, payload[:max(1, len(payload) // 2)])

    monkeypatch.setattr(os, "write", short_write)
    with pytest.raises(OSError, match="Incomplete audit append"):
        writer.append({"record_id": "interrupted"})
    monkeypatch.setattr(os, "write", real_write)

    partial = path.read_bytes()
    assert partial.startswith(original)
    assert len(partial) > len(original)
    with pytest.raises(ValueError):
        RecordWriter(str(path)).append({"record_id": "must-not-append"})
    assert path.read_bytes() == partial


@pytest.mark.parametrize("failure_call", [1, 2])
def test_fsync_failure_raises_after_complete_record_write(tmp_path, monkeypatch, failure_call):
    path = tmp_path / "records.jsonl"
    writer = RecordWriter(str(path))
    writer.append({"record_id": "existing"})
    original = path.read_bytes()

    real_fsync = os.fsync
    calls = 0

    def failed_fsync(descriptor):
        nonlocal calls
        calls += 1
        if calls == failure_call:
            raise OSError("injected fsync failure")
        return real_fsync(descriptor)

    monkeypatch.setattr(os, "fsync", failed_fsync)
    with pytest.raises(OSError, match="injected fsync failure"):
        writer.append({"record_id": "possibly-written"})
    monkeypatch.undo()

    appended = path.read_bytes()
    assert appended.startswith(original)
    assert len(appended) > len(original)
    result = verify_chain(str(path))
    assert result.ok and result.n_records == 2


def test_append_fsyncs_log_and_parent_directory_before_return(tmp_path, monkeypatch):
    path = tmp_path / "records.jsonl"
    real_fsync = os.fsync
    sync_targets = []

    def track_fsync(descriptor):
        sync_targets.append(os.fstat(descriptor).st_mode)
        return real_fsync(descriptor)

    monkeypatch.setattr(os, "fsync", track_fsync)
    RecordWriter(str(path)).append({"record_id": "durable"})

    assert len(sync_targets) == 2
    assert stat.S_ISREG(sync_targets[0])
    assert stat.S_ISDIR(sync_targets[1])


def test_verify_and_checkpoint_wait_for_exclusive_lock_until_record_is_complete(tmp_path):
    import fcntl

    path = tmp_path / "records.jsonl"
    source = tmp_path / "source.jsonl"
    RecordWriter(str(source)).append({"record_id": "complete"})
    complete_record = source.read_bytes()
    assert complete_record.endswith(b"\n")
    descriptor = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
    os.write(descriptor, complete_record[:-1])
    fcntl.flock(descriptor, fcntl.LOCK_EX)

    started = [threading.Event(), threading.Event()]
    finished = [threading.Event(), threading.Event()]
    results = [None, None]

    def verify(index, operation):
        started[index].set()
        try:
            results[index] = operation()
        finally:
            finished[index].set()

    threads = [
        threading.Thread(target=verify, args=(0, lambda: verify_chain(str(path))), daemon=True),
        threading.Thread(target=verify, args=(1, lambda: checkpoint(str(path))), daemon=True),
    ]
    try:
        for thread in threads:
            thread.start()
        assert all(event.wait(timeout=5) for event in started)
        time.sleep(0.1)
        assert not any(event.is_set() for event in finished)

        os.lseek(descriptor, 0, os.SEEK_END)
        os.write(descriptor, b"\n")
        fcntl.flock(descriptor, fcntl.LOCK_UN)

        for thread in threads:
            thread.join(timeout=5)
        assert all(not thread.is_alive() for thread in threads)
        assert results[0].ok and results[0].n_records == 1
        assert results[1]["count"] == 1
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)
        for thread in threads:
            if thread.is_alive():
                thread.join(timeout=1)
