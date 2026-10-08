"""
cultureqc.pipeline — End-to-end analysis: image -> auditable record.

    from cultureqc.pipeline import analyze
    record = analyze("path/to/image.tif", flask_id="F-001", cell_line="A172")
"""

from __future__ import annotations

import hashlib
import os
import uuid
from datetime import datetime, timezone

from culture.seg import cpsam_confluency
from culture.qc import qc_classify, classifier_demoted, CLASS_NAMES
from culture.calibration import DEFAULT_CALIBRATION_PATH
from culture.rules import decide, LineConfig, DEFAULT_CONFIG, RULES_VERSION
from culture.records import SCHEMA_VERSION, RecordWriter, hash_file
from culture.rationale import generate_rationale


def config_hashes() -> dict:
    """SHA-256 of each config that shaped this record; a config that isn't
    there (e.g. a Space without configs/) is left out, not faked."""
    from culture.qc import QC_CONFIG_PATH
    from culture import detectability
    from culture.anomaly import ANOMALY_CONFIG_PATH
    from culture.profiles import PROFILES_PATH
    from culture.quality import _DEFAULT_CONFIG_PATH as QUALITY_CONFIG_PATH
    from culture.approvals import APPROVALS_PATH
    from culture.finetuned import CONFIG_PATH as FINETUNED_CONFIG_PATH
    paths = {"qc.yaml": QC_CONFIG_PATH, "calibration.yaml": DEFAULT_CALIBRATION_PATH,
             "detectability.yaml": detectability.DEFAULT_PATH, "anomaly.yaml": ANOMALY_CONFIG_PATH,
             "confluency_profiles.yaml": PROFILES_PATH, "quality.yaml": QUALITY_CONFIG_PATH,
             "approved_changes.jsonl": APPROVALS_PATH, "finetuned_models.yaml": FINETUNED_CONFIG_PATH}
    return {name: hash_file(p) for name, p in paths.items() if os.path.exists(p)}


def analyze(
    image_path: str,
    flask_id: str = "unknown",
    cell_line: str = "unknown",
    line_config: LineConfig | None = None,
    hours_since_passage: float | None = None,
    hours_since_feed: float | None = None,
    log_path: str = "events.jsonl",
    protocol_stage: str | None = None,
    pixel_size_um: float | None = None,
    image_ref: str | None = None,
    observer=None,
    details: dict | None = None,
    profile_id: str | None = None,
    lineage: dict | None = None,
    imager_id: str | None = None,
    fov: dict | None = None,
    environment: dict | None = None,
    finetuned_id: str | None = None,
) -> dict:
    """
    Full pipeline: profile + quality gate + confluency + anomaly + QC + rules
    -> hash-chained reading record.

    The host platform supplies what only it knows: flask_id, lineage,
    imager_id, fov, environment, protocol_stage, and profile_id (which
    imaging setup took the image). Returns the finalized record (already
    appended to the log).

    The shipped model's weights are checked against the approvals log before
    it reads (culture/approvals.py); a mismatch raises approvals.NotApproved
    and no record is written, because there is no reading. finetuned_id adds a
    fine-tuned model's reading beside the shipped one (culture/finetuned.py):
    recorded, never used in the decision, refused if its weights don't match.
    """
    import cv2
    import numpy as np

    from culture.anomaly import score_frame
    from culture.profiles import get_profile
    from culture.quality import quality_gate
    from culture.weights import weights_hashes

    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise FileNotFoundError(f"Could not read image: {image_path}")
    emit = observer or (lambda event: None)
    profile = get_profile(profile_id)
    quality = quality_gate(img, dataset=profile.quality) if profile.quality else None

    # ── Confluency, at the profile's cutoff ──
    from culture.visuals import segmentation_visuals, qc_visual
    emit({"stage": "segmentation", "status": "running"})
    visuals = {}
    def segmentation_ready(prob, mask):
        visuals.update(segmentation_visuals(img, prob, mask))
    conf_result = cpsam_confluency(img, method="probmap", thr=profile.cutoff, **(
        {"on_visual": segmentation_ready} if observer or details is not None else {}))
    emit({"stage": "segmentation", "status": "complete", "visuals": dict(visuals),
          "confluency_pct": conf_result.pct})

    # ── A fine-tuned model's reading: shown beside the shipped one, never decides ──
    finetuned = None
    if finetuned_id:
        from culture.finetuned import read as finetuned_read
        finetuned = finetuned_read(img, finetuned_id)

    # ── Per-image anomaly (B2): shown for review; a flag holds a passage (rules v0.3).
    #    Its density bins were calibrated on the reading at Cellpose's default cutoff. ──
    from culture.visuals import anomaly_tile_view, png
    emit({"stage": "anomaly", "status": "running"})
    anomaly = score_frame(img, conf_result.extra["pct_default_cutoff"])
    if anomaly.status == "ok" and (observer or details is not None):
        visuals["anomaly_tile"] = png(anomaly_tile_view(img, anomaly))
    emit({"stage": "anomaly", "status": "complete", "anomaly_status": anomaly.status})

    # ── QC classification (demoted: recorded, no vote; centre 256 px tile) ──
    h, w = img.shape[:2]
    tile_size = 256
    if h >= tile_size and w >= tile_size:
        cy, cx = h // 2, w // 2
        tile = img[cy - tile_size//2 : cy + tile_size//2,
                   cx - tile_size//2 : cx + tile_size//2]
    else:
        tile = cv2.resize(img, (tile_size, tile_size))
    demoted = classifier_demoted()
    emit({"stage": "qc", "status": "running"})
    def cam_ready(cam):
        visuals["heatmap"] = qc_visual(cam, w, h)
    qc_result = qc_classify(tile, run_gradcam=not demoted, **(
        {"on_visual": cam_ready} if not demoted and (observer or details is not None) else {}))
    if details is not None:
        details.update(qc=qc_result, anomaly=anomaly, visuals=visuals, profile=profile, quality=quality)
    emit({"stage": "qc", "status": "complete", "visuals": dict(visuals)})

    # ── Rules (rules_v0.5) ──
    cfg = line_config or DEFAULT_CONFIG
    action, reason = decide(
        confluency_pct=conf_result.pct,
        confluency_confidence=conf_result.confidence,
        qc_flag=None if demoted else qc_result.flag,
        qc_confidence=None if demoted else qc_result.confidence,
        line_config=cfg,
        hours_since_passage=hours_since_passage,
        hours_since_feed=hours_since_feed,
        anomaly_flag=anomaly.flag if anomaly.status == "ok" else None,
        band_pp=profile.band_pp,
        quality_passed=quality.passed if quality else None,
        quality_reasons=quality.reasons if quality else None,
    )

    rat = generate_rationale(
        qc_flag=None if demoted else qc_result.flag,
        qc_confidence=None if demoted else qc_result.confidence,
        evidence_bbox=qc_result.evidence_bbox,
        confluency_pct=conf_result.pct,
        target_confluency=cfg.target_confluency,
        action=action,
        tile_size=256,
        use_vlm=False,  # set True to try VLM; falls back to template on failure
        image_path=image_path,
        anomaly_flag=anomaly.flag if anomaly.status == "ok" else None,
    )

    now = datetime.now(timezone.utc).isoformat()
    record = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "reading",
        "flask_id": flask_id,
        "cell_line": cell_line,
        "protocol_stage": protocol_stage,
        "lineage": lineage,
        "imager_id": imager_id,
        "fov": fov,
        "environment": environment,
        "captured_at": now,  # in a real system this comes from the imager, via the host
        "image_ref": image_ref if image_ref is not None else os.path.abspath(image_path),
        "image_hash": hash_file(image_path),
        "pixel_size_um": pixel_size_um,
        "confluency_pct": conf_result.pct,
        "confluency_interval": profile.interval(conf_result.pct),
        "confluency_profile": profile.record_fields(),
        "confluency_confidence": conf_result.confidence,
        "confluency_method": conf_result.method,
        "quality_gate": None if quality is None else {
            "passed": quality.passed, "reasons": quality.reasons, "thresholds": quality.thresholds,
            "blur": round(quality.blur, 3), "mean_intensity": round(quality.mean_intensity, 3),
            "uniformity": round(quality.uniformity, 3)},
        "recovery_request": {"action": "reimage", "reasons": quality.reasons} if action == "reimage" else None,
        "qc_flag": qc_result.flag,
        "qc_confidence": qc_result.confidence,
        "qc_severity": None,  # would come from a severity sub-classifier
        "qc_evidence_bbox": list(qc_result.evidence_bbox) if qc_result.evidence_bbox else None,
        "qc_rationale": rat["rationale"],
        "qc_calibrated": qc_result.calibrated,
        "qc_used_in_decision": not demoted,
        **anomaly.record_fields(),
        "anomaly_bin_confluency_pct": conf_result.extra["pct_default_cutoff"],
        "growth_trend": None,  # would come from time-series mode
        "eta_to_target_hours": None,
        "recommended_action": action,
        "action_reason": reason,
        "decided_by": RULES_VERSION,
        "model_versions": {
            "seg": conf_result.model_version,
            "qc": qc_result.model_version,
            "dino": anomaly.model_version,
            "vlm": rat["method"],
        },
        "model_weights_hash": weights_hashes(),
        "model_check": conf_result.extra["model_check"],
        "finetuned_reading": finetuned,
        "config_hashes": config_hashes(),
    }

    writer = RecordWriter(log_path)
    return writer.append(record)
