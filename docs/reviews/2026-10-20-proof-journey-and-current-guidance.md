# T12 — Proof journey and current guidance

Historical implementation record. Subsequent
[post-update visual acceptance](2026-10-20-proof-visual-acceptance.md) closes the
fresh review-section visual and pointer follow-up; human AT/zoom gates remain open.

Status: implemented locally; automated desktop/mobile interaction checks pass.
Fresh screenshot-based visual acceptance is pending because browser capture timed
out. Human screen-reader and actual 200% zoom checks remain pending by request.
No commit, push, merge, tag, deployment or repository-setting change was performed.

Subsequent [pointer follow-up](2026-10-20-proof-pointer-followup.md) passes at both
viewport widths with a documented chain-link scrolling workaround; fresh visual
acceptance remains blocked. T02's initial manifests and cached-policy replays are
now implemented for [EVICAN](2026-10-20-matched-policy-replay.md) and
[C2C12 workload](2026-10-20-c2c12-workload-replay.md). The dated next-step inventory
below is preserved; use [current status](../STATUS.md) for remaining work.

## What changed

- The selected homepage sample links to its exact historical reading. The generic
  chain CTA and legacy `/#records` and `/#chain` routes reach `/records#chain`,
  including hash changes on an already-loaded homepage.
- HT29's exception links to a separate illustrative review. The fictional reviewer
  retains `human_review`; this is not a real review, approval, signature or action.
  The review links back to the original reading, which links back to the sample.
- `site/assets/build_data.py` copies the historical nine-record chain into a
  temporary file, appends a review through `review_event` / `RecordWriter`,
  validates it and generates a separate ten-record extension and checkpoint.
  Original canonical records, measurements, hashes and source files are unchanged.
- The browser re-hashes all ten records, checks their links and both checkpoints,
  and verifies the exact reviewed record ID and hash. Verification failure is
  explicit and retryable; malformed review JSON does not crash its display.
  As elsewhere on the site, checkpoints shipped with the page are demonstration
  anchors, not independently protected production audit storage.
- Current build metadata identifies schema `0.8` / `rules_v0.7`, not a remote
  deployment. The seven historical readings retain `0.4` / `rules_v0.5`.
- README, product guidance, release-state documentation, local Space guidance,
  site documentation and presenter notes distinguish current/local, historical,
  illustrative and experimental outputs. C2C12's quality gate and lack of
  independent confluency labels are explicit. EVICAN bias is not transferred.
- The old console product brief is preserved in `docs/history/`; the old repo map
  is marked historical. The orphaned App surface brief is archived outside the
  active surface directory. A stale V1–V10 homepage link now describes the actual
  evidence page instead of promising a removed architecture table.

## Verification

| Check | Result |
|---|---|
| Two consecutive `site/assets/build_data.py` runs | Byte-identical `site/src/data.json`; SHA-256 `2c2a86a47510e6065b32cc8d879436840729a18c555fb91728c67e69d2b0ddb7` |
| `.venv/bin/python -m pytest tests/test_review_demo.py tests/test_claims.py tests/test_readme_provenance.py tests/test_demo_examples.py tests/test_records_chain.py -q -p no:rerunfailures` | 119 passed |
| Focused review/claims/provenance rerun after final copy correction | 54 passed; subset of the 119, not additional coverage |
| `node --test site/tests/*.test.js` | 15 passed, including four new review-verifier tests |
| `npm run build` | Passed |
| `.venv/bin/python deploy/sync_space.py --check` | Both local generated Space trees match root code/config |
| `git diff --check` | Passed |
| `site/tests/proof-journey.browser.js`, Ego Lite, local port 5173 | Passed at 1440px and 390px with reduced motion: keyboard sample selection/focus retention, exact record, review disclosure, original return, chain CTA, evidence destination and no document overflow |
| Legacy fragments | Direct and already-loaded homepage navigation passed for both fragments |
| Independent current-document audit | Links/anchors resolve; archived original brief and repo-map body preserved; no blockers |
| Screenshot capture | `Page.captureScreenshot` timed out; no new visual-pass claim |

Browser automation initially asserted the return link before React rendered it;
the saved regression waits for the destination DOM. A separate pointer attempt
was intercepted during scrolling; the saved keyboard path passes. This does not
constitute a completed pointer/visual acceptance pass.

Run the saved browser regression with the local Vite server available:

```sh
ego-browser nodejs < site/tests/proof-journey.browser.js
```

It owns and finishes one task space when run standalone. Do not count DOM focus
checks as a human screen-reader announcement test.

## Remaining gates and next implementation

1. Fresh desktop/mobile visual and pointer check of the new review section.
   Human screen-reader/200% zoom evidence remains deliberately pending.
2. T02: freeze a common-input comparison manifest and inventory historical inputs
   before any bounded inference request. A cached-policy replay must not be called
   an end-to-end model benchmark. This is internal validation, not a v2-first site.
3. V3: timed presenter/reviewer walkthrough after the outstanding acceptance gates;
   use `docs/DEMO_SCRIPT.md`, including the fictional-review disclosure.
4. Partner setup, independent labels, approved experimental protocol, commercial
   clearance and authenticated host integration remain owner/external gates.
   T12 creates no new biological evidence, threshold approval or actuation permission.

Local review remains at `http://127.0.0.1:5173/`. Publishing still requires explicit
owner approval. An Ego Lite update was offered by the tool but was not installed.
