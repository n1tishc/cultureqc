# V2 independent source accessibility audit

Date: 2026-10-17. Reviewer: independent standards/regression agent, not an implementation owner.

## Status and scope

Update: the [S1–S6 correction and confirmation record](2026-10-17-v2-corrections.md) supersedes the open code-fix status below. Original findings are retained as history; visual/assistive-technology acceptance remains pending.

**Source review complete; V2 is not passed.** This review makes no runtime, screenshot, assistive-technology or visual acceptance claim. No overall audit score is assigned without rendered evidence. The orchestrator owns the separate browser report and DAG status.

Reviewed the working-tree workspace, shared navigation/styles, record controls and secondary technical views against [C0](../specs/standalone-product-site/00-contracts.md), [V2 acceptance](../specs/standalone-product-site/05-acceptance.md), `docs/DESIGN.md` and the Impeccable audit playbook. No UI source, scientific data, records, configuration or generated deployment files were edited by this review.

The orchestrator reports that desktop and mobile screenshot capture both timed out. It also confirmed the mobile navigation mask remains in the computed style at 390px. Those observations do not establish whether the rendered label remains legible.

## Prioritized fix packets

P1 denotes a major acceptance risk to address before signoff; P2 denotes a bounded accessibility/implementation defect or follow-up. Source-derived ratios below are not a completed rendered contrast audit. Check the actual computed colors, surrounding surfaces, browser appearance and relevant states during acceptance.

### V2-S1 — P1: unchecked tamper-control contrast

- Acceptance area: V2 Adaptation; specified 3:1 control-boundary contrast, relevant to WCAG 1.4.11.
- Location: `site/src/styles.css:1718` and `site/src/styles.css:1730`.
- Reproduction: open `/records#chain`, leave the tamper switches unchecked, and inspect the switch track and thumb.
- Expected: control/state boundaries needed to identify the switch remain distinguishable at at least 3:1.
- Source actual: unchecked track uses `--rule-2` (`#c8cfd7`); paper is `#f5f6f8`; thumb is `#ffffff`. The source declares no contrasting border for the track. Track/paper is **1.45:1**, thumb/track is **1.57:1**. These are opaque sRGB token calculations, not screenshot measurements; the thumb shadow and browser rendering are not included.
- Bounded fix: give the inactive track and/or required boundary a contrast-checked treatment, preserving the existing design world and positional checked-state cue. Do not change tamper behavior or record data.
- Acceptance: inspect checked, unchecked and focused controls on their actual surfaces; record at least 3:1 for the necessary visual boundaries. Keyboard Space must still toggle the labelled checkbox, and all three tamper modes/reset must retain their existing verification behavior.

### V2-S2 — P2: JSON scrolling ignores reduced motion

- Acceptance area: V2 Adaptation, reduced-motion preference.
- Location: `site/src/components/Records.jsx:39`.
- Reproduction: enable reduced motion, open an exact record, and activate a tamper mode that highlights a changed field.
- Expected: reveal the changed field without forced animated scrolling when reduced motion is requested.
- Source actual: the JSON effect calls `scrollTo` with explicit `behavior: "smooth"`; the stylesheet's `html { scroll-behavior: auto; }` media rule cannot override that explicit JavaScript option.
- Bounded fix: use `auto` when `matchMedia("(prefers-reduced-motion: reduce)").matches`, retaining the same target position and normal-preference behavior.
- Acceptance: under reduced motion the changed field is revealed without smooth scrolling; under normal preference it remains revealed correctly. Focus and the selected record do not change as a side effect.

### V2-S3 — P2: the physical scale label is hidden from assistive technology

- Acceptance area: V2 Accessibility, labelled scale and non-text information equivalence.
- Location: `site/src/components/Stage.jsx:145`.
- Reproduction: inspect the accessibility representation of a C2C12 image with a known pixel scale.
- Expected: the visible physical scale has an accessible textual equivalent.
- Source actual: `aria-hidden="true"` covers the entire `ScaleBar`, including its only `200 µm` label. The microscopy image alt does not contain that scale information.
- Bounded fix: expose a concise textual scale label while hiding only decorative bar geometry, or provide an equivalent associated image description. Preserve the existing calculation from `umPerPx`, `widthPx` and `um`.
- Acceptance: a screen-reader/accessibility-tree check exposes the correct scale once for known-scale images. EVICAN images with unknown pixel scale still have no invented scale bar or scale announcement. Visual scale geometry must remain unchanged.

### V2-S4 — P2: workspace verification changes lack a live announcement

- Acceptance area: V2 Accessibility, status feedback; WCAG 4.1.3 risk.
- Location: `site/src/components/Stage.jsx:200`.
- Reproduction: delay or reject initial verification while focus stays on another workspace control.
- Expected: the later verification outcome is available as a concise status announcement without moving focus.
- Source actual: `VerifyLine` changes its pending/result/error text without a live region. The separate analysis-result announcement reports the specimen, action and confluency, not verification. The Records page already has a separate live verdict region.
- Bounded fix: give verification text a suitable polite status region; do not make the entire hash/record block repeatedly announce. Preserve pending, mismatch and unavailable wording and avoid any premature success announcement.
- Acceptance: delayed success and forced verification failure each produce understandable, non-duplicated feedback in an assistive-technology check. Failure never says a match was confirmed; keyboard focus remains stable.

### V2-S5 — P2: undefined primary-control border token

- Acceptance area: V2 Accessibility/Adaptation, visible controls and focus/state clarity.
- Location: `site/src/components/GuidedStage.css:51`.
- Reproduction: inspect computed borders for Raw image, Segmentation and the invalid-selection recovery button.
- Expected: the authored border resolves to an intentional, contrast-checked style in selected and unselected states.
- Source actual: the border shorthand uses `var(--stage-rule-2)`, but that property is not defined in the reviewed stylesheets. The declaration is therefore invalid at computed-value time. A later selected-state `border-color` does not itself provide a border style.
- Bounded fix: define an intentional contrast-checked token or use a suitable existing token/fallback. The documented `#3d4652` candidate would be only **1.92:1** against `--stage-2` (`#11151a`), so merely adding that value is not evidence of satisfying the requested 3:1 control-boundary criterion.
- Acceptance: verify the computed border is present and intentional, relevant boundaries meet the stated criterion, selected state remains understandable, and the visible focus ring is not clipped. Raw/Segmentation output values and record identity remain unchanged.

### V2-S6 — P2 risk: mobile navigation retains an obsolete fade mask

- Acceptance area: V2 Navigation/Adaptation, text and focus legibility.
- Location: `site/src/styles.css:2761` and `site/src/components/Journey.css:91`.
- Reproduction: inspect the rightmost Integration link at 390px and 320px, including keyboard focus.
- Expected: a fitting, non-scrolling navigation row does not fade its final link or focus indicator.
- Source actual: the legacy <=640px mask fades the final 40px of `.nav`, while the newer layout uses `overflow: visible` and `justify-content: space-between`. The orchestrator confirmed that the mask persists in computed style at 390px. Its effect on actual label legibility is **not visually verified**.
- Bounded fix if the risk is confirmed: remove/override the scrolling affordance mask for the fitted navigation layout, including the prefixed property; retain navigation order and wrapping.
- Acceptance: inspect actual captures at both widths; all three links and their focus rings remain legible, with no horizontal page overflow. Normal text must meet 4.5:1 after any compositing/masking.

## Secondary follow-up, outside primary-journey blockers

Closed by the [technical-selector keyboard follow-up](2026-10-17-technical-controls.md): native labelled button groups, pressed states, preserved styling and browser keyboard regression. The original finding follows for history.

`site/src/components/Timeline.jsx:211` and `site/src/components/DenseTest.jsx:194` use tablist/tab roles without a complete tab keyboard/panel-association pattern. Their native buttons still support Tab and activation, so this source review does not claim the controls are unusable. In a separate bounded pass, either implement consistent tab semantics or use ordinary labelled button groups with pressed states. Verify the resulting keyboard behavior rather than adding ARIA alone.

## Positive source evidence

- Primary task and view controls are native buttons with labelled states; disclosures use native details/summary.
- The primary workspace has a single logical image/result/control order and explicit focus-visible rules.
- Analysis-result and media-error/status announcements are present. Band values and target have textual equivalents; missing calibration is stated rather than drawn as a zero-width band.
- Timeline autoplay checks the reduced-motion preference; CSS disables smooth document scrolling under that preference. The explicit JSON scroll is the identified exception.
- Examined opaque text-token pairs meet 4.5:1: `#86919d` on `#1a1f26` **5.17:1**; `#04707f` on `#f5f6f8` **5.35:1**; `#56616e` on `#f5f6f8` **5.83:1**. These spot checks do not certify every rendered text/state combination.

## Detector evidence

Read-only command, from the repository root:

```sh
/Users/nitishc/.agents/skills/impeccable/scripts/impeccable detect \
  site/src/components/Stage.jsx \
  site/src/components/GuidedStage.css \
  site/src/components/Journey.css \
  site/src/components/Records.jsx \
  site/src/styles.css
```

Result: exit code 0, **0 anti-patterns found; 27 advisory notes**. Advisories concern documented type-ramp deviations and literal colors. They are not automatic defects or permission to change the approved visual direction. Black microscopy/contact/scale treatments and inherited technical-chart/code colors must be interpreted in their documented context, not mechanically removed.

The detector did not establish runtime accessibility, resolve the missing screenshots, or invalidate the manually identified source findings.

## Handoff and acceptance boundary

Batch only confirmed fixes, preserving scientific fixtures, source claims, exact-record handoffs and the approved standalone-product layout. Re-run focused tests/build after implementation changes, then perform one bounded confirmation batch for affected visual/keyboard states. If screenshots or assistive-technology evidence remain unavailable, record that limitation and leave the corresponding acceptance pending. V3 must not be marked complete on the strength of this source audit.
