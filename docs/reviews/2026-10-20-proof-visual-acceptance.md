# T12 — Post-update visual acceptance

Status: scoped review-section visual checks pass locally. Human screen-reader
and actual 200% zoom verification remain pending; V3 remains gated on them.

## Scope and evidence

The owner approved the Ego Lite update. `ego-browser upgrade` reported the update
installed and restarted the browser; the usage guide was re-read afterward.
The existing local demo at `http://127.0.0.1:5173/` was used, not a public deploy.
Standard screenshot capture now works. These four fresh captures were opened
and visually inspected at 1440 × 1000 and 390 × 1000 CSS pixels, device scale 1,
with reduced motion:

| Capture | Observation |
|---|---|
| [Desktop review](assets/2026-10-20-t12/review-desktop.png) | Clear two-column heading/disclosure, visible original-reading link, legible verification status and JSON disclosure |
| [Desktop expanded JSON](assets/2026-10-20-t12/review-desktop-expanded.png) | JSON stays in its dark pane, with surrounding explanation and return link intact |
| [Mobile review](assets/2026-10-20-t12/review-mobile.png) | Single-column wrapping, visible disclaimer and original-reading link; sticky navigation does not cover the review heading |
| [Mobile expanded JSON](assets/2026-10-20-t12/review-mobile-expanded.png) | Narrow pane contains long JSON lines rather than widening the document; horizontal scrolling is intentional inside the pane |

No blocking layout defect was found in this scoped inspection. The review is
still explicitly fictional, preserves `human_review`, and does not claim an
authenticated signature, scientific validity or an approved physical action.
This is not a whole-site accessibility/performance audit or a physical-device test.

## Interaction and regression

The generic chain CTA was retested after returning from the exact HT29 reading
to its homepage sample. Selector-based pointer clicks and automatic browser
scrolling reached `/records#chain` at both widths without explicit scrolling.
The old coordinate/scroll workaround was removed from
`site/tests/proof-pointer.browser.js`; its URL assertion is now explicit.

| Validation | Result |
|---|---|
| Full saved pointer regression after removing workaround | Passed at 1440px and 390px: sample selection, exact record, review expand/collapse, original/sample return and generic chain CTA |
| `node --check site/tests/proof-pointer.browser.js` | Passed |
| `node --test site/tests/*.test.js` | 15 passed |
| `git diff --check` | Passed |

No new Python suite or production build was needed for this browser-test/documentation
change; prior implementation checks remain recorded in the original T12 handoff.

The earlier [pointer follow-up](2026-10-20-proof-pointer-followup.md) remains the
historical record of the pre-update capture failure and workaround. This record
supersedes its screenshot and chain-link retest gates, not its human gates.

## Remaining work

1. Keep human screen-reader verification pending: sample changes should announce
   the result once without moving focus. Actual 200% browser zoom is also pending.
2. Run V3's timed presenter/reviewer walkthrough only after those acceptance
   gates close. Use `docs/DEMO_SCRIPT.md`; lead with confluency and traceability,
   not a homepage version-comparison scoreboard.
3. T02 remains partial: cached EVICAN and C2C12 policy replays do not replace
   independent labels, authenticated model provenance or approved pilot evidence.
4. Commit, push and deployment still require explicit owner approval.

No product UI, model thresholds, historical records or generated scientific
evidence changed in this follow-up. Screenshot artifacts, the browser regression
and handoff documentation are the only repository changes for this step.
