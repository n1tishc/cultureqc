# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Existing codebase: Python backend (`culture/pipeline.py` and friends) already implemented and working. The presentation layer is a single-file Gradio app (`demo/app.py`) wired directly to the backend functions. Inferred, not asked: UI_PLAN.md frames this as presentation-layer-only work on top of a finished backend, and no frontend framework/build scaffold (React, Node, FastAPI) exists in the repo — so the stack decision is "reskin the existing Gradio app with a custom theme and CSS" (Gradio Blocks, custom `gr.themes.Base` subclass, `elem_classes`, `css=`), not a rewrite. This keeps zero new infra between now and the demo recording.

## Users

Primary operating mode is **API-first / automation-integrated**: cultureQC is meant to be embedded in a lab automation pipeline (e.g. a robotics/automation company's culture-handling workflow), calling `analyze()` per image capture. Humans are not doing this at the bench routinely — they step in only when the system flags an exception (contamination suspected, detachment, image quality issue) or when reviewing the audit trail. This UI (`demo/app.py`) is a human-facing demo/review surface standing in for that exception-review and evaluation experience, shown to a VP at a lab automation company (Celltrio) evaluating whether to integrate cultureQC.

## Product Purpose

cultureQC takes a brightfield/phase-contrast microscopy image of a cell culture and returns: confluency percentage, a QC flag (normal / contamination_suspected / detachment / image_quality) with visual evidence of where the model is looking, a recommended action (passage / feed / hold / human review), a plain-language rationale, and a hash-chained audit record. Success is a lab automation system (or the human reviewing its exceptions) being able to trust a confluency/QC call enough to act on it, and being able to prove after the fact why that call was made.

## Positioning

The differentiator this demo needs to sell is **explainability + auditability**, not raw accuracy. Reference products (Incucyte, CellXpress.ai, Mateo, CellProfiler Analyst) show confluency and masks but not *why* a QC flag was raised. cultureQC draws evidence bounding boxes (Grad-CAM regions, max 8) showing exactly where suspected contamination/detachment/image-quality problems are, and every result is written to a hash-chained, tamper-evident audit log (`culture/records.py`, schema in `culture/schema.json`, mapped in `docs/audit_mapping.md`). The contamination case with visible red evidence boxes is the intended "money shot" of the demo.

## Operating Context

- Backend entry points: `culture/pipeline.py::analyze()` (the intended integration surface) and the individual stage functions (`culture/seg.py`, `culture/qc.py`, `culture/rules.py`, `culture/rationale.py`) that `demo/app.py` currently calls directly.
- Models are ML (Cellpose-SAM for segmentation/confluency, EfficientNet-B0 for QC classification) downloaded from Hugging Face on first run; QC classifier is trained entirely on synthetic data (bacterial sprites composited onto real microscopy + synthetic detachment) — no real contaminated-culture training data exists, per `culture/qc.py` docstring.
- Sample/test images live in `test-data/` (real phase-contrast tiles per cell line, plus synthetic `contam_*`, `detach_*`, `imgq_*`, `normal_*` tiles) and are what the demo recording plan (in UI_PLAN.md) runs through the UI in sequence.
- The deliverable at the end of this work is a screen recording (1280×800) run through three images without refreshing the page, ending on the contamination case.

## Capabilities and Constraints

- Confluency: probability-map method (`cpsam_confluency`) plus a threshold baseline; both computed, probability map is primary.
- QC classes: `normal`, `contamination_suspected`, `detachment`, `image_quality`, each with per-class probabilities and up to 8 evidence bounding boxes from Grad-CAM.
- Rules engine (`culture/rules.py`) maps confluency + QC flag + timing into a recommended action; not itself in scope for this visual work.
- Every analysis is appended to a hash-chained JSONL log (`culture/records.py`); chain integrity is verifiable and should remain inspectable (collapsed by default) in the UI per UI_PLAN.md.
- This work is presentation-layer only: no changes to `culture/*` analysis logic, model behavior, or the record schema. `demo/app.py` may be restructured (layout, styling, what it displays and how) but must keep calling the same backend functions and produce the same underlying data.

## Evidence on Hand

- Working backend producing real output on real and synthetic test images (`test-data/`).
- Detailed, already-approved visual brief for this surface: `UI_PLAN.md` (layout wireframe, full color system, typography scale, interaction/animation timing, explicit do-not list). This document is the visual authority for this redesign — it is treated as the equivalent of a confirmed DESIGN.md brief rather than something to re-derive from scratch.
- Reference products named as the bar to clear: Sartorius Incucyte, Molecular Devices CellXpress.ai, Leica Mateo, CellProfiler Analyst — all dark-theme, image-dominant, card-based lab software.

## Product Principles

1. The image is the hero — analysis chrome (forms, labels, JSON) never competes with it for visual weight.
2. Every result must be traceable: the audit record is always present, even when visually de-emphasized.
3. Status is read by color before it's read by text — a VP glancing at the screen should get the verdict in under a second.
4. This is exception-review software for an automated pipeline, not a bench scientist's daily driver — polish and trust signals (dark "real lab software" aesthetic, no toy defaults) matter more than dense manual controls.
5. Visual work never changes what the backend computes or how the audit chain is built.
