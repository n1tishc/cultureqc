# T04 — missing checks and timing safeguards

Status: implemented and tested locally on `slice-1b-compute-cache`. Nothing
committed, pushed or deployed. Human screen-reader and actual 200% zoom
verification remain pending.

## Reproduced defects

`.venv/bin/python -m pytest tests/test_rules_missing_checks.py -q` initially
produced **11 failures** against the existing rules:

- An approved synthetic scope with missing quality still returned `passage`.
- Unknown passage timing also returned `passage`.
- A 95% reading at an 80% target six hours after passage returned the false
  explanation “below target … No action needed.”
- Negative, NaN, infinite and boolean elapsed times were accepted.

The causes were the missing-value defaults, absent numeric validation and the
catch-all continue explanation. The regressions now pass against the actual
rule function; no instrumentation or fabricated detector evidence was added.

## Implemented

- `rules_v0.7` adds structured decisions with stable reason codes, explicit
  check requirements/results and known/unknown/held timing.
- Quality is required for passage candidates. Optional unavailable anomaly
  does not force blanket review; required unavailable anomaly does. Demoted
  QC is explicitly not applicable, not a passing result. Conflicting inputs
  for a not-applicable check are rejected.
- Unknown passage timing cannot satisfy its prerequisite. Live console timing
  defaults to unknown rather than assuming 48h since passage and 12h since feed.
- Recent passage gives a factual timing hold, including when a feed interval
  has elapsed. Unsupported low readings never establish “no action needed.”
- Every output is explicitly advisory with `host_actionable: false`, even a
  synthetic eligible passage candidate. Runtime rationale uses the rule's
  explanation, not a separate confluency-only clearance.
- Invalid numeric/check inputs are rejected. The writer refuses nonfinite
  nested/raw output before append; verification reports such records as broken.
- New policy metadata is required by schema for rules_v0.7. Library/console
  records agree under identical contexts. Historical valid records still
  validate; measured results and precomputed examples were not rewritten.
- Deployment mirrors were regenerated locally. Host docs assign bounded
  timeout/reimage retry and escalation ownership without inventing a retry
  budget, scientific threshold or operational approval.

Policy details: [missing checks and timing](../specs/missing-checks-and-timing.md).

## Validation

Focused policy, profile, record, historical example and console tests:

```sh
.venv/bin/python -m pytest tests/test_rules_missing_checks.py tests/test_passage_eligibility.py tests/test_rules_band.py tests/test_rules_anomaly.py tests/test_profiles_config.py tests/test_record_model_identity.py tests/test_demo_examples.py tests/test_console_cards.py tests/test_record_events.py tests/test_records_chain.py tests/test_live_calibration.py tests/test_console_lab_demo.py -q
```

**250 passed** in 26.75s. Synthetic stand-ins exercise the real library/console
paths; they are not biological validation.

```sh
.venv/bin/python -m pytest deploy/hf-space/test_api.py tests/test_console_zerogpu.py -q
```

**33 passed** in 96.75s, with two existing Starlette/httpx/AnyIO deprecation
warnings. Model startup/downloads are stubbed; no remote deployment or GPU
readiness is claimed. **283 passing tests total** across these two commands.

Changed Python modules compile; `git diff --check` and
`deploy/sync_space.py --check` pass. No diff under `results/` or `demo/examples/`.
No real-model inference or browser/assistive-technology test was rerun for this
policy-only change.

## Next: T05

Persist immutable effective rule inputs/config identity and host capture-time
provenance, then provide pure decision replay. Current timing/check metadata
is not yet a complete reconstructible snapshot. Configuration activation and
host capacity remain separate gates; no shipped profile is passage-approved.

Follow-up identified: the offline `scripts/export_demo_examples.py --rederive`
path predates the structured eligibility/decision contract and updates only
legacy decision fields. Migrate and test it with T05 before using it for new
policy fixtures; do not use it to relabel the existing historical records as
current-policy evidence. It was not run or changed in this step.

This work improves failure handling, not contamination or growth-stall accuracy.
Those experimental signals still need the approved E0 validation protocol and
target-setup evidence before operational use.
