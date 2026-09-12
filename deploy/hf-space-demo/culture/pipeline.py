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
from culture.qc import qc_classify, CLASS_NAMES
from culture.rules import decide, LineConfig, DEFAULT_CONFIG
from culture.records import RecordWriter, hash_file
from culture.rationale import generate_rationale


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
) -> dict:
    """
    Full pipeline: confluency + QC + rules -> hash-chained record.

    Returns the finalized record dict (already appended to the log).
    """
    import cv2
    import numpy as np

    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise FileNotFoundError(f"Could not read image: {image_path}")

    # ── Confluency ──
    emit = observer or (lambda event: None)
    from culture.visuals import segmentation_visuals, qc_visual
    emit({"stage": "segmentation", "status": "running"})
    visuals = {}
    def segmentation_ready(prob, mask):
        visuals.update(segmentation_visuals(img, prob, mask))
    conf_result = cpsam_confluency(img, method="probmap", **(
        {"on_visual": segmentation_ready} if observer or details is not None else {}))
    emit({"stage": "segmentation", "status": "complete", "visuals": dict(visuals),
          "confluency_pct": conf_result.pct})

    # ── QC classification ──
    # The classifier expects ~256x256 tiles. For a full flask image,
    # tile it and aggregate. For now, center-crop to 256x256.
    h, w = img.shape[:2]
    tile_size = 256
    if h >= tile_size and w >= tile_size:
        cy, cx = h // 2, w // 2
        tile = img[cy - tile_size//2 : cy + tile_size//2,
                   cx - tile_size//2 : cx + tile_size//2]
    else:
        tile = cv2.resize(img, (tile_size, tile_size))

    emit({"stage": "qc", "status": "running"})
    def cam_ready(cam):
        visuals["heatmap"] = qc_visual(cam, w, h)
    qc_result = qc_classify(tile, run_gradcam=True, **(
        {"on_visual": cam_ready} if observer or details is not None else {}))
    if details is not None:
        details.update(qc=qc_result, visuals=visuals)
    emit({"stage": "qc", "status": "complete", "visuals": dict(visuals)})

    # ── Rules ──
    cfg = line_config or DEFAULT_CONFIG
    action, reason = decide(
        confluency_pct=conf_result.pct,
        confluency_confidence=conf_result.confidence,
        qc_flag=qc_result.flag,
        qc_confidence=qc_result.confidence,
        line_config=cfg,
        hours_since_passage=hours_since_passage,
        hours_since_feed=hours_since_feed,
    )

    # ── Rationale ──
    rat = generate_rationale(
        qc_flag=qc_result.flag,
        qc_confidence=qc_result.confidence,
        evidence_bbox=qc_result.evidence_bbox,
        confluency_pct=conf_result.pct,
        target_confluency=cfg.target_confluency,
        action=action,
        tile_size=256,
        use_vlm=False,  # set True to try VLM; falls back to template on failure
        image_path=image_path,
    )

    # ── Build record ──
    now = datetime.now(timezone.utc).isoformat()
    record = {
        "schema_version": "0.2",
        "flask_id": flask_id,
        "cell_line": cell_line,
        "protocol_stage": protocol_stage,
        "captured_at": now,  # in a real system this comes from the microscope
        "image_ref": image_ref if image_ref is not None else os.path.abspath(image_path),
        "image_hash": hash_file(image_path),
        "pixel_size_um": pixel_size_um,
        "confluency_pct": conf_result.pct,
        "confluency_confidence": conf_result.confidence,
        "confluency_method": conf_result.method,
        "qc_flag": qc_result.flag,
        "qc_confidence": qc_result.confidence,
        "qc_severity": None,  # would come from a severity sub-classifier
        "qc_evidence_bbox": list(qc_result.evidence_bbox) if qc_result.evidence_bbox else None,
        "qc_rationale": rat["rationale"],
        "growth_trend": None,  # would come from time-series mode
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

    # ── Write to hash-chained log ──
    writer = RecordWriter(log_path)
    finalized = writer.append(record)

    return finalized
