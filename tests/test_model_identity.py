"""Fixture-only checks that approvals describe the weights used for inference."""

import hashlib
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from culture import approvals, seg
from culture.approvals import NotApproved
from culture.records import RecordWriter, change_event


def approve(log, payload):
    return RecordWriter(str(log)).append(change_event(
        "model", None,
        {"id": "cpsam_v2", "sha256": hashlib.sha256(payload).hexdigest()},
        "fixture activation", [{"path": "fixture", "sha256": "0" * 64}],
        "test owner", "repository owner"))


@pytest.fixture
def lifecycle(tmp_path, monkeypatch):
    source = tmp_path / "cpsam_v2"
    source.write_bytes(b"approved A")
    log = tmp_path / "approved.jsonl"
    approve(log, b"approved A")
    evaluated = []
    built = []
    hooks = {}

    class Model:
        def __init__(self, pretrained_model, **kwargs):
            if "load" in hooks:
                hooks["load"]()
            self.pretrained_model = pretrained_model
            self.options = kwargs
            self.payload = Path(pretrained_model).read_bytes()
            built.append(self)

        def eval(self, img, **kwargs):
            evaluated.append(self.payload)
            if "eval" in hooks:
                hooks["eval"]()
            prob = np.full(img.shape, 2 if self.payload == b"approved A" else -2)
            return np.zeros(img.shape, int), [None, None, prob], None

    monkeypatch.setattr(approvals, "APPROVALS_PATH", str(log))
    monkeypatch.setitem(sys.modules, "torch", SimpleNamespace(
        cuda=SimpleNamespace(is_available=lambda: False),
        backends=SimpleNamespace(mps=SimpleNamespace(is_available=lambda: False))))
    monkeypatch.setitem(sys.modules, "cellpose", SimpleNamespace(
        models=SimpleNamespace(MODEL_DIR=tmp_path, CellposeModel=Model)))
    monkeypatch.setattr(seg, "_cp_model", None)
    return SimpleNamespace(source=source, log=log, evaluated=evaluated, built=built, hooks=hooks)


def read():
    return seg.cpsam_confluency(np.zeros((4, 4), np.uint8))


def test_approved_replacement_never_labels_loaded_a_as_b(lifecycle):
    source, log = lifecycle.source, lifecycle.log
    first = seg.cpsam_confluency(np.zeros((4, 4), np.uint8))
    assert first.pct == 100
    source.write_bytes(b"approved B")
    approve(log, b"approved B")
    try:
        second = seg.cpsam_confluency(np.zeros((4, 4), np.uint8))
    except NotApproved:
        assert lifecycle.evaluated == [b"approved A"]
        second = read()
        assert second.pct == 0
    else:
        assert second.pct == 0, "loaded A ran while the approval identifies replacement B"
        assert second.extra["model_check"]["sha256"] == hashlib.sha256(b"approved B").hexdigest()
    assert second.extra["model_check"]["sha256"] == hashlib.sha256(b"approved B").hexdigest()
    assert second.model_version == second.extra["model_check"]["id"] == "cpsam_v2"


def test_snapshot_is_private_readonly_and_retained(lifecycle):
    result = read()
    model = lifecycle.built[0]
    snapshot = Path(model.pretrained_model)
    assert snapshot != lifecycle.source
    assert snapshot.read_bytes() == b"approved A"
    assert snapshot.stat().st_mode & 0o222 == 0
    assert model._cultureqc_identity.sha256 == result.extra["model_check"]["sha256"]
    assert seg.weights_path(model) == str(lifecycle.source)


def test_unapproved_replacement_refuses_and_restored_a_reloads(lifecycle):
    read()
    lifecycle.source.write_bytes(b"unapproved B")
    with pytest.raises(NotApproved, match="not the approved"):
        read()
    assert lifecycle.evaluated == [b"approved A"]
    assert seg._cp_model is None
    lifecycle.source.write_bytes(b"approved A")
    assert read().pct == 100
    assert len(lifecycle.built) == 2


def test_explicitly_approved_rollback_loads_a_again(lifecycle):
    read()
    lifecycle.source.write_bytes(b"approved B")
    approve(lifecycle.log, b"approved B")
    with pytest.raises(NotApproved):
        read()
    assert read().pct == 0
    lifecycle.source.write_bytes(b"approved A")
    approve(lifecycle.log, b"approved A")
    with pytest.raises(NotApproved):
        read()
    assert read().pct == 100


@pytest.mark.parametrize("atomic", [False, True])
def test_same_size_replacement_preserving_mtime_activates_after_refusal(lifecycle, atomic):
    read()
    original_stat = lifecycle.source.stat()
    replacement = lifecycle.source.with_suffix(".replacement") if atomic else lifecycle.source
    replacement.write_bytes(b"approved B")
    os.utime(replacement, ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns))
    if atomic:
        replacement.replace(lifecycle.source)
    approve(lifecycle.log, b"approved B")
    with pytest.raises(NotApproved):
        read()
    assert read().pct == 0


@pytest.mark.parametrize("loaded", [False, True])
def test_missing_source_refuses_without_evaluation(lifecycle, loaded):
    if loaded:
        read()
    lifecycle.source.unlink()
    with pytest.raises(NotApproved) as error:
        read()
    assert error.value.check.status == "missing_file"
    assert len(lifecycle.evaluated) == int(loaded)
    assert seg._cp_model is None


@pytest.mark.parametrize("loaded", [False, True])
@pytest.mark.parametrize("log_status", ["missing", "broken", "no_model"])
def test_unavailable_approval_refuses_without_new_inference(lifecycle, loaded, log_status):
    if loaded:
        read()
    lifecycle.log.unlink()
    if log_status == "broken":
        lifecycle.log.write_text('{"record_hash": "invalid"}\n')
    elif log_status == "no_model":
        RecordWriter(str(lifecycle.log)).append(change_event(
            "model", None, {"id": "another-model", "sha256": "0" * 64},
            "unrelated fixture activation", [{"path": "fixture", "sha256": "0" * 64}],
            "test owner", "repository owner"))
    with pytest.raises(NotApproved) as error:
        read()
    expected = "not_approved" if log_status == "no_model" else "approvals_unavailable"
    assert error.value.check.status == expected
    assert len(lifecycle.evaluated) == int(loaded)
    assert seg._cp_model is None


def test_model_without_verified_identity_refuses(lifecycle, monkeypatch):
    read()
    model = lifecycle.built[0]
    model.pretrained_model = str(lifecycle.source)
    del model._cultureqc_identity
    with pytest.raises(NotApproved, match="no verified snapshot identity") as error:
        read()
    assert error.value.check.sha256 is None
    assert lifecycle.evaluated == [b"approved A"]
    assert seg._cp_model is None


@pytest.mark.parametrize("cuda,mps,opt_in,expected", [
    (False, False, False, {"gpu": False}),
    (True, False, False, {"gpu": True}),
    (False, True, False, {"gpu": False}),
    (False, True, True, {"gpu": True, "device": "mps"}),
])
def test_snapshot_loading_preserves_device_selection(lifecycle, monkeypatch, cuda, mps, opt_in, expected):
    monkeypatch.setitem(sys.modules, "torch", SimpleNamespace(
        cuda=SimpleNamespace(is_available=lambda: cuda), device=lambda name: name,
        backends=SimpleNamespace(mps=SimpleNamespace(is_available=lambda: mps))))
    if opt_in:
        monkeypatch.setenv("CULTUREQC_DEVICE", "mps")
    else:
        monkeypatch.delenv("CULTUREQC_DEVICE", raising=False)
    read()
    assert lifecycle.built[0].options == expected


def test_failed_load_does_not_cache_model_or_snapshot(lifecycle):
    snapshots = []
    original = seg.tempfile.TemporaryDirectory

    def temporary_directory(**kwargs):
        snapshot = original(**kwargs)
        snapshots.append(snapshot.name)
        return snapshot

    def fail():
        raise RuntimeError("fixture load failed")

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(seg.tempfile, "TemporaryDirectory", temporary_directory)
        lifecycle.hooks["load"] = fail
        with pytest.raises(RuntimeError, match="fixture load failed"):
            read()
    assert seg._cp_model is None
    assert not any(os.path.exists(path) for path in snapshots)
    assert lifecycle.evaluated == []
    lifecycle.hooks.clear()
    assert read().pct == 100


def test_source_replacement_during_load_cannot_change_loaded_snapshot(lifecycle):
    def replace_source():
        lifecycle.source.write_bytes(b"approved B")
        approve(lifecycle.log, b"approved B")

    lifecycle.hooks["load"] = replace_source
    with pytest.raises(NotApproved) as error:
        read()
    assert lifecycle.built[0].payload == b"approved A"
    assert error.value.check.sha256 == hashlib.sha256(b"approved A").hexdigest()
    assert error.value.check.approved_sha256 == hashlib.sha256(b"approved B").hexdigest()
    assert lifecycle.evaluated == []
    assert seg._cp_model is None
    lifecycle.hooks.clear()
    assert read().pct == 0


def test_replacement_during_snapshot_copy_is_checked_before_loading(lifecycle, monkeypatch):
    original = seg.shutil.copyfile

    def replace_before_copy(source, destination):
        lifecycle.source.write_bytes(b"unapproved B")
        return original(source, destination)

    monkeypatch.setattr(seg.shutil, "copyfile", replace_before_copy)
    with pytest.raises(NotApproved) as error:
        read()
    assert error.value.check.status == "mismatch"
    assert lifecycle.built == lifecycle.evaluated == []
    assert seg._cp_model is None


def test_replacement_during_inference_keeps_actual_loaded_identity(lifecycle):
    def replace_source():
        lifecycle.source.write_bytes(b"approved B")
        approve(lifecycle.log, b"approved B")

    lifecycle.hooks["eval"] = replace_source
    result = read()
    assert result.pct == 100
    assert result.extra["model_check"]["sha256"] == hashlib.sha256(b"approved A").hexdigest()
    with pytest.raises(NotApproved):
        read()
    assert lifecycle.evaluated == [b"approved A"]
