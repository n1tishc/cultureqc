"""The hash chain and its anchored checkpoint (culture/records.py).

One test per tamper row. A chain alone catches an edit, an insertion or a
reordering, but not a full rewrite (edit a record, then recompute its hash and
every later one) or a deleted tail: those two rows pass without a checkpoint,
and the tests assert that as the documented limitation. Against a checkpoint
(record count + head hash, kept outside the log), both fail.

| Tamper                               | Chain alone          | With checkpoint |
|--------------------------------------|----------------------|-----------------|
| Edit record k, hash left as it was   | caught at k          | caught          |
| Edit record k, recompute its hash    | caught at k+1        | caught          |
| Edit k + recompute all later hashes  | passes (limitation)  | rewritten       |
| Delete the last 2                    | passes (limitation)  | truncated       |
| Reorder two records                  | caught               | caught          |
| Missing file                         | missing_log          | missing_log     |
| Empty file                           | empty_chain          | empty_chain     |
"""

import json
import os
import subprocess
import sys

import pytest

from culture.records import (GENESIS_HASH, RecordWriter, _canonical_json, _sha256, checkpoint,
                             verify_chain)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
N = 6
K = 2  # the record a forger edits (0-based)


def _make_log(path, n=N):
    w = RecordWriter(str(path))
    for i in range(n):
        w.append({"record_id": f"r{i}", "analysed_at": f"2026-09-30T00:00:0{i}+00:00",
                  "confluency_pct": 10.0 + i})
    return str(path)


def _read(path):
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def _write(path, records):
    with open(path, "w") as f:
        f.write("".join(json.dumps(r, sort_keys=True) + "\n" for r in records))


def _rehash(records, start, stop=None):
    """What a forger with write access does: recompute record hashes (and the
    links between them) from `start` up to `stop`."""
    prev = records[start - 1]["record_hash"] if start else GENESIS_HASH
    for r in records[start:stop]:
        r["prev_record_hash"] = prev
        r.pop("record_hash", None)
        r["record_hash"] = _sha256(_canonical_json(r))
        prev = r["record_hash"]
    return records


@pytest.fixture
def log(tmp_path):
    return _make_log(tmp_path / "events.jsonl")


@pytest.fixture
def cp(log):
    return checkpoint(log)


def test_intact_chain_reports_count_and_head(log, cp):
    res = verify_chain(log)
    assert res.ok and res.status == "intact"
    assert res.n_records == N and res.head_hash == _read(log)[-1]["record_hash"]
    assert res.first_bad_index is None
    assert verify_chain(log, checkpoint=cp).ok
    assert cp["count"] == N and cp["head_hash"] == res.head_hash and cp["hash_alg"] == "sha256"


def test_old_call_sites_still_unpack(log):
    ok, bad_line = verify_chain(log)
    assert ok and bad_line is None


def test_edit_leaving_the_hash_is_caught_at_the_record(log, cp):
    recs = _read(log)
    recs[K]["confluency_pct"] += 10
    _write(log, recs)
    for res in (verify_chain(log), verify_chain(log, checkpoint=cp)):
        assert not res.ok and res.status == "broken" and res.first_bad_index == K
    ok, bad_line = verify_chain(log)
    assert not ok and bad_line == K + 1  # 1-indexed line, as before


def test_edit_with_its_own_hash_recomputed_is_caught_at_the_next_link(log, cp):
    recs = _read(log)
    recs[K]["confluency_pct"] += 10
    _rehash(recs, K, K + 1)
    _write(log, recs)
    for res in (verify_chain(log), verify_chain(log, checkpoint=cp)):
        assert not res.ok and res.status == "broken" and res.first_bad_index == K + 1


def test_full_rewrite_passes_alone_but_not_against_the_checkpoint(log, cp):
    recs = _read(log)
    recs[K]["confluency_pct"] += 10
    _write(log, _rehash(recs, K))
    alone = verify_chain(log)
    assert alone.ok and alone.status == "intact"  # documented limitation
    res = verify_chain(log, checkpoint=cp)
    assert not res.ok and res.status == "rewritten" and res.first_bad_index == N - 1


def test_deleted_tail_passes_alone_but_not_against_the_checkpoint(log, cp):
    _write(log, _read(log)[:-2])
    alone = verify_chain(log)
    assert alone.ok and alone.n_records == N - 2  # documented limitation
    res = verify_chain(log, checkpoint=cp)
    assert not res.ok and res.status == "truncated" and res.n_records == N - 2


def test_reorder_is_caught(log, cp):
    recs = _read(log)
    recs[K], recs[K + 1] = recs[K + 1], recs[K]
    _write(log, recs)
    for res in (verify_chain(log), verify_chain(log, checkpoint=cp)):
        assert not res.ok and res.status == "broken" and res.first_bad_index == K


def test_missing_file_is_a_failure(tmp_path, cp):
    path = str(tmp_path / "nope.jsonl")
    for res in (verify_chain(path), verify_chain(path, checkpoint=cp)):
        assert not res.ok and res.status == "missing_log" and res.n_records == 0
    ok, bad_line = verify_chain(path)
    assert not ok and bad_line is None


@pytest.mark.parametrize("content", ["", "\n\n  \n"])
def test_empty_file_is_a_failure(tmp_path, cp, content):
    path = tmp_path / "empty.jsonl"
    path.write_text(content)
    for res in (verify_chain(str(path)), verify_chain(str(path), checkpoint=cp)):
        assert not res.ok and res.status == "empty_chain"


def test_bad_json_line_is_caught(log):
    with open(log, "a") as f:
        f.write("{not json\n")
    res = verify_chain(log)
    assert not res.ok and res.status == "broken" and res.first_bad_index == N


def test_records_appended_after_the_checkpoint_pass(log, cp):
    w = RecordWriter(log)
    w.append({"record_id": "late", "analysed_at": "2026-09-30T01:00:00+00:00"})
    res = verify_chain(log, checkpoint=cp)
    assert res.ok and res.n_records == N + 1


def test_truncate_then_append_back_to_the_count_is_a_rewrite(log, cp):
    _write(log, _read(log)[:-2])
    w = RecordWriter(log)
    for i in range(2):
        w.append({"record_id": f"forged{i}", "analysed_at": "2026-09-30T02:00:00+00:00"})
    assert verify_chain(log).ok
    res = verify_chain(log, checkpoint=cp)
    assert not res.ok and res.status == "rewritten"


def test_no_checkpoint_of_a_chain_that_does_not_verify(tmp_path, log):
    with pytest.raises(ValueError):
        checkpoint(str(tmp_path / "missing.jsonl"))
    recs = _read(log)
    recs[K]["confluency_pct"] += 10
    _write(log, recs)
    with pytest.raises(ValueError):
        checkpoint(log)


def test_malformed_checkpoint_is_rejected(log, cp):
    res = verify_chain(log, checkpoint={k: v for k, v in cp.items() if k != "head_hash"})
    assert not res.ok and res.status == "checkpoint_invalid"


def test_signed_checkpoint(log, monkeypatch):
    monkeypatch.setenv("CULTUREQC_CHECKPOINT_KEY", "test-key")
    cp = checkpoint(log, sign=True)
    assert "hmac_sha256" in cp
    assert verify_chain(log, checkpoint=cp).ok

    edited = dict(cp, count=cp["count"] - 2)  # a forger lowering the count to hide a truncation
    res = verify_chain(log, checkpoint=edited)
    assert not res.ok and res.status == "checkpoint_invalid"

    monkeypatch.delenv("CULTUREQC_CHECKPOINT_KEY")
    res = verify_chain(log, checkpoint=cp)
    assert not res.ok and res.status == "checkpoint_invalid"
    with pytest.raises(ValueError):
        checkpoint(log, sign=True)


def test_unsigned_by_default(log, monkeypatch):
    monkeypatch.setenv("CULTUREQC_CHECKPOINT_KEY", "test-key")
    assert "hmac_sha256" not in checkpoint(log)


def _cli(*args):
    return subprocess.run([sys.executable, "-m", "culture.records", *args], cwd=REPO,
                          capture_output=True, text=True, timeout=60)


def test_cli(tmp_path, log):
    cp_path = str(tmp_path / "cp.json")
    r = _cli("checkpoint", log, "-o", cp_path)
    assert r.returncode == 0, r.stderr
    assert json.load(open(cp_path))["count"] == N

    assert _cli("verify", log, "--checkpoint", cp_path).returncode == 0
    assert _cli(log).returncode == 0  # the old form, as in the README

    _write(log, _read(log)[:-2])
    assert _cli("verify", log).returncode == 0  # documented limitation
    r = _cli("verify", log, "--checkpoint", cp_path)
    assert r.returncode == 1 and "truncated" in r.stdout

    r = _cli("verify", str(tmp_path / "missing.jsonl"))
    assert r.returncode == 1 and "missing_log" in r.stdout


def test_stored_example_records_verify(tmp_path):
    """The seven records the console and the site show (demo/examples/examples.json)
    are one chain, in example order."""
    with open(os.path.join(REPO, "demo", "examples", "examples.json")) as f:
        records = [ex["record"] for ex in json.load(f)["examples"]]
    path = str(tmp_path / "examples.jsonl")
    _write(path, records)
    res = verify_chain(path)
    assert res.ok and res.n_records == len(records) == 7
    assert verify_chain(path, checkpoint=checkpoint(path)).ok


def test_the_sites_checkpoint_anchors_the_stored_chain(tmp_path):
    """site/src/data.json ships a checkpoint of the seven stored records
    (site/assets/build_data.py); the Records section checks its tamper switches
    against it. It must anchor the stored chain, and catch the two changes a
    chain alone passes, by the same rules the browser applies."""
    with open(os.path.join(REPO, "site", "src", "data.json")) as f:
        cp = json.load(f)["examples"]["checkpoint"]
    with open(os.path.join(REPO, "demo", "examples", "examples.json")) as f:
        records = [ex["record"] for ex in json.load(f)["examples"]]
    assert cp["count"] == len(records) == 7 and cp["head_hash"] == records[-1]["record_hash"]
    path = str(tmp_path / "examples.jsonl")
    _write(path, records)
    assert verify_chain(path, checkpoint=cp).status == "intact"
    short = str(tmp_path / "short.jsonl")
    _write(short, records[:-2])
    assert verify_chain(short).ok and verify_chain(short, checkpoint=cp).status == "truncated"
