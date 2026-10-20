# T10 — Partner pilot specification handoff

2026-10-19. **Proposed specification delivered; partner approval and study
execution pending.** Documentation only: no inference, training, data collection,
scientific threshold changes, profile activation, commit, push or deployment.

## Deliverables

- [One-setup protocol](../specs/partner-pilot.md): confluency/audit-first offline
  evaluation, operational baseline, separate calibrated and fine-tuned arms,
  annotation, allocation, proposed acceptance rules, precision plan, stops,
  run packet, deliverables and go/no-go outcomes.
- [Approval worksheet](../specs/partner-pilot-approvals.md): actual setup,
  accountable people, sample-count/cost justification, rights/retention, compute
  caps and signed approval fields, all deliberately pending.
- [Primary-source statistical notes](2026-10-19-pilot-statistical-source-notes.md):
  independent units, exact-binomial illustrations and cluster-aware planning.
- Links added to the main backlog, host boundary and E0–E4 experiment handoff.

The partner's existing SOP is the operational baseline, not a v2 comparison
page. Calibration-only C and optional fine-tuned F are separate candidates;
neither a promising public benchmark nor a fixed image count is partner evidence.
Contamination and growth remain separately approved optional studies.

## T10 acceptance coverage

| Requirement | Protocol treatment |
|---|---|
| Statistical uncertainty versus individual error | Mean-error confidence bounds and per-reading bands are explicitly distinct |
| Adequate independent sample size | Development-only variation, cluster-aware simulation, precision/power goals and signed counts; no invented n or frame-as-replicate shortcut |
| Correctness and useful coverage | Separate early-passage/missed-readiness rates and decided-coverage floors; an all-review system cannot pass decision confirmation |
| Explicit annotation | Blinded dual coverage masks/adjudication, fixed valid-area rubric, separate training instance masks and disclosure of the historical 29–31 pp discrepancy |
| Separate candidates and untouched test | Development-only training, tuning-only selection, candidate/analysis lock and separate final-test custodian |
| Non-actuating first run | Actual advisory runtime and counterfactual band-policy results kept separate; no fabricated eligible profile |
| Business outcomes measured honestly | Existing-workflow baseline, review/reimage and annotation/training cost, latency tails; missing margins/timings remain unmeasured |
| Ownership and integration | Named-role worksheet for setup, QA, statistics, custody, engineering, rights, budget and final approval; all real signatures pending |

The research agent independently reviewed the protocol and found no
all-abstention success path or conflation of hypothetical decisions with current
runtime capability. Its review identified the need to freeze cluster mapping,
interval construction and resampling across density strata. The draft now
specifies whole-unit resampling across those strata and proposed percentile
limits; the worksheet still requires statistician signoff and simulation-based
adequacy checks. Sparse-event bootstrap bounds cannot establish zero risk.

## Validation and limits

- The existing E0 draft readiness command remains `ready: false` with exit 1:
  no approvals, setup or sample allocation were invented to make it pass.
- Local Markdown links in the three new protocol/source documents and this
  handoff are checked for existing destinations; `git diff --check` passes.
- No runtime implementation changed, so model/regression suites were not rerun.
  This document delivers neither a pilot runner nor the T11 host harness.
- Proposed numerical gates require partner approval before confirmation. A
  separately authorized development-only phase can estimate variance and costs;
  it cannot supply untouched confirmation data or a performance claim.
- Human screen-reader/actual 200% zoom and timed VP rehearsal remain pending.

Next implementation: **T11 — release-state reconciliation and a minimal
library-based host evaluation harness**. T02's matched internal benchmark,
E0 approvals/E1–E4 scientific evidence, and T12's final documentation/proof
consistency pass remain separate. No release approval is implied by completing
this proposed protocol.
