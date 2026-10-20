# I2 — Standalone homepage handoff

Date: 2026-10-16. Dependency: I1 implemented. Status: implementation and scoped functional checks complete; rendered visual acceptance remains pending under V2.

## Changes

- `site/src/pages/Home.jsx`: one actual Stage immediately after the proposition. Order: ProductIntro → Stage → Workflow → HostFit → Evidence → compact RecordHandoff → Pilot → technical appendix. Removed comparison table and duplicate full ledger; retained browser verification for Stage and Specs.
- `site/src/components/Journey.jsx`: approved standalone hero; Measure/Understand/Trace; intended host boundary; one qualified MSC calibration finding; compact integrity handoff; offline evaluation proposal. No scientific data changed.
- `site/src/components/Journey.css`: compact hero, responsive workflow and host flow, wrapping evaluation CTA, mobile anchor offset. Removed obsolete comparison styles. Disabled inherited size containment within the homepage frame box: it previously let the image exceed its container and clip into adjacent content.
- `site/src/components/Shell.jsx`: Product → `/#demo`, Evidence → `/validation`, Integration → `/records#integration`, primary Evaluate on your setup → `/#pilot`. Live console is secondary and labelled research. Release history remains in the footer.
- `site/index.html`: standalone title, description and social copy. No asset regeneration or deployment.

## Scientific copy and I3 coordination

Homepage MSC values still come from `data.profiles.items`: 320 images, default MAE 8.19 pp and calibrated MAE 3.43 pp. Source checked: `results/confluency_profiles.md`, leave-one-population-out, calibration fitted on the other two populations. Only four dense-range images; passage criteria unmeasurable. This is a calibration finding, not a release comparison or action-validation claim.

Host capture, scheduling, identity/signatures, durable retention and physical action remain host-owned. The diagram explicitly describes an intended boundary, not a shipped integration. Chain integrity does not establish science or compliance; the stored chain contains no human-review event. I3 must preserve these qualifications in its drilldowns.

## Checks

| Acceptance | Evidence |
|---|---|
| I2-A | Browser geometry at 1280×800: hero ends y=220; full microscopy frame y=233–643; coverage measurement y=290–392, recommendation y=392–550, record ends y=652. Review-boundary record ends below y=743. Image, scope and record fit; no scope text was hidden to achieve this. |
| I2-B | No horizontal page overflow at 390, 320 or 640 CSS pixels; mobile image precedes result and all top-nav controls remain within width. 640px checks reflow equivalent to a 1280px layout at 200% zoom. A separate 2× computed-font/line-height stress check at 1280px showed no horizontal overflow. Native zoom and screenshot-based clipping review remain V2 work. |
| I2-C | Exactly one `.guided-stage`; comparison table and full ledger absent from primary path. Technical appendix retains all legacy targets and auto-opens on deep links. |
| I2-D | Direct navigation to all four page entries works. Shared nav/CTA/footer internal destinations resolve, with Evidence active only on its page. All six moved legacy hashes redirect correctly; all eleven retained legacy targets resolve, including model terms. External live service availability was not asserted. |
| I2-E | Existing fonts/tokens and image assets retained. Source claims checked locally; no invented readiness, ROI, action, review event or production-service claim. Rendered visual signoff remains pending. |

Commands: `node --test site/tests/*.test.js` — 11 passed; `npm --prefix site run build` — passed; `git diff --check` — passed.

Browser: Ego Browser TaskSpace 5, local Vite at `http://127.0.0.1:5173/`. `Page.captureScreenshot` timed out; no usable desktop screenshot was produced and mobile screenshot capture was not retried. DOM/geometry checks are not visual approval. V2 still requires desktop/mobile captures and native zoom inspection.

## Remaining work

I3 evidence/integration drilldowns were completed separately in this pass; see the I3 handoff. I4 presentation/current docs and V1–V3 gates remain pending. This node does not close runtime correctness, commercial clearance or partner evaluation gates. No commit, merge, push or deployment performed; pre-existing edits and canonical output preserved.
