# cultureQC v0.4 versus v0.2: a tough review from the VP's side

Reviewed 2026-10-15. Baseline: `e2274dd` (`main`, v0.2). Current checkout: `confluency-evidence-v2` at `2cd691a158bcffad7d283fea5b8aa6629665246b`, including the pre-existing working-tree edits. This is a review, not an implementation or release approval.

Read next: [agent backlog](2026-10-15-v4-vs-v2-agent-backlog.md) and [reproduction evidence](2026-10-15-v4-vs-v2-evidence.md).

## Verdict

**v4 is a substantially more credible research and evaluation system than v2. It is not yet a demonstrated autonomous culture-management product.** Its strongest improvement is the discipline around measurement, uncertainty, retirement of failed detectors, and traceability. Those improvements justify asking an engineering VP to sponsor a bounded calibration evaluation. They do not yet justify asking that VP to trust passage decisions in production.

The uncomfortable question is: **what can the VP now delegate to this system that could not responsibly be delegated to v2?** Today the defensible answer is a better-instrumented, setup-specific evaluation of confluency and decision boundaries. Reduced operator workload, reliable passage automation, realistic contamination protection, and production integration remain unproved.

This is not a cosmetic problem. Several implementation gaps undermine the exact promise that makes v4 valuable: knowing which evidence, inputs and approved model produced an action. The targeted tests pass, but additional probes reproduce those gaps.

## What the project is actually trying to achieve

The current useful product boundary is:

1. Receive a microscopy image and host context.
2. Produce a setup-specific confluency reading and an explicitly scoped uncertainty estimate.
3. Recommend an action only within supported conditions; explain exceptions.
4. Return a record the host can retain, authenticate, review and replay.

The host owns vessel handling, scheduling, identity, signatures and durable audit integration. `docs/host_platform.md` explicitly says integration has not been run inside a host platform. The VP audience's stated priorities in `docs/DEMO_SCRIPT.md:3` are confluency QC and traceable records. That is the right focus.

The earlier temporal ambition was tested and substantially cut back: growth signal was below the required signal-to-noise ratio, SPC missed the simulated faults, and instrument drift did not separate cleanly. Those negative results are valuable. Rebuilding those features for demo breadth would dilute the current proposition.

Version vocabulary needs care: the site is **v0.4**, current rules are **rules_v0.5**, current reading schema is **0.5**, and the stored site examples use **0.4**. `cultureQC_upgrade_specv4.md` is a filename whose title says **Upgrade Spec v3.3**; it is not a complete specification of today's v0.4. Evaluate current code against current evidence and recorded decisions, not every superseded slice in that document.

## The honest v2 → v4 comparison

| Dimension | v2 | What v4 genuinely improves | How a VP should interpret it |
|---|---|---|---|
| Evidence behind confluency | Headline 2.3 pp versus about 31 pp thresholding came from synthetic tiles; original per-tile artifacts are not in this repo | Real-image evaluations, named splits, sources and explicit failures | Better diligence and a reproducible evaluation process. **Do not compare 2.3 with 3.43 or 3.78 as a direct improvement.** |
| Setup calibration | Fixed/default segmentation cutoff | MSC error 8.19 → 3.43 pp across 320 images under leave-one-population-out evaluation; EVICAN 8.36 → 3.78 pp on 33 images, explicitly not fully blind | Evidence that calibration can help specific data distributions, not a universal accuracy claim |
| Decision uncertainty | Boundary-derived confidence drove review | The failed confidence proxy is retired from decisions; a setup-level error band is attached to readings and used around the target | A better rule design. Dense-range validation and useful decision coverage still need proof |
| Fault classifier | Synthetic accuracy/recall suggested a capable QC detector | Real-image failure is documented and classifier output is demoted from decisions | Removal of a bad decision input is real progress. It is **not** proof that its replacement catches contamination |
| Anomaly check | Classifier-derived QC | A per-image DINOv2 flag with a visible region and reference-bank provenance | Useful inspection evidence with narrow scope. Real-size simulated bacteria remain near chance; a negative flag is not culture clearance |
| Audit | Chained image-analysis records already existed | Review/change event types, calibration identities, model checks, anchored-checkpoint verification and browser tamper demonstrations | More complete provenance design, but not a new invention of auditability and not a complete host audit system |
| Fine-tuning | No convincing current same-data dense-range story | Sealed mCellSeg test: 7.80 → 2.65 pp overall for calibrated zero-shot versus fine-tuned/calibrated; dense result and replication limitations disclosed | A promising adaptation route. The fine-tuned console reading is experimental and decides nothing |
| Operational maturity | Single-image demo/API | More evidence, stored examples, live console parity checks and explicit limitations | Better evaluation readiness. The public HTTP API is deliberately still v2; production reliability is not demonstrated |

Sources: `results/v02_headline.md`, `results/confluency_profiles.md`, `results/confidence_vs_error.md`, `results/classifier_c2c12.md`, `results/contamination_scale.md`, `results/confluency_mcellseg.md`, `results/confluency_mcellseg_swap.md`, `culture/records.py`, `deploy/README.md`.

Three tempting claims must stay out of the upgrade pitch:

- “Accuracy improved from 2.3 to 3.43 pp”: different datasets and protocols, and the direction itself would be worse.
- “Human review fell from 77% to zero”: 77% is v2's classifier-triggered review on normal C2C12 frames; v4's zero is at an 80% target none of those frames reaches, with 149/1,228 requiring re-imaging. It does not establish useful autonomous decisions.
- “v4 is much faster”: CPU approximations and ZeroGPU timings are different hardware and operating conditions, not a controlled software-version speedup.

## Where the VP's confidence should stop

### 1. A good mean error does not establish useful passage automation

The most revealing result is not a headline MAE. In the **secondary pooled mCellSeg analysis**, the calibrated zero-shot method sends **28 of 36 images at 60–100% to review**, makes **zero passage calls**, and gets **8 of 8 decided calls** correct. The fine-tuned method makes **7 passage / 10 continue / 19 review** decisions, with **15 of 17 decided calls** correct; it fails the registered agreement mark. See `results/confluency_mcellseg_swap.md:162`.

The derived dense-subset review shares are 77.8% and 52.8%, respectively. The reported all-image review shares, 20.1% and 12.4%, answer a different question because most images are outside that dense subset. These are research arms, not a full paired v2-versus-v4 product evaluation.

**VP interpretation:** “I can see measurement improvement. I cannot yet see a system that reliably handles the decisions my operators spend time on.” A pilot must measure correct decisions, early passage, missed readiness, review burden and re-image burden together. It must also count independent vessels/runs, not treat adjacent frames as independent successes.

### 2. Calibration status overreaches its measured scope

`msc_phase` and `evican_mixed` are marked `validated` even though A2–A4, including passage-range error and decision agreement, are “not measurable.” This follows the old rule that every *measurable* criterion must pass; it is not a failure to implement that rule. **The rule itself is too permissive for action eligibility.**

`culture/rules.py:183` uses the band without an eligibility/scope check. A reproduced call with the current MSC band, reading 90%, target 80% and 48 hours since passage returns `passage`, despite the missing dense-range evidence.

At the default target, MSC needs a reading of at least **87.11%** to clear its band. EVICAN would need **109.4%**, which is impossible for a percentage. EVICAN's cautious abstention is honest, but cannot be sold as demonstrated automation. These thresholds are arithmetic from the current configuration, not new benchmark results.

**VP interpretation:** “You have calibrated some measurements, but your software does not distinguish that from permission to act in the passage range.” See **T03**.

### 3. “It abstains when uncertain” is only partially true

An uncalibrated reading below the target still returns `continue` or `feed`. In the pooled mCellSeg evaluation, the uncalibrated arm calls **four ready images `continue`** (`results/confluency_mcellseg_swap.md:170`). Abstaining from passage prevents one kind of mistake, while missing readiness remains possible.

Missing safeguards are also permissive: a 90% reading with a ±5 pp band returns `passage` when both `quality_passed` and `anomaly_flag` are `None`. Unknown passage timing is treated as acceptable. Separately, NaN confluency returns `continue` with “No action needed.” A valid 95% reading only six hours after passage correctly avoids passage but falsely explains that 95% is below the 80% target.

These are different issues: unsupported operating scope requires an explicit product policy; missing required checks require a failure policy; invalid numeric values and false reasons are correctness defects. Do not solve them by blindly routing every absent optional check to review. Specify which checks and context are required for each approved use. See **T04**.

### 4. The strongest differentiator has reproducibility gaps

Confirmed in code and local probes:

- **The decision record is incomplete.** Target, effective `LineConfig`, hours since passage/feed are consumed but not persisted as structured inputs. `config_hashes()` omits the effective line policy. `captured_at` is generated after inference and cannot be supplied through `analyze()`. The library also omits the map hash that the console records. A rationale string is not a substitute for complete replay inputs. See **T05**.
- **A recorded model identity can be wrong.** After one model is loaded, replace its file and approve the replacement between calls. The next check hashes the new file, reports `match`, and inference still uses the old cached model. Reproduced with a deterministic model stand-in, without GPU inference. See **T06**.
- **Recorded changes are not uniformly enforced.** Profile/config approval enforcement is explicitly absent from `culture/approvals.py:18`; the runtime verifies model files only. `approved()` chooses the last entry without evaluating `effective_from`; a future-dated approval returned `match` in the probe. Profile caching also has no file-change invalidation. See **T07**.
- **Two writers can produce a broken chain without any tampering.** Instantiate two `RecordWriter`s before either appends, then append once through each: verification fails. The legacy API's process-local lock mitigates its own path, but does not make the library or multi-process host safe. See **T08**.

The existing chain verifier and checkpoint design are genuine improvements; the older missing/empty-log and wholesale-rewrite caveats were already addressed. Do not reopen those as if unfixed. The new concern is whether the records accurately capture execution and remain valid under ordinary host use.

### 5. Instrument input is not yet a controlled measurement contract

`culture/pipeline.py:83` decodes with `cv2.IMREAD_GRAYSCALE`. A 16-bit TIFF containing 12-bit values with maximum 4095 is silently decoded to uint8 with maximum **15**, reproduced locally. The prepared C2C12 dataset has a conversion step, but arbitrary incoming TIFFs do not acquire that preparation automatically.

Neither an image hash nor a model hash tells the VP which intensity mapping was used. The host interface needs a declared bit depth, intensity policy and image-identity policy. Decode and hash the same immutable input; reject unsupported formats or require explicit setup conversion rather than inventing per-image normalization. See **T09**.

## What the current presentation gets right—and wrong

The visual work is strong and specific to microscopy. Computed layers, image-linked readings, source links, bands, and the tamper demonstration are meaningful. A visual redesign would not fix the main problem.

The VP journey is weak in five places:

1. **The opening does not explain the upgrade.** The default 39.4% C2C12 example has no calibrated band. At the inspected 1500×770 viewport, the action and record are below the first viewport while model mechanics are visible. A calibrated decision-boundary example would explain v4 sooner.
2. **The ask is an exploratory upload.** `site/src/components/Shell.jsx:94` ends with “Run it on your own image.” The site does not convert its evidence into a concrete pilot: one setup, agreed data, frozen criteria, shadow operation, defined outputs and a go/no-go decision.
3. **The proof path breaks.** “verify the chain” at `site/src/components/Stage.jsx:331` points to `#records`. The target moved to a separate page; the migration effect in `Home.jsx:75` only runs on mount. A live click leaves the viewer at `/#records` on the homepage.
4. **The review loop is described but not demonstrated in the site's chain.** The Records page explains reading/review/change, while its nine-record interactive chain contains seven readings and two changes, with no operator-review record. Showing one linked, explicitly illustrative review would make the human handoff concrete.
5. **Commercial and version state requires too much interpretation.** The hero says “MIT licence,” while the repo explicitly records unresolved commercial-use questions for the loaded weights. The v2 link opens an active older product without an on-page retirement notice. Current schema 0.5 versus stored 0.4 is disclosed, but still asks the viewer to reconcile multiple states.

The release history contains much of the necessary comparison. It needs a short synthesis near the beginning, not another page of history. Preserve the current scientific visual language. See **T01**, **T11**, **T12**.

## The demo I would put in front of the VP

Target a **five-minute core**, with the current 15–16 minute script available for depth. This is a proposed presentation budget, not a performance measurement.

| Segment | What to show | What the VP should learn |
|---|---|---|
| 0:00–0:45 | Three-row v2/v4 comparison | Real data exposed weak assumptions; v4 changed the decisions and evidence accordingly |
| 0:45–2:00 | Calibrated HT29 example, reading, band, target, review reason | Better measurement plus a visible boundary on what it can decide; disclose EVICAN's non-blind status |
| 2:00–2:45 | Dense-range aggregate and one fine-tuned comparison, explicitly experimental | Adaptation is promising; the aggregate and failed criterion matter more than a selected attractive image |
| 2:45–4:00 | Reading → illustrative review → change → checkpoint tamper check | How a host can trace an exception and a model/configuration change; clearly distinguish implemented, demonstrated and missing controls |
| 4:00–5:00 | One-setup pilot card | Exact collaboration requested, limits, deliverables, go/no-go criteria |

Suggested opening:

> v2 demonstrated the image-to-action workflow. Real-image tests showed where its confidence and fault claims did not hold. v4 adds setup-specific calibration, measured error bands and a stronger record of the decision. It is ready to be evaluated on one imaging setup; it has not established autonomous passage or contamination clearance. The proposed next step is a bounded, labelled-data pilot with the criteria fixed before scoring.

Do not lead with an oversized contamination stress test, a 3D rotation, or a list of model names. Keep those available as technical detail. Do not imply the fine-tuned demo is the shipped decision model. Do not describe an error band estimated across a setup as knowing this individual image's actual error.

## The pilot the VP can reasonably sponsor

**Phase 1: offline evidence.** Agree the intended confluency definition and annotation protocol; name the instrument/objective, image encoding, cell types and relevant density range. Split by appropriate independent biological/acquisition units before fitting. Decide sample size from the desired precision and failure tolerance; the existing minimum of ten dense images is a measurability floor, not proof of production adequacy.

**Phase 2: frozen shadow evaluation.** Run the shipped baseline and proposed calibration on the same held-out inputs. Fine-tuning is a separately labelled candidate. Capture the host's current decision as a comparator. Fix metrics and thresholds beforehand; report early passage, missed readiness, review/reimage frequency, decision coverage, per-setup/subgroup error, latency and reproducibility. No automatic vessel actuation.

**Deliverable:** one decision report, input/annotation manifest, frozen model/config identities, per-image results, a replayable record set and a recommendation to stop, gather more data, or proceed to a separately approved integration test.

**Business questions to measure, not invent:** operator minutes per exception, re-image capacity consumed, usable decisions per visit, inference cost at realistic batch sizes, turnaround including queues, and engineering effort to fit the existing host. A model that achieves high agreement by deferring almost every important image may be safe as a reviewer but weak as automation.

**Separate commercial gate:** the repo itself says the assembled pipeline is not cleared for commercial use pending review (`README.md:574`). This review does not make a new legal determination. The owner needs an explicit clearance/replacement workstream before promising commercial deployment; fine-tuning the same base is not evidence of clearance. Keep that ownership question separate from what agents can implement.

## Agent order and stop conditions

1. **Before the VP meeting:** T01 narrative/pilot card; T12 factual consistency, broken link and explicit demonstration states; T11 accurate code/model licence labels. Disclose the runtime gaps rather than claiming them fixed.
2. **Before relying on v4 outputs in a host evaluation:** T03–T09 correctness and provenance contracts. T06, T08 and T09 can be developed independently; T03/T04/T05/T07 need one coordinated schema/policy plan.
3. **Before claiming measurable operational improvement:** T02 paired comparison and T10 preregistered target-instrument pilot.
4. **Before production:** clear the separate commercial gate, finish the host durability/retry/identity boundary and validate the integrated system. This is not a reason to block a candid, non-actuating research demo.

Do not restart SPC, growth-stall detection, instrument drift, or classifier retraining just to make the upgrade look larger. Do not relax acceptance criteria after seeing results. Do not publish, merge or change the preserved v2 deployment as a side effect of these tickets.

## Review method and limits

Core review covered current product/host/demo documents, superseded specifications and review notes, result reports and evaluation scripts, pipeline/rules/profiles/models/approvals/records, console construction, website routes, deployment and CI. Private call context informed the audience interpretation; personal details are intentionally absent here.

The UI critique used independent assessments: **A `/root/vp_design_review`**, **B `/root/site_evidence_review`**. A inspected the rendered home/records/releases/v2 pages without seeing B's detector output. Its heuristic assessment is **23/36**, a qualitative design judgment, not a product-readiness metric:

| Heuristic | Score / 4 | Main issue |
|---|---:|---|
| System status | 3 | Action below opening viewport |
| Match to user's world | 2 | Pilot decision buried by mechanics |
| User control | 3 | Broken record shortcut |
| Consistency | 3 | Release/schema/stored-state interpretation |
| Error prevention | 3 | Good caveats, incomplete licence label |
| Recognition over recall | 2 | Upgrade requires reconstructing history |
| Efficiency for repeat tasks | n/a | Evaluation/persuasion surface |
| Minimalism | 3 | Strong imagery; explanatory density |
| Error recovery | 1 | Broken shortcut without feedback |
| Help/documentation | 3 | Extensive, organized around features |

B's source detector returned 21 advisory token-consistency findings (6 font-size, 15 color), all in `site/src/styles.css`; these are not evidence of 21 UX defects. Black image masks/outlines and syntax colors are plausible intentional choices. The higher-value issues are the actual journey and record shortcut. Narrow-screen inspection found no document overflow at 390px, but release-note discovery depends on horizontally scrolling navigation.

Validation: **120 selected Python tests passed**, **2 browser-verifier unit tests passed**, site production build passed, generated Space copies passed `--check`. Nine additional local probes reproduced the behaviors documented in the evidence file. No model retraining or full GPU benchmark was run. The weight-reload reproduction uses a model stand-in to isolate lifecycle behavior. Browser inference was not rerun; existing dry-run results remain existing evidence, not new observations.

The working tree already contained edits in README/status/data/demo documentation and untracked files. They were preserved. Current published pages were inspected separately from the working tree; this review does not assert that all local edits are deployed.
