"""Run-time check of model weights against approved change records (culture/approvals.py), and a
fine-tuned model's reading beside the shipped one (culture/finetuned.py).

No real model is loaded: the weights are small stand-in files and the fine-tuned model is a stub."""

import json
import os

import jsonschema
import numpy as np
import pytest

from culture import approvals, finetuned
from culture.approvals import NotApproved, check, require
from culture.records import RecordWriter, change_event, hash_file, verify_chain

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA = os.path.join(REPO, "culture", "schema.json")


def approve(log, model_id, weights, before=None):
    return RecordWriter(str(log)).append(change_event(
        "model", before, {"id": model_id, "sha256": hash_file(str(weights))}, "why",
        [{"path": "results/x.md", "sha256": "0" * 64}], "owner", "repository owner"))


@pytest.fixture
def setup(tmp_path):
    w = tmp_path / "m.weights"
    w.write_bytes(b"weights v1")
    log = tmp_path / "approved.jsonl"
    approve(log, "m", w)
    return tmp_path, w, log


def test_match(setup):
    _, w, log = setup
    c = check("model", "m", str(w), str(log))
    assert c.ok and c.sha256 == c.approved_sha256 == hash_file(str(w)) and c.approvals_head


def test_one_changed_byte_is_a_mismatch(setup):
    tmp, w, log = setup
    t = tmp / "tampered.weights"
    t.write_bytes(b"weights v2")
    c = check("model", "m", str(t), str(log))
    assert c.status == "mismatch" and c.sha256 != c.approved_sha256
    with pytest.raises(NotApproved) as e:
        require("model", "m", str(t), str(log))
    assert e.value.check.status == "mismatch"


def test_missing_file_and_no_approval(setup):
    tmp, w, log = setup
    assert check("model", "m", str(tmp / "nowhere"), str(log)).status == "missing_file"
    assert check("model", "m", None, str(log)).status == "missing_file"
    assert check("model", "other", str(w), str(log)).status == "not_approved"


def test_a_broken_or_missing_log_approves_nothing(setup):
    tmp, w, log = setup
    assert check("model", "m", str(w), str(tmp / "none.jsonl")).status == "approvals_unavailable"
    lines = log.read_text().splitlines()
    rec = json.loads(lines[0])
    rec["after"]["sha256"] = "f" * 64                       # edited after the fact
    log.write_text(json.dumps(rec, sort_keys=True) + "\n")
    assert not verify_chain(str(log)).ok
    c = check("model", "m", str(w), str(log))
    assert c.status == "approvals_unavailable" and c.approvals_head is None


def test_a_later_record_replaces_an_earlier_one(setup):
    tmp, w, log = setup
    old = hash_file(str(w))
    w.write_bytes(b"weights v2, retrained")
    assert check("model", "m", str(w), str(log)).status == "mismatch"
    approve(log, "m", w, before={"id": "m", "sha256": old})
    assert check("model", "m", str(w), str(log)).ok
    w.write_bytes(b"weights v1")                             # the replaced weights are no longer approved
    assert check("model", "m", str(w), str(log)).status == "mismatch"


def test_committed_log_names_the_two_models():
    res = verify_chain(approvals.APPROVALS_PATH)
    assert res.ok and res.n_records >= 2
    items = approvals.approved()["items"]
    assert items[("model", "cpsam_v2")]["after"]["sha256"].startswith("0f1cc3f7ecdd8a03")
    ft = items[("model", "mcellseg_ftF_r2")]
    assert ft["after"]["sha256"].startswith("2d1549682c1da482")
    for e in [e for r in items.values() for e in r["evidence"]]:
        assert os.path.exists(os.path.join(REPO, e["path"])), e["path"]
    # the fine-tuned model's approval is tied to the run that trained it
    man = json.load(open(os.path.join(REPO, "results", "confluency_finetune_figure_curves.json")))["run"]
    assert man["weights_sha256"] == ft["after"]["sha256"]
    assert set(finetuned.load_config()) == {k[1] for k in items if k[1] != "cpsam_v2"}


class _Stub:
    def __init__(self, prob):
        self.prob = prob

    def eval(self, img, **kw):
        assert kw.get("compute_masks") is False
        return None, [None, None, self.prob], None


@pytest.fixture
def ft(setup, monkeypatch):
    tmp, w, log = setup
    cfg = tmp / "finetuned.yaml"
    cfg.write_text(f"models:\n  m:\n    base: cpsam_v2\n    status: not_validated\n    cutoff: 0.0\n    path: {w}\n")
    monkeypatch.setattr(approvals, "APPROVALS_PATH", str(log))
    monkeypatch.setattr(finetuned, "REPO", "/")
    built = []
    prob = np.full((10, 10), -1.0)
    prob[:3] = 2.0                                           # 30% above the cutoff
    import culture.seg
    monkeypatch.setattr(culture.seg, "_new_model", lambda pretrained_model=None: built.append(pretrained_model) or _Stub(prob))
    finetuned._models.clear()
    return tmp, w, cfg, built


def test_finetuned_reading_when_the_weights_match(ft):
    tmp, w, cfg, built = ft
    r = finetuned.read(np.zeros((10, 10), np.uint8), "m", str(cfg))
    assert r["confluency_pct"] == 30.0 and r["check"]["status"] == "match" and r["used_in_decision"] is False
    assert r["status"] == "not_validated" and r["band_pp"] is None and built == [str(w)]


def test_finetuned_refusal_loads_nothing(ft):
    tmp, w, cfg, built = ft
    w.write_bytes(b"weights v1, one byte off")
    r = finetuned.read(np.zeros((10, 10), np.uint8), "m", str(cfg))
    assert r["confluency_pct"] is None and r["check"]["status"] == "mismatch" and "not the approved" in r["reason"]
    assert built == []


def _reading(tmp, **kw):
    from test_record_events import reading
    return RecordWriter(str(tmp / "events.jsonl")).append(reading(schema_version="0.5", **kw))


def test_schema_05_reading_carries_the_check_and_the_finetuned_reading(ft):
    tmp, w, cfg, built = ft
    schema = json.load(open(SCHEMA))
    mc = check("model", "m", str(w)).record_fields()
    ok = finetuned.read(np.zeros((10, 10), np.uint8), "m", str(cfg))
    w.write_bytes(b"tampered")
    refused = finetuned.read(np.zeros((10, 10), np.uint8), "m", str(cfg))
    for fr in (None, ok, refused):
        jsonschema.validate(_reading(tmp, model_check=mc, finetuned_reading=fr), schema)
    with pytest.raises(jsonschema.ValidationError):        # 0.5 readings must state the check
        jsonschema.validate(_reading(tmp), schema)
    with pytest.raises(jsonschema.ValidationError):        # a fine-tuned reading never decides
        jsonschema.validate(_reading(tmp, model_check=mc, finetuned_reading=dict(ok, used_in_decision=True)), schema)


def test_shipped_model_mismatch_reads_nothing(setup, monkeypatch):
    tmp, w, log = setup
    import culture.seg as seg
    calls = []

    class Shipped:
        pretrained_model = str(tmp / "cpsam_v2")

        def eval(self, *a, **kw):
            calls.append(1)

    (tmp / "cpsam_v2").write_bytes(b"not the approved weights")
    approve(log, "cpsam_v2", w)                              # approves different bytes
    monkeypatch.setattr(approvals, "APPROVALS_PATH", str(log))
    monkeypatch.setattr(seg, "_get_model", lambda: Shipped())
    with pytest.raises(NotApproved) as e:
        seg.cpsam_confluency(np.zeros((10, 10), np.uint8))
    assert e.value.check.status == "mismatch" and calls == []
