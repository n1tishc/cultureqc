# Technical selectors — keyboard follow-up

Status: **Implemented and checked.** This closes the secondary control-pattern finding in the [V2 source audit](2026-10-17-v2-source-audit.md), not the outstanding human screen-reader/200% zoom acceptance or V3 rehearsal.

## Changes

- `Timeline.jsx`: replay choices are native buttons within the labelled “Replayed flasks” group, with exactly one `aria-pressed` state. Removed incomplete tab semantics.
- `DenseTest.jsx`: imaging-setup choices use the same group/button pattern; the two reading figures form a group named for their selected setup rather than an unassociated tab panel.
- `styles.css`: the two selected-state selectors now match `aria-pressed`; visual values and layout are unchanged.
- Keyboard contract: Tab/Shift+Tab traverse ordinary buttons; Enter/Space activate them without moving focus. These selectors do not advertise arrow-key tab navigation. Timeline's separate visit-arrow behavior is unchanged.

## Defect found while testing

Switching from a 15-visit replay to a 14-visit replay could render with the previous out-of-range visit index before the reset effect ran. The browser regression initially timed out and inspection showed an empty application root.

The scenario activation now batches the new scenario and its last valid visit together. React therefore does not render the shorter replay with the old index. Reactivating the already-selected scenario preserves the manually selected visit. Stored scientific values, replay data and forecast logic are unchanged.

## Fresh verification

- `node --test site/tests/*.test.js`: 11 passed, zero failures.
- `npm --prefix site run build`: passed, all four page entries.
- `node --check site/tests/technical-controls.browser.js`: passed.
- `git diff --check`: passed.
- New browser regression: all five replay choices and four imaging setups pass Tab traversal, Enter/Space activation, single pressed state, selected styling, visible keyboard focus, retained focus, matching output identity, and leaving/re-entering each group. Includes longer-to-shorter replay switching and preserving the chosen visit when reactivating the current flask.
- Independent read-only reviewer `v1_standards_review`: no application blocker in this change.

Run the browser regression with the existing server at `http://127.0.0.1:5173/`:

```sh
ego-browser nodejs < site/tests/technical-controls.browser.js
```

The actual test reused TaskSpace 1 by prepending `const regressionSpaceId = 1;`. Reduced-motion emulation is removed in `finally`. A standalone successful run closes its own space; a reused space remains the caller's responsibility.

One desktop/mobile image batch was captured and inspected after the fixes. Selected styling and focus outlines remain visible. Imaging setup buttons wrap on mobile; replay choices retain their existing horizontal control-row scrolling. There was no horizontal document overflow at either checked width.

| Surface | Desktop 1280×800 | Mobile 390×844 |
|---|---|---|
| Replay selector | [Image](assets/2026-10-17-v2/controls-timeline-desktop.png) | [Image](assets/2026-10-17-v2/controls-timeline-mobile.png) |
| Imaging setup | [Image](assets/2026-10-17-v2/controls-setup-desktop.png) | [Image](assets/2026-10-17-v2/controls-setup-mobile.png) |

## Limits and preservation

The user elected to keep real screen-reader verification pending. Neither these keyboard checks nor screenshots certify speech or actual 200% zoom. V2 remains open and V3 has not run. No new dependency, scientific artifact, generated deployment copy, commit or deployment was introduced. Protected tracked scientific/backend paths match HEAD; the pre-existing 12-line `site/src/data.json` addition is untouched. The local demo remains available.

The separate test-harness cleanup follow-up is now closed by the [code-first follow-up](2026-10-17-demo-code-followup.md). The technical-controls regression itself does not inject or override digest behavior.
