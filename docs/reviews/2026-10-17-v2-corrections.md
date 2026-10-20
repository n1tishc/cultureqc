# V2 — Accessibility corrections and bounded confirmation

Date: 2026-10-17. **S1–S6 code corrections implemented and independently reviewed; scoped browser regression passes. V2 still awaits visual/assistive-technology and 200% zoom evidence. V3 remains pending.**

Follow-up: the approved browser update resolved screenshot capture. See [inspected visual evidence and manual handoff](2026-10-17-v2-visual-followup.md). Actual 200% zoom and screen-reader confirmation remain pending; the limitations below describe the earlier run.

This closes the code work returned by the [initial source audit](2026-10-17-v2-source-audit.md), not the full [browser acceptance gate](2026-10-17-v2-browser-acceptance.md). Historical reports remain intact with pointers to this update.

## Correction ownership and scope

One bounded batch, preserving the current design and all pre-existing working-tree changes:

| Finding | Correction | Owner / files |
|---|---|---|
| S1 | Unchecked switch track uses existing `--ink-3`; checked state and thumb position unchanged | Records builder: `site/src/styles.css`, switch background only |
| S2 | JSON reveal uses `auto` under reduced motion, `smooth` otherwise; target calculation unchanged | Records builder: `site/src/components/Records.jsx` |
| S3 | Physical scale exposes one image-role label, “Scale bar: 200 micrometres”; decorative bar hidden; unknown-scale suppression preserved | Root: `site/src/components/Stage.jsx` |
| S4 | Verification text is an atomic polite status region, excluding the hash | Root: `site/src/components/Stage.jsx` |
| S5 | View/recovery controls use defined `--stage-ink-3` border token | Root: `site/src/components/GuidedStage.css` |
| S6 | Fitted mobile navigation overrides both legacy mask properties to `none` | Root: `site/src/components/Journey.css` |

S6 removes the confirmed obsolete computed mask rather than claiming the previous label's visual opacity was measured. No new scientific values, claims, recommendation logic, records or data were introduced. The Records builder's narrow shared-stylesheet assignment was exclusive to the switch background; no concurrent shared-file edits occurred.

Independent reviewer `v1_standards_review` found the six source corrections meet intent, with no remaining source blocker in this batch. This source review does not certify real screen-reader speech or missing rendered images.

## Fresh validation

| Command / check | Result |
|---|---|
| `node --test site/tests/*.test.js` | 11 passed; no failures/skips |
| `npm --prefix site run build` | Passed; all four entries built |
| `node --check site/tests/accessibility.browser.js` | Passed |
| `git diff --check` | Passed |
| Impeccable detector on the five changed UI files | 0 anti-patterns; 27 existing advisory type/color notes, not automatically treated as defects |
| Saved browser regression on local Vite | All six logged groups passed |

No new dependencies or frameworks were installed. Python/scientific regressions were not rerun for this presentation-only batch; V1's earlier results are recorded in its report, not relabelled as fresh results here.

The new browser regression is deliberately separate from the Node `*.test.js` suite:

```sh
ego-browser nodejs < site/tests/accessibility.browser.js
```

Prerequisites: local site at `http://127.0.0.1:5173/`, Ego Lite available. Standalone runs close their task space on success. To reuse an existing agent-owned test space, prepend `const regressionSpaceId = <spaceId>;`; the caller then owns closing that space. The actual confirmation reused TaskSpace 8. This is not a Playwright script or an application dependency.

### Runtime evidence

- Chromium's actual accessibility tree exposes exactly one unignored image node named `Scale bar: 200 micrometres` for default C2C12. HT29 renders no scale bar. Measurement geometry and stored values remain unchanged.
- The verification accessibility node is `status`, with `live=polite` and `atomic=true`. A deliberately pending verification, rejected while Raw image holds focus, becomes an honest unavailable status without moving focus. Actual announcement timing/duplication in a screen reader remains untested.
- Both view controls compute `1px solid` borders with at least 3:1 against their backgrounds. Independent source checks give normal/hover unselected border contrast **5.72:1 / 5.17:1**.
- Unchecked switch computed colors yield **5.83:1** track/paper and **6.30:1** thumb/track. The existing checked colors remain unchanged and above 3:1 in source calculations.
- Instrumented actual `Element.scrollTo` calls from the JSON reveal use `auto` when reduced motion is enabled and `smooth` under normal preference. Keyboard focus stays on the activated checkbox; Reset restores all nine verified records after each test.
- Navigation computes `mask-image: none` at both 390px and 320px. Document width equals viewport width at both sizes in the tested homepage state.
- Browser test instrumentation is temporary. Media emulation, scroll instrumentation and document-start digest rejection are restored/removed; the page reloads with normal verification before leaving the test.

## Confirmation limitations — do not mark V2 passed

The one allowed desktop/mobile screenshot confirmation batch was attempted after corrections, using `raw: true` to avoid wrapper scaling. Both calls still timed out at `Page.captureScreenshot`:

| Attempted location | Observed pre-capture viewport | Result |
|---|---|---|
| `/tmp/cultureqc-v2-confirm-desktop.png` | 1280 × 800; default C2C12 | Timeout; no usable image |
| `/tmp/cultureqc-v2-confirm-mobile.png` | 390 × 844; default C2C12 | Timeout; no usable image |

These paths are not delivered visual evidence. No screenshot was inspected or claimed as passing. Do not keep retrying/polishing in this cycle. HT29/layer captures, complete rendered contrast/legibility and visual first-view acceptance remain outstanding.

A native zoom shortcut attempt (reset, five increase shortcuts, then reset in `finally`) did not change measured width or device-pixel ratio: 390px and DPR 2 before and after. Therefore **200% zoom is not verified**; narrow viewport checks are not substituted for it.

The selector-based summary click again reported an intercepted pointer event during automation scrolling. Subsequent hit testing identified the intended summary at its centre. A single native pointer click at that inspected location **successfully opened the disclosure**. The control is actionable in that tested state; the selector/scroll wrapper still fails. This narrow result is not a full visual/pointer acceptance sweep.

Ego Lite still reports `0.5.1.13` with an update available. No upgrade was authorized or performed. An update may help the tooling but is not guaranteed to resolve capture or zoom.

## Next step and preservation

1. Obtain actual desktop/mobile and HT29/layer captures, 200% zoom/reflow and assistive-technology announcement confirmation through a working browser or explicit manual review. Browser repair/update requires user approval where applicable.
2. Resolve any newly demonstrated acceptance defect as explicit follow-up; do not perform an unbounded cosmetic pass. The six source corrections need no speculative redesign.
3. Only after V2 passes, run V3's actual timed presenter/fresh-reviewer rehearsal.

Protected tracked backend, scientific reports, assets, policies and deployment mirrors still match HEAD. The known pre-existing `site/src/data.json` addition remains 12 lines. No commit, merge, push, deployment, commercial clearance or live action occurred. TaskSpace 8 closed successfully with no retained pages. The local Vite server remains running.
