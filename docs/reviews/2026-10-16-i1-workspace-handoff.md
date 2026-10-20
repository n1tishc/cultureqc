# I1 — Two-task workspace implementation handoff

Date: 2026-10-16. Dependency C0 satisfied. I1 is implemented with scoped functional checks; I2 and the final V1–V3 gates are not complete.

## Changed files

- `site/src/components/Stage.jsx`: default coverage example, independent task buttons, primary Raw/Segmentation controls, honest Custom layers state, visible invalid-link recovery, direct More examples disclosure, preserved exact-record handoff and visible scope. Measurement precedes recommendation; mobile image precedes result. Exported helpers and public props remain compatible.
- `site/src/components/GuidedStage.css`: two-task layout, image-view controls, image-first mobile order, focus treatment and media/selection states.
- `site/src/lib/scenarios.js`: two primary tasks; secondary PC3/synthetic context; explicit invalid selection; shared pure layer-state helpers.
- `site/tests/scenarios.test.js`: default/task contract, all-seven URLs, invalid versus missing query, raw/segmentation/custom/reset state, fixture values and record identity.

No scientific outputs, canonical records, backend/configuration, generated deployment source copies or existing user edits were modified. Build output is local. No commit, merge, push or deployment occurred.

## Acceptance evidence

| Criterion | Evidence |
|---|---|
| I1-A | Browser default and Reset show C2C12 39.41%; boundary shows HT29 52.91%, 23.51–82.31% band. Both task buttons, action/reason, scope and exact-record links present. Fixtures also checked in Node tests. |
| I1-B | Browser Raw removes all overlay attributes; advanced anomaly produces Custom layers with neither primary view falsely selected; Reset on the same sample restores contour-only state. Pure-state tests pass. |
| I1-C | All seven selections and all seven direct URLs resolve to matching exact-record links. Browser Back/Forward restores selection. Campaign query survives. Invalid link explicitly discloses the default fallback; recovery corrects the URL. |
| I1-D | Browser network blocking verifies base-image, contour and both enabled PNG-mask failures and retry. Raw remains usable after contour failure. Deliberately delayed coverage contour cannot replace selected HT29 contour after switching. Stored result identity remains unchanged. Requests have bounded failure handling rather than endless loading. |
| I1-E | Keyboard Enter changes the task and focus outline is present. Polite announcement and native buttons/selected states retained. Mobile DOM geometry at 390×844 confirms image → result → tasks → details, no horizontal overflow; 320px also has no horizontal overflow. Full screen-reader/contrast/zoom and rendered visual acceptance remain V2. |
| I1-F | `node --test site/tests/*.test.js`: 11 passed, 0 failed. Includes existing verification and record-selection regressions. |

`npm --prefix site run build` and `git diff --check` pass. The new fixture test initially used the wrong action token (`continue_culture`); inspection confirmed the actual stored `continue` token and the test was corrected without editing data.

Independent read-only source review found no I1 blockers. Browser checks used local Vite on `http://127.0.0.1:5173`; the existing server was left running. Temporary network blocking/injection was removed and the agent-created test TaskSpace closed.

## Remaining work and limitations

- Desktop screenshot capture failed with `Page.captureScreenshot` timeout; no usable screenshots were produced. DOM geometry is not visual signoff. V2 remains pending, including its desktop/mobile captures and broader accessibility checks.
- I2 owns the surrounding homepage. Its old “Three cases” heading and comparison-first hero still exist; this task intentionally changed only the analysis workspace. Remove those in I2 rather than treating this intermediate page as the approved final presentation.
- I3 evidence/integration work, I4 script, V1 integrated regression/claims gate and V3 timed rehearsal remain pending. Scoped I1 checks do not substitute for them.
- Runtime T03–T09 and readiness/commercial boundaries are unchanged. No new action-validation or contamination-detection capability is implied.
- Ego Lite reports an available update. No browser upgrade was performed; it requires owner approval and is not part of I1.
