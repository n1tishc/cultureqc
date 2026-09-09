"""cultureQC analysis API — the FastAPI app the HuggingFace Space runs.

    uvicorn api:app --host 0.0.0.0 --port 7860

Two routes:

    GET  /health   -> {"status": "ok", "models_loaded": bool, ...}
    POST /analyze  -> the full result for one image (multipart form)

This calls the same `culture.pipeline.analyze()` an automation platform would
call. Nothing here reimplements or approximates the pipeline; if a number is in
the response, the shipped models produced it.

Both models are loaded during startup rather than on the first request, so the
first visitor does not pay for a cold model load. Loading happens on a worker
thread: the event loop stays responsive and /health can answer
`models_loaded: false` while the Space is still warming up, which is what the
frontend shows its warming state from.

The audit log is per-boot by deliberate choice. HuggingFace Space disks are
wiped on restart, so a chain written here cannot claim continuity across boots.
Each record is still individually verifiable, and the browser builds and
verifies its own chain across an upload batch — see /health's `audit` field,
which states this rather than leaving it implied.
"""

from __future__ import annotations

import base64
import logging
import os
import tempfile
import threading
import time
from contextlib import asynccontextmanager

import numpy as np
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool

log = logging.getLogger("cultureqc.api")
logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s")

TILE = 256
MAX_BYTES = 64 * 1024 * 1024
ALLOWED_EXT = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}

# Per-boot, and named so it is obvious in a file listing that it is not durable.
LOG_PATH = os.environ.get("CULTUREQC_LOG", "/tmp/events_boot.jsonl")

_state = {"models_loaded": False, "error": None, "loaded_at": None, "boot": time.time()}

# One analysis at a time. Two reasons, and either alone would be enough:
#
#   The chain. culture.pipeline.analyze() constructs a RecordWriter per call, and
#   RecordWriter reads the log's tail hash in __init__. Two concurrent calls both
#   read the same tail and both write it as prev_record_hash, which silently
#   breaks the chain for every record after them — the page's own Verify would
#   report the log we produced as tampered. The frontend sends three at a time.
#
#   The models. Cellpose-SAM and the classifier are process-wide singletons and
#   are not documented as safe for concurrent inference.
#
# Serialising costs nothing real here: the target is a 2-vCPU box, where parallel
# CPU inference is not faster anyway.
_pipeline_lock = threading.Lock()


def _warm() -> None:
    """Load both models once, on a worker thread, at startup.

    Cellpose-SAM downloads its weights on first construction and the QC
    classifier pulls its checkpoint from the Hub, so this is also what makes the
    first real request fast. A failure here is recorded rather than raised: the
    Space stays up and /health reports why, which is far easier to debug than a
    container that will not boot.
    """
    try:
        t0 = time.time()
        from culture.qc import _get_model as _qc_model
        from culture.seg import _get_model as _seg_model

        log.info("loading QC classifier…")
        _qc_model()
        log.info("loading Cellpose-SAM…")
        _seg_model()

        # One tiny inference so lazy CUDA/CPU kernels and the Grad-CAM hooks are
        # built now instead of inside the first user request.
        from culture.qc import qc_classify
        qc_classify(np.zeros((TILE, TILE), dtype=np.uint8), run_gradcam=True)

        _state["models_loaded"] = True
        _state["loaded_at"] = round(time.time() - t0, 1)
        log.info("models ready in %.1fs", time.time() - t0)
    except Exception as exc:                      # noqa: BLE001 — reported, not raised
        _state["error"] = f"{type(exc).__name__}: {exc}"
        log.exception("model warm-up failed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    threading.Thread(target=_warm, daemon=True).start()
    yield


app = FastAPI(
    title="cultureQC API",
    version="0.2",
    description="Confluency, QC flag with visual evidence, recommended action, "
                "and a hash-chained record — from one brightfield image.",
    lifespan=lifespan,
)

# HuggingFace sets these in the Space container; their absence means a checkout.
IN_SPACE = bool(os.environ.get("SPACE_ID") or os.environ.get("SPACE_HOST"))

# The Space is public, but that is no reason for the browser API to be. Named
# origins for production; a regex for Vercel preview deployments, which get a
# fresh subdomain per push and cannot be enumerated ahead of time.
ORIGINS = ["https://cultureqc.vercel.app"]

# Locally the page is often opened straight off disk, where the browser sends
# `Origin: null`. Allowing that in the deployed Space would let any local HTML
# file — and any sandboxed iframe, which also sends `null` — call the public API,
# so it is granted only when this is not running as a Space.
if not IN_SPACE:
    ORIGINS += ["null", "http://localhost:7860", "http://127.0.0.1:7860",
                "http://localhost:5173", "http://localhost:3000",
                "http://localhost:8000", "http://127.0.0.1:8000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGINS,
    allow_origin_regex=r"https://cultureqc-[a-z0-9-]+\.vercel\.app",
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    max_age=600,
)


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "models_loaded": _state["models_loaded"],
        "warm_seconds": _state["loaded_at"],
        "error": _state["error"],
        "schema_version": "0.2",
        "max_bytes": MAX_BYTES,
        # Stated, not implied: this disk does not survive a restart.
        "audit": "per-boot chain; Space storage is ephemeral, so prev_record_hash "
                 "links within one boot only. Each record is independently verifiable.",
    }


# Repo checkout: <root>/site/index.html. In the Space this path does not exist.
_SITE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "site")
_PAGE = os.path.join(_SITE, "index.html")
if os.path.isdir(_SITE):
    from fastapi.staticfiles import StaticFiles
    app.mount("/site", StaticFiles(directory=_SITE, html=True), name="site")


@app.get("/")
def root():
    """The API in the Space; the page too when running from a checkout.

    site/ is not copied into the Space (see deploy/sync_space.py), so in
    production this stays JSON and Vercel serves the page. Locally it means one
    command gives you the page and the pipeline on one origin, which is also the
    only way to exercise the real CORS-free path before deploying.
    """
    if os.path.isfile(_PAGE):
        from fastapi.responses import FileResponse
        return FileResponse(_PAGE, media_type="text/html")
    return {"service": "cultureqc", "docs": "/docs", "health": "/health"}


def _boxes_normalised(qc, w: int, h: int) -> list[list[float]]:
    """Grad-CAM boxes as [x1, y1, x2, y2] fractions of the full image.

    The classifier reads a centred 256x256 crop, so mapping a box back to the
    whole field offsets the origin and leaves the box's own width and height in
    tile pixels. Scaling them by the full-image factor — as demo/app.py does —
    draws a box far wider than the region actually analysed.
    """
    ox = (w - TILE) // 2 if w >= TILE else 0
    oy = (h - TILE) // 2 if h >= TILE else 0
    out = []
    for bx, by, bw, bh in (qc.evidence_bboxes or []):
        x1, y1 = (bx + ox) / w, (by + oy) / h
        x2, y2 = min((bx + ox + bw) / w, 1.0), min((by + oy + bh) / h, 1.0)
        out.append([round(x1, 5), round(y1, 5), round(x2, 5), round(y2, 5)])
    return out


def _overlay_png(path: str, boxes: list[list[float]]) -> str:
    """The field with its evidence boxes drawn, as a data: URI.

    Off by default. A caller that renders its own boxes from `evidence_boxes`
    gains nothing from this and would pay a few hundred KB per image for it,
    which matters when a batch is 200 files.
    """
    import cv2

    img = cv2.imread(path, cv2.IMREAD_COLOR)
    if img is None:
        return ""
    h, w = img.shape[:2]
    for x1, y1, x2, y2 in boxes:
        cv2.rectangle(img, (int(x1 * w), int(y1 * h)), (int(x2 * w), int(y2 * h)),
                      (46, 73, 224), 2)          # BGR of the page's cinnabar
    ok, buf = cv2.imencode(".png", img)
    if not ok:
        return ""
    return "data:image/png;base64," + base64.b64encode(buf.tobytes()).decode("ascii")


@app.post("/analyze")
async def analyze_endpoint(
    image: UploadFile = File(..., description="Brightfield / phase-contrast image"),
    cell_line: str = Form("unknown"),
    target_confluency: float = Form(80.0),
    flask_id: str = Form(""),
    include_overlay: bool = Form(False),
) -> dict:
    name = os.path.basename(image.filename or "upload.png")
    ext = os.path.splitext(name)[1].lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(415, f"unsupported file type '{ext}'")

    body = await image.read()
    if not body:
        raise HTTPException(400, "empty file")
    if len(body) > MAX_BYTES:
        raise HTTPException(413, f"file exceeds {MAX_BYTES} bytes")

    if not _state["models_loaded"]:
        if _state["error"]:
            raise HTTPException(500, f"models failed to load: {_state['error']}")
        # 503 + Retry-After is the honest answer while warming, and it is what
        # lets the frontend distinguish "not ready yet" from "broken".
        raise HTTPException(503, "models are still loading", headers={"Retry-After": "20"})

    # Every line below this point is blocking CPU work — Cellpose-SAM inference is
    # tens of seconds — so it runs on a worker thread. Doing it inline in this
    # coroutine would occupy the event loop for the whole inference and make the
    # server unresponsive to everything else, /health included, which is exactly
    # the signal the frontend's warming state depends on.
    return await run_in_threadpool(
        _run, body, name, cell_line, target_confluency, flask_id, include_overlay)


def _run(body: bytes, name: str, cell_line: str, target_confluency: float,
         flask_id: str, include_overlay: bool) -> dict:
    from culture.pipeline import analyze
    from culture.qc import qc_classify
    from culture.rules import LineConfig

    # analyze() records os.path.abspath(image_path) as image_ref, so the file has
    # to exist while the record is written. Nothing here is durable, so the temp
    # directory is cleaned up on the way out and image_ref is reduced to the
    # filename in the response rather than a path that resolves nowhere.
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, name)
        with open(path, "wb") as fh:
            fh.write(body)

        try:
            import cv2
            cfg = LineConfig(cell_line=cell_line, target_confluency=target_confluency)

            img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                raise HTTPException(400, "could not decode that image")
            h, w = img.shape[:2]

            # analyze() keeps one evidence bbox; re-run on the same centre tile to
            # recover the full per-class distribution and every box.
            if h >= TILE and w >= TILE:
                cy, cx = h // 2, w // 2
                tile = img[cy - TILE // 2: cy + TILE // 2, cx - TILE // 2: cx + TILE // 2]
            else:
                tile = cv2.resize(img, (TILE, TILE))

            # Both model calls under one lock: the chain write must not interleave,
            # and the two of them are one logical analysis of the same image.
            with _pipeline_lock:
                record = analyze(
                    path,
                    flask_id=flask_id or f"WEB-{name}",
                    cell_line=cell_line,
                    line_config=cfg,
                    log_path=LOG_PATH,
                )
                qc = qc_classify(tile, run_gradcam=True)
            boxes = _boxes_normalised(qc, w, h)

            record = dict(record)
            record["image_ref"] = name

            return {
                "confluency_pct": record["confluency_pct"],
                "confluency_confidence": record["confluency_confidence"],
                "confluency_method": record["confluency_method"],
                "qc_flag": record["qc_flag"],
                "qc_confidence": record["qc_confidence"],
                "per_class_probs": qc.per_class_probs,
                "evidence_boxes": boxes,
                "analysed_region": TILE,
                "width": w,
                "height": h,
                "rationale": record["qc_rationale"],
                "recommended_action": record["recommended_action"],
                "action_reason": record["action_reason"],
                "overlay_image_base64": _overlay_png(path, boxes) if include_overlay else None,
                "record": record,
            }
        except HTTPException:
            raise
        except Exception as exc:                  # noqa: BLE001
            log.exception("analysis failed for %s", name)
            raise HTTPException(500, f"{type(exc).__name__}: {exc}") from exc


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=7860, timeout_keep_alive=120)
