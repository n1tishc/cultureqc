# VP demo and website upgrade plan

Date: 2026-10-15. Implementation status updated after owner approval of the complete journey, comparison first.

## Implementation status

W1–W4 are implemented locally: comparison-first homepage, three-scenario walkthrough plus all seven stored examples, exact record handoff and local tamper/reset, evidence/limits panel, pilot proposal and five-minute script. Scientific results and canonical records are unchanged; only the obsolete display tooltip was regenerated. Runtime policy and deployment are unchanged.

W5 functional checks cover scenario navigation/history, exact HT29 record selection, tamper/reset, invalid record fallback, legacy timeline disclosure, desktop result position and mobile navigation/overflow. The production build, eight JavaScript tests and 70 targeted Python tests pass. Generated Space copies match the root tooltip source.

Independent implementation review found a false-success verification explanation and missing screen-reader transition feedback; both received targeted fixes and regression checks. Current visual acceptance remains pending: browser screenshot requests repeatedly timed out after a browser reset, and native capture was blank. DOM/geometry evidence is not visual signoff. A timed five-minute rehearsal is also still required before the VP presentation. No live inference or deployment was performed.

The specification below records the approved direction and remains the acceptance reference, not a claim that visual validation or backend correctness work is complete.

Companion documents: [technical review](2026-10-15-v4-vs-v2-vp-review.md), [correctness backlog](2026-10-15-v4-vs-v2-agent-backlog.md), [reproductions](2026-10-15-v4-vs-v2-evidence.md).

## Executive direction

**Change the experience from “explore our pipeline” to “inspect the evidence and decide whether to sponsor a bounded evaluation.”**

Keep the scientific identity: actual microscopy, cyan segmentation, restrained typography, dark image stages on a light reading surface. Do not replace it with generic AI gradients, decorative dashboards, fabricated customer logos, or claims of production readiness.

The main upgrade is not that v4 has more controls. It is that v4 better distinguishes measured capability from unsupported decisions. The site must make that improvement understandable before discussing model names or internal arithmetic.

Proposed opening copy, subject to owner approval:

> From a confluency reading to a decision you can inspect.
>
> v4 adds setup-specific calibration, measured uncertainty and a stronger decision record. Explore what changed since v2, where a person still decides, and what we need to test on your instrument.

Primary action: **Walk through the evidence**. Secondary: **Open live console**. Closing action: **Review the pilot plan**. The pilot link must lead to a real plan, not an invented contact form or unsupported submission backend.

## Homepage structure

| Order | Section | VP question answered | Required content |
|---|---|---|---|
| 1 | Proposition and compact result | What is this, and why should I care? | Image, reading, action, reason, setup/scope and stored/live label visible together |
| 2 | What changed since v2 | Why another meeting? | Three rows: measurement evidence, decision boundaries, traceability; link each to supporting evidence |
| 3 | Guided evidence walkthrough | Does the behavior make sense? | Three named scenarios; next/back/reset; advanced layers collapsed initially |
| 4 | Evidence and its limits | How much confidence is earned? | Dataset/protocol/n beside every metric; dense-range limitations beside overall error; shipped versus experimental distinction |
| 5 | Inspect one decision record | Could my team investigate this later? | Selected reading linked to its exact record; verification and reversible local tamper demonstration |
| 6 | Proposed pilot | What do you need from us? | One setup, labelled images, frozen evaluation, responsibilities, outputs and go/no-go measures |

Move detailed architecture, replay timelines, model mechanics and release history into evidence drill-downs. Do not delete them. Keep validation and records directly addressable for technical reviewers.

Suggested navigation: **Demo · Evidence · Records · Pilot**. Put release notes under Evidence or in the footer. Preserve old deep links. Desktop and mobile must expose the same core destinations without a hidden horizontal-nav dependency.

## The five-minute core demo

| Time | Screen/action | Message |
|---|---|---|
| 0:00–0:35 | Three-row v2/v4 comparison | v2 established the workflow; real-data evaluation exposed weaknesses; v4 improves calibration, uncertainty and provenance |
| 0:35–1:35 | EVICAN HT29 boundary example | Stored reading 52.91%, error band 23.51–82.31%, target 80%; the band crosses the target, so the rules request human review |
| 1:35–2:05 | Sparse EVICAN PC3 | Stored reading 6.60%, band 0–36%, target 80%; explain the stored continue recommendation and its research scope, not universal safe clearance |
| 2:05–2:35 | Image-quality exception | Show why the workflow asks for another image; do not call an oversized synthetic contamination stress test a realistic contamination success |
| 2:35–3:25 | Exact selected record | Identify input/profile/policy, verify integrity, alter a local demonstration copy, show failure, reset |
| 3:25–4:10 | Evidence panel | Show MSC calibration evidence and the unresolved dense decision-range limitation; optional fine-tuning belongs in technical Q&A |
| 4:10–5:00 | Pilot card | Ask for one-setup offline evaluation; agree evidence, responsibility and stop/go criteria before any host actuation |

The HT29 example demonstrates the uncertainty workflow, not general biological validity. Its mixed-setup EVICAN evaluation is not fully blind, and its anomaly reference bank is not calibrated for HT29. Keep these qualifications at the point of use.

Existing stored examples contain a reimage case with oversized simulated bacteria, not a clean ordinary blur/exposure vignette. For the core demo, either label that exact stress test prominently or generate and verify a separate quality-only example using the actual pipeline. Never assign a reimage outcome to a convenient image in frontend code.

Live inference is optional corroboration, not the backbone of the presentation. Make its queue/loading/failure state explicit and keep a labelled stored fallback. A fallback must never be presented as the live result. Retain the longer current demo script as a technical appendix, not the required opening experience.

## Honest v2 → v4 proof block

| Dimension | v2 | v4 | Operational interpretation |
|---|---|---|---|
| Measurement | Synthetic headline plus default cutoff | Real-image evaluation and setup calibration | A more credible way to evaluate the partner's microscope; not a cross-version accuracy percentage |
| Decision policy | Classifier and weak confidence signals drove review | Failed signals demoted; setup error bands inform decision boundaries | Clearer reasons to defer; useful automation coverage still needs measurement |
| Traceability | Hash-chained readings already existed | Additional review/change event types and more provenance | Better investigation support, not a claim that v2 lacked audit records or that v4 is compliant on its own |

Do not render a numerical before/after chart across incompatible datasets. The MSC 8.19 → 3.43 pp result is a calibration comparison within v4's evaluation, not “v2 versus v4.” Label it accordingly.

## Decision-stage design contract

- Keep image and a compact result summary together at desktop presentation sizes, including 1280×800. On mobile, put the summary before advanced controls; do not force a visitor through model details to find the recommendation.
- Summary fields: scenario name, stored/live state, confluency, setup-level error band or explicit absence, target, recommended action, reason, and research/unsupported-scope status.
- Use **scenario labels**, not only cell-line IDs: “Boundary: a person decides,” “Sparse: continue recommendation,” “Image quality: capture again.” Scientific labels remain adjacent.
- Do not label a missing band as low uncertainty. Do not label “not flagged” as healthy or contamination-free.
- Put model names, raw anomaly distances, borderline-pixel arithmetic and SHA strings behind labelled details. Keep the exact values inspectable.
- Keep annotation controls keyboard-operable and understandable without hover; show focus and selected states. Never depend on status color alone.
- Make each scenario shareable with a stable URL and explicit initial state. Switching scenarios resets transient overlays predictably, without rewriting stored records.
- Add an exact record destination that preserves the chosen reading. The existing stage's `href="#records"` is not sufficient for the separate records route.
- Distinguish three independent labels: **stored/live execution**, **shipped/experimental model**, and **calibration/action eligibility**. A single green “validated” badge must not stand in for all three.

## What the pilot card must contain

**Partner provides:** imaging setup description, intended decision target, representative images spanning the intended density range, and an agreed independent annotation process.

**Project provides:** frozen comparison protocol, setup calibration, held-out results, explicit exception/decision coverage, replayable artifacts and a stop/gather-more/proceed recommendation.

**Measure:** early passage, missed readiness, review and reimage separately, useful decided coverage, setup-specific error, end-to-end latency and operator time. Reduced work and savings are hypotheses until measured.

**Boundary:** offline first; shadow evaluation only after the relevant correctness issues are addressed; no vessel actuation. Sample size, schedule, budget and acceptance thresholds require agreement, not invented website promises.

**Separate gate:** commercial-use clearance and host integration remain unresolved. Qualify the MIT label as repository-code licensing, not clearance of the assembled model pipeline. This is based on the repository's existing disclosure, not a new legal assessment.

## Implementation slices and acceptance tests

### W1 — Proposition and upgrade story

Owner: frontend/content agent. Depends on owner approval of the proposed story, not backend changes. Maps to T01/T11 in the correctness backlog.

Files: `site/src/pages/Home.jsx`, `site/src/components/Shell.jsx`, `site/src/components/Sections.jsx`, `docs/DEMO_SCRIPT.md`.

Acceptance: in a short comprehension check, a new viewer can state what changed, what remains unproved and what the pilot asks for. All comparison claims link to source/protocol; unsupported ROI and speedup claims are absent. The demo core fits five minutes in a rehearsal.

### W2 — Guided decision stage

Owner: frontend interaction agent, after W1's content contract. Maps to T01/T12.

Files: `site/src/components/Stage.jsx`, `site/src/pages/Home.jsx`, `site/src/styles.css`, generated example metadata only through its builder.

Acceptance: desktop and mobile show action/reason before optional mechanics; next/back/reset and direct scenario links work; keyboard focus is visible; stored labels survive every transition. Outputs remain identical to source records. No fabricated passage success or mutated historical artifacts.

### W3 — Traceability and factual repairs

Owner: focused correctness/QA agent. Can start independently of W1/W2. Maps to T11/T12; do not silently take on backend T03–T09.

Files: stage record link, records-page selection, route handling, `site/assets/build_data.py`, the source of `AMBIGUITY_TOOLTIP`, applicable product/demo docs.

Acceptance: every scenario opens the exact intended record; back/deep-link navigation works; local tampering is clearly demonstration-only and reset restores verification. The tooltip no longer describes ambiguity as an active review trigger under rules_v0.5. Fix the current-display derivation, not canonical historical record bytes. Document the distinction if historical wording must remain visible.

If a human-review event is demonstrated, create a separately identified generated fixture with its parent hash and explicit demo identity. Do not invent a real reviewer approval or imply that the current seven-reading/two-change chain already contains a review event.

### W4 — Evidence and pilot panel

Owner: evidence/content agent after W1. Maps to T02/T10 for future experiments; this slice presents existing evidence only.

Acceptance: overall and dense-subset results are not mixed; failed criteria stay beside gains; fine-tuning remains experimental and decides nothing. Pilot responsibilities and unknowns are explicit. No matched end-to-end v2/v4 result is implied before that experiment exists.

### W5 — Presentation hardening

Owner: QA agent after W1–W4. One batched desktop/mobile inspection, one fix batch, one confirmation pass.

Acceptance: 1280×800 and 390×844 journeys, keyboard flow, readable zoom, reduced motion, missing assets, failed verification and unavailable live console are checked. Existing verifier tests and production build pass. Do not add a new broad testing stack merely for this review.

## Token-conscious agent orchestration

Use a stronger reasoning agent for narrative/evidence reconciliation; a smaller agent for bounded link, source and responsive checks. Assign disjoint file ownership before implementation. Do not ask every agent to reread the whole repository. Pass a compact content contract and relevant source paths instead.

Run W3 independently while the owner resolves W1 direction. W2 waits for the content contract; W4 shares that contract rather than reinterpreting the claims. One integrator reviews cross-page consistency and runs the final batched checks. Do not launch parallel agents that all edit Home, Stage or the same generated data.

## Not part of this presentation upgrade

No retraining, new benchmark claims, backend-policy changes, model replacement, commercial approval, hosting migration or deployment. Correctness findings T03–T09 remain separate work and must be disclosed, not disguised by polished UI. Do not revive the retired detector or temporal features to make the demo appear broader.
