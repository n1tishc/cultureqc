# T12 — Pointer follow-up and remaining acceptance

Historical pre-update record. The subsequent
[approved update and visual retest](2026-10-20-proof-visual-acceptance.md) restores
captures and closes the scoped visual/chain-link scrolling gates. Human
verification remains pending. The observations below are preserved as recorded.

Status: scoped desktop/mobile pointer regression passed locally. Fresh
screenshot-based visual acceptance remains blocked; human screen-reader and
actual 200% browser zoom verification remain pending by request.

## Verified locally

`site/tests/proof-pointer.browser.js` passed against `http://127.0.0.1:5173/`
at 1440 × 1000 and 390 × 1000 CSS pixels with reduced motion. The mobile run
uses viewport emulation and mouse input, not a physical device or touch test.

- Select the review-boundary sample and navigate to its exact HT29 record.
- Follow the exception into the separate illustrative review; wait for chain
  verification, expand/collapse JSON, return to the original reading and sample.
- Preserve the fictional-review disclosure, `human_review` and null signature.
- Keep JSON overflow inside its pane with no document horizontal overflow.
- Reach `/records#chain` through the generic homepage chain link, subject to the
  controlled-scroll qualification below.

### Pointer qualification

Ego's selector click twice reported interception while automatically scrolling
to the generic chain CTA. After inspecting the page, explicitly scrolling the
link into view and checking `elementFromPoint`, a real mouse click succeeded.
The saved regression uses that controlled-scroll workaround for this link only;
the other interactions use selector-based pointer clicks. This establishes the
link's behavior, not an unqualified natural-scrolling acceptance pass. No source
obstruction was established and no speculative UI fix was made.

A bounded read-only source review found no actionable blocker in responsive
chain columns, JSON overflow containment, focus styles or native controls. This
is not a screenshot review or an accessibility certification.

## Validation record

| Check | Result |
|---|---|
| Saved pointer regression | Passed at both widths, with the chain-link workaround above |
| `node --check site/tests/proof-pointer.browser.js` | Passed |
| `node --test site/tests/*.test.js` | 15 passed |
| `.venv/bin/python -m pytest tests/test_review_demo.py -q -p no:rerunfailures` | 2 passed |
| `git diff --check` | Passed |
| Standard screenshot and one alternate CDP capture | Both timed out; no new screenshot inspected or visual pass claimed |

The completed regression reused task space 4. On resuming after interruption,
its output was recovered successfully, but cleanup returned `task space not
found: 4`; no replacement space was created and no successful `finish` is claimed.
Ego Lite reported an available update (installed version 0.6.0.12). It was not
installed. No product UI, historical records, scientific thresholds or evidence
were changed in this follow-up. Nothing was committed, pushed or deployed.

## Next steps, in order

1. Obtain approval to update Ego Lite, then retry fresh desktop/mobile captures
   and visually inspect the review section, expanded JSON and return links.
   Check natural scrolling to the generic chain CTA again without the workaround.
2. Keep human screen-reader and actual 200% zoom verification pending until a
   person performs them; DOM focus assertions do not establish spoken output.
3. After acceptance gates close, run V3's timed presenter/reviewer walkthrough
   using `docs/DEMO_SCRIPT.md`. Lead with confluency and traceable decisions;
   disclose that the review event is illustrative and outputs are advisory.
4. Continue T02 only against its remaining evidence gates: independent labels,
   authenticated model provenance and an approved target protocol. Existing
   EVICAN/C2C12 cached-policy replays are not new model-accuracy evidence.
5. Obtain explicit owner approval before any push or deployment.

See the [original T12 implementation record](2026-10-20-proof-journey-and-current-guidance.md)
and [current status](../STATUS.md) for the parallel technical/evidence track.
