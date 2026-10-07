"""
demo/analysis.py — one image through the console's live path: the imaging
setup's confluency profile (cutoff and error band, culture/profiles.py), the
quality gate where one is calibrated for the setup, Cellpose-SAM confluency
(one pass; the overlay mask is the same probability map at the profile's
cutoff), the QC classifier (recorded; kept out of the action while demoted),
the per-image anomaly check (shown for review; a flag holds a passage) and the
action rules (rules_v0.5).

demo/app.py runs it live; scripts/export_demo_examples.py runs it once per
precomputed example, so the two show the same computation.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

import cv2
import numpy as np

from culture.anomaly import AnomalyResult, score_frame
from culture.cache import downsample_probmap, probmap_sha256
from culture.pipeline import config_hashes
from culture.profiles import Profile, get_profile
from culture.qc import QCResult, classifier_demoted, qc_classify
from culture.quality import QualityResult, quality_gate
from culture.rationale import generate_rationale
from culture.records import SCHEMA_VERSION, hash_file
from culture.rules import RULES_VERSION, LineConfig, decide
from culture.seg import ConfluencyResult, cpsam_confluency, threshold_confluency
from culture.visuals import outline_scored_region
from culture.weights import weights_hashes

TILE_SIZE = 256
DEFAULT_HOURS_SINCE_PASSAGE = 48.0
DEFAULT_HOURS_SINCE_FEED = 12.0


@dataclass
class Analysis:
    confluency: ConfluencyResult
    qc: QCResult
    demoted: bool
    anomaly: AnomalyResult
    action: str
    reason: str
    rationale: dict
    evidence_boxes: list
    overlay: np.ndarray                      # RGB, full frame
    timings_s: dict = field(default_factory=dict)
    # The cell-probability map the confluency was counted from, in the
    # cache's stored form (culture.cache.downsample_probmap); its SHA-256 goes
    # in the record as confluency_map_hash. Kept in memory only.
    probmap_x1000: np.ndarray | None = None
    profile: Profile | None = None
    quality: QualityResult | None = None     # None: no gate calibrated for this setup
    finetuned: dict | None = None            # culture/finetuned.py: recorded, never decides

    @property
    def interval(self) -> list[float] | None:
        return self.profile.interval(self.confluency.pct) if self.profile else None


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


def analyze_image(img: np.ndarray, image_path: str, cell_line: str, target_confluency: float,
                  profile_id: str | None = None, finetuned_id: str | None = None) -> Analysis:
    t = {}
    profile = get_profile(profile_id)
    t0 = time.perf_counter()
    quality = quality_gate(img, dataset=profile.quality) if profile.quality else None
    t["quality_gate"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    captured = {}
    # One Cellpose-SAM pass: the overlay mask is the same prob > cutoff the confluency counts.
    conf = cpsam_confluency(img, method="probmap", thr=profile.cutoff,
                            on_visual=lambda prob, fg: captured.update(prob=prob, fg=fg))
    threshold_confluency(img)  # baseline computed for parity; not shown in this surface
    t["segmentation"] = time.perf_counter() - t0

    finetuned = None
    if finetuned_id:                         # beside the shipped reading; left out of everything below
        from culture.finetuned import read as finetuned_read
        t0 = time.perf_counter()
        finetuned = finetuned_read(img, finetuned_id)
        t["finetuned"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    # B2: shown for review; a flag holds a passage (rules v0.3). Its density
    # bins were calibrated on the reading at Cellpose's default cutoff.
    anomaly = score_frame(img, conf.extra["pct_default_cutoff"])
    anomaly_flag = anomaly.flag if anomaly.status == "ok" else None
    t["anomaly"] = time.perf_counter() - t0

    h, w = img.shape[:2]
    if h >= TILE_SIZE and w >= TILE_SIZE:
        cy, cx = h // 2, w // 2
        tile = img[cy - TILE_SIZE // 2 : cy + TILE_SIZE // 2, cx - TILE_SIZE // 2 : cx + TILE_SIZE // 2]
    else:
        tile = cv2.resize(img, (TILE_SIZE, TILE_SIZE))

    # Demoted classifier (configs/qc.yaml): recorded, shown collapsed, no
    # evidence boxes, and left out of decide() and the rationale.
    t0 = time.perf_counter()
    demoted = classifier_demoted()
    qc = qc_classify(tile, run_gradcam=not demoted)
    t["qc_classifier"] = time.perf_counter() - t0
    decision_flag = None if demoted else qc.flag
    decision_conf = None if demoted else qc.confidence

    action, reason = decide(
        confluency_pct=conf.pct,
        confluency_confidence=conf.confidence,
        qc_flag=decision_flag,
        qc_confidence=decision_conf,
        line_config=LineConfig(cell_line=cell_line, target_confluency=target_confluency),
        hours_since_passage=DEFAULT_HOURS_SINCE_PASSAGE,
        hours_since_feed=DEFAULT_HOURS_SINCE_FEED,
        anomaly_flag=anomaly_flag,
        band_pp=profile.band_pp,
        quality_passed=quality.passed if quality else None,
        quality_reasons=quality.reasons if quality else None,
    )

    evidence_boxes = []
    if not demoted and qc.evidence_bboxes and qc.flag != "normal":
        evidence_boxes = _scale_bboxes(qc.evidence_bboxes, h, w)
    overlay = _build_overlay(img, captured["fg"], evidence_boxes)
    if anomaly.status == "ok":
        overlay = outline_scored_region(overlay, h, w)

    rationale = generate_rationale(
        qc_flag=decision_flag,
        qc_confidence=decision_conf,
        evidence_bbox=qc.evidence_bbox,
        confluency_pct=conf.pct,
        target_confluency=target_confluency,
        action=action,
        tile_size=TILE_SIZE,
        use_vlm=False,
        image_path=image_path,
        anomaly_flag=anomaly_flag,
    )
    t["total"] = sum(t.values())
    return Analysis(confluency=conf, qc=qc, demoted=demoted, anomaly=anomaly, action=action, reason=reason,
                    rationale=rationale, evidence_boxes=evidence_boxes, overlay=overlay,
                    timings_s={k: round(v, 3) for k, v in t.items()},
                    probmap_x1000=downsample_probmap(captured["prob"]), profile=profile, quality=quality,
                    finetuned=finetuned)


def build_record(a: Analysis, image_path: str, cell_line: str, captured_at: str | None = None,
                 host: dict | None = None) -> dict:
    """The reading record, before the writer adds its chain hashes.

    host carries what only the host platform knows (flask_id, lineage,
    imager_id, fov, environment, protocol_stage); the demo has none of it.
    """
    host = host or {}
    q = a.quality
    return {
        "schema_version": SCHEMA_VERSION,
        "record_type": "reading",
        "flask_id": host.get("flask_id", "demo"),
        "cell_line": cell_line,
        "protocol_stage": host.get("protocol_stage"),
        "lineage": host.get("lineage"),
        "imager_id": host.get("imager_id"),
        "fov": host.get("fov"),
        "environment": host.get("environment"),
        "captured_at": captured_at or datetime.now(timezone.utc).isoformat(),
        "image_ref": os.path.basename(image_path),
        "image_hash": hash_file(image_path),
        "pixel_size_um": None,
        "confluency_pct": a.confluency.pct,
        "confluency_interval": a.interval,
        "confluency_profile": a.profile.record_fields(),
        "confluency_confidence": a.confluency.confidence,
        "confluency_method": a.confluency.method,
        "confluency_map_hash": probmap_sha256(a.probmap_x1000) if a.probmap_x1000 is not None else None,
        "quality_gate": None if q is None else {"passed": q.passed, "reasons": q.reasons, "thresholds": q.thresholds,
                                                 "blur": round(q.blur, 3), "mean_intensity": round(q.mean_intensity, 3),
                                                 "uniformity": round(q.uniformity, 3)},
        "recovery_request": {"action": "reimage", "reasons": q.reasons} if a.action == "reimage" else None,
        "qc_flag": a.qc.flag,
        "qc_confidence": a.qc.confidence,
        "qc_severity": None,
        "qc_evidence_bbox": list(a.qc.evidence_bbox) if a.qc.evidence_bbox else None,
        "qc_rationale": a.rationale["rationale"],
        "qc_calibrated": a.qc.calibrated,
        "qc_used_in_decision": not a.demoted,
        **a.anomaly.record_fields(),
        "anomaly_bin_confluency_pct": a.confluency.extra.get("pct_default_cutoff"),
        "growth_trend": None,
        "eta_to_target_hours": None,
        "recommended_action": a.action,
        "action_reason": a.reason,
        "decided_by": RULES_VERSION,
        "model_versions": {
            "seg": a.confluency.model_version,
            "qc": a.qc.model_version,
            "dino": a.anomaly.model_version,
            "vlm": a.rationale["method"],
        },
        "model_weights_hash": weights_hashes(),
        "model_check": a.confluency.extra.get("model_check"),
        "finetuned_reading": a.finetuned,
        "config_hashes": config_hashes(),
    }
