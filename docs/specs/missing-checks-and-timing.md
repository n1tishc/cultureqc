# Missing checks and timing — rules_v0.7

## Boundary

This is a conservative software policy, not biological validation or a new
detector threshold. All recommendations are advisory, including `passage`,
`feed`, `continue` and `reimage`. Every new reading stores
`decision.mode: advisory` and `decision.host_actionable: false`. A host must
not execute equipment operations merely because `recommended_action` exists.
No shipped profile has approved passage scope.

## Checks

`evaluate_decision()` returns a structured `Decision`; `decide()` retains its
two-item `(action, reason)` compatibility API. Library and live console use
the structured API. `CheckPolicy` declares anomaly/QC requirements:

| Check | Default | Effect |
|---|---|---|
| Image quality | Always required for a passage candidate | Failed → reimage; unavailable → blocks a candidate |
| Anomaly | Optional, exploratory | Flagged → holds a passage candidate; unavailable is recorded, never a negative result |
| QC | Optional for direct callers; not applicable when runtime classifier is demoted | High-confidence non-normal flag → review; a flag without confidence → incomplete-check review |
| Passage timing | Known interval required for a candidate | Unknown → review near/above target; recent passage → explicit interval hold |
| Feed timing | Must be known before proposing feed | Unknown is retained; feeding is not presumed unnecessary |

`required`, `optional` and `not_applicable` are distinct. Each check also records
`passed`, `failed`, `unavailable` or `not_applicable`. “Passed” means that check's
existing rule condition, **not** proof of culture health. A not-applicable check
must not be given decision inputs; conflicting inputs raise `ValueError`.
Demoted classifier observations remain in raw record fields but do not vote.
An explicit required QC policy with a demoted classifier remains unavailable;
it is not silently downgraded. Optional checks do not cause blanket review.

Requiring anomaly via `CheckPolicy(anomaly="required")` makes unavailable results
block passage candidates. It does not validate the detector's coverage or
justify an operational release. Its exploratory default is not a declaration
that contamination screening is unnecessary. An approved host SOP must decide
which validated checks are needed before real action; this implementation
offers no host-actionable mode.

## Precedence and timing

1. Invalid inputs raise before producing a normal decision.
2. A QC flag at/above the existing confidence threshold requests review.
3. Failed image quality requests reimaging; incomplete flagged QC requests review.
4. Unknown passage time near/above target requests review.
5. With elapsed passage time: no band at/above target requests review; an anomaly
   flag holds a candidate; unsupported scope or missing required checks blocks
   it; a straddling error band requests review. Only an otherwise eligible
   candidate gets the advisory `passage` label.
6. Known elapsed feed time proposes advisory feed. A passage interval hold is
   retained in the explanation if applicable; feeding is not declared safe.
7. Otherwise monitoring remains advisory, not “no action needed.” Low unsupported
   readings explicitly do not establish that no action is needed.

At 95%, target 80%, six hours after passage with a 24-hour minimum, the reason
states `6h < 24h`, never “below target.” Interval equality satisfies the interval.
The lower band endpoint equal to target is a candidate; upper endpoint equal to
target remains ambiguous. Unknown passage/feed times are separate structured
states and warning codes. Live console input no longer assumes 48h/12h; callers
may explicitly supply elapsed times, otherwise they stay null. Historical demo
fixtures retain their original rules and assumptions, without rewriting files.

## Records, validation and migration

- `decision.reason_code` is a stable enum in `culture/schema.json`. `checks`,
  `timing` and `warnings` retain unavailability and the effective requirements.
- Runtime rationale uses the exact rule explanation, so it cannot independently
  describe a timing hold as a confluency-based clearance.
- Percentages/bands must be finite in 0–100, confidence/thresholds in 0–1,
  intervals and elapsed times finite/nonnegative. Booleans do not count as
  numeric inputs. Check flags must be actual booleans or null.
- Invalid inputs raise `ValueError`; they do not generate a normal reading.
  The record writer also rejects nonfinite values in unused/nested model output
  before appending. Verification reports nonfinite records as broken.
- Schema 0.5 gains fields required conditionally for `rules_v0.7`. Historical
  valid 0.4/0.5 records remain readable; no historical numbers or hashes change.
  Closed-schema consumers must update before deployment. This is not a push or
  activation approval.
- Full replay from immutable effective inputs/configuration is **T05**, not
  delivered here. Timing is now structured, but target/config snapshots,
  host capture-time provenance and transactional activation remain separate work.

## Host recovery ownership

The host owns inference timeouts, cancellations, retry budgets, backoff,
reimage scheduling, duplicate-result suppression, stale-result rejection and
operator escalation. Timeout/exception is unavailable, not a negative check
or implicit continue. No automatic retry loop is added. The host must configure
a bounded recovery policy under its SOP, log failed attempts and stop/escalate
when that budget is exhausted. No retry count, time budget, capture cadence or
scientific acceptance threshold is invented by this policy.

## Tests

Synthetic approvals/check outputs test software only. Regressions cover missing
required versus optional/not-applicable checks, failed versus missing inputs,
boundary equality, combined-failure precedence, invalid inputs, record rejection,
historical schema compatibility and same-context library/console parity.
Real-model detection accuracy, target-host readiness and human accessibility
verification remain separate release gates.
