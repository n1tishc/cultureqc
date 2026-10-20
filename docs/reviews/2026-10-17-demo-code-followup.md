# Local demo: code-first follow-up

Status: **Recorded demo test-harness follow-ups resolved; human acceptance and backend correctness remain pending.** No VP rehearsal performed.

## Changes

- `site/tests/accessibility.browser.js`: removing the document-start digest mock now explicitly reloads the document, asserts that the mock's window property is absent, and waits for successful real record verification before reporting success. This cleanup also runs when the injected-failure assertions throw.
- `site/tests/media-reset.browser.js`: only finishes a task space it creates. A caller-provided `regressionSpaceId` remains open for subsequent checks and user review, matching the other saved regressions.
- No application code, dependencies, stored measurements or backend behavior changed in this follow-up.

## Evidence and limits

The new mock-absence assertion was first run against the previous same-URL navigation cleanup and passed on the installed Ego version. The suspected stale mock was therefore **not reproduced** in this run. The explicit reload is defensive hardening with a checked postcondition, not a newly demonstrated production defect.

The media test previously called `task.finish()` unconditionally, even when using a caller-provided space. After the ownership guard, the accessibility, media and technical-controls scripts all passed sequentially in the same TaskSpace 1. The third script successfully reused the space after the media test, directly checking the lifecycle fix without closing the user's demo.

Fresh checks:

- `node --test site/tests/*.test.js`: 11 passed, zero failures.
- `node --check site/tests/accessibility.browser.js` and `node --check site/tests/media-reset.browser.js`: passed.
- `npm --prefix site run build`: passed, all four page entries.
- `git diff --check`: passed.
- Accessibility browser regression: all existing checks plus mock removal and real verification recovery passed.
- Media browser regression: all three failure/recovery paths, reset, sample switching, query preservation and history passed.
- Technical-controls browser regression: all five replays and four imaging setups, keyboard focus/activation and selected-visit preservation passed.
- Independent bounded source audit found no additional concrete local stored-example demo code blocker; this is not a repository-wide correctness certification.

Each browser script ran via `ego-browser nodejs` with `const regressionSpaceId = 1;` prepended. Existing local server: `http://127.0.0.1:5173/`.

## Still open

- V2: real screen-reader announcements and actual 200% zoom verification remain pending, as requested. Automated checks do not substitute for them.
- V3: presenter/reviewer walkthrough has not run. Preparation can follow, but the acceptance gate is not passed.
- T03–T09: separate backend correctness backlog remains unresolved; these test-harness changes do not qualify live automation.
- T10/T11: partner protocol and release/commercial clearance remain separate owner decisions.

No commit, merge, push or deployment performed. Existing uncommitted work is preserved.
