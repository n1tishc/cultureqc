# v4 versus v2: executable agent backlog

> **Narrative correction, 2026-10-16:** v4 must stand alone as a product. The approved [standalone design](2026-10-16-v4-standalone-product-design.md) and [implementation DAG](../specs/standalone-product-site/README.md) replace comparison-first T01 requirements. T02 is internal validation work, not a homepage prerequisite. Correctness tickets remain in force.

Parent: [VP review](2026-10-15-v4-vs-v2-vp-review.md). Reproductions: [evidence](2026-10-15-v4-vs-v2-evidence.md). Reviewed state: `2cd691a` plus existing local edits, 2026-10-15.

**These are proposed upgrades, not claims that fixes have landed.** P1 means a correctness/evidence gap to close before the corresponding capability is relied upon; P2 means a presentation or reproducibility improvement. No finding is labelled a current production incident. “Before meeting” work can be small even when its strategic impact is high.

## Shared instructions for implementing agents

- Preserve existing user changes and historical evidence. Do not overwrite a preregistered result, silently re-score its test set, rewrite old audit records, or relabel experimental evidence as shipped performance.
- Treat site v0.4, rules_v0.5, record schema 0.5 and stored schema 0.4 as separate versions. The old spec filenames and `docs/PRODUCT.md` are not reliable current implementation maps.
- `deploy/*/culture`, `config` and `configs` copies are generated: edit root modules, then use `deploy/sync_space.py`. Do not manually maintain duplicate fixes.
- Existing evidence-based demotion and limits remain in force. No new contamination, regulatory-compliance, universal accuracy or commercial-clearance claim follows from completing a code ticket.
- For schema/policy changes, make a migration plan, keep historical verification working, regenerate new demo artifacts intentionally, and show old/new behavior on the same inputs. Do not retroactively replace old records.
- Regression tests should exercise the failure and the public behavior. Passing the current tests is insufficient: this review reproduced issues while 120 targeted tests passed.
- Each handoff must name changed files, tests run, before/after behavior, remaining uncertainty and any separately required model computation or release action.
- No publishing, remote configuration changes, commits, merges or retraining are authorized by this review document itself. Follow the user's actual authorization in the implementation session.

## Work map

| Ticket | Priority | Workstream | Dependency | Completion proves |
|---|---|---|---|---|
| T01 | P1 | Standalone product proposition and short demo | Design approved; execute standalone DAG | Product value and evaluation request are understandable without v2 context |
| T02 | P1 | Matched v2/v4 decision comparison | Frozen policy from T03/T04; T05 for reproducible records | Version differences measured on a common protocol |
| T03 | P1 | Calibration scope versus action eligibility | Coordinate with T04/T05/T07 | A fitted band alone cannot authorize unsupported passage |
| T04 | P1 | Unknown inputs, absent checks, reasons | T03 policy agreement | Invalid/unsupported conditions have explicit outcomes |
| T05 | P1 | Complete reproducible decision record | Coordinate schema with T03/T04/T07 | A decision can be replayed from recorded structured inputs |
| T06 | P1 | Loaded-model identity | None | Recorded approval/hash describes the model that actually ran |
| T07 | P1 | Configuration activation/change control | T03/T05 schema contract | Effective approval and runtime configuration agree |
| T08 | P1 | Concurrent audit append | None | Ordinary multi-writer use cannot fork the chain |
| T09 | P1 | Controlled image ingestion | T05 for preprocessing provenance | Raw input encoding cannot silently change measurement scale |
| T10 | P1 | Target-instrument pilot specification | T01; policy/evidence from T02–T05 | A partner can approve a bounded evaluation, not an open-ended integration |
| T11 | P1 | Release and commercial-readiness boundary | None for documentation; owner for clearance/deployment | Users know what code, models and endpoint they are evaluating |
| T12 | P2 | Proof journey and current documentation | T01; event example may follow T05 | Links, examples and agent instructions match the current product |

Suggested ownership: one agent owns T03/T04 policy and coordinates the T05/T07 record contract; separate agents can own model lifecycle, log persistence, and narrative/evidence work. This is a division of work for later execution, not a requirement to spawn all agents immediately.

## T01 — Make the standalone product and VP request explicit

**Problem (updated 2026-10-16):** the implemented comparison-first journey makes release history the product story. The owner wants cultureQC to demonstrate independent value, with an understandable path to a setup-specific evaluation.

**Evidence:** `site/src/pages/Home.jsx:98`, `site/src/components/Shell.jsx:94`, `site/src/components/Sections.jsx:467`, `docs/DEMO_SCRIPT.md:1`. The current script is 15–16 minutes before questions.

**Implementation specification:** follow the [standalone DAG and task packets](../specs/standalone-product-site/README.md), which replace the coarse S1–S4 handoff. Lead with microscopy and understandable analysis; demonstrate measurement, a review boundary and exact records. Keep comparisons in release notes and technical evaluation, not the homepage or core presentation. Retain the evaluation proposal and distinguish shipped, experimental and unresolved capabilities.

**Acceptance:**

- A reviewer can identify the product's job, output and reason, host responsibility and next evaluation without knowing v2 existed.
- No homepage release comparison or incompatible cross-version accuracy chart; historical comparisons retain their protocol limitations.
- Fine-tuning is labelled experimental and not used for decisions; the failed dense-range criterion and replication limitation remain accessible alongside the gain.
- The pilot card states setup/data responsibilities, non-actuating evaluation, output deliverables and criteria fixed before scoring; no invented ROI, schedule or sufficient sample size.
- A timed walkthrough fits the proposed five-minute core. Scientific sources remain available without dominating the first view.

**Do not:** claim competitor capabilities are absent without evidence, or revive the synthetic contamination demonstration as the main proof.

## T02 — Produce a matched comparison for internal validation

**Implementation status (2026-10-20):** first bounded EVICAN cached-policy replay
implemented locally: 33 expert-mask images, exact archived v2 rules, current
source/input hashes, four sequential variants, explicit timing assumptions and
unavailable checks. Every paired output and all/dense/near-target denominators
are reproducible without inference or the compute cache. The
[C2C12 workload-only companion](2026-10-20-c2c12-workload-replay.md) now also freezes
1,228 held-out frames, reports separate review/reimage burden and preserves
14 sequence / 3 experiment groups without treating model readings as truth.
**T02 remains partial**: independent target-range evidence, authenticated weight
provenance and any justified end-to-end reconstruction remain outstanding.
See [protocol](../specs/matched-policy-comparison.md)
and [results/handoff](2026-10-20-matched-policy-replay.md). This is not an end-to-end
model comparison, a fine-tuning claim or a website change.

**Problem:** `results/v02_vs_v03_flags.md` compares detector behavior, not the full v2 versus v4 decision policy. Lower false-review rates alone do not show useful automation. The current review-rate and confluency studies do not supply a complete same-input end-to-end version comparison.

**Start in:** `scripts/compare_v02_v03_flags.py`, `scripts/review_rate.py`, `scripts/confluency_mcellseg.py`, `results/v02_headline.md`, baseline `e2274dd:culture/rules.py`.

**Implement:** a frozen, machine-readable comparison manifest naming baseline/current commits, input hashes, weights, effective policies, target, timing, setup and split. Replay both versions' applicable rules on common inputs; if old inference cannot be reconstructed, label the result a cached-policy replay rather than an end-to-end comparison. Separate the effect of classifier demotion, calibration and decision policy. Preserve the historical code/outputs.

**Report:** confusion/action counts, early passage, ready-called-continue, review and reimage separately, correct decided coverage, performance around the target, sample/independent-unit counts and uncertainty. A before/after workload calculation must use measured review time and explicitly assumed workload, or remain a labelled scenario.

**Acceptance:**

- Every row has both versions' outputs for the same image/context and can be regenerated by one documented command without hidden files or new tuning.
- Distinguish real masks from Cellpose-derived proxy truth; do not treat C2C12's own model reading as independent confluency truth.
- No “zero review” success on an evaluation with no target-reaching cases; report this as insufficient decision evidence.
- Report dense-subset burden beside all-image burden. Do not substitute normal-frame anomaly rate for human-review rate.
- Declare unavailable historical data honestly; do not recreate v2's missing synthetic headline artifacts from approximate numbers.
- If additional model inference is necessary, produce the exact bounded compute request and inputs before running it.

## T03 — Separate calibration validity from permission to recommend passage

**Implementation status (2026-10-18):** implemented locally as rules_v0.6. Existing
measurement values are retained; all shipped profiles explicitly lack passage
approval. Setup/model/cell-line and reading/target scope checks, profile validation,
record fields, console messaging and migration guidance are covered by regression
tests. Synthetic eligible fixtures are not biological evidence. See
`docs/specs/passage-eligibility.md` and
`docs/reviews/2026-10-18-passage-eligibility-fix.md`. Host activation remains pending;
missing-check semantics and timing honesty remain T04, not solved by this gate.

**Problem:** a profile can be `validated` with A2/A3/A4 “not measurable,” yet its band can authorize passage. Current MSC configuration reproduces this at 90%/80%.

**Start in:** `scripts/write_profiles_config.py:68`, `configs/confluency_profiles.yaml:64`, `culture/profiles.py:74`, `culture/rules.py:183`, `tests/test_rules_band.py`, `tests/test_profiles_config.py`.

**Implement:** distinct representation of measurement calibration, validated operating scope and action eligibility. Scope must cover relevant setup identity and decision range; a coarse status string or the existence of a band must not imply passage validation. Preserve numerical readings for research use while making non-eligible action output explicit. Validate profile schema on load; an unknown requested profile must not silently become a successful-looking configured request.

**Acceptance:**

- The exact MSC probe in the evidence file cannot return an actionable automatic-passage recommendation based only on the existing A1/A5 evidence.
- A profile with insufficient dense-range evidence stays useful for measurement but is visibly ineligible for automatic passage under the supported policy.
- Invalid status/value combinations, negative/nonfinite bands, unknown IDs and setup mismatches produce a documented error or explicit unsupported status.
- Matching an approved eligible profile is exercised with a synthetic rule fixture; this fixture is never presented as clinical/biological validation.
- Old measured results are unchanged. New eligibility rules get a new policy version and a migration explanation.
- UI, schema, examples and host docs distinguish “calibrated measurement” from “validated decision range.”

**Policy boundary:** the conservative eligibility proposal is a new product policy, not a claim that the old preregistration was implemented incorrectly. Surface the exact behavior change for review.

## T04 — Make missing information and failure behavior explicit

**Update, 2026-10-18:** implemented locally in `rules_v0.7`: explicit required/
optional/not-applicable checks, unknown timing, factual interval holds, finite
input/record safeguards and advisory-only output. See the
[policy contract](../specs/missing-checks-and-timing.md) and
[implementation report](2026-10-18-missing-checks-and-timing-fix.md).
No new detector thresholds, operational approval, push or deployment.

**Problem:** `None` quality/anomaly checks can permit passage; absent passage timing passes the timing gate; NaN reads as continue; a recent-passage hold generates a mathematically false reason. Uncalibrated low readings can miss readiness.

**Start in:** `culture/rules.py:153`, `culture/pipeline.py:135`, `culture/rationale.py`, `tests/test_rules_band.py`, `tests/test_rules_anomaly.py`, `docs/host_platform.md`.

**Implement:** define required/optional/not-applicable checks per supported operating policy, distinguish unavailable from negative, and validate finite input ranges. Record stable reason codes plus factual explanations. Distinguish advisory/shadow output from host-actionable output, including uncalibrated `continue` and `feed`. Specify timeout/reimage retry ownership with the host; do not invent an infinite automatic retry loop.

**Acceptance:**

- Missing a policy-required check cannot silently produce an actionable passage. Optional/not-applicable checks remain distinguishable and do not force blanket review.
- NaN, infinity, out-of-range percentages, invalid targets/bands and invalid elapsed times cannot produce normal decisions or nonstandard JSON numeric values.
- 95% at an 80% target six hours after passage has a timing-based reason, never “below target.”
- Unknown timing has an explicit policy status; “unknown” does not silently satisfy an operational prerequisite.
- A model under-read on an unsupported setup is not presented as proof that no action is needed. Advisory numeric results may remain available.
- Tests cover boundaries/equality, combined failure precedence, absent versus failed checks, and parity between console and library.

## T05 — Make every decision reconstructible from its record

**Update, 2026-10-18:** implemented locally with schema 0.6 input/config snapshots,
pure named-policy replay, nullable host capture time and shared map provenance.
The exporter replay command is now read-only and refuses legacy missing-input
records. See [the contract](../specs/decision-replay.md) and
[validation report](2026-10-18-decision-replay-fix.md). No push/deployment.

**T04 handoff (resolved by read-only verification):** migrate/test `scripts/export_demo_examples.py --rederive`:
its legacy tuple-only rewrite omits the new structured eligibility/decision
contract. Do not regenerate historical examples as current-policy evidence
before this replay/migration work is complete.

**Problem:** consumed target/timing/line configuration is absent from structured records, image capture time is fabricated at analysis time, and the library lacks the console's map provenance.

**Start in:** `culture/pipeline.py:40`, `culture/pipeline.py:164`, `culture/schema.json`, `demo/analysis.py:194`, `culture/records.py`, `docs/host_platform.md`.

**Implement:** persist the effective rule input snapshot, policy/config identity, explicit unknowns, capture timestamp supplied by the host, and separate analysis timestamps. Record map provenance consistently or document a deliberate per-surface distinction. Snapshot the configurations actually used rather than hashing potentially changed files after the fact. Include effective anomaly-config paths when environment overrides are used.

**Acceptance:**

- A pure replay function takes a finalized record and the named policy version and reproduces action plus reason code without model inference or reading mutable local config.
- Different targets/timing inputs producing different actions are distinguishable as structured values, not merely prose.
- `captured_at` round-trips an old host timestamp and is never silently replaced with inference time; missing timestamp provenance is explicit.
- Same-image/context console and library results share equivalent decision/provenance fields; intentionally absent visuals are explained.
- Historical schema 0.4/0.5 verification continues to work. New fields are versioned and validated before appending new records.
- Tests change a config during a stand-in inference and prove the record identifies the configuration used, not merely whichever file existed at completion.

## T06 — Bind approval to the loaded model, not only its current file

**Update, 2026-10-18:** implemented locally with private verified snapshots,
replacement refusal/reload and per-inference record hashes. Fixture lifecycle
and record regressions are covered. [Real-Cellpose local CPU parity](2026-10-18-cellpose-release-validation.md)
now passes; target-host provisioning/capacity validation remains a deployment gate.
See [implementation and limits](2026-10-18-model-identity-fix.md).
This does not close T03–T05 or T07–T09. Nothing pushed or deployed.

**Problem:** the shipped Cellpose singleton survives an approved file replacement. `require()` checks the replacement file while inference runs the previously loaded weights.

**Start in:** `culture/seg.py:103`, `culture/seg.py:149`, `culture/weights.py`, `tests/test_approvals.py:168`. `culture/finetuned.py` already keys its cache by hash; assess reuse of that principle without a broad refactor.

**Implement:** bind each loaded model instance to the verified immutable artifact identity used at loading. On a supported replacement, reload safely or require a restart and refuse until then. Prevent check/load races; record the actual loaded artifact, not a separately rediscovered default cache file.

**Acceptance:**

- Load A, replace with approved B between calls: either B is loaded and its distinct output recorded, or inference refuses pending a documented activation/restart. Never output A with B's hash.
- Replacement with unapproved B refuses; rollback to an explicitly approved artifact behaves predictably.
- Missing file, failed load and concurrent replacement do not retain a misleading successful check.
- Stand-in lifecycle regression is required; one bounded real-model parity run is a release validation step when resources permit, not needed to discover the bug.
- The model instance, `model_check`, `model_weights_hash` and emitted runtime version agree.

## T07 — Turn change records into a well-defined activation contract

**Implementation status (2026-10-19):** local implementation uses the explicitly
host-managed configuration option, not a new local release approval authority.
Schema 0.7 records that distinction and the consumed configuration identity.
Model checks now respect effective time and verify/select from one log snapshot;
anomaly bank replacements cannot reuse a mismatched cached identity. Host
approval, atomic deployment and authentication remain external responsibilities.
See [contract](../specs/configuration-activation.md) and
[validation report](2026-10-19-activation-controls.md). Nothing pushed or deployed.

**Problem:** model approvals ignore effective time; profiles/configs are recorded but explicitly not checked against approvals. Profiles are cached forever by path, while config files are hashed afresh. Recording and enforcing a change are different capabilities.

**Start in:** `culture/approvals.py:18`, `culture/approvals.py:82`, `culture/profiles.py:71`, `culture/anomaly.py:200`, `culture/pipeline.py:23`, `configs/approved_changes.jsonl`, `scripts/approve_change.py`.

**Implement:** specify whether activation is enforced by cultureQC or the host. For a cultureQC-managed deployment, resolve approved effective artifact identities before a run, including eligible profiles/rules/required config. Respect effective time and make rollback/invalid approval behavior explicit. Ensure caches are keyed by immutable identity or a documented restart boundary. A host-managed mode must say so explicitly in records and documentation instead of claiming a local check.

**Acceptance:**

- A change dated 2099 is not active now. Tests cross the effective-time boundary with a controlled clock, including a log that does not change on disk.
- A profile changed without required activation cannot silently become the new eligible policy; its full before/after identity is traceable.
- No reading combines a cached old profile with a newly hashed config file and implies both were the active configuration.
- Anomaly banks/configs remain a matching pair after supported updates; path caching cannot bypass identity validation.
- UI says “recorded change” versus “enforced approval” accurately. Host authentication/signatures are not invented locally.
- Existing historical profile-change records are preserved; add a documented baseline/migration if a new enforcement registry is introduced.

## T08 — Keep the audit chain intact under ordinary concurrent use

**Implementation status (2026-10-19):** implemented locally for cooperating
threads/processes on a regular local POSIX log. The writer locks full-chain
verification, finalization, append and file/directory synchronization; no cached
predecessor remains. Corrupt/torn tails are refused without altering history.
Verification/checkpoint readers share the lock. Host storage, external anchors,
idempotency and authorized recovery remain required. See
[contract](../specs/concurrent-audit-append.md) and
[validation report](2026-10-19-concurrent-audit-append.md). Nothing pushed.

**Problem:** two `RecordWriter` instances can cache the same predecessor then append conflicting links. `deploy/hf-space/api.py` documents this and uses a local lock; direct library users and separate workers are not protected by that lock.

**Start in:** `culture/records.py:93`, `culture/records.py:115`, `tests/test_records_chain.py`, host integration boundary.

**Implement:** serialize tail-read/finalize/append as one transaction across the documented writer boundary. A process-safe locking strategy, transactional store or explicitly enforced single-writer service is acceptable; do not prescribe a new database without need. Detect a corrupt tail rather than silently scanning past malformed JSON. Define what is durable when append returns.

**Acceptance:**

- The two-writer sequential interleaving from the evidence file produces one valid chain with both records or a clear rejected concurrent operation.
- A bounded multi-process test with unique input IDs verifies count, uniqueness and all links after restart.
- A partial/corrupt last record produces a detectable failure and preserves the evidence; never silently repair history.
- Document durable storage, externally retained checkpoint and retry/idempotency ownership. A hash chain alone is not exactly-once delivery.
- Keep both single-record tamper and anchored rewrite/truncation verification working.

## T09 — Define and record the image decoding contract

**Implementation status (2026-10-19):** implemented locally with a shared,
single-frame uint8 decoder. High-bit-depth inputs are refused, not guessed or
auto-scaled. Schema 0.8 binds original bytes, the decoding policy and output pixels;
console, API and library refuse unsupported input before inference. Historical
records remain unchanged. See [contract](../specs/controlled-image-ingestion.md)
and [validation report](2026-10-19-controlled-image-ingestion.md). Nothing pushed.

**Problem:** raw 12-bit-in-16-bit TIFF input silently becomes near-black under the current OpenCV read flag. Dataset-specific offline preparation does not protect incoming host images.

**Start in:** `culture/pipeline.py:83`, console upload handling in `demo/app.py`, `scripts/fetch_c2c12.py`, `culture/schema.json`, `docs/host_platform.md`.

**Implement:** inspect bit depth/format before conversion; accept a documented setup-specific mapping or reject unsupported encoding with an actionable message. Preserve the original image identity and record preprocessing identity. Decode/hash from the same immutable bytes or a controlled snapshot.

**Acceptance:**

- Fixture with uint16 maximum 4095 either maps according to an explicit fixed 12-bit policy or is refused. It never silently passes as an ordinary uint8 image with maximum 15.
- Tests cover uint8, full-range uint16, 12-bit stored in uint16, corrupt images and the supported multichannel/page policy.
- No auto-contrast chosen independently per image without declaring and validating that behavior for the setup.
- Console and library apply equivalent preprocessing, with recorded transform and original-byte hash.
- A changed file between decode and hashing cannot produce a record whose image hash names different bytes from those analyzed.

## T10 — Write the actual partner pilot protocol

**Specification status (2026-10-19):** the proposed
[one-setup pilot protocol](../specs/partner-pilot.md) and
[approval worksheet](../specs/partner-pilot-approvals.md) are written. They cover
confluency/audit-first scope, the existing partner workflow, separate calibration
and fine-tuning arms, independent units, proposed confidence-bound gates,
coverage/safety denominators, sample-size signoff, access/retention and run
artifacts. See the [handoff](2026-10-19-partner-pilot-protocol.md).
This completes the proposed-specification deliverable, **not partner approval,
E0 readiness or a scientific evaluation**. Actual setup, owners, counts, budgets
and signed acceptance remain pending. No data scored or thresholds changed.

**Problem:** the repo has substantial experiments but no compact, decision-ready target-instrument plan tying annotation, benefit and integration effort to a go/no-go outcome.

**Start in:** `docs/host_platform.md`, `results/confluency_profiles.md`, `results/confluency_mcellseg.md`, `results/confluency_mcellseg_swap.md`, `docs/DEMO_SCRIPT.md`.

**Deliver a proposed protocol, before collecting/scoring new partner data:** intended use; one target setup; image/annotation definition; independent-unit split; target-range representation; primary metrics; statistical precision plan; all acceptance and stop rules; rights/access/retention responsibilities; run manifest; output artifacts; owner of each decision. Include the partner's existing workflow as the operational baseline.

**Acceptance:**

- No conflation of statistical uncertainty with per-image actual error, or frame count with independent sample count.
- Required sample size is justified for the proposed decision claim; “ten dense images” is not automatically enough because an old criterion used ten.
- Decision correctness is paired with coverage and separate early-passage/missed-readiness counts. Aggregate accuracy cannot pass solely by abstaining on every passage-ready image.
- Annotation definition is explicit: the supplementary dense-image study reports 29–31 pp differences between instance and lazy masks, so target truth cannot be assumed interchangeable.
- Calibration-only and fine-tuned candidates are separate arms with fixed procedures. New test data is not used to choose cutoffs or revise pass marks.
- The first run is offline/shadow; review findings do not operate the instrument. Host integration and commercial clearance are separate gates.
- Unmeasured business outcomes remain blank fields or labelled scenarios until observed; include review/reimage cost, latency tails and setup effort.

## T11 — Make evaluation, deployment and commercial boundaries legible

**Local implementation delivered (2026-10-19):** [release-state map](../specs/release-state.md),
[host evaluation contract and commands](../specs/host-evaluation.md),
`scripts/host_evaluation.py`, pinned lightweight dependencies and a dedicated CI
job. The site now states Code: MIT, stored execution and unresolved pipeline
commercial status outside disclosures. See the
[T11 handoff](2026-10-19-release-boundary-and-host-evaluation.md).
This does not approve the pilot, clear rights, verify remote deployment or publish
anything; source/deployment reconciliation remains owner-controlled.

**Problem:** a MIT hero label overgeneralizes the repo licence; the current public API is v2; a v4 console, stored artifacts, current schemas and a research branch coexist. This is disclosed in places but too easy to misunderstand.

**Start in:** `site/src/pages/Home.jsx:117`, `site/src/components/Shell.jsx`, `deploy/README.md:5`, `README.md:574`, `.github/workflows/tests.yml`, deployment manifests.

**Implement now:** qualify “Code: MIT,” link the existing component terms/status, and add one release-state table mapping each surface to product/rules/schema/model/config/source identities. State that the v4 site displays stored outputs and the legacy API is not a v4 integration endpoint. Prepare a minimal library-based host contract harness; a new HTTP service is not required for an offline pilot.

**Acceptance:**

- A VP sees the repository's current unresolved commercial status without searching release-note details. No new legal conclusion is inferred from dataset licences alone.
- Current vs archived releases, stored vs live vs experimental outputs are obvious and linked to exact artifacts where practical.
- A clean-environment evaluation command and dependency/artifact manifest exist; network/private-weight prerequisites and disabled optional paths are stated.
- Missing/check-failed/timeout paths produce specified host outcomes. p95/queue/batch claims remain unmeasured until benchmarked on target hardware.
- A source/default-branch/deployment reconciliation plan is reviewable. Do not merge, tag, change repository settings or modify the intentionally preserved v2 site without that action being authorized.

**Owner-held gate:** identify who obtains clearance or chooses a replacement model and what evidence closes the gate. An agent cannot resolve this by editing the README to say “commercial.”

## T12 — Fix the proof journey and stale agent guidance

**Implementation status (2026-10-20):** implemented locally. Exact-record and legacy
navigation, a separately labelled illustrative review extension, and current agent
guidance are in place. 119 targeted Python tests, 15 Node tests, build, deployment-copy
parity and desktop/mobile keyboard journey checks pass. Subsequent
[post-update visual acceptance](2026-10-20-proof-visual-acceptance.md) adds inspected
desktop/mobile review captures and passes the chain-link scrolling retest without
the earlier workaround. Human AT/200% zoom verification remains pending. See the
[T12 handoff](2026-10-20-proof-journey-and-current-guidance.md).

**Problem:** the core record link is broken; the interactive site chain lacks an example review; current context files contain obsolete v2 product instructions and contradictory limitations.

**Start in:** `site/src/components/Stage.jsx:331`, `site/src/pages/Home.jsx:75`, `site/src/components/Records.jsx`, `site/assets/build_data.py`, `docs/PRODUCT.md:11`, `README.md:429`, `docs/REPO_MAP.md`, site surface brief.

**Implement:** link the stage directly to `/records#chain` after verifying that anchor; include a clearly marked illustrative human-review event linked to a displayed reading, with the same integrity checks as other records. Rewrite current product instructions to match demoted classifier, calibrated bands and actual React/Gradio surfaces. Mark historical repo maps/specs as historical rather than overwriting the research record.

**Acceptance:**

- Clicking “verify the chain” from an already loaded homepage reaches the records chain; direct old URLs and keyboard navigation also work.
- One displayed exception can be followed through a labelled review event and the original reading remains unchanged. A fabricated demo identity is explicitly illustrative, not a claimed real approval.
- README no longer says Analyze has no quality gate: C2C12's configured gate runs in `demo/analysis.py:112`; other profiles without gates remain explicitly different.
- Remove stale claims that no React/FastAPI code exists or that demoted Grad-CAM contamination boxes are the current product's main proof.
- Do not transfer EVICAN's observed bias to C2C12 as an established correction; C2C12 lacks independent confluency labels in this evidence set.
- Show current local schema 0.8 / rules_v0.7 versus historical stored 0.4 / rules_v0.5 deliberately; update a new stored demo only through the artifact-generation path, without rewriting historical source logs.
- Desktop/mobile browser pass verifies action visibility, comparison discovery and review-chain navigation. Token advisories are secondary; do not rebrand the site.
- Reconcile the orphaned site surface brief (`site/src/App.jsx` no longer exists) when updating agent context; do not let future agents follow a nonexistent target.

## Completion checklist for the upgrade program

- [ ] VP can explain the measured upgrade and proposed pilot without reading release-history details.
- [ ] A paired benchmark separates measured gains from removed unsafe claims and increased abstention.
- [ ] Decision eligibility is narrower than generic calibration success and survives missing/invalid inputs.
- [ ] Every new action can be replayed from its immutable structured record.
- [ ] Active model/configuration identities agree with the bytes and policy actually used.
- [ ] Concurrent append, restart, corrupt tail and retry behavior have tested contracts.
- [ ] The target image encoding and annotation definition are controlled.
- [ ] Experimental fine-tuning remains separate until it passes a new approved evaluation.
- [ ] Commercial and host-integration prerequisites have named owners and explicit unresolved status.
- [ ] No historical benchmark, log or archived v2 deployment was silently replaced to improve the story.
