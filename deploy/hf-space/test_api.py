"""Contract tests for the cultureQC API.

    python -m pytest deploy/hf-space/test_api.py -q

These test the HTTP contract the frontend depends on — status codes, response
shape, box arithmetic, readiness semantics — with the pipeline stubbed. That is
deliberate: a real Cellpose-SAM call is tens of seconds on CPU, so a suite that
ran the models would be too slow to run often and would be testing the models
rather than the API. The models are exercised end-to-end separately, by hitting
a running server (see deploy/README.md).

The box arithmetic is tested against real numbers because it is the one piece of
logic in api.py that is easy to get wrong and wrong in a way nobody notices —
demo/app.py has carried the over-scaled version of it for a while.
"""

from __future__ import annotations

import io
import os
import sys
import types

import numpy as np
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import api  # noqa: E402


# ── helpers ────────────────────────────────────────────────────────────────

def png_bytes(w: int = 256, h: int = 256) -> bytes:
    import cv2
    arr = (np.random.default_rng(0).random((h, w)) * 255).astype(np.uint8)
    ok, buf = cv2.imencode(".png", arr)
    assert ok
    return buf.tobytes()


RECORD = {
    "schema_version": "0.2", "flask_id": "WEB-x.png", "cell_line": "Huh7",
    "image_ref": "/tmp/whatever/x.png", "image_hash": "a" * 64,
    "confluency_pct": 42.5, "confluency_confidence": 0.9, "confluency_method": "probmap",
    "qc_flag": "contamination_suspected", "qc_confidence": 0.99,
    "qc_rationale": "Small dark rod-like objects detected.",
    "recommended_action": "human_review", "action_reason": "flagged",
    "record_id": "id", "prev_record_hash": "b" * 64, "record_hash": "c" * 64,
    "model_versions": {"seg": "cpsam_v2", "qc": "qc_effnetb0_v1"},
}


class FakeQC:
    per_class_probs = {"normal": 0.001, "contamination_suspected": 0.999}
    evidence_bboxes = [(0, 0, 256, 256)]


@pytest.fixture
def client(monkeypatch):
    """A ready server with the pipeline stubbed."""
    monkeypatch.setitem(api._state, "models_loaded", True)
    monkeypatch.setitem(api._state, "error", None)

    fake_pipeline = types.ModuleType("culture.pipeline")
    fake_pipeline.analyze = lambda *a, **k: {**RECORD, "image_ref": k["image_ref"]}
    fake_qc = types.ModuleType("culture.qc")
    fake_qc.qc_classify = lambda *a, **k: FakeQC()
    fake_rules = types.ModuleType("culture.rules")
    fake_rules.LineConfig = lambda **k: None

    monkeypatch.setitem(sys.modules, "culture.pipeline", fake_pipeline)
    monkeypatch.setitem(sys.modules, "culture.qc", fake_qc)
    monkeypatch.setitem(sys.modules, "culture.rules", fake_rules)

    # No lifespan: the fixture decides readiness, and starting the real warm-up
    # thread would download models during a unit test.
    return TestClient(api.app)


def post(client, *, name="x.png", data=None, **form):
    return client.post(
        "/analyze",
        files={"image": (name, data if data is not None else png_bytes(), "image/png")},
        data={"cell_line": "Huh7", "target_confluency": "80", **form},
    )


# ── readiness ──────────────────────────────────────────────────────────────

def test_health_shape():
    c = TestClient(api.app)
    j = c.get("/health").json()
    assert j["status"] == "ok"
    assert isinstance(j["models_loaded"], bool)
    assert "audit" in j and "per-boot" in j["audit"]


def test_health_answers_before_models_are_loaded(monkeypatch):
    """The whole warming UX depends on /health answering while models load."""
    monkeypatch.setitem(api._state, "models_loaded", False)
    r = TestClient(api.app).get("/health")
    assert r.status_code == 200
    assert r.json()["models_loaded"] is False


def test_analyze_while_warming_is_503_with_retry_after(monkeypatch):
    monkeypatch.setitem(api._state, "models_loaded", False)
    monkeypatch.setitem(api._state, "error", None)
    r = post(TestClient(api.app))
    assert r.status_code == 503
    assert r.headers.get("Retry-After") == "20"


def test_analyze_reports_a_warm_up_failure_rather_than_hanging(monkeypatch):
    monkeypatch.setitem(api._state, "models_loaded", False)
    monkeypatch.setitem(api._state, "error", "RuntimeError: no weights")
    r = post(TestClient(api.app))
    assert r.status_code == 500
    assert "no weights" in r.json()["detail"]


# ── input validation ───────────────────────────────────────────────────────

def test_analysis_does_not_occupy_the_event_loop(client, monkeypatch):
    """/health must answer while an analysis is in flight.

    The endpoint is a coroutine, so doing the inference inline would hold the
    event loop for its whole duration — tens of seconds — and every other
    request, /health included, would queue behind it. That would break the
    warming state the frontend polls for, and make the server look hung.

    Asserted structurally rather than by racing threads: the blocking work lives
    in a plain function that the coroutine hands to a threadpool.
    """
    import asyncio
    import inspect

    assert not inspect.iscoroutinefunction(api._run), \
        "_run holds the blocking work and must be an ordinary function"
    src = inspect.getsource(api.analyze_endpoint)
    assert "run_in_threadpool" in src, \
        "analyze_endpoint must offload _run rather than awaiting it inline"
    # and the coroutine itself must not import or touch the pipeline directly
    assert "culture.pipeline" not in src


def test_rejects_unsupported_extension(client):
    r = post(client, name="notes.txt", data=b"hello")
    assert r.status_code == 415


def test_rejects_empty_file(client):
    r = post(client, name="x.png", data=b"")
    assert r.status_code == 415 or r.status_code == 400


def test_rejects_oversize_file(client, monkeypatch):
    monkeypatch.setattr(api, "MAX_BYTES", 128)
    r = post(client, data=png_bytes())
    assert r.status_code == 413


# ── response contract ──────────────────────────────────────────────────────

REQUIRED = ["confluency_pct", "confluency_confidence", "confluency_method",
            "qc_flag", "qc_confidence", "evidence_boxes", "rationale",
            "recommended_action", "overlay_image_base64", "record",
            "analysed_region", "width", "height"]


def test_response_carries_every_field_the_frontend_reads(client):
    j = post(client).json()
    for k in REQUIRED:
        assert k in j, f"missing {k}"
    assert j["qc_flag"] == "contamination_suspected"
    assert j["record"]["record_hash"] == "c" * 64


def test_image_ref_is_a_filename_not_a_dead_temp_path(client):
    """The temp dir is gone by the time anyone reads the record."""
    j = post(client, name="field.png").json()
    assert j["record"]["image_ref"] == "field.png"
    assert "/tmp" not in j["record"]["image_ref"]


def test_overlay_is_off_by_default_and_opt_in(client):
    assert post(client).json()["overlay_image_base64"] is None
    on = post(client, include_overlay="true").json()["overlay_image_base64"]
    assert on and on.startswith("data:image/png;base64,")


# ── the arithmetic that is easy to get quietly wrong ───────────────────────

def test_boxes_are_fractions_of_the_full_image(client):
    j = post(client).json()
    for box in j["evidence_boxes"]:
        assert len(box) == 4
        assert all(0.0 <= v <= 1.0 for v in box), box
        assert box[0] < box[2] and box[1] < box[3]


def test_box_keeps_tile_size_on_a_larger_field():
    """A 256px box on a 704x520 field is 256/704 wide — not scaled by 704/256.

    This is the bug demo/app.py::_scale_bboxes has: multiplying the box's own
    width by the full-image factor draws it ~2.75x too wide.
    """
    qc = FakeQC()
    qc.evidence_bboxes = [(0, 0, 256, 256)]
    (x1, y1, x2, y2), = api._boxes_normalised(qc, 704, 520)
    assert x2 - x1 == pytest.approx(256 / 704, abs=1e-4)
    assert y2 - y1 == pytest.approx(256 / 520, abs=1e-4)
    # and it is centred, because the classifier reads the centre crop
    assert x1 == pytest.approx(((704 - 256) // 2) / 704, abs=1e-4)


def test_box_is_clamped_to_the_image(client):
    qc = FakeQC()
    qc.evidence_bboxes = [(200, 200, 256, 256)]     # runs off a 256px tile
    (x1, y1, x2, y2), = api._boxes_normalised(qc, 256, 256)
    assert x2 <= 1.0 and y2 <= 1.0


def test_small_image_is_not_offset(client):
    """Below the tile size there is no centre crop, so there is no origin shift."""
    qc = FakeQC()
    qc.evidence_bboxes = [(0, 0, 64, 64)]
    (x1, y1, _, _), = api._boxes_normalised(qc, 128, 128)
    assert (x1, y1) == (0.0, 0.0)


# ── concurrency ────────────────────────────────────────────────────────────

def test_concurrent_uploads_do_not_break_the_hash_chain(tmp_path, monkeypatch):
    """The page sends three at a time, and the chain has to survive that.

    culture.pipeline.analyze() builds a RecordWriter per call, and RecordWriter
    reads the log's tail hash in __init__. Without serialising, two calls read
    the same tail, both write it as prev_record_hash, and every record after
    them fails verification — the page's own Verify would call the log we
    produced tampered.

    The real RecordWriter is used here; only the models are stubbed, because the
    bug is in the write path, not the inference.
    """
    from concurrent.futures import ThreadPoolExecutor

    sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__)))))
    from culture.records import RecordWriter, verify_chain

    log = str(tmp_path / "events.jsonl")
    monkeypatch.setattr(api, "LOG_PATH", log)
    monkeypatch.setitem(api._state, "models_loaded", True)

    def fake_analyze(path, **kw):
        rec = dict(RECORD)
        rec.pop("prev_record_hash", None)
        rec.pop("record_hash", None)
        rec["flask_id"] = kw.get("flask_id", "x")
        rec["image_ref"] = kw.get("image_ref", os.path.abspath(path))
        # the real writer, and therefore the real race
        return RecordWriter(kw["log_path"]).append(rec)

    fake_pipeline = types.ModuleType("culture.pipeline")
    fake_pipeline.analyze = fake_analyze
    fake_qc = types.ModuleType("culture.qc")
    fake_qc.qc_classify = lambda *a, **k: FakeQC()
    fake_rules = types.ModuleType("culture.rules")
    fake_rules.LineConfig = lambda **k: None
    monkeypatch.setitem(sys.modules, "culture.pipeline", fake_pipeline)
    monkeypatch.setitem(sys.modules, "culture.qc", fake_qc)
    monkeypatch.setitem(sys.modules, "culture.rules", fake_rules)

    data = png_bytes()
    with ThreadPoolExecutor(max_workers=3) as ex:
        results = list(ex.map(
            lambda i: api._run(data, f"f{i}.png", "Huh7", 80.0, f"F-{i}", False),
            range(12)))

    assert len(results) == 12
    with open(log) as fh:
        assert sum(1 for line in fh if line.strip()) == 12
    intact, bad_line = verify_chain(log)
    assert intact, f"chain broken under concurrency, first bad record at line {bad_line}"
    import json
    with open(log) as fh:
        stored = {r["record_hash"]: r for r in map(json.loads, fh)}
    for result in results:
        record = result["record"]
        assert record == stored[record["record_hash"]], "API mutated a signed record"
        import hashlib
        assert hashlib.sha256(result["record_canonical"].encode()).hexdigest() == record["record_hash"]
        assert json.loads(result["record_canonical"]) == {
            k: v for k, v in record.items() if k != "record_hash"
        }


# ── CORS ───────────────────────────────────────────────────────────────────

def _preflight(origin):
    r = TestClient(api.app).options("/analyze", headers={
        "Origin": origin,
        "Access-Control-Request-Method": "POST",
    })
    return r.headers.get("access-control-allow-origin")


@pytest.mark.parametrize("origin,allowed", [
    ("https://cultureqc.vercel.app", True),
    ("https://cultureqc-git-main-abc.vercel.app", True),
    ("http://localhost:5173", True),        # dev only; see the Space test below
    ("null", True),                         # file:// during local development
    ("https://evil.example.com", False),
    ("https://notcultureqc.vercel.app", False),
])
def test_cors_allows_only_the_intended_origins(origin, allowed):
    assert (_preflight(origin) is not None) is allowed, origin


def test_file_and_localhost_origins_are_refused_in_the_space(monkeypatch):
    """`null` is what file:// sends — and what a sandboxed iframe sends.

    Convenient locally, wrong in production: it would let any local page call the
    public API. The allowlist is built at import time, so this reimports the
    module with the Space environment set rather than trusting the comment.
    """
    import importlib
    monkeypatch.setenv("SPACE_ID", "LongGrainRice/cultureqc-api")
    space_api = importlib.reload(api)
    try:
        assert space_api.IN_SPACE is True
        assert "null" not in space_api.ORIGINS
        assert not any("localhost" in o for o in space_api.ORIGINS)
        assert "https://cultureqc.vercel.app" in space_api.ORIGINS
    finally:
        monkeypatch.delenv("SPACE_ID", raising=False)
        importlib.reload(api)
