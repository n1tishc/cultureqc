# I3 — Evidence and integration handoff

Date: 2026-10-16. Scope: `03-proof.md`, subject to `00-contracts.md`.

Status: implemented; source audit and scoped automated checks pass. Parent reports the browser checks below passing. No deployment, model execution, scientific-data regeneration or backend/schema changes were performed by this node.

## Changed paths

- `site/src/pages/ValidationPage.jsx`: scoped opening and headline findings; immediate source links; optional dense-band fallback.
- `site/src/components/Profiles.jsx`: calibration protocols, model-overlap/blindness limitations and dense-range sample counts.
- `site/src/components/DenseTest.jsx`: pooled-secondary versus sealed/swapped-primary distinction; experimental decision failures; sample-bound shipped-policy observations.
- `site/src/pages/RecordsPage.jsx`: integrity is not biological validity, action validation or compliance.
- `site/src/components/Records.jsx`: supported review schema is not an actual stored review event; explicit host/compliance boundary. Selection, canonical bytes, verifier and tamper/reset logic are unchanged.
- `site/src/components/Sections.jsx`: qualified V1–V10 introduction; current Python integration, inputs/outputs/host ownership, latency scope and single-image limitations.

All existing named exports and section IDs remain. No global CSS, Home, Journey or Shell edits belong to I3. Existing source metrics, stored records and adverse evidence remain intact.

## Audit failures and fixes

1. **Blanket held-out/unseen claims:** the validation opening and generated architecture introduction collapsed different evidence protocols into one. Replaced with named MSC, EVICAN, LIVECell, replay, synthetic and latency scopes. A source file being linked below was not sufficient qualification for the opening claim.
2. **Calibration presented without enough dense-range context:** the headline now says within-study default-versus-calibrated MSC, 320 images, leave-one-population-out, only four images at 60–90%, and unmeasurable passage-range criteria. This is not a v2/v4 comparison.
3. **Pooled evidence presented like one independent test:** 169 mCellSeg images are a secondary pool of 90 sealed and 79 swapped tests. The swapped primary comparison does not replicate; experimental fine-tuning fails pooled decision agreement. Those limitations are now visible beside the overview/scatter, not only in the details. Fine-tuning decides nothing in the shipped workflow.
4. **Over-general safety wording:** removed “fails safe” and qualified zero ready-continue observations as belonging to this test sample. No instrument-specific safety claim follows.
5. **Integration boundary mismatch:** profile image-quality gating is inside `analyze()` when configured, not a separate promised host call. The example now includes imager identity and recovery output; null growth/forecast fields, caller-owned exception handling and local JSONL limits are explicit. No HTTP service, actuation or deployed host integration is claimed.
6. **Review/compliance implication:** clarified that the stored chain contains readings and changes, not a review event. Valid hashes establish consistency with stored bytes and checkpoint, not biological truth, approval or Part 11 compliance.

## Source-to-claim ledger

These entries cover the prominent evidence summaries and retained numeric figure/table families. Rendered measurements continue to come from existing data; no scientific number was rewritten to satisfy a claim.

| Surface / claim | Repository source | Protocol and sample count | Qualification retained or added |
|---|---|---|---|
| Validation headline; Profiles: MSC MAE 8.19 → 3.43 pp | `results/confluency_profiles.md`, companion JSON | 320 MSC images; leave one filename population out across three populations | Within-study calibration, not release improvement. Four images at 60–90%; dense criteria unmeasurable. Calibration is not partner action eligibility. |
| Profiles: EVICAN MAE 8.36 → 3.78 pp | `results/confluency_profiles.md` | 65 calibration / 33 test images; mixed microscopes | Test used previously in V1/preview/cutoff work, not fully blind; zero 60–90% images in this study. |
| Profiles: LIVECell MAE 2.14 → 2.05 pp | `results/confluency_profiles.md` | 756 calibration / 756 test images, split by field within eight cell lines; 91 dense-range test images | In-domain check; model-training overlap unconfirmed, not held-out model evidence. Its measurable acceptance criteria do not erase the other studies’ insufficient dense evidence. |
| Dense headline/scatter: shipped 7.61 versus experimental 2.22 pp overall MAE; 73 versus 153 within 5 pp | `results/confluency_mcellseg.md`, `results/confluency_mcellseg_swap.md` | 169-image secondary pool: sealed 90 + swapped 79, four setups from one lab | Not one independent pre-registered pooled test. No test image trains its corresponding model. Experimental output does not drive recommendations. |
| Dense primary contrast: sealed holds, swapped does not replicate | Same sealed and swapped reports | Sealed C−F improvement 4.45 pp, interval [0.83, 7.94]; swapped 4.84 pp, interval [−0.80, 12.29] | Swap planned after seeing sealed result; interval crossing zero prevents a replication claim. Pooled secondary result cannot override it. |
| Dense tables / PassageRange: shipped 28 of 36 dense images defer; no ready continue | Same sealed and swapped reports | Pooled 36 images at 60–100%; 10 ready images; shipped 0 passage / 8 continue / 28 review | Observation in this sample, not general safety. Shipped dense error 8.82 pp and bias −3.27 pp fail criteria. |
| Dense experimental decision agreement | Same sealed and swapped reports | Pooled 7 passage / 10 continue / 19 review; 15 of 17 decisions agree | Fails 95% criterion; two early passage outputs. Measurement improvement does not establish action validity. |
| Fine-tuning image illustration | `results/confluency_finetune_figure.md` | Four setup images, selected by density near 75%; separate retrained F weights | Original scored weights were not retained. Existing caption identifies retraining and up-to-2-pp display differences; illustration is not a new scored result. |
| Confluency V1: Cellpose 8.35 pp vs threshold 11.20 pp | `results/confluency_real_summary.md` | 33 expert-masked EVICAN images from 98 available, constrained by CPU budget | Sparse overall sample; first-run dense case severely underexposed. This historical run is distinct from the later profile rescore (8.36), not a release delta. |
| Historical review-rate figure: 5.7% overall; 43.8% near threshold | `results/review_rate.md`, companion CSV | Retired `rules_v0.4`; 1,228 frames / 14 sequences, 160 frames at 40–60% | Correlated frames; sequences are the unit of generalization. Retired rule, not current policy behavior. |
| Growth signal: 6 h and 12 h versus noise | `results/growth_signal_summary.md` | C2C12 replay; 6 h: 37 pairs / 9 streams, 12 h: 12 pairs / 8 streams | Simulated visits, quarter-frame noise, correlated samples and model-derived full-frame readings; not independent action ground truth. Existing ratios remain below the required signal/noise threshold. |
| V1–V10 verdict counts and table | `docs/ARCHITECTURE_VALIDATION.md` and linked per-test reports | Replay split 10 tuning / 14 held-out base sequences plus simulated faults; separate EVICAN, synthetic-tile and CPU tests | These are heterogeneous architecture checks, not all held-out C2C12 images or production qualification. Failures/insufficient evidence remain visible; V8 synthetic calibration is not biological contamination validation. |
| Detectability: real-size simulated contamination AUROC 0.48 | `results/contamination_scale.md` | 97 injected frames / 4 sequences across both splits; held-out 49 / 2; normal comparison 1,228 frames | Simulated contamination only. Oversized 16.5× display does not establish realistic biological detection; ≥150 px result also fails. |
| Integration CPU timing: 689 s | `results/live_latency.md`, `docs/ARCHITECTURE_VALIDATION.md` | Two-thread CPU approximation on M2 Pro, median two timed runs/input after warmup | Real LIVECell fixture tiled to C2C12 size, not a C2C12 image; resident models and excluded load time. Source table gives 689.7 s while architecture headline uses 689; retained published headline, no data rewrite. |
| Integration MPS / T4 / ZeroGPU timings | `results/live_latency_mac_mps.md`, `results/live_latency_colab_gpu.md`, `results/space_dry_run_712a9e54.md`, `results/space_dry_run_712a9e54_run2.md`; median calculation in `demo/selfcheck.py` | MPS 16.48 s and T4 12.06 s: medians across five distinct C2C12 example images, not repeated timings of one image; one untimed warm-up pass, resident models, model loading excluded. ZeroGPU 3.27 s and 6.22 s: median across six subsequent distinct example analyses after excluding the first call in each run | Historical, non-matched environments; T4 predates setup profiles. ZeroGPU includes client/network/queue overhead and owner-token access. Not a latency guarantee or hosted API promise. Existing seven-example parity is stored-output comparison, not new scientific validation. |
| Integration callable/outputs | `culture/pipeline.py`, `culture/records.py`, `docs/host_platform.md` | `analyze(image_path, flask_id, cell_line, profile_id, imager_id, hours_since_passage, log_path)` using existing keyword interface | Single image, configured models, local append; no physical action. Profile quality gate when configured; recovery request is advisory. Growth and ETA currently null. Exceptions may occur before a record exists. |
| Records integrity and host responsibilities | `culture/records.py`, `site/src/lib/verify.js`, stored example chain, `docs/host_platform.md` | Seven readings plus two change records; no stored human-review event | Browser checks canonical bytes/links/checkpoint; host supplies capture, scheduling, identity/signatures, durable retention and physical action. No compliance certification. |

Source distinctions were reported rather than “fixed” in scientific inputs: historical EVICAN V1 versus later profile scoring; CPU headline rounding versus timing-table precision; reconstructed fine-tuning illustration versus original scored weights; pooled secondary versus primary tests. No additional scientific evidence is claimed.

### V1 F3 correction

The independent acceptance review identified missing visible latency conditions and an incorrect sample unit in this ledger. Corrected the MPS/T4 ledger from “five warm repeats” to five distinct C2C12 example images, verified against the five named C2C12 rows in each report and `demo/selfcheck.py`’s per-example loop and median. CPU remains two timed runs per input. `Sections.jsx` now places these sample units plus warm-up, resident-model and model-load-excluded conditions directly beside the respective timings; the T4 label explicitly says before calibration profiles, matching its existing data description. Timing numbers, reports and generated data remain untouched. Root owns F1/F2 and regression checks; no benchmarks or inference were run for F3.

## Checks performed

Commands run from repository root unless otherwise noted:

```sh
node --test site/tests/*.test.js
.venv/bin/python -m pytest tests/test_claims.py tests/test_readme_provenance.py tests/test_records_chain.py tests/test_record_events.py -q
cd site && npm run build
```

- Node: **11/11 pass** (scenario, exact-record selection and verification tests).
- Python: **76 pass**. No model execution or data regeneration.
- Vite production build: pass.
- `git diff --check` on the six owned source files: pass.
- Static Python AST check: snippet keywords exist on `analyze`; displayed confluency, interval, action, reason and recovery fields are constructed by that callable. Hash is finalized by record append.
- Impeccable deterministic hooks on changed Validation/Dense/Sections surfaces: no issues reported. No new visual system or global styling introduced.

Parent-reported browser checks (I3 did not operate the browser):

- Both primary examples select their exact record; record-to-reading return links work; unrelated campaign query survives.
- All three tamper modes fail the anchored checkpoint. Reset restores the identical parsed original record and original query.
- Forced browser-only `crypto.digest` rejection shows “could not verify,” no success states, and Retry verification. Injection removed; explicit full reload restores passing checks. Same-URL navigation initially retained the test stub, a test-harness reload issue rather than application behavior.
- Updated integration/current callable and Validation scope are visible. Neither page overflows horizontally at 390 px.
- Parent closed browser TaskSpace 5; development server remains running. These functional checks are not a claim of public deployment or full visual/accessibility certification.

## Handoff and remaining ownership

- I2 received shared-copy guidance: retain 320-image MSC LOPO/four-dense limitation, distinguish intended host boundary from shipped integration, and do not headline tuning as replicated or decision-driving. Parent confirmed I2 already follows these limits.
- Shared-file follow-up resolved by orchestrator: `site/validation.html` descriptions/Open Graph metadata no longer use blanket held-out/unseen wording; `site/records.html` metadata now says no review event and distinguishes integrity from validity/compliance. Parent documented this narrow ownership addition in `03-proof.md`; these are orchestrator edits, not I3-authored changes.
- Parent owns final acceptance aggregation, DAG/status updates, any remaining visual/accessibility review and any later deployment. No production/commercial-readiness signoff is supplied by I3.
