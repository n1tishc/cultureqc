# T10 — One-setup partner pilot protocol

**Status: proposed, not approved — 2026-10-19.** This is a decision-ready design
for an offline evaluation, not an experiment authorization, completed study or
deployment plan. Resolve and sign the [approval worksheet](partner-pilot-approvals.md)
before collecting/scoring new partner study data. No hardware, partner, budget,
sample count or acceptance threshold is assumed approved.

Approval can be staged: a separately bounded development-only acquisition and
annotation phase may estimate variation/cost before the confirmation sample
plan is signed. Its authorization must already resolve setup, rights, reference
rubric, access, budget and stopping limits. Those data stay development-only;
no final-test collection or performance claim follows from that authorization.

## 1. The VP decision

Authorize a bounded evaluation of **setup-specific confluency measurement and
traceable review records** against the partner's existing workflow. Deliver a
go/no-go report for a subsequent supervised shadow phase, not permission to
automatically passage, feed, discard or release cultures.

- Core: one cell line, one instrument/capture configuration and one vessel type;
  independently annotated coverage, explicit uncertainty, original-image and
  model/configuration identities, replayable decisions and linked review events.
- Fine-tuning: a separately costed candidate arm, not a prerequisite or an
  already-proven improvement on this partner's setup.
- Contamination and growth: optional E1/E2 research packets. A useful confluency
  result cannot validate either detector; a negative image cannot clear a culture.
- Success has two parts: measurement quality **and** records that a reviewer can
  follow. Operator savings, ROI, throughput and commercial clearance are not
  inferred from an accurate reading or a valid hash chain.

The initial phase runs on copied acquisitions with no instrument-control path.
Routine culture handling and established contamination testing remain unchanged.

## 2. Setup and capture contract

The laboratory lead supplies the exact instrument, modality, objective/NA,
specimen-plane pixel size, camera, exposure/illumination, dimensions, vessel,
cell line/source, passage range, medium, stage and environmental conditions.
These become one versioned `setup_id`; relevant changes invalidate pooling and
require a new approved scope. Do not borrow the public datasets' pixel scale.

Starting acquisition proposal: 10× phase contrast, 4–5 repeatable distributed
FOVs every 2 hours, subject to actual instrument compatibility. This is an
acquisition example, not evidence that the optics resolve bacteria or that
two-hour growth increments are measurable. The lab must fix placement, observed
area, registration tolerance and allowed missing FOVs before allocation. See
the [sourced acquisition proposal](../reviews/2026-10-17-researched-pilot-thresholds.md).

The primary measurement is **coverage of the acquired valid image area**, not
whole-vessel coverage. For a visit, aggregate coverage with frozen valid-area
weights across non-overlapping FOVs; do not average duplicated overlap. The lab
must approve that sampling scheme before using visit results as vessel proxies.
Report between-FOV variation; an unsampled region is not proven healthy.

Retain original sensor files plus any export mapping. The current live decoder
accepts only single-frame uint8 grayscale/RGB with default orientation and no
transparency. A 12/16-bit acquisition requires a separately validated, fixed
export mapping and linked source/export hashes, or is refused. Per-image
auto-contrast is not an approved workaround. See [T09](controlled-image-ingestion.md).

## 3. Reference labels and operational baseline

Before model output is available, two qualified annotators independently mark
cell-covered area, using a written rule for cell edges, halos, debris, gaps,
dead/detached cells, overlaps and invalid pixels. A third reviewer adjudicates
disagreements without seeing model predictions. Keep both original masks,
adjudicated masks, valid-area masks, identities, timestamps and revisions.

Reference percentage = 100 × cell-covered valid pixels / all valid pixels.
Agree the rubric on development images; freeze it before final-test labelling.
If additional modalities inform labels, retain their provenance and disclose
that assistance. Instance masks for fine-tuning are a separate annotation
product, not an automatic substitute for coverage masks. The repository's
[dense supplementary study](../../results/confluency_mcellseg.md) found 29–31 pp
differences between instance and confluence-oriented masks on two dense images.

Report annotator disagreement before adjudication. Unresolvable reference
labels are recorded as indeterminate, with reasons, counts and sensitivity
bounds; do not silently drop hard images. Reference readiness is coverage ≥ the
approved target T (proposal: 80%) and is not a complete biological passage decision.
Other eligibility/timing/health conditions are recorded separately.

**Operational baseline H:** the partner's current SOP, including its human
estimate, action, review/reimage events and active operator time, recorded before
model assistance on the same visits. Independent adjudication, not H's decision,
defines measurement truth. If H uses additional views or assays, record them;
do not describe this as an equal-input algorithm comparison. Missing baseline
measurements make operational benefit unmeasured, not zero-cost success.

## 4. Arms, allocation and candidate freeze

| Arm | Fixed procedure and role |
|---|---|
| H | Existing partner workflow, unchanged; operational comparator |
| Z | Pinned base segmentation model, cutoff 0.0, no fitted band; measurement reference |
| C | Same base model with setup-specific cutoff and error band; core candidate |
| F | Optional retained fine-tuned model plus its own calibration/band; separate candidate |

All image arms use the same bytes, valid-area definition and aggregation. C/F
use the same allocated development/tuning images; extra F instance annotation
and training costs are recorded. Historical mCellSeg gains motivate F but do
not validate it here; unavailable historical scored weights must not be
replaced by illustration weights under the same identity.

Allocate development, tuning and final test by the highest connected unit:
shared source culture/lineage, vessel, time series or acquisition session must
not cross splits. Crops, augmented images and repeated visits are not independent
cultures. The custodian records globally consistent IDs, original image hashes,
prior use and labels. Previously inspected data cannot become an untouched test.

Recruit independent units below, near and above T. Freeze strata before scoring:
proposal `[0,60)`, `[60,70)`, `[70,80)`, `[80,90]`, `(90,100]` at T=80, with the
near-target region `[T−10,T+10]`. Both sides of T need separately powered counts.
The 60–90% historical dense endpoint is reported separately. If enrichment
changes the natural mix, report stratum results and frozen weights; do not call
the pooled review rate routine-workflow burden. Include a representative
consecutive-visit operational cohort rather than estimating workload from an
artificially balanced case set.

F trains only on development groups, never tuning/final-test groups.
Development fixes F's bounded training recipe/seeds and all candidate variants.
Tuning selects C/F cutoffs from −4.0 to +1.0 in 0.5 steps by equal-cluster-weight
MAE; ties choose closest to 0.0, then the smaller numerical cutoff. Band fitting
uses group-held-out residuals with the selection repeated within folds; freeze
the exact quantile/aggregation algorithm. A nominal 90% band is not a confidence
interval for mean error or a guarantee for any individual image.
Fit visit-level bands from visit-level residuals after the frozen FOV aggregation;
averaging per-image bounds does not establish visit-level coverage. Visit
aggregation and its evaluator are study tooling to implement, not a capability
claimed for today's per-image pipeline. Retain source reading hashes for every
derived visit result and keep those study artifacts separate from reading records.

The signed candidate plan fixes training budget, seed handling, band algorithm,
missing-data behavior, visit aggregation and the evaluation command. C is the
default primary arm. If F is selected instead, do so using tuning data before
test release; report all arms and do not pick a winner after seeing final scores.
The candidate lock retains exact artifacts/hashes, code/environment and approval.
Final-test access stays with a separate custodian until that lock is signed.

## 5. Endpoints and proposed acceptance rules

Every number below is a **proposal for approval**, not a universal standard or
an inherited partner requirement. Historical 5 pp MAE / 3 pp bias / 85% band
coverage motivate the measurement limits; the confidence-bound requirements,
coverage floors and safety budgets here are new, stricter study proposals.
Changing a limit after seeing test outputs requires a new untouched evaluation.

| Claim/gate | Endpoint and proposed rule |
|---|---|
| Core measurement | One-sided 95% upper bound on MAE ≤5 pp, both overall under frozen weights and in 60–90%; two-sided 95% bias interval wholly within −3 to +3 pp in 60–90% |
| Band validity | One-sided 95% lower bound on empirical coverage of the nominal 90% band ≥85%, overall and near T; also report width and missing-band rate |
| Usable measurement | One-sided 95% lower bound on valid paired output/reference coverage ≥90% of all scheduled visits, overall and near T; invalid/indeterminate visits stay in the denominator |
| Fine-tuning benefit, only if claimed | Paired C-minus-F absolute-error difference, equal cluster weight in 60–90%: one-sided 95% lower bound >0 pp, plus F independently meets all measurement gates; report annotation/training cost and both arms |
| Record integrity | Every successful run has schema 0.8 source/pixel/model/config provenance, exact named-policy replay and valid local chain plus independently retained checkpoint; each review links to its unchanged reading |
| Host boundary | No equipment actuation; missing checks, unsupported inputs, timeout and stale capture cannot be presented as a successful negative finding; fixture results and authentic study readings remain distinct |
| Optional decision confirmation | Lower 95% bound on correct-decided fraction ≥95%; lower bounds on decided coverage ≥50% both near T and among reference-ready visits; upper bounds on early-passage rate ≤1% and ready-called-continue rate ≤5% |
| Operational benefit | Descriptive until an owner approves a time/cost improvement margin and powered comparison; no ROI or productivity pass without that plan |

For decision endpoints, explicitly count passage / continue / review / reimage /
unavailable. Early-passage denominator is all reference-not-ready scheduled
visits; ready-called-continue denominator is all reference-ready scheduled
visits. Correct-decided fraction uses only passage/continue outputs with known
reference; decided coverage uses **all** scheduled visits in that stratum.
Also report correctness among passage calls, missed-ready counts, and total
review/reimage/unavailable burden. An all-review system cannot pass coverage.
Indeterminate labels have separate best/worst-case sensitivity bounds; if those
bounds change a gate outcome, the result is insufficient evidence.

**Actual runtime and hypothetical band decisions are separate outputs.** Current
rules are advisory and all shipped profiles lack passage eligibility. Report
actual runtime actions as emitted, including scope holds; never create an
eligible configuration to improve this pilot's action counts. A frozen offline
band-policy analysis may measure hypothetical passage/continue/review outcomes,
but label it counterfactual and non-actuating. It cannot establish current
end-to-end decision capability. Passing measurement gates alone permits only a
measurement-focused shadow proposal, not a decision or detector claim.

## 6. Independent units, precision and sample-size signoff

The statistical reviewer must complete counts **per split, stratum and independent
unit** in the worksheet before recruitment/scoring. There is deliberately no
arbitrary “ten dense images is enough” rule or fixed partner sample count here.
Until justified counts and a funded budget are approved, evaluation is blocked.

- Define primary MAE as the equal-weight mean of independent clusters' mean
  absolute visit errors, not the absolute value of a mean signed error. Bias
  uses signed errors. Within a cluster use the predeclared visit schedule and equal visit
  weights. Report per-image and visit-weighted operational summaries separately.
  Pair C/F within the same clusters. Never give long sequences extra independent
  degrees of freedom.
- Use development-only cluster variation for a planning simulation that
  reproduces repeated visits, target strata, failures and missing labels. Record
  assumed effect/error, dependence, attrition, allocation, candidate counts,
  precision goal and desired probability of meeting the bounds. Proposed
  planning goals: 95% interval half-width ≤2 pp for dense MAE/paired improvement
  and ≥80% power under the explicitly stated useful alternative. These are
  planning targets, not evidence that the selected n suffices.
- Freeze an interval method before test release. A proposed cluster bootstrap
  resamples whole independent units with all paired arms/visits, respecting
  independent-unit recruitment strata, with 10,000 replicates and fixed recorded
  seed. A culture crossing density strata is resampled once with all its visits;
  never resample its density subsets independently. Recompute every density
  statistic inside that same replicate. Proposed percentile endpoints are the
  5th/95th percentiles for one-sided lower/upper limits and 2.5th/97.5th for a
  two-sided interval; freeze the quantile implementation. Empty-stratum
  replicates signal an inadequate design, not permission to silently discard
  them. The reviewer must
  validate coverage at the proposed count/dependence using development-based
  simulations, especially for sparse binary events. Ordinary bootstrap bounds
  of zero from zero observed errors are not valid evidence of zero risk.
- For genuinely independent Bernoulli units, use exact one-sided binomial
  bounds. Zero events in 299 independent units can bound risk below 1%; 29/29
  successes can bound success above 90%, each at one-sided 95%. These are
  best-case illustrations, not powered sample plans or counts of correlated
  frames. Clustered visit rates require a separately justified interval/design;
  a culture-level event rate must not be relabelled as a visit-level rate.
- Core approval requires all mandatory gates for the one preselected candidate,
  not whichever endpoint succeeds. The reviewer must freeze multiplicity
  handling for additional candidate, subgroup or benefit claims; otherwise
  mark those analyses descriptive. A passing broad average cannot rescue an
  underpowered near-target or ready stratum.

See [statistical source notes](../reviews/2026-10-19-pilot-statistical-source-notes.md).
If feasible recruitment cannot support the precision, explicitly narrow the
claim to descriptive feasibility before data collection; do not relax the
limits after testing or report inadequate precision as a pass.

## 7. Optional contamination and growth packets

Use separate [E0–E4 packets](detection-experiments/README.md), with independent
references and sample plans. Proposed E1/E2 targets remain ≤0.5 false-positive
healthy visits per 100 preferred (ceiling 1), ≥90% of visibly confirmed
contamination episodes warned within 4 hours of independently visible onset,
and ≥90% of independently defined slowdown episodes warned within 24 hours.
These are **unapproved research goals**, not achieved detection performance.

Freeze the combined alert budget, spatial aggregation, persistence, deduplication,
onset adjudication and latency censoring before testing. Include all qualifying
episodes, including missed cases, in deadline denominators. Report invisible
confirmed contamination separately and in the all-confirmed-episode summary.
Growth references must be independent of the detector and account for lag,
saturation and treatment; warm-up/low-signal windows count toward unavailable
monitoring. No thresholds are lowered or monitors activated by this document.

## 8. Stops, access and costs

Pause the affected workstream for wrong setup/encoding, corrupted provenance,
split leakage, unauthorised test access, annotation-rubric drift, unexpected
rights restrictions or unintended instrument actions. Preserve evidence; the
lab owns safety response under its existing SOP. A valid but inaccurate model
result is recorded as such, not deleted as an acquisition fault.

The lab supplies acquisition/annotation rights and biosafety authorization; the
data steward signs storage location, access roles, permitted model training,
retention/deletion periods, sharing restrictions and incident procedure. Use
study IDs rather than personal identifiers. No cloud upload, external training
job or public artifact release is assumed. Legal/commercial clearance and host
authentication/signatures remain owner-held gates, not claims made by a hash.

Before compute, approve input hashes/counts, candidate count, hardware, wall-time
and cost caps, output location and stop conditions. No run starts with these
blank. Record annotation minutes, calibration/training/setup hours, reimage and
review minutes, new notifications and persistent alert duration. For shadow
workflow benefits, predeclare a balanced/randomized assisted-versus-usual
review design with carryover controls; a faster second read is not causal proof.
Record cold/warm latency, p50/p95, failures, queues and batches on the actual
hardware; offline CPU smoke timings do not establish host throughput.

## 9. Run packet, deliverables and decisions

Each run packet retains protocol/version/approval; manifest and label hashes;
split-custody reference; source commit **plus dirty patch hash**; dependency/OS/
hardware identity; exact command and seeds; input/export mappings; all weights,
profiles and config hashes; band/aggregation/policy definitions; candidate-lock
approval; start/end times; success/error rows; output digests; and chain/checkpoint
locations. Persist original bytes, reference masks and exact F weights under
the approved retention plan. A commit hash alone cannot identify this dirty tree.

Deliver: (1) per-visit paired outputs and all refusals, (2) per-stratum error,
bias, band/decision coverage and uncertainty, (3) separate actual/counterfactual
action matrices, (4) audit/replay verification and linked illustrative fixture
versus real-review evidence, (5) measured resource/operator costs with missing
values explicit, (6) deviations and a one-page recommendation.

| Outcome | Decision |
|---|---|
| All core gates met, precision sufficient | Lab/QA may approve a separately scoped measurement-only shadow phase; no automatic actuation |
| Accurate but too costly, or decision/detector evidence inadequate | Report measurement result; decline those extra claims and decide whether further research is worth funding |
| A measured gate is outside its limit | No-go for that claim; preserve results; revise on development data and require a new untouched test |
| Bounds cross limits, missing strata or unresolved references | Insufficient evidence, not pass; no optional recruitment after looking at results unless a sequential design was approved in advance |
| Integrity, access or safety stop | Suspend affected scoring/release; independent incident review and authorized recovery |

The lab lead owns intended use and biological interpretation; QA owns annotation
and evidence acceptance; the statistician owns precision/analysis; the custodian
owns test allocation/access; engineering owns reproducible outputs and host
failure handling; the data/legal owners own rights/retention/clearance; the sponsor
owns budget and go/no-go. Names/signatures remain pending in the worksheet.
T02's historical version comparison is supporting internal evidence, not this
pilot's operational baseline and not a homepage requirement. T11's host harness
and release-state reconciliation remain separate implementation work.
