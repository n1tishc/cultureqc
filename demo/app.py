"""
cultureQC demo — dark, image-dominant review surface for exception review
of automated cell-culture QC calls. See docs/UI_PLAN.md for the design brief.

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

from culture.qc import demoted_label
from culture.profiles import choices as profile_choices, get_profile
from culture.records import RecordWriter, review_event, verify_chain
from culture.rules import ACTIONS, AMBIGUITY_TOOLTIP, boundary_ambiguity
from culture import detectability
from culture.anomaly import LIVE_LIMITS
from culture.visuals import anomaly_tile_view, png
from demo import confluency_3d, lab_demo, precomputed, replay_3d, replay_timeline, viz3d
from demo.analysis import analyze_image, build_record
from demo.theme import CultureQCTheme

WORK_DIR = tempfile.mkdtemp(prefix="cultureqc_demo_")
LOG_PATH = os.path.join(WORK_DIR, "cultureqc_demo_events.jsonl")
writer = RecordWriter(LOG_PATH)

CELL_LINES = ["A172", "BT474", "BV2", "Huh7", "MCF7", "SHSY5Y", "SKOV3", "SkBr3", "C2C12", "unknown"]
# Imaging setup -> confluency profile (configs/confluency_profiles.yaml). An
# upload is `uncalibrated` until the viewer says which setup took it: a
# profile's band holds only for images from its own setup. Offered: the
# validated profiles, the named setups without one (they keep their quality
# gate), and `uncalibrated` (culture.profiles.choices). Picking an example sets
# its own setup; an upload resets the picker (on_upload).
PROFILE_CHOICES = profile_choices()
DEFAULT_PROFILE = "uncalibrated"
# Hash the weights once at startup, not inside the first Analyze (the Cellpose-SAM file is ~1.2 GB).
from culture.weights import weights_hashes as _warm_weights  # noqa: E402
_warm_weights()

# Precomputed Analyze examples (scripts/export_demo_examples.py): real C2C12
# and EVICAN frames run once through demo/analysis.py, shown instantly and
# labelled as precomputed; Analyze re-runs them live.
EXAMPLES = precomputed.load()
# The approved fine-tuned model's demo set (demo/lab_demo.py): empty unless CULTUREQC_FINETUNED is set, as on the
# console Space (deploy/hf-space-demo/console.py) and the Colab console (nb/11_lab_demo.ipynb). With it empty,
# nothing below changes.
LAB_IMAGES = lab_demo.available()
if LAB_IMAGES:
    CELL_LINES = CELL_LINES[:-1] + lab_demo.CELL_LINES + CELL_LINES[-1:]
# The demoted classifier's collapsed heading. The rate is "called normal" on held-out
# normal frames, results/classifier_c2c12.md; tests/test_replay_notes.py checks it.
CLASSIFIER_SUMMARY = ("Demoted — known wrong on real frames (5.0% of normal frames called normal); "
                      "not used for the action")
CONTAMINATION_FIGURE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "figures", "contamination_scale.png")

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
    "continue": ("Continue", "amber"),
    "human_review": ("Human Review", "red"),
    "reimage": ("Re-image", "amber"),
}
STATUS_TEXT = {"validated": "validated", "failed": "failed its criteria", "in_domain_check": "in-domain check only",
               "uncalibrated": "uncalibrated"}

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


# ─── Analysis ───

def run_analysis(original_path, cell_line, target_confluency, profile_id=None):
    if not original_path:
        empty = '<div class="rc-empty">Upload an image to begin analysis.</div>'
        return gr.update(), gr.update(visible=False), empty, None, None, None, gr.update(visible=False)

    img = cv2.imread(original_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        err = '<div class="rc-empty">Could not read that image file.</div>'
        return gr.update(), gr.update(visible=False), err, None, None, None, gr.update(visible=False)

    target_confluency = float(target_confluency or 80.0)
    lab = lab_demo.match(original_path, LAB_IMAGES)        # the fine-tuned model reads the demo set only
    a = analyze_image(img, original_path, cell_line, target_confluency, profile_id=profile_id,
                      finetuned_id=lab_demo.model_id() if lab else None)
    overlay_path = os.path.join(WORK_DIR, f"overlay_{next(tempfile._get_candidate_names())}.png")
    cv2.imwrite(overlay_path, cv2.cvtColor(a.overlay, cv2.COLOR_RGB2BGR))

    finalized = writer.append(build_record(a, original_path, cell_line))
    chain_ok, _ = verify_chain(LOG_PATH)

    results_html = render_results(
        anomaly_html=render_anomaly(img, a.anomaly),
        demoted=a.demoted,
        qc_calibrated=a.qc.calibrated,
        qc_flag=a.qc.flag,
        qc_confidence=a.qc.confidence,
        per_class_probs=a.qc.per_class_probs,
        evidence_region_count=len(a.evidence_boxes),
        confluency_pct=a.confluency.pct,
        confluency_confidence=a.confluency.confidence,
        confluency_method=a.confluency.method,
        target_confluency=target_confluency,
        action=a.action,
        rationale=a.rationale["rationale"],
        record=finalized,
        chain_ok=chain_ok,
        record_count=writer.record_count,
        finetuned=a.finetuned,
        lab=lab,
    )

    known = precomputed.match(original_path, EXAMPLES)   # same image as an example: same opening camera
    map_view = {"prob": a.probmap_x1000, "confluency": a.confluency.to_dict(),
                "map_hash": finalized["confluency_map_hash"], "precomputed": False,
                "id": known["id"] if known else None}
    return (overlay_path, gr.update(visible=True, value="Overlay"), results_html, overlay_path, map_view,
            finalized, gr.update(visible=True))


def sign_review(reading, reviewer, decision, final_action, reason):
    """A person's decision on the last live reading, appended to this session's
    chain as its own record. Identity and the e-signature belong to the host
    platform; this demo records the name typed here and no signature."""
    if not reading:
        return '<div class="review-out">Run Analyze first; a review needs a reading in this session.</div>'
    reviewer = (reviewer or "").strip()
    if not reviewer:
        return '<div class="review-out bad">Type the reviewer\'s name.</div>'
    decision = "accept" if decision.startswith("Accept") else "override"
    if decision == "accept":
        final_action = reading["recommended_action"]
    try:
        ev = review_event(reading, reviewer_id=f"demo:{reviewer.lower().replace(' ', '-')}", reviewer_name=reviewer,
                          meaning="approval", decision=decision, final_action=final_action,
                          reason=(reason or "").strip() or None)
    except ValueError as e:
        return f'<div class="review-out bad">{html.escape(str(e))}</div>'
    rec = writer.append(ev)
    res = verify_chain(LOG_PATH)
    return f"""<div class="review-out"><b>Review recorded</b> as record #{writer.record_count}, linked to the reading by
    its hash ({reading["record_hash"][:12]}…); the reading itself is unchanged. Chain {"intact" if res.ok else "BROKEN"}.
    <pre class="audit-json">{html.escape(json.dumps(rec, indent=2, sort_keys=True))}</pre></div>"""


def render_anomaly(img, anomaly):
    """The per-image anomaly card (B2): flag, score vs the bin's threshold, the
    zoomed tile heatmap, and the known limits. A flag holds a passage (rules v0.3)."""
    limits = "".join(f"<li>{html.escape(t)}</li>" for t in LIVE_LIMITS)
    if anomaly.status != "ok":
        return f"""
  <div class="rc-card anomaly-card" style="animation-delay:100ms">
    <div class="anomaly-head"><span class="anomaly-title">Anomaly check</span>
      <span class="anomaly-state muted">Unavailable</span></div>
    <div class="classifier-note">{html.escape(anomaly.reason or "")}</div>
  </div>"""
    color = STATUS_COLORS["red"] if anomaly.flag else STATUS_COLORS["green"]
    state = "Flagged for review" if anomaly.flag else "Within the normal range"
    ratio = anomaly.score / anomaly.threshold
    tile_uri = png(cv2.cvtColor(anomaly_tile_view(img, anomaly), cv2.COLOR_RGB2BGR))
    return f"""
  <div class="rc-card anomaly-card" style="animation-delay:100ms;border-color:{_tint(color, 0.35)}">
    <div class="anomaly-head"><span class="anomaly-title">Anomaly check</span>
      <span class="anomaly-state" style="color:{color}">{state}</span></div>
    <div class="anomaly-body">
      <img class="anomaly-tile" src="{tile_uri}" alt="Patch distances on the centre tile">
      <div class="anomaly-metrics">
        <div><span class="anomaly-k">Score</span> <span class="anomaly-v">{anomaly.score:.3f}</span></div>
        <div><span class="anomaly-k">Threshold</span> <span class="anomaly-v">{anomaly.threshold:.3f}</span></div>
        <div><span class="anomaly-k">Score / threshold</span> <span class="anomaly-v">{ratio:.2f}</span></div>
        <div><span class="anomaly-k">Confluency bin</span> <span class="anomaly-v">{html.escape(anomaly.bin_label)}%</span></div>
        <div class="classifier-note">DINOv2 patch distance to the nearest normal C2C12 patch, on the outlined
        centre region only. Boxes: the patches that set the score.</div>
      </div>
    </div>
    <ul class="anomaly-limits">{limits}</ul>
  </div>"""


def render_provenance(ex):
    """The label every precomputed example carries (claims policy: precomputed
    outputs are never presented as live)."""
    t = ex["timings_s"]
    rd = ex.get("decision_rederived")
    rederived = ("" if not rd else
                 f" Recommendation re-derived {html.escape(rd['at'])} under {html.escape(rd['rules'])} from these "
                 "stored outputs (rules change only; no model re-run).")
    return f"""
  <div class="rc-card precomputed-card">
    <div class="precomputed-head">Precomputed example</div>
    <div class="classifier-note">Produced by <code>scripts/export_demo_examples.py</code> with the same code as
    the Analyze button, on {html.escape(ex["device"].upper())} ({t["wall"]:.0f} s),
    {html.escape(ex["generated_at"][:10])}.{rederived} Press Analyze to run this image live.</div>
    <div class="precomputed-caption">{html.escape(ex["caption"])}</div>
    <div class="classifier-note">{html.escape(ex["credit"])}</div>
  </div>"""


def show_example(ex):
    """Render a precomputed example: no model runs."""
    img = cv2.imread(precomputed.image_path(ex), cv2.IMREAD_GRAYSCALE)
    anomaly = precomputed.anomaly_result(ex)
    qc = ex["qc"]
    return render_results(
        anomaly_html=render_anomaly(img, anomaly),
        demoted=ex["demoted"],
        qc_calibrated=qc["calibrated"],
        qc_flag=qc["flag"],
        qc_confidence=qc["confidence"],
        per_class_probs=qc["per_class_probs"],
        evidence_region_count=ex["evidence_region_count"],
        confluency_pct=ex["confluency"]["pct"],
        confluency_confidence=ex["confluency"]["confidence"],
        confluency_method=ex["confluency"]["method"],
        target_confluency=ex["target_confluency"],
        action=ex["action"],
        rationale=ex["rationale"],
        record=ex["record"],
        chain_ok=None,
        record_count=None,
        example=ex,
    )


def confluency_card(record, confluency_pct, confluency_confidence, confluency_method, target_confluency, delay_ms):
    """The reading, its 90% error band from the imaging setup's profile, the
    target, and the quality gate. Older stored records have no profile: they
    show the reading alone."""
    above_target = confluency_pct >= target_confluency
    bar_pct = max(0.0, min(100.0, confluency_pct))
    target_pct = max(0.0, min(100.0, target_confluency))
    fill_color = STATUS_COLORS["green"] if above_target else "#4b5563"
    prof = (record or {}).get("confluency_profile")
    interval = (record or {}).get("confluency_interval")
    band_html, band_line = "", ""
    amb = (f'<span class="amb" title="{html.escape(AMBIGUITY_TOOLTIP)}">Boundary ambiguity '
           f'{boundary_ambiguity(confluency_confidence):.2f}: recorded; since rules_v0.5 it no longer decides '
           f'(it tracks density, not error)</span>')
    if prof:
        label = get_profile(prof["id"]).entry.get("label", prof["id"])
        status = STATUS_TEXT.get(prof["status"], prof["status"])
        if interval:
            lo, hi = interval
            band_html = (f'<div class="confluency-band" style="left:{lo:.1f}%;width:{max(0.6, hi - lo):.1f}%"></div>')
            straddle = lo < target_confluency <= hi
            band_line = (f'<div class="band-line">90% error band <b>{lo:.1f}–{hi:.1f}%</b> (±{prof["band_pp"]:.1f} pp, '
                         f'measured on held-out labelled images from this setup)'
                         + (' · <span class="straddle">the band includes the target</span>' if straddle else "")
                         + f'<br>Profile <code>{html.escape(prof["id"])}</code>, {html.escape(status)}, cutoff '
                         f'{format(prof["cutoff"], "+g").replace("-", "−")} · {html.escape(label)}</div>')
        else:
            band_line = (f'<div class="band-line"><b>No error band:</b> this imaging setup has no validated calibration '
                         f'profile, so a reading at or above the target goes to a person. Profile '
                         f'<code>{html.escape(prof["id"])}</code>, cutoff {prof["cutoff"]:+.1f}'.replace("cutoff -", "cutoff −")
                         + amb + '</div>')
    q = (record or {}).get("quality_gate", "absent")
    if q == "absent":
        gate_line = ""
    elif q is None:
        gate_line = '<div class="gate-line">Quality gate: not calibrated for this imaging setup</div>'
    elif q["passed"]:
        gate_line = f'<div class="gate-line ok">Quality gate: passed ({html.escape(q["thresholds"])} thresholds)</div>'
    else:
        why = ", ".join(r.replace("_", " ") for r in q["reasons"])
        gate_line = f'<div class="gate-line bad">Quality gate: failed ({html.escape(why)}): re-image</div>'
    return f"""
  <div class="rc-card confluency-card" style="animation-delay:{delay_ms}ms">
    <div class="confluency-number">{confluency_pct:.1f}<span class="unit">%</span></div>
    <div class="confluency-bar">
      <div class="confluency-fill" style="transform:scaleX({bar_pct / 100:.4f});background:{fill_color}"></div>
      {band_html}
      <div class="confluency-target-marker" style="left:{target_pct:.1f}%"></div>
    </div>
    <div class="confluency-meta">
      <span>Target: {target_confluency:.0f}%</span>
      {"" if prof else f'<span title="{html.escape(AMBIGUITY_TOOLTIP)}">Boundary ambiguity: {boundary_ambiguity(confluency_confidence):.2f}</span>'}
      <span>Method: {html.escape(confluency_method)}</span>
    </div>
    {band_line}{gate_line}
  </div>
"""


def lab_card(lab, delay_ms):
    """The experts' coverage of a demo-set image, for comparison; neither model sees it."""
    if not lab:
        return ""
    return f"""
  <div class="rc-card lab-card" style="animation-delay:{delay_ms}ms">
    <div class="lab-line">Demo image <code>{html.escape(lab["name"])}</code> · experts' outline coverage
      <b>{lab["experts_pct"]:.1f}%</b></div>
    <div class="band-line">From the experts' own mask, shown for comparison; neither model uses it.
      {html.escape(lab_demo.CREDIT)}</div>
  </div>
"""


def finetuned_card(fr, delay_ms):
    """The fine-tuned model's reading (culture/finetuned.py), beside the shipped one: its weights check, and no
    part in the action."""
    if not fr:
        return ""
    c = fr.get("check") or {}
    status = c.get("status", "unknown")
    if fr.get("confluency_pct") is None:
        reading = f'<div class="ft-refused">No reading: {html.escape(fr.get("reason") or status)}</div>'
    else:
        reading = f'<div class="ft-number">{fr["confluency_pct"]:.1f}<span class="unit">%</span></div>'
    return f"""
  <div class="rc-card ft-card" style="animation-delay:{delay_ms}ms">
    <div class="ft-head">Fine-tuned model <code>{html.escape(fr["id"])}</code> ·
      {html.escape(str(fr.get("status", "")).replace("_", " "))} · decides nothing</div>
    {reading}
    <div class="band-line">Weights check: <b>{html.escape(status)}</b> · SHA-256
      <code>{html.escape((c.get("sha256") or "")[:12])}…</code> · approvals log head
      <code>{html.escape((c.get("approvals_head") or "none")[:12])}…</code><br>Read at cutoff
      {fr.get("cutoff", 0.0):+.1f} with no error band; recorded beside the reading above and left out of the
      action.</div>
  </div>
"""


def render_results(
    anomaly_html,
    demoted,
    qc_calibrated,
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
    example=None,
    finetuned=None,
    lab=None,
):
    flag_label, flag_color_key = FLAG_META.get(qc_flag, (qc_flag.replace("_", " ").title(), "amber"))
    flag_color = STATUS_COLORS[flag_color_key]
    icon = ICONS[STATUS_ICON.get(qc_flag, "alert-triangle")]

    action_label, action_color_key = ACTION_META.get(action, (action.replace("_", " ").title(), "amber"))
    action_color = STATUS_COLORS[action_color_key]

    evidence_rows = []
    for cls_key, (_, cls_color_key) in FLAG_META.items():
        cls_label = EVIDENCE_LABELS[cls_key]
        prob = per_class_probs.get(cls_key, 0.0)
        is_predicted = cls_key == qc_flag
        # Demoted: no status colours, so no row reads as a finding.
        highlight = is_predicted and not demoted
        row_color = STATUS_COLORS[cls_color_key] if highlight else "#4b5563"
        label_color = STATUS_COLORS[cls_color_key] if highlight else "var(--text-secondary)"
        weight = "600" if highlight else "400"
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
    if example is None:
        audit_meta = f"Chain {'intact' if chain_ok else 'BROKEN'} &middot; record #{record_count}"
        provenance_html = ""
    else:
        audit_meta = ("Precomputed record, stored with the example; not part of this session's chain")
        provenance_html = render_provenance(example)
    calibration_line = ("Probabilities temperature-scaled on synthetic validation tiles (V8); "
                        "calibration on real images not measured." if qc_calibrated
                        else "Probabilities not temperature-scaled.")

    if demoted:
        return f"""
<div class="rc-stack">
{provenance_html}{lab_card(lab, 0)}
{confluency_card(record, confluency_pct, confluency_confidence, confluency_method, target_confluency, 0)}
{finetuned_card(finetuned, 50)}{anomaly_html}

  <div class="rc-card action-card" style="animation-delay:200ms">
    <span class="action-badge" style="background:{_tint(action_color, 0.15)};color:{action_color}">{html.escape(action_label)}</span>
  </div>

  <div class="rc-card rationale" style="animation-delay:250ms">{html.escape(rationale)}</div>

  <details class="rc-card audit-details classifier-details" style="animation-delay:300ms">
    <summary><span class="audit-chevron"></span>QC classifier: {html.escape(CLASSIFIER_SUMMARY)}</summary>
    <div class="classifier-note">{html.escape(demoted_label())}</div>
    <div class="evidence-rows">{"".join(evidence_rows)}
    </div>
    <div class="classifier-note">{html.escape(calibration_line)} Recorded in the audit record for traceability.</div>
  </details>

  <details class="rc-card audit-details" style="animation-delay:400ms">
    <summary><span class="audit-chevron"></span>Audit Record</summary>
    <div class="audit-meta">{audit_meta}</div>
    <pre class="audit-json">{audit_json}</pre>
  </details>
</div>
"""

    return f"""
<div class="rc-stack">
{provenance_html}
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
    <div class="classifier-note">{html.escape(calibration_line)}</div>
  </div>

{lab_card(lab, 100)}{confluency_card(record, confluency_pct, confluency_confidence, confluency_method, target_confluency, 100)}
{finetuned_card(finetuned, 150)}  <div class="rc-card action-card" style="animation-delay:200ms">
    <span class="action-badge" style="background:{_tint(action_color, 0.15)};color:{action_color}">{html.escape(action_label)}</span>
  </div>

  <div class="rc-card rationale" style="animation-delay:300ms">{html.escape(rationale)}</div>

  <details class="rc-card audit-details" style="animation-delay:400ms">
    <summary><span class="audit-chevron"></span>Audit Record</summary>
    <div class="audit-meta">{audit_meta}</div>
    <pre class="audit-json">{audit_json}</pre>
  </details>
</div>
"""


# ─── Event handlers ───

def on_upload(path):
    """The last output resets the setup picker: a new image is `uncalibrated` until the
    viewer picks the setup that took it, never read with the previous example's profile."""
    if not path:
        return gr.update(visible=False), "", None, None, gr.update(), DEFAULT_PROFILE

    # Browsers can't render TIFF in an <img> tag, and several test-data tiles
    # are real microscopy TIFFs — re-encode a browser-safe preview copy so the
    # upload doesn't show a broken-image glyph. The original file (not this
    # copy) is still what gets analyzed and hashed into the audit record.
    preview_path = path
    raw = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if raw is not None:
        preview_path = os.path.join(WORK_DIR, f"preview_{next(tempfile._get_candidate_names())}.png")
        cv2.imwrite(preview_path, raw)

    return gr.update(visible=False), "", path, None, preview_path, DEFAULT_PROFILE


def on_example(path):
    ex = precomputed.match(path, EXAMPLES)
    if ex is None:
        vis, html_, orig, ov, preview, prof = on_upload(path)
        return preview, vis, html_, orig, ov, gr.update(), gr.update(), None, prof, None, gr.update(visible=False)
    overlay = precomputed.overlay_path(ex)
    prob = precomputed.probmap(ex)
    map_view = None if prob is None else {
        "prob": prob, "confluency": ex["confluency"], "map_hash": ex["record"].get("confluency_map_hash"),
        "precomputed": True, "id": ex["id"]}
    prof = (ex["record"].get("confluency_profile") or {}).get("id", DEFAULT_PROFILE)
    return (overlay, gr.update(visible=True, value="Overlay"), show_example(ex), precomputed.image_path(ex),
            overlay, ex["cell_line"], ex["target_confluency"], map_view, prof, None, gr.update(visible=False))


def on_lab_image(name):
    """A demo-set image, analysed from its own file (not a browser copy), so its hash matches; the setup picker
    resets to `uncalibrated` (this lab has no profile) and the cell line follows the image."""
    lab = next(i for i in LAB_IMAGES if i["name"] == name)
    return (gr.update(visible=False), "", lab["path"], None, lab_demo.preview(lab["path"], WORK_DIR),
            DEFAULT_PROFILE, lab["cell_line"])


def switch_view(choice, original_path, overlay_path, map_view):
    """Original / Overlay show the image; 3D swaps in the confluency landscape."""
    if choice == "3D" and map_view is not None:
        return (gr.update(visible=False),
                gr.update(value=confluency_3d.landscape_figure(map_view["prob"], example_id=map_view.get("id")),
                          visible=True),
                gr.update(value=confluency_3d.landscape_note(map_view["prob"], map_view["confluency"],
                                                             map_view["map_hash"], map_view["precomputed"]),
                          visible=True))
    path = original_path if choice == "Original" else (overlay_path or original_path)
    return gr.update(value=path, visible=True), gr.update(visible=False), gr.update(visible=False)


def on_timeline(scenario, mode, replays=None):
    """Flask Timeline: the confluency curve, or the 3D space x time view."""
    replays = replay_timeline.load_replays() if replays is None else replays
    curve, summary, table = replay_timeline.render(scenario, replays)
    if mode != "Curve" and replay_3d.available(scenario):
        return (gr.update(value=curve, visible=False), summary, table,
                gr.update(value=replay_3d.figure(scenario, replays[scenario]), visible=True),
                gr.update(value=replay_3d.note(scenario), visible=True))
    return gr.update(value=curve, visible=True), summary, table, gr.update(visible=False), gr.update(visible=False)


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
    map_state = gr.State(None)        # the 3D view's map: {"prob", "confluency", "map_hash", "precomputed", "id"}

    with gr.Row(elem_classes="topbar"):
        gr.HTML('<div class="wordmark"><span class="wordmark-dot"></span>cultureQC</div>')

    with gr.Tabs(elem_classes="app-tabs"):
        with gr.Tab("Analyze"):
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
                    setup = gr.Dropdown(
                        choices=PROFILE_CHOICES, value=DEFAULT_PROFILE, show_label=False, container=False,
                        elem_classes=["topbar-field", "setup-field"],
                    )
                analyze_btn = gr.Button("Analyze", variant="primary", elem_classes=["analyze-btn"])

            with gr.Row(elem_classes="main-row"):
                with gr.Column(scale=62, min_width=0, elem_classes="image-pane"):
                    view_toggle = gr.Radio(
                        ["Original", "Overlay", "3D"], value="Overlay", visible=False, show_label=False,
                        container=False, elem_classes="view-toggle",
                    )
                    loading_overlay = gr.HTML('<div class="image-loading-overlay"></div>', visible=False)
                    image_view = gr.Image(
                        type="filepath", show_label=False, container=False, elem_classes="hero-image",
                        sources=["upload"], buttons=[], height="100%",
                    )
                    landscape_plot = gr.Plot(visible=False, show_label=False, container=False,
                                             elem_classes="landscape-plot")
                    landscape_note = gr.HTML(visible=False)

                with gr.Column(scale=38, min_width=0, elem_classes="results-pane"):
                    results_html = gr.HTML('<div class="rc-empty">Upload an image to begin analysis.</div>')
                    reading_state = gr.State(None)   # the last live reading, for the review form
                    with gr.Column(visible=False, elem_classes="review-panel") as review_panel:
                        gr.HTML('<div class="review-head">Review this reading</div><div class="review-sub">Writes a '
                                'separate review record into this session\'s chain, linked to the reading by its hash. '
                                'On an instrument, identity and the electronic signature come from the host platform; '
                                'this demo records the name typed here.</div>')
                        reviewer = gr.Textbox(placeholder="Reviewer name", show_label=False, container=False)
                        decision = gr.Radio(["Accept the recommendation", "Override"], value="Accept the recommendation",
                                            show_label=False, container=False)
                        final_action = gr.Dropdown(choices=list(ACTIONS), value="passage", label="Final action (override)")
                        reason = gr.Textbox(placeholder="Reason (required for an override)", show_label=False,
                                            container=False, lines=2)
                        sign_btn = gr.Button("Record review", elem_classes=["review-btn"])
                        review_out = gr.HTML()

            with gr.Row(elem_classes="real-examples-row"):
                gr.Markdown(
                    "**Examples: precomputed, labelled as such; press Analyze to run one live.** "
                    "C2C12 frames are held-out frames from the Phase A replays; the contaminated ones are "
                    "simulated (bacteria pasted at 16.5× their real size). EVICAN: two of its 33 test images, "
                    "read with the EVICAN calibration profile and compared with the dataset's own expert masks. "
                    + " · ".join(sorted({part for e in EXAMPLES for part in e["credit"].split("; ")}))
                )
                # Spaces set GRADIO_CACHE_EXAMPLES=true; caching would write the
                # stored maps into Gradio's CSV log (over its field limit) and
                # adds nothing, since on_example is already precomputed.
                EXAMPLES_UI = gr.Examples(
                    examples=[[precomputed.image_path(e)] for e in EXAMPLES],
                    example_labels=[e["label"] for e in EXAMPLES],
                    inputs=[image_view],
                    outputs=[image_view, view_toggle, results_html, original_state, overlay_state, cell_line,
                             target_conf, map_state, setup, reading_state, review_panel],
                    fn=on_example,
                    run_on_click=True,
                    cache_examples=False,
                    label="",
                )

            if LAB_IMAGES:
                with gr.Row(elem_classes="real-examples-row lab-demo-row"):
                    gr.Markdown(
                        f"**Fine-tuned demo set: {len(LAB_IMAGES)} test images from the lab the fine-tuned model "
                        "was trained on; it never saw these images.** Press one, then Analyze. Only these images get "
                        "the fine-tuned reading, shown beside the shipped one; it decides nothing. "
                        + lab_demo.CREDIT)
                    for _lab in LAB_IMAGES:
                        gr.Button(_lab["label"], size="sm", elem_classes="lab-btn").click(
                            fn=(lambda n: lambda: on_lab_image(n))(_lab["name"]), inputs=None,
                            outputs=[view_toggle, results_html, original_state, overlay_state, image_view, setup,
                                     cell_line],
                        ).then(fn=lambda: (None, None, gr.update(visible=False), ""), inputs=None,
                               outputs=[map_state, reading_state, review_panel, review_out], show_progress="hidden")

        with gr.Tab("Flask Timeline"):
            # Precomputed replays (scripts/export_demo_replays.py): no cache, no
            # models, instant on CPU. Banner and credit come from the JSONs.
            _replays = replay_timeline.load_replays()
            _first = next(iter(_replays.values()))
            gr.HTML(
                '<div class="rc-card" style="border-left:3px solid var(--accent);'
                'padding:12px 16px;margin-bottom:10px;">'
                f'<strong style="color:var(--text-primary)">{html.escape(_first["banner"])}</strong><br>'
                '<span style="color:var(--text-secondary);font-size:0.85em;line-height:1.5">'
                f'{html.escape(_first["target_note"])}<br>'
                "Precomputed from held-out sequences: every number below was produced before the app "
                "started, by the same code the Phase A checks used. No SPC or trend charts; the QC "
                "classifier is not shown (demoted, see the Analyze tab).</span></div>"
            )
            timeline_choice = gr.Radio(
                choices=replay_timeline.choices(_replays), value=next(iter(_replays)), show_label=False,
                container=False, elem_classes="scenario-picker",
            )
            timeline_mode = gr.Radio(["Curve", "3D: space × time"], value="Curve", show_label=False,
                                     container=False, elem_classes="view-mode")
            timeline_plot = gr.Plot(show_label=False, container=False)
            timeline_3d = gr.Plot(show_label=False, container=False, visible=False)
            timeline_3d_note = gr.HTML(visible=False)
            timeline_summary = gr.Markdown()
            timeline_table = gr.HTML()
            gr.Markdown(f'<span class="replay-credit">{html.escape(_first["credit"])}</span>')

        with gr.Tab("Detectability"):
            gr.HTML(detectability.to_html())
            if os.path.exists(CONTAMINATION_FIGURE):
                gr.Image(CONTAMINATION_FIGURE, label="Simulated bacterial contamination, oversized and at real size",
                         interactive=False, show_label=True, container=True)
                gr.Markdown(
                    '<p class="detect-note">The anomaly check\'s 256 px tile of one late held-out frame. Left to '
                    "right: no fault; the stress test the first contamination example comes from (bacteria 16.5× too "
                    "large); the same bacteria at their real size, with and without the simulator's haze. At real "
                    "size, up to 400 per 256 px tile area, the per-visit flag is at chance and confluency does not "
                    "rise; heavier contamination is not tested (results/contamination_scale.md).</p>")

    gr.HTML(
        '<div class="app-footer">cultureQC v0.4 &middot; Cellpose-SAM &middot; DINOv2-small (anomaly check) '
        '&middot; EfficientNet-B0 (synthetic-trained QC classifier, demoted) &middot; code MIT; model weights and '
        'datasets carry their own licences, see the README</div>'
    )

    image_view.upload(
        fn=on_upload,
        inputs=[image_view],
        outputs=[view_toggle, results_html, original_state, overlay_state, image_view, setup],
    ).then(fn=lambda: (None, None, gr.update(visible=False), ""), inputs=None,
           outputs=[map_state, reading_state, review_panel, review_out], show_progress="hidden")

    analyze_btn.click(
        fn=start_loading, inputs=None, outputs=[analyze_btn, loading_overlay], show_progress="hidden",
    ).then(
        fn=run_analysis,
        inputs=[original_state, cell_line, target_conf, setup],
        outputs=[image_view, view_toggle, results_html, overlay_state, map_state, reading_state, review_panel],
        show_progress="hidden",
    ).then(
        fn=lambda: "", inputs=None, outputs=[review_out], show_progress="hidden",
    ).then(
        fn=end_loading, inputs=None, outputs=[analyze_btn, loading_overlay], show_progress="hidden",
    ).then(
        fn=None, inputs=None, outputs=None, js=COUNT_UP_JS, show_progress="hidden",
    )

    sign_btn.click(fn=sign_review, inputs=[reading_state, reviewer, decision, final_action, reason],
                   outputs=[review_out], show_progress="hidden")

    view_toggle.change(
        fn=switch_view,
        inputs=[view_toggle, original_state, overlay_state, map_state],
        outputs=[image_view, landscape_plot, landscape_note],
        show_progress="hidden",
    )

    def _on_timeline(scenario, mode):
        return on_timeline(scenario, mode, _replays)

    _timeline_outputs = [timeline_plot, timeline_summary, timeline_table, timeline_3d, timeline_3d_note]
    demo.load(fn=_on_timeline, inputs=[timeline_choice, timeline_mode], outputs=_timeline_outputs,
              show_progress="hidden")
    timeline_choice.change(fn=_on_timeline, inputs=[timeline_choice, timeline_mode], outputs=_timeline_outputs,
                           show_progress="hidden")
    timeline_mode.change(fn=_on_timeline, inputs=[timeline_choice, timeline_mode], outputs=_timeline_outputs,
                         show_progress="hidden")


if __name__ == "__main__":
    demo.launch(theme=CultureQCTheme(), css=CSS, head=viz3d.HEAD, footer_links=[])
