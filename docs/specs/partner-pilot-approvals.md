# T10 — Partner approval worksheet

**DRAFT / NOT READY, 2026-10-19.** Companion to the
[pilot protocol](partner-pilot.md). Every `PENDING` is a blocker, not an agent
invitation to invent a partner choice. Proposed numbers in that protocol are
not active settings. Completion of this document is not deployment approval.
A separately signed development-only phase may resolve planning uncertainty;
it still requires setup, reference rubric, rights/access and bounded cost/stop
authorization. All confirmation fields must be resolved before final-test
collection/scoring. Development data cannot later be counted as untouched test.

## Accountable decisions

| Decision | Accountable role | Required signed value/reference |
|---|---|---|
| Sponsor, budget and scope | Sponsor | PENDING: named sponsor; core measurement/records; optional F/E1/E2/decision claims selected explicitly |
| Intended use and baseline | Lab lead | PENDING: cell line, vessel, stage, target, existing SOP, reference readiness versus biological eligibility |
| Acquisition | Imaging lead | PENDING: exact setup_id, microscope/modality/objective/NA/pixel size, exposure, cadence, FOV placement/area/overlap, registration and missing-FOV rules |
| Input policy | Imaging + engineering | PENDING: supported uint8 capture or validated fixed sensor-to-export mapping and paired hashes |
| Ground truth | Annotation/QA lead | PENDING: named qualified annotators/adjudicator, coverage rubric, valid-area masks, disagreement/indeterminate handling, separate F instance-label budget |
| Decision criteria | Lab + QA + statistician | PENDING: approve or replace every proposed applicable limit before scoring, including coverage and separate early/missed-readiness budgets |
| Sample plan | Statistician | PENDING: estimand, explicit culture/lineage/session-to-inferential-cluster mapping, counts by split/stratum, variance/effect assumptions, interval method/resampling strata, precision/power simulation artifact, attrition, multiplicity and maximum recruitment |
| Test custody | Separate custodian | PENDING: person distinct from experiment owner, split manifest/hash, prior-use audit, access restrictions and test-release authorization |
| Training/candidate lock | Engineering + QA | PENDING: bounded recipe, grids, seeds, group-held-out band method, candidate selection, exact artifacts and frozen command |
| Compute | Sponsor + engineering | PENDING: hardware, input/candidate counts, wall-time/cost caps, output location and stop conditions |
| Workload study | Workflow owner | PENDING: baseline timings, representative cohort, assistance/carryover design; or explicitly mark operational benefit descriptive only |
| Rights and data | Lab + data/legal owner | PENDING: image/label/training rights, model/component terms, authorized storage/access/sharing, retention/deletion periods, incident response |
| Host shadow safeguards | Host owner + QA | PENDING: no actuation, timing/staleness/retry rules, durable records, external checkpoints, authenticated approvals and review identity |
| Final authorization | Sponsor + lab + QA | PENDING: exact protocol/manifest/analysis hashes, signed approval references and scope; record date |

## Count and cost worksheet

Populate a row per split and reference-density stratum, including both sides of
the target and the representative operational cohort. Do not substitute total
frames for independent cultures/lineages/sessions. Include control/case counts
for each optional E1/E2/E3 packet; one culture can contribute both phases but is
not thereby two independent units.

| Split/stratum | Independent units and definition | Expected visits/FOVs | Expected losses | Precision/power justification | Acquisition/annotation cost |
|---|---|---|---|---|---|
| Development | PENDING | PENDING | PENDING | PENDING | PENDING |
| Tuning | PENDING | PENDING | PENDING | PENDING | PENDING |
| Final test, each frozen density stratum | PENDING | PENDING | PENDING | PENDING | PENDING |
| Representative operational cohort | PENDING | PENDING | PENDING | PENDING | PENDING |

No fixed calendar or ROI estimate is approved. Set a budget cap and deliverable
review date only after acquisition, labelling and compute estimates are signed.

## Reuse the existing E0 preflight, do not create a bypass

For each selected E1/E2/E3 workstream, copy the existing protocol/manifest drafts
into a new versioned study directory. Keep the checked-in templates unresolved.
Map this signed worksheet and protocol into the packet's label/analysis/sample
plan fields, citing exact retained versions, not mutable document paths alone.

For E3, define `control` as reference coverage below T and `case` as at/above T;
retain finer strata in a separately hashed allocation table. Explain any other
mapping explicitly. The readiness checker counts culture IDs, not statistical
independence, and cannot validate this protocol's numerical gates or annotations.
The E3 immediate image-based decision endpoint uses denominator `decisions` and
delay `0`; do not inherit contamination's alert budget or deadline. A measurement-
only packet must explicitly describe action outputs as exploratory rather than
claim the checker certifies a decision evaluation.

Existing read-only draft preflight (expected exit 1, `ready: false`):

```sh
.venv/bin/python scripts/check_experiment_protocol.py \
  docs/specs/detection-experiments/protocol.draft.json \
  docs/specs/detection-experiments/manifest.draft.json
```

For the real packet, bind the manifest hash, obtain authorization for the exact
protocol/manifest bytes, retain their digests with the independent custodian,
then run the same command on those files. Structural readiness is not scientific
approval, authenticated authorization, a candidate lock or enforcement of test
access. No pilot runner/host harness is delivered by T10; that implementation
remains T11/E1–E4 as applicable.

## Release gates kept separate

- Scientific measurement/decision/detector acceptance applies only to the
  approved setup, target, labels and operating range; no universal claim.
- All current output remains advisory; no profile activation is authorized.
- Human screen-reader/actual 200% zoom checks remain pending, as requested.
- Local demo review, timed VP rehearsal, commercial clearance, host validation
  and explicit user permission to push/deploy are separate gates.
