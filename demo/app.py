"""
cultureQC demo — dark, image-dominant review surface for exception review
of automated cell-culture QC calls. See UI_PLAN.md for the design brief.

    python demo/app.py

Requires: cellpose, timm, grad-cam, gradio, jsonschema
Models are downloaded from Hugging Face on first run.
"""

import html
import json
import os
import sys
import tempfile
from pathlib import Path

import cv2
import gradio as gr
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from culture.seg import cpsam_confluency, threshold_confluency, _get_model as _get_seg_model
from culture.qc import qc_classify
from culture.rules import decide, LineConfig
from culture.records import RecordWriter, verify_chain, hash_file
from culture.rationale import generate_rationale
from demo.theme import CultureQCTheme

WORK_DIR = tempfile.mkdtemp(prefix="cultureqc_demo_")
LOG_PATH = os.path.join(WORK_DIR, "cultureqc_demo_events.jsonl")
writer = RecordWriter(LOG_PATH)

TILE_SIZE = 256
DEFAULT_HOURS_SINCE_PASSAGE = 48.0
DEFAULT_HOURS_SINCE_FEED = 12.0
CELL_LINES = ["A172", "BT474", "BV2", "Huh7", "MCF7", "SHSY5Y", "SKOV3", "SkBr3", "unknown"]

STATUS_COLORS = {"green": "#22c55e", "amber": "#f59e0b", "red": "#ef4444"}

FLAG_META = {
    "normal": ("Normal", "green"),
    "contamination_suspected": ("Contamination Suspected", "red"),
    "detachment": ("Detachment", "amber"),
    "image_quality": ("Image Quality", "amber"),
}

# Shorter row labels for the evidence breakdown, where "Suspected" is redundant
# with the probability bar sitting right next to it.
EVIDENCE_LABELS = {
    "normal": "Normal",
    "contamination_suspected": "Contamination",
    "detachment": "Detachment",
    "image_quality": "Image Quality",
}

ACTION_META = {
    "passage": ("Passage", "green"),
    "feed": ("Feed", "amber"),
    "hold": ("Hold", "amber"),
    "human_review": ("Human Review", "red"),
}

ICONS = {
    "check-circle": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/>'
        '<path d="M8.3 12.4l2.6 2.6 4.8-5.4"/></svg>'
    ),
    "alert-triangle": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round"><path d="M12 3.6 21 19.3H3z"/>'
        '<path d="M12 9.6v4"/><circle cx="12" cy="16.6" r="0.65" fill="currentColor" stroke="none"/></svg>'
    ),
    "alert-octagon": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round"><path d="M8 3h8l5 5v8l-5 5H8l-5-5V8z"/>'
        '<path d="M12 8v4.6"/><circle cx="12" cy="16" r="0.65" fill="currentColor" stroke="none"/></svg>'
    ),
}

STATUS_ICON = {
    "normal": "check-circle",
    "contamination_suspected": "alert-octagon",
    "detachment": "alert-triangle",
    "image_quality": "alert-triangle",
}


def _hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


def _tint(hex_color, alpha):
    r, g, b = _hex_to_rgb(hex_color)
    return f"rgba({r},{g},{b},{alpha})"


# ─── Overlay rendering ───

def _scale_bboxes(bboxes, img_h, img_w):
    """Map QC evidence boxes from the centered 256x256 tile back to full-image coords."""
    scale_y = img_h / TILE_SIZE
    scale_x = img_w / TILE_SIZE
    offset_y = (img_h - TILE_SIZE) // 2 if img_h >= TILE_SIZE else 0
    offset_x = (img_w - TILE_SIZE) // 2 if img_w >= TILE_SIZE else 0
    out = []
    for bx, by, bw, bh in bboxes:
        ix = int(bx * scale_x) + offset_x
        iy = int(by * scale_y) + offset_y
        iw = int(bw * scale_x)
        ih = int(bh * scale_y)
        out.append((ix, iy, ix + iw, iy + ih))
    return out


def _build_overlay(img_gray, cell_mask, evidence_boxes):
    overlay = cv2.cvtColor(img_gray, cv2.COLOR_GRAY2RGB)

    green = np.zeros_like(overlay)
    green[:, :, 1] = 190
    blended = cv2.addWeighted(overlay, 0.68, green, 0.32, 0)
    overlay = np.where(cell_mask[:, :, None].astype(bool), blended, overlay)

    if evidence_boxes:
        glow = np.zeros_like(overlay)
        for x1, y1, x2, y2 in evidence_boxes:
            cv2.rectangle(glow, (x1, y1), (x2, y2), (255, 40, 40), 7)
        glow = cv2.GaussianBlur(glow, (13, 13), 0)
        overlay = cv2.add(overlay, glow)
        for x1, y1, x2, y2 in evidence_boxes:
            cv2.rectangle(overlay, (x1, y1), (x2, y2), (255, 30, 30), 2)

    return overlay


# ─── Analysis ───

def run_analysis(original_path, cell_line, target_confluency):
    if not original_path:
        empty = '<div class="rc-empty">Upload an image to begin analysis.</div>'
        return gr.update(), gr.update(visible=False), empty, None

    img = cv2.imread(original_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        err = '<div class="rc-empty">Could not read that image file.</div>'
        return gr.update(), gr.update(visible=False), err, None

    target_confluency = float(target_confluency or 80.0)

    conf_result = cpsam_confluency(img, method="probmap")
    threshold_confluency(img)  # baseline computed for parity; not shown in this surface

    h, w = img.shape[:2]
    if h >= TILE_SIZE and w >= TILE_SIZE:
        cy, cx = h // 2, w // 2
        tile = img[cy - TILE_SIZE // 2 : cy + TILE_SIZE // 2, cx - TILE_SIZE // 2 : cx + TILE_SIZE // 2]
    else:
        tile = cv2.resize(img, (TILE_SIZE, TILE_SIZE))

    qc_result = qc_classify(tile, run_gradcam=True)

    cfg = LineConfig(cell_line=cell_line, target_confluency=target_confluency)
    action, reason = decide(
        confluency_pct=conf_result.pct,
        confluency_confidence=conf_result.confidence,
        qc_flag=qc_result.flag,
        qc_confidence=qc_result.confidence,
        line_config=cfg,
        hours_since_passage=DEFAULT_HOURS_SINCE_PASSAGE,
        hours_since_feed=DEFAULT_HOURS_SINCE_FEED,
    )

    seg_model = _get_seg_model()
    masks, flows, _ = seg_model.eval(img, diameter=None, channels=[0, 0])
    cell_mask = flows[2] > 0

    evidence_boxes = []
    if qc_result.evidence_bboxes and qc_result.flag != "normal":
        evidence_boxes = _scale_bboxes(qc_result.evidence_bboxes, h, w)

    overlay = _build_overlay(img, cell_mask, evidence_boxes)
    overlay_path = os.path.join(WORK_DIR, f"overlay_{next(tempfile._get_candidate_names())}.png")
    cv2.imwrite(overlay_path, cv2.cvtColor(overlay, cv2.COLOR_RGB2BGR))

    rat = generate_rationale(
        qc_flag=qc_result.flag,
        qc_confidence=qc_result.confidence,
        evidence_bbox=qc_result.evidence_bbox,
        confluency_pct=conf_result.pct,
        target_confluency=target_confluency,
        action=action,
        tile_size=TILE_SIZE,
        use_vlm=False,
        image_path=original_path,
    )

    from datetime import datetime, timezone

    record = {
        "schema_version": "0.2",
        "flask_id": "demo",
        "cell_line": cell_line,
        "protocol_stage": None,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "image_ref": os.path.basename(original_path),
        "image_hash": hash_file(original_path),
        "pixel_size_um": None,
        "confluency_pct": conf_result.pct,
        "confluency_confidence": conf_result.confidence,
        "confluency_method": conf_result.method,
        "qc_flag": qc_result.flag,
        "qc_confidence": qc_result.confidence,
        "qc_severity": None,
        "qc_evidence_bbox": list(qc_result.evidence_bbox) if qc_result.evidence_bbox else None,
        "qc_rationale": rat["rationale"],
        "growth_trend": None,
        "eta_to_target_hours": None,
        "recommended_action": action,
        "action_reason": reason,
        "decided_by": "rules_v0.2",
        "model_versions": {
            "seg": conf_result.model_version,
            "qc": qc_result.model_version,
            "vlm": rat["method"],
        },
        "model_weights_hash": None,
        "reviewed_by": None,
        "review_outcome": None,
    }
    finalized = writer.append(record)
    chain_ok, _ = verify_chain(LOG_PATH)

    results_html = render_results(
        qc_flag=qc_result.flag,
        qc_confidence=qc_result.confidence,
        per_class_probs=qc_result.per_class_probs,
        evidence_region_count=len(evidence_boxes),
        confluency_pct=conf_result.pct,
        confluency_confidence=conf_result.confidence,
        confluency_method=conf_result.method,
        target_confluency=target_confluency,
        action=action,
        rationale=rat["rationale"],
        record=finalized,
        chain_ok=chain_ok,
        record_count=writer.record_count,
    )

    return overlay_path, gr.update(visible=True, value="Overlay"), results_html, overlay_path


def render_results(
    qc_flag,
    qc_confidence,
    per_class_probs,
    evidence_region_count,
    confluency_pct,
    confluency_confidence,
    confluency_method,
    target_confluency,
    action,
    rationale,
    record,
    chain_ok,
    record_count,
):
    flag_label, flag_color_key = FLAG_META.get(qc_flag, (qc_flag.replace("_", " ").title(), "amber"))
    flag_color = STATUS_COLORS[flag_color_key]
    icon = ICONS[STATUS_ICON.get(qc_flag, "alert-triangle")]

    action_label, action_color_key = ACTION_META.get(action, (action.replace("_", " ").title(), "amber"))
    action_color = STATUS_COLORS[action_color_key]

    above_target = confluency_pct >= target_confluency
    bar_pct = max(0.0, min(100.0, confluency_pct))
    target_pct = max(0.0, min(100.0, target_confluency))
    fill_color = STATUS_COLORS["green"] if above_target else "#4b5563"

    evidence_rows = []
    for cls_key, (_, cls_color_key) in FLAG_META.items():
        cls_label = EVIDENCE_LABELS[cls_key]
        prob = per_class_probs.get(cls_key, 0.0)
        is_predicted = cls_key == qc_flag
        row_color = STATUS_COLORS[cls_color_key] if is_predicted else "#4b5563"
        label_color = STATUS_COLORS[cls_color_key] if is_predicted else "var(--text-secondary)"
        weight = "600" if is_predicted else "400"
        evidence_rows.append(f"""
    <div class="evidence-row">
      <span class="evidence-label" style="color:{label_color};font-weight:{weight}">{html.escape(cls_label)}</span>
      <span class="evidence-bar-track"><span class="evidence-bar-fill" style="transform:scaleX({prob:.4f});background:{row_color}"></span></span>
      <span class="evidence-pct">{prob * 100:.0f}%</span>
    </div>""")

    if evidence_region_count > 0:
        region_line = f"{evidence_region_count} evidence region{'s' if evidence_region_count != 1 else ''} marked on image"
        region_dot_style = f"background:{STATUS_COLORS['red']};border-color:{STATUS_COLORS['red']}"
    else:
        region_line = "No evidence regions marked on this image"
        region_dot_style = "background:transparent;border-color:var(--border)"

    audit_json = html.escape(json.dumps(record, indent=2, sort_keys=True))
    chain_label = "intact" if chain_ok else "BROKEN"

    return f"""
<div class="rc-stack">
  <div class="rc-card status-card" style="animation-delay:0ms;background:{_tint(flag_color, 0.08)};border-color:{_tint(flag_color, 0.28)}">
    <div class="status-row">
      <span class="status-icon" style="color:{flag_color}">{icon}</span>
      <span class="status-label" style="color:{flag_color}">{html.escape(flag_label)}</span>
      <span class="confidence-pill">{qc_confidence:.2f}</span>
    </div>
    <div class="evidence-rows">{"".join(evidence_rows)}
    </div>
    <div class="evidence-regions">
      <span class="evidence-region-dot" style="{region_dot_style}"></span>
      <span>{region_line}</span>
    </div>
  </div>

  <div class="rc-card confluency-card" style="animation-delay:100ms">
    <div class="confluency-number">{confluency_pct:.1f}<span class="unit">%</span></div>
    <div class="confluency-bar">
      <div class="confluency-fill" style="transform:scaleX({bar_pct / 100:.4f});background:{fill_color}"></div>
      <div class="confluency-target-marker" style="left:{target_pct:.1f}%"></div>
    </div>
    <div class="confluency-meta">
      <span>Target: {target_confluency:.0f}%</span>
      <span>Confidence: {confluency_confidence:.2f}</span>
      <span>Method: {html.escape(confluency_method)}</span>
    </div>
  </div>

  <div class="rc-card action-card" style="animation-delay:200ms">
    <span class="action-badge" style="background:{_tint(action_color, 0.15)};color:{action_color}">{html.escape(action_label)}</span>
  </div>

  <div class="rc-card rationale" style="animation-delay:300ms">{html.escape(rationale)}</div>

  <details class="rc-card audit-details" style="animation-delay:400ms">
    <summary><span class="audit-chevron"></span>Audit Record</summary>
    <div class="audit-meta">Chain {chain_label} &middot; record #{record_count}</div>
    <pre class="audit-json">{audit_json}</pre>
  </details>
</div>
"""


# ─── Event handlers ───

def on_upload(path):
    if not path:
        return gr.update(visible=False), "", None, None, gr.update()

    # Browsers can't render TIFF in an <img> tag, and several test-data tiles
    # are real microscopy TIFFs — re-encode a browser-safe preview copy so the
    # upload doesn't show a broken-image glyph. The original file (not this
    # copy) is still what gets analyzed and hashed into the audit record.
    preview_path = path
    raw = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if raw is not None:
        preview_path = os.path.join(WORK_DIR, f"preview_{next(tempfile._get_candidate_names())}.png")
        cv2.imwrite(preview_path, raw)

    return gr.update(visible=False), "", path, None, preview_path


def switch_view(choice, original_path, overlay_path):
    if choice == "Original":
        return original_path
    return overlay_path or original_path


def start_loading():
    return (
        gr.update(value="", interactive=False, elem_classes=["analyze-btn", "is-loading"]),
        gr.update(visible=True),
    )


def end_loading():
    return (
        gr.update(value="Analyze", interactive=True, elem_classes=["analyze-btn"]),
        gr.update(visible=False),
    )


# ─── UI ───

CSS_PATH = Path(__file__).resolve().parent / "style.css"
CSS = CSS_PATH.read_text()

# Confluency readout count-up: the one signature interaction. Runs client-side
# only (no backend round-trip) after results_html lands, so the big number
# ticks up from zero like an instrument readout rather than snapping in static.
COUNT_UP_JS = """
() => {
  const el = document.querySelector('.confluency-number');
  if (!el || !el.firstChild) return;
  const node = el.firstChild;
  const target = parseFloat(node.textContent);
  if (Number.isNaN(target)) return;
  node.textContent = '0.0';
  const duration = 600;
  const start = performance.now() + 460;
  function tick(now) {
    if (now < start) { requestAnimationFrame(tick); return; }
    const t = Math.min(1, (now - start) / duration);
    const eased = 1 - Math.pow(1 - t, 3);
    node.textContent = (target * eased).toFixed(1);
    if (t < 1) requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
}
"""

with gr.Blocks(
    title="cultureQC",
    fill_width=True,
    fill_height=True,
) as demo:
    original_state = gr.State(None)
    overlay_state = gr.State(None)

    with gr.Row(elem_classes="topbar"):
        gr.HTML('<div class="wordmark"><span class="wordmark-dot"></span>cultureQC</div>')
        with gr.Row(elem_classes="topbar-controls"):
            with gr.Row(elem_classes="control-cluster"):
                cell_line = gr.Dropdown(
                    choices=CELL_LINES, value="A172", show_label=False, container=False,
                    elem_classes=["topbar-field", "cell-line-field"],
                )
                target_conf = gr.Number(
                    value=80, minimum=0, maximum=100, step=5, show_label=False, container=False,
                    elem_classes=["topbar-field", "target-field"],
                )
            analyze_btn = gr.Button("Analyze", variant="primary", elem_classes=["analyze-btn"])

    with gr.Row(elem_classes="main-row"):
        with gr.Column(scale=62, min_width=0, elem_classes="image-pane"):
            view_toggle = gr.Radio(
                ["Original", "Overlay"], value="Overlay", visible=False, show_label=False,
                container=False, elem_classes="view-toggle",
            )
            loading_overlay = gr.HTML('<div class="image-loading-overlay"></div>', visible=False)
            image_view = gr.Image(
                type="filepath", show_label=False, container=False, elem_classes="hero-image",
                sources=["upload"], buttons=[], height="100%",
            )

        with gr.Column(scale=38, min_width=0, elem_classes="results-pane"):
            results_html = gr.HTML('<div class="rc-empty">Upload an image to begin analysis.</div>')

    gr.HTML(
        '<div class="app-footer">cultureQC v0.1 &middot; Cellpose-SAM &middot; EfficientNet-B0 '
        '(synthetic-trained QC classifier) &middot; MIT</div>'
    )

    image_view.upload(
        fn=on_upload,
        inputs=[image_view],
        outputs=[view_toggle, results_html, original_state, overlay_state, image_view],
    )

    analyze_btn.click(
        fn=start_loading, inputs=None, outputs=[analyze_btn, loading_overlay], show_progress="hidden",
    ).then(
        fn=run_analysis,
        inputs=[original_state, cell_line, target_conf],
        outputs=[image_view, view_toggle, results_html, overlay_state],
        show_progress="hidden",
    ).then(
        fn=end_loading, inputs=None, outputs=[analyze_btn, loading_overlay], show_progress="hidden",
    ).then(
        fn=None, inputs=None, outputs=None, js=COUNT_UP_JS, show_progress="hidden",
    )

    view_toggle.change(
        fn=switch_view,
        inputs=[view_toggle, original_state, overlay_state],
        outputs=[image_view],
        show_progress="hidden",
    )


if __name__ == "__main__":
    demo.launch(theme=CultureQCTheme(), css=CSS, footer_links=[])
