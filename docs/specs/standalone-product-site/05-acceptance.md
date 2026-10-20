# V1–V3 — Independent acceptance gates

Owner: reviewer independent of implementation. Do not fix shared files while builders own them; return defects with acceptance ID, reproduction, expected/actual and severity. Record results in a new dated report under `docs/reviews/`, linked from the DAG status table when execution begins.

## V1 — Build, regression and claims

Dependencies: I2 and I3. I4 may run in parallel.

From repository root, use the installed project environment:

```sh
node --test site/tests/*.test.js
npm --prefix site run build
python -m pytest -q tests/test_demo_examples.py tests/test_demo_replays.py tests/test_claims.py tests/test_records_chain.py
git diff --check
```

The Python command is a scoped regression check, not a requirement to download missing models or launch new inference. Report environment failures/skips with reasons; they are not passes. Do not use `npm test` (no current script), install a new test framework, or assume previous-turn test results validate new changes.

- **V1-A:** Node scenario tests cover the new default/two tasks, all seven IDs, invalid selection and query preservation; record selection and verification suites still pass. Build succeeds.
- **V1-B:** Review I3's claim ledger against working-tree sources and C0. Spot-check both primary fixtures, band absence, HT29 scope, evidence protocol and current callable.
- **V1-C:** Diff shows no scientific artifact, canonical record, policy/configuration, generated deployment copy or unrelated user edit was altered by these nodes. Compare against implementation-start baseline, not a blanket clean-tree expectation.
- **V1-D:** Link inventory includes all C0 destinations and legacy anchors. Record test limitations and environmental gaps; remedy or explicitly narrow the affected gate before proceeding.

## V2 — Browser, accessibility and visual gate

Dependencies: V1 and I4. Use the local site; no deployment needed. Start a server only if the existing one is unavailable. Capture both desktop 1280×800 and mobile 390×844 in one inspection batch; inspect actual rendered images, not only DOM geometry.

| Check | Required evidence |
|---|---|
| Default first view | Desktop screenshot with hero + actual microscopy/result; mobile image/result order; no comparison table |
| Both tasks | Screenshots showing measurement, recommendation/reason and relevant qualifications; HT29 annotated band |
| Layer interaction | Raw, segmentation, custom-layer state and reset; outputs/identity unchanged |
| Selection | All seven IDs via More examples and URLs; unknown-ID notice; unrelated query survives; Back/Forward restores |
| Exact records | Both primary links select the correct record; local tamper/reset; forced verification failure says unavailable, not verified |
| Async errors | Delayed contour then sample switch; missing image/contour/enabled layer; visible retry; no stale or substituted media |
| Navigation | Four page entries and C0 legacy URLs; collapsed legacy targets open; return from Records works |
| Accessibility | Keyboard-only journey, no trap, visible focus, selected control states, concise live announcements, labelled scale/target and status text |
| Adaptation | No horizontal page overflow at 390px/320px; 200% text zoom/reflow; reduced-motion preference; readable contrast (4.5:1 normal text, 3:1 large text/control boundaries) |

Save screenshot locations, browser/viewport, sample ID and observed results in the report. No request timeouts or blank screenshots count as visual evidence. If capture fails, finish independent functional checks but leave V2 and therefore V3 pending. Inspect once, correct defects in a batch with the owner, confirm at most once; remaining defects require explicit follow-up, not endless polishing.

## V3 — VP rehearsal and handoff

Dependency: V2.

- **V3-A:** Run I4 from its starting state in five minutes, excluding Q&A, and record actual elapsed time and any detours. A written timeline is not a rehearsal result.
- **V3-B:** A fresh reviewer can answer: What goes in/out? Why review HT29? Who controls physical action? What does the record prove? What is needed to evaluate a new setup? They do not need to hear about v2. Record reviewer feedback, not an invented user-study score.
- **V3-C:** Report completed nodes, checks and screenshot paths, unresolved runtime/readiness issues, and any remaining defect. No claim that a partner pilot, commercial clearance, production integration or deployment has occurred.

Incorrect source values, hidden material qualifications, broken exact-record links, silent sample substitution, inaccessible primary controls and verification false success are blockers. Cosmetic observations may be recorded separately only if acceptance criteria still pass. If no fresh reviewer/presenter is available, report that human acceptance as pending rather than simulating it.
