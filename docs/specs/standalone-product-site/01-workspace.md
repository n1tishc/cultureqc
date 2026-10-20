# I1 — Two-task analysis workspace

Dependency: C0. Owner: frontend builder, also owning I2.

Execution status (2026-10-16): implemented; focused tests, build and scoped browser checks pass. See [handoff and remaining acceptance](../../reviews/2026-10-16-i1-workspace-handoff.md). Screenshot capture failed; final visual acceptance remains pending under V2. I2's homepage composition has not started.

Owned files: `site/src/components/Stage.jsx`, `site/src/components/GuidedStage.css`, `site/src/lib/scenarios.js`, `site/tests/scenarios.test.js`. Coordinate any need to edit shared utilities; do not alter their callers casually.

## Implementation

1. Replace the three-step default tour with the two task entries in C0. Remove forced Back/Next progress and step numbering. Use labelled buttons with a selected state; no simulated wizard completion. Keep Reset and an obvious More examples disclosure containing all existing samples.
2. Initial view is the stored image with its existing computed cutoff contour enabled. Expose a primary Raw image / Segmentation control outside advanced details; “Segmentation” means the existing cutoff-contour overlay, not a newly generated mask. Add a short legend. Raw hides every overlay; selecting Segmentation enables the contour and clears other layers. Advanced layer controls reflect the same state; a nonstandard combination is labelled Custom layers, not misleadingly Raw or Segmentation.
3. On selecting/resetting an example, restore contour-only mode and clear sample-specific media errors. Closing More examples need not change selection. A deep-linked advanced example stays selected and named even with the explorer closed.
4. Desktop: image dominates with measurement, recommendation, reason, scope and exact-record link beside it. Mobile: image → compact result → task selector → advanced detail. Keep a single logical control set rather than duplicate interactive desktop/mobile copies.
5. The HT29 band scale labels estimate and target with text; it must not look like an editable threshold. No band is rendered as an explicit absence, never a zero-width certainty band.
6. Preserve exact-record handoff, verification pending/failure semantics, scale bar and existing specialist views. Fetch/asset loading is labelled as loading stored media, not running inference.

## Acceptance

- **I1-A:** Initial load and Reset select C2C12 mid; exactly two primary task buttons exist. Both fixtures match C0, with material qualifications visible before expanding details.
- **I1-B:** Raw/Segmentation switches only visual layers; result values and record identity never change. Custom advanced layers cannot make the primary toggle lie about what is visible.
- **I1-C:** All seven IDs work by selection and direct URL; other query parameters survive. Back/Forward restores the selected sample. Unknown ID produces a visible fallback notice. Missing ID simply selects the default.
- **I1-D:** Switching while contour requests are pending cannot display another sample's contour. Image, contour and other enabled asset failures are explicit, retryable and do not erase result identity; raw image remains usable when only an overlay fails.
- **I1-E:** Selected states, labels, visible focus and a concise polite result announcement work with keyboard/screen reader. No color-only meaning or mandatory motion.
- **I1-F:** Update the existing Node tests (currently asserting three scenarios) to assert two primary IDs, new default, all seven URL cases, invalid selection handling and query preservation. Add pure-state tests if extracting state helpers is warranted; avoid a new framework just for this work.

Handoff: focused test results, changed exports if any, example/state matrix and known browser checks deferred to V2. I1 completing does not mean the new homepage composition is finished.
