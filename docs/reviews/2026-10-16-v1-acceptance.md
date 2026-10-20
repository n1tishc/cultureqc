# V1 — Independent regression and claims review

Date: 2026-10-16; closure recorded 2026-10-17. Status: **passed after corrections and independent retest**. Scope: `docs/specs/standalone-product-site/05-acceptance.md`, V1 only. Original findings below are retained as review history; all three are closed by the correction record.

Reviewing the current working tree on `slice-1b-compute-cache`, HEAD `01b8ead1ea09f7ebf442a9862d3113369614cdd1`. Independent standards and specification reviewers inspect the implementation while the orchestrator runs the required regression checks. V2 browser/visual acceptance and V3 rehearsal are not part of this result.

## Baseline

The implementation-start baseline was already dirty. Pre-existing changes include `README.md`, `docs/DATASETS.md`, `docs/DEMO_SCRIPT.md`, `docs/PRODUCT.md`, `docs/PROGRESS_SUMMARY.md`, `docs/STATUS.md`, the October 15 review/backlog documents, the homepage surface brief and `site/src/data.json`; existing untracked archives, `files/`, design/research documents and specs also predate implementation. Do not attribute all differences from HEAD to I1–I4. Node handoffs identify their owned paths and preserved regions.

## Initial review results

| Check | Fresh result |
|---|---|
| `node --test site/tests/*.test.js` | 11 passed; zero failures/skips |
| `npm --prefix site run build` | Passed; Vite built all four entries |
| `.venv/bin/python -m pytest -q tests/test_demo_examples.py tests/test_demo_replays.py tests/test_claims.py tests/test_records_chain.py` | 130 passed in 40.33 seconds; zero failures/skips |
| `git diff --check` | Passed |
| Existing local server, HTTP GET `/`, `/records`, `/validation`, `/release-notes` | All returned 200; no new server started |

The installed Python environment was used rather than a different system interpreter. No models downloaded, new inference launched, dependency installed or scientific data regenerated. Build artifacts are ignored local `site/dist/` output, not a deployed/generated source mirror.

| Acceptance | Disposition |
|---|---|
| V1-A | Required automated checks pass. Static review also finds an uncovered same-example Reset recovery defect, F1. |
| V1-B | Primary fixtures and main evidence/callable checks agree with sources; claims gate remains pending F2 and F3. |
| V1-C | Scoped change-control check passes with the historical-baseline limits below. |
| V1-D | Static destination inventory and local HTTP entries pass. Browser interactions and external availability remain explicitly outside this V1 result. |

## Standards / regression review

Independent reviewer: `v1_standards_review`, uninvolved in I1–I4 implementation. No additional documented-standard breach or material heuristic smell found. One medium-severity direct specification mismatch:

### F1 — Reset does not clear an initial same-example media failure

- **Acceptance:** V1-A; I1 implementation step 3 / I1-D. **Severity:** P2 (medium). **Owner:** I1 frontend owner.
- **Location:** `site/src/components/Stage.jsx:236`; hook dependency arrays at lines 63 and 96.
- **Reproduce:** On a fresh default C2C12 load, fail its first image or contour request. Restore availability and press **Reset** without first using **Retry media**.
- **Expected:** Reset retains the default identity, restores contour-only mode, clears the sample-specific error and starts recovery.
- **Actual:** `selectScenario` sets `mediaRetry` to `0`, its existing value. The URL, enabled state and contour dependencies also remain unchanged, so neither hook reruns and its error persists. This is established by static state/dependency analysis; browser fault-injection reproduction is still required. **Retry media** remains usable, so this is not silent substitution or false verification.
- **Fix packet:** Use a reset/select refresh generation or equivalent explicit failed-media reset. Preserve query/history semantics and avoid an unrelated caching rewrite. Add a targeted regression covering initial failure → restored availability → Reset on the same default; also check normal Reset, another sample, and Retry media. Do not consider the existing pure layer-helper test proof of hook recovery.

## Specification / claims review

Independent reviewer: `v1_spec_review`, uninvolved in implementation. Two medium-severity claims gaps; root additionally verified F3's sample-unit correction directly against the reports and generator.

### F2 — Retained technical copy contradicts the default reading

- **Acceptance:** V1-B / C0 data and claim contracts. **Severity:** P2 (medium). **Owner:** I2 homepage owner, with a narrow scope extension to `Product.jsx`.
- **Location:** `site/src/components/Product.jsx:208`.
- **Reproduce:** Open `/#accuracy`, then inspect default coverage. The technical copy says every reading carries a measured band and otherwise/on an uncalibrated microscope a person decides; the default is explicitly `null` band and `continue`.
- **Expected:** Bands exist only for calibrated profiles. Passage eligibility and review at its boundary must be distinguished from below-target continue/feed outcomes and other rule conditions.
- **Actual:** Blanket wording misstates both band availability and rule behavior. `culture/rules.py:176` and `culture/rules.py:210` distinguish target-related review from default continue. This wording is **inherited**, not introduced by I1–I4, but remains a claims acceptance gap on a retained, directly linked product surface.
- **Fix packet:** Qualify the paragraph using the current callable/rules, without changing outputs. Check the related explanations at `Product.jsx:126` and `Product.jsx:331` for the same overbroad review wording. Keep section IDs and historical evidence intact. Test wording against default C2C12, HT29, and below-target calibrated PC3. Record this narrow ownership addition before editing the previously unowned file.

### F3 — Visible latency qualifications and the ledger need correction

- **Acceptance:** V1-B / I3-A. **Severity:** P2 (medium). **Owner:** I3 evidence/integration owner.
- **Location:** `site/src/components/Sections.jsx:359`, `site/src/components/Sections.jsx:409`, and the latency row of `docs/reviews/2026-10-16-i3-proof-handoff.md`.
- **Reproduce:** Open `/records#integration`; compare its timing table and ledger with `results/live_latency.md:5`, `results/live_latency.md:9`, and the opening/table of `results/live_latency_mac_mps.md` and `results/live_latency_colab_gpu.md`.
- **Expected:** Material timing protocol and sample unit remain beside the values: CPU two timed runs per input after warm-up; MPS/T4 five distinct C2C12 example images after warm-up; models already loaded, load time excluded. T4 predates calibration profiles. These are not cold-start service guarantees or a matched hardware comparison.
- **Actual:** The table omits warm/resident/load-excluded conditions and CPU sample count; the shortened T4 label drops the pre-profile qualification. Its generic non-guarantee paragraph is insufficient. Separately, the I3 ledger incorrectly calls MPS/T4 samples “five warm repeats”: the reports list five different C2C12 images, and `demo/selfcheck.py:57` / `demo/selfcheck.py:77` compute their median, not repeated measurements of one image.
- **Fix packet:** Add concise row-specific/contextual qualifiers and correct the ledger's sample unit. Keep existing timing numbers, source reports and `site/src/data.json` untouched. Check all timing captions for consistent units; do not rerun benchmarks or imply new performance evidence.

**Axis summary:** Standards/regression: one finding, medium Reset recovery mismatch. Specification/claims: two findings, medium retained-rule and latency-protocol gaps. No claim that passing tests overrides these findings.

## Source checks that passed

- Coverage: `c2c12_normal_20_40`, 39.41%, no band, `continue`, exact record 4. Boundary: `evican_ht29`, 52.91%, 23.51–82.31%, target 80%, `human_review`, exact record 9. Both match current stored data, record order and Node assertions.
- HT29 mixed-setup/non-blind calibration and unsupported anomaly-bank qualifications are visible in workspace source. Normal-source coverage is not contamination clearance. All seven example IDs, missing versus invalid selection, unrelated queries and layer helpers have focused tests.
- MSC/EVICAN/LIVECell protocol counts, errors and dense limitations agree with repository reports. Sealed/swapped primary studies and the secondary pool are distinguished; experimental fine-tuning does not drive recommendations. Historical error/review/growth/contamination and reconstructed illustration claims were spot-checked.
- The Python snippet keywords/returned fields match `culture/pipeline.py`; host-owned action, retention and identity, null growth/forecast and pre-record exceptions remain explicit. Records integrity is not biological validity/compliance, and no stored review event is claimed.

## Change-control evidence and limits

- `git diff --quiet HEAD -- culture results configs demo deploy site/public site/assets` returned 0. No tracked backend, scientific report, canonical record, policy/config, static scientific asset or deployment mirror differs from HEAD in these protected paths.
- The `site/src/data.json` difference is the known pre-existing 12-line addition of two evidence rows, not a V1 or I1–I4 edit. It was read as current truth and not rewritten.
- Recomputed I4 preservation hashes match: Demo Script technical appendix `41e8f3e2df34f6ddedfd41b4f3a8c337f97c3a96fb03b1404c5ba9bd8d4679de`; Product history from `## Platform` `eb7df66e784672163ee5afcee15de8e1a56cf680a30a2dc107eee01b8c125746`.
- Implementation-owned source paths match the handoff manifests. The baseline records dirty-path ownership rather than a complete byte snapshot of every unrelated user file; this review cannot independently certify every historical byte of that pre-existing work. It does not equate a dirty tree with unauthorized implementation changes.
- The initial V1 review changed only this report and DAG status. Reviewers did not fix implementation files. The subsequent correction batch is recorded below. No commit, merge, push, deployment or change to scientific evidence occurred.

## Link inventory

| Family | Inventory / static result |
|---|---|
| Page entries | `/`, `/records`, `/validation`, `/release-notes`; build entries and clean-route middleware exist; local HTTP 200 for each |
| Primary destinations | Product / Explore → `/#demo`; Evidence → `/validation`; Integration → `/records#integration`; Evaluate → `/#pilot`; inline host diagram → `#fit` |
| Reading / record | Both `/records?record=<ID>#chain` links and `/?example=<ID>#demo` returns retain exact identity; selection/query/verifier helpers pass Node tests |
| Moved legacy hashes | `#records` → `/records`; `#integration` → `/records#integration`; `#validation` → `/validation#checks`; `#limits` → `/validation#detectability`; `#confluency` → `/validation#confluency`; `#changes` → `/release-notes` |
| Retained legacy targets | `#timeline`, `#accuracy`, `#passage`, `#specs`, `#scope`, `#how`, `#top`, `#evidence`, `#pilot`, `#trail`; technical disclosure opening handler exists |
| Accessibility / secondary | `#main` skip targets and `#model-terms` exist; release history remains secondary/footer |

The first sandboxed loopback request could not connect; repeating the four GETs with approved network access returned 200. No browser navigation, fresh screenshot, native zoom, keyboard/contrast certification or external GitHub/live-console availability check was performed in V1. Earlier screenshot timeouts remain unresolved, not visual evidence. These are V2/external-service limits, not reported as passing here.

## Correction and retest record

- **F1 closed:** `Stage.jsx` increments the media refresh generation on selection/reset and history restoration. The original failure was reproduced in the browser before correction. The saved `site/tests/media-reset.browser.js` passes initial image/contour failures followed by Reset, Measure coverage and Retry media, plus normal reset, sample switching, unrelated query preservation and Back/Forward identity. It uses native keyboard activation; it does not certify pointer interaction or layout. Independent reviewer `v1_standards_review` confirmed the fix and regression coverage.
- **F2 closed:** The narrow `Product.jsx` ownership extension is recorded in `02-homepage.md`. All three related explanations now distinguish calibrated band availability, target-boundary review, timing/quality conditions and below-target continue/feed outcomes. No rules or stored outputs changed.
- **F3 closed:** Visible timing protocols now identify warm-up, resident models, excluded model loading, CPU two runs per input and MPS/T4 five distinct examples; T4 retains its pre-profile context. The I3 ledger also corrects ZeroGPU's six subsequent distinct analyses, rather than repeats. Independent reviewer `v1_spec_review` closed F2 and F3 against source.

Fresh correction validation: **11 Node tests passed; production build passed; 130 scoped Python tests passed in 39.57 seconds; `git diff --check` passed.** No failures/skips. `node --check site/tests/media-reset.browser.js` also passed. Protected paths still have no tracked differences from HEAD; the known pre-existing 12-line `data.json` addition is unchanged.

Reproduce the additional browser regression with the existing local server running and Ego Lite available:

```sh
ego-browser nodejs < site/tests/media-reset.browser.js
```

It is deliberately separate from `node --test site/tests/*.test.js`, requires the browser runtime, and closes its task space on success. The final regression run passed all four logged groups. An earlier pointer automation attempt encountered an intercepted click during scrolling; no durable obstruction was established. Pointer behavior is left for V2, not counted as passed. No screenshots or visual acceptance were produced by this regression.

Final V1 dispositions: **V1-A/B passed after correction; V1-C/D passed within the explicitly recorded baseline and static-link limits.** This closes V1, not V2 or V3.

## Next dispatch

V2 may now inspect the local browser experience. V3 still requires V2 and an actual timed fresh-reviewer rehearsal. Runtime correctness, partner evaluation, commercial clearance and deployment remain separate tracks.
