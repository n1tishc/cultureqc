# Product

<!-- impeccable:product-schema 1 -->

## Current Product Direction (2026-10-19)

The React site is `site/src/pages/Home.jsx`, with supporting evidence, records and release-note pages. The approved [standalone design direction](reviews/2026-10-16-v4-standalone-product-design.md) is implemented locally through I1–I3 of the [implementation DAG](specs/standalone-product-site/README.md). The opening is “Read the culture. Understand the next step.” One actual image/result workspace leads into Measure/Understand/Trace, the intended host boundary, scoped evidence and an offline evaluation proposal. Version history is secondary. The [previous upgrade plan](reviews/2026-10-15-vp-demo-upgrade-plan.md) records history.

The default task, **Measure coverage**, shows the real C2C12 mid-density example with its absent calibrated error band. **Understand a review boundary** shows HT29 with its band crossing the target and its evaluation/setup restrictions. Raw image/Segmentation controls annotate stored results; the exact-record link follows the selected example. All seven stored examples remain in More examples and by deep link. Navigation is Product, Evidence, Integration and **Evaluate on your setup**; the last opens the offline plan at `/#pilot`.

The [five-minute script](DEMO_SCRIPT.md) documents these controls and routes, preflight and failure recovery. I1–I3 functional checks and V1 scoped acceptance passed; V2 scoped rendered checks passed, while human screen-reader and real 200% browser-zoom checks remain pending. V3 fresh-reviewer timed rehearsal remains pending. These local checks do not establish deployment parity. The [technical backlog](reviews/2026-10-15-v4-vs-v2-agent-backlog.md) remains applicable.

## Platform

web

## Stack

The product site is React/Vite in `site/`, displaying generated stored outputs. The separate Gradio review console is `demo/app.py`, with live analysis in `demo/analysis.py`. The intended integration entry point is the Python callable `culture.pipeline.analyze()`; the [host evaluation harness](specs/host-evaluation.md) exercises an offline, non-actuating contract. Legacy FastAPI source exists at `deploy/hf-space/api.py`; it is not a v4 integration endpoint. Remote revisions and runtime parity have not been freshly verified; consult the [release-state boundary](specs/release-state.md).

## Users

The site helps lab automation evaluators understand a reading, its limitations, a review boundary and its record. The console supports optional live evaluation. A partner host owns capture, scheduling, identity, signatures, durable retention and physical action. The current workflow proposes a bounded offline evaluation with representative images, independent labels, a target, and a protocol and decision gate frozen before scoring.

## Product Purpose

cultureQC estimates confluency from microscopy images, records scoped checks and an advisory next step, and makes the result traceable. Setup calibration estimates measurement error; it does not validate an action on a partner's instrument. Current local records use schema `0.8` and policy `rules_v0.7`, with `host_actionable: false`. All shipped profiles lack automatic-passage approval.

## Positioning

Lead with actual microscopy, measured coverage, understandable uncertainty and inspectable records. The synthetic-trained QC classifier is demoted: its outputs are recorded but do not decide, and its Grad-CAM boxes are not drawn while demoted. Historical contamination stress tests retain their synthetic-data and scale limitations. They do not establish contamination-detection capability or serve as the current product's main proof.

## Operating Context

- Cellpose-SAM provides confluency; DINOv2 provides an exploratory anomaly check whose calibration is setup-specific. The demoted classifier remains a separate diagnostic output.
- C2C12 has no independent confluency labels in this evidence set and no calibrated confluency error band. EVICAN's observed bias is not a measured C2C12 correction.
- Local Analyze and the library run the C2C12 profile's configured quality gate. Other shipped profiles have no configured quality gate; missing is not passing.
- The seven stored readings retain schema `0.4` / `rules_v0.5` and their original identities. They are historical outputs, not fresh inference or a replay under the current policy.
- The records page preserves the original nine-record chain. A separate, explicitly illustrative extension links a schema `0.8` human-review event to the stored HT29 reading, leaving that reading unchanged. Its fabricated reviewer identity is not a real approval or signature; `final_action: human_review` authorizes no actuation.

## Capabilities and Constraints

- Confluency uses a probability map and, where calibrated, a setup-specific error band; boundary ambiguity is recorded but does not predict measurement error or decide the action.
- Rules `rules_v0.7` evaluate confluency, timing, required checks and explicit decision scope. A calibrated band alone cannot authorize passage; unavailable checks and unknown timing remain explicit.
- Hash verification checks record integrity and linkage, not scientific validity, reviewer identity, signatures or compliance.
- Fine-tuning remains experimental and decides nothing in the shipped workflow. Dense-range failures and the replication limitation remain accessible alongside measured gains.
- Runtime correctness, commercial clearance and production integration remain separate gates. Repository MIT licensing does not clear all model weights or datasets for commercial use.

## Evidence on Hand

The [README results and sources](../README.md#results-and-where-they-come-from), [validation page source](../site/src/pages/ValidationPage.jsx), [host evaluation contract](specs/host-evaluation.md) and [release-state boundary](specs/release-state.md) distinguish measured evidence, historical studies, current local behavior and unresolved work. The current site surface brief is [Home](../site/.impeccable/surfaces/site-src-pages-home-jsx.md).

The superseded console brief is preserved in [historical context](history/2026-09-console-product-brief.md). Its stack assumptions, contamination demonstration, visual authority and presentation-only task restrictions are not current instructions.

## Product Principles

1. The actual image and measured result lead; limits remain visible beside the reading.
2. Every displayed example has a path to its exact record and integrity checks.
3. Text communicates status and available actions; color supports it.
4. Stored, live, illustrative and experimental outputs remain distinguishable.
5. Historical evidence and original readings remain unchanged when presentation or policy evolves.

## Brand commitments

The product's own output leads: real frames, computed layers, measured numbers with sample counts and sources, and the record chain. Keep the scientific presentation and existing design language; T12 does not rebrand the site.
