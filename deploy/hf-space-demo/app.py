"""cultureQC — raw model demo, on ZeroGPU.

    python app.py                  # http://127.0.0.1:7860

This is a Gradio Blocks app, not the product. It exists so a link can go to
one person and they see the model's own output directly — the raw field, the
segmentation mask, the Grad-CAM heatmap, the confluency estimate, the QC
verdict, and the full signed record — with nothing else in front of it. The
product frontend is https://cultureqc.vercel.app; its backend is the separate
`hf-space` FastAPI Space, unaffected by anything here.

`import spaces` has to happen before any torch-touching import: it patches
`torch.cuda.is_available()` so module-scope `.to("cuda")` calls (culture/seg.py,
culture/qc.py) succeed here even though the physical GPU is only attached for
the duration of an `@spaces.GPU`-decorated call. See
https://huggingface.co/docs/hub/en/spaces-zerogpu.
"""
from __future__ import annotations

import base64
import os
import tempfile
import threading
import time

import spaces  # noqa: E402  (must precede the torch-touching imports below)

import cv2
import numpy as np
import gradio as gr

from culture.pipeline import analyze
from culture.rules import LineConfig

LOG_PATH = os.environ.get("CULTUREQC_LOG", "/tmp/events_boot.jsonl")

# Same reason hf-space/api.py serialises analysis: RecordWriter reads the log's
# tail hash in __init__, so two concurrent writers can both read the same tail
# and corrupt the chain, and the Cellpose/QC singletons carry mutable Grad-CAM
# hook state that is not documented as safe for concurrent forward passes. The
# lock lives in this process regardless of which worker ZeroGPU attaches a GPU
# to for the call itself.
_pipeline_lock = threading.Lock()


def _decode_data_uri(data_uri: str | None):
    """Decode one of culture.visuals.png()'s data: URIs back to a BGR(A) array."""
    if not data_uri:
        return None
    _, encoded = data_uri.split(",", 1)
    buf = np.frombuffer(base64.b64decode(encoded), dtype=np.uint8)
    return cv2.imdecode(buf, cv2.IMREAD_UNCHANGED)


def _to_rgb(img):
    if img is None:
        return None
    if img.ndim == 2:
        return cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
    if img.shape[2] == 4:
        return cv2.cvtColor(img, cv2.COLOR_BGRA2RGB)
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)


def _composite(base_gray, overlay_data_uri):
    """Alpha-blend an RGBA evidence layer over the raw field for one preview image."""
    overlay = _decode_data_uri(overlay_data_uri)
    if overlay is None:
        return _to_rgb(base_gray)
    base_bgr = cv2.cvtColor(base_gray, cv2.COLOR_GRAY2BGR).astype(np.float32)
    if overlay.ndim == 2 or overlay.shape[2] == 3:
        return _to_rgb(overlay)
    b, g, r, a = cv2.split(overlay)
    alpha = (a.astype(np.float32) / 255.0)[..., None]
    fg = cv2.merge([b, g, r]).astype(np.float32)
    out = (fg * alpha + base_bgr * (1 - alpha)).astype(np.uint8)
    return cv2.cvtColor(out, cv2.COLOR_BGR2RGB)


def _warm() -> None:
    """Load both models at module scope, per ZeroGPU's own guidance.

    Loading only — no forward pass here. On a real ZeroGPU Space,
    `torch.cuda.is_available()` is patched True at import time so `.to("cuda")`
    succeeds, but no physical GPU is attached outside an `@spaces.GPU` call; a
    forward pass run here would either fail or silently run on nothing. The
    Grad-CAM hooks build on the first real (decorated) call instead.
    """
    from culture.qc import _get_model as _qc_model
    from culture.seg import _get_model as _seg_model

    _qc_model()
    _seg_model()


# Declared duration matters: too small and ZeroGPU kills a genuinely slow run;
# too generous and a visitor with little quota left gets `quota exceeded`
# before the call even starts. 60s is a starting point for GPU inference on a
# single tile-sized field — hf-space/README.md's CPU numbers (21.8s per 256x256
# tile) are the closest measured reference this repo has; tune this after
# watching real ZeroGPU run times.
@spaces.GPU(duration=60)
def _run_analysis(image_path: str, cell_line: str, target_confluency: float):
    cfg = LineConfig(cell_line=cell_line or "unknown", target_confluency=target_confluency)
    details: dict = {}
    with _pipeline_lock:
        record = analyze(
            image_path,
            flask_id="DEMO",
            cell_line=cell_line or "unknown",
            line_config=cfg,
            log_path=LOG_PATH,
            image_ref=os.path.basename(image_path),
            details=details,
        )
    return record, details.get("visuals", {})


def infer(image: np.ndarray | None, cell_line: str, target_confluency: float):
    if image is None:
        raise gr.Error("Upload a brightfield image first.")
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY) if image.ndim == 3 else image
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "upload.png")
        cv2.imwrite(path, gray)
        t0 = time.time()
        record, visuals = _run_analysis(path, cell_line, target_confluency)
        elapsed = time.time() - t0

    verdict = f"{record['qc_flag'].replace('_', ' ')} · {record['confluency_pct']}% confluent"
    detail = (
        f"Recommended action: {record['recommended_action']} — {record['action_reason']}\n\n"
        f"{record['qc_rationale']}\n\n"
        f"Analysed in {elapsed:.1f}s."
    )
    return (
        _to_rgb(gray),
        _composite(gray, visuals.get("mask")),
        _composite(gray, visuals.get("heatmap")),
        verdict,
        detail,
        record,
    )


with gr.Blocks(title="cultureQC — raw model demo") as demo:
    gr.Markdown(
        "# cultureQC — raw model output\n"
        "Upload one brightfield / phase-contrast image. This calls the same "
        "`culture.pipeline.analyze()` the product uses on real Cellpose-SAM and "
        "EfficientNet-B0 output — nothing here is approximated. "
        "[Product site →](https://cultureqc.vercel.app)"
    )
    with gr.Row():
        with gr.Column():
            image_in = gr.Image(label="Brightfield image", type="numpy")
            cell_line_in = gr.Textbox(label="Cell line", value="Huh7")
            target_in = gr.Slider(label="Target confluency %", minimum=10, maximum=100, value=80, step=1)
            run_btn = gr.Button("Analyse", variant="primary")
        with gr.Column():
            verdict_out = gr.Textbox(label="QC verdict", interactive=False)
            detail_out = gr.Textbox(label="Rationale & recommendation", lines=5, interactive=False)
    with gr.Row():
        raw_out = gr.Image(label="Raw field", interactive=False)
        mask_out = gr.Image(label="Segmentation mask", interactive=False)
        heatmap_out = gr.Image(label="Grad-CAM heatmap", interactive=False)
    record_out = gr.JSON(label="Full signed record")

    run_btn.click(
        infer,
        inputs=[image_in, cell_line_in, target_in],
        outputs=[raw_out, mask_out, heatmap_out, verdict_out, detail_out, record_out],
    )

_warm()

if __name__ == "__main__":
    demo.launch()
