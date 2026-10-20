# Offline frozen growth reference experiment

Implemented 2026-10-17. This is an experimental signal API in
`culture/growth_signal.py`, with deterministic regression fixtures in
`tests/test_growth_signal.py`. It is not wired into runtime decisions, SPC,
configuration defaults or website claims. Generated local deployment mirrors
include the module, but no deployment or activation occurred. Historical held-out
stall detection remains **0/2**; these code checks do not change that evidence.

## Problem and reproduced failure

The existing rolling `one_step_ahead_series` refits every new prefix. A persistent
stall enters that prefix and gradually becomes the expected trajectory. The
existing one-step test already describes this limitation. A new deterministic
fixture supplied identical logistic visits through 42 hours, then held one
trajectory flat through 96 hours. Before implementation, the test called the
existing rolling API and asserted that the late forecast remained equal for the
healthy and stalled continuations of the same fixed baseline.

The red check was:

```text
.venv/bin/python -m pytest tests/test_growth_signal.py -q
FAILED test_frozen_reference_does_not_absorb_a_sustained_stall
stalled expected 38.54820182741822 != healthy expected 83.58675973083005
1 failed in 1.52s
```

Ranked hypotheses were (1) the rolling fit absorbs the plateau, (2) short-horizon
increments hide accumulated growth loss, and (3) uncertainty scaling obscures
raw measurement differences. The deterministic failure directly establishes the
first mechanism. This change evaluates longer-horizon raw growth deficits without
requiring a claim about calibrated uncertainty. It does not establish that this
solves the real FOV-noise problem or quantifies either alternative mechanism.

The same fixture now uses a cutoff fixed at 36 hours and passes: healthy and
stalled late forecasts agree, the sustained level deficit remains over 30
percentage points, the stalled trailing growth fraction is zero and the clean
fixture's fraction is approximately one. This fixture is a mechanism check,
not a sensitivity or specificity study.

## API and interpretation

```python
from dataclasses import asdict
from culture.growth_signal import frozen_growth_series

signals = frozen_growth_series(
    visits,
    baseline_end="2026-01-02T12:00:00+00:00",
    baseline_reason="Acquisition prefix specified before outcome review",
    horizon_hours=12.0,
    max_gap_hours=6.0,
    min_expected_growth_pp=1.0,
)
rows = [asdict(signal) for signal in signals]
```

The caller supplies a cutoff and documented selection rationale. The API neither
reads fault labels/onset nor automatically chooses a supposedly healthy period.
**A nonempty rationale is not authentication that the prefix is healthy.** A real
study needs independently supported baseline suitability and a frozen selection
rule. Selecting a cutoff after viewing a fault or held-out outcome invalidates
the evaluation even though the API cannot detect that human choice.

Only eligible observations at or before that cutoff enter a single weighted
logistic/Gompertz fit. The implementation reuses `culture.growth`'s weighting,
bounded fitting and AIC selection primitives. Post-cutoff measurements never
change that fit. Baseline rows are warmup records without a reference ID or
forecast, so returning an entire offline series does not backfill earlier rows
with information learned later. The fit is constructed at the first post-cutoff
row and remains fixed even after quality failures or apparent faults.

Each output dataclass supports `dataclasses.asdict` and strict JSON serialization.
The reference ID hashes selected baseline timestamps, measurements and effective
weights, baseline rationale/cutoff, acquisition provenance, fitted model/parameters
and actual growth/noise configuration file hashes. It identifies the reference;
it is not a signature, approval or complete replay manifest. Replay tooling must
also retain the full input artifact, its hash, code revision and analysis settings.

For each eligible post-baseline observation:

- `expected` is the frozen model's confluency forecast.
- `level_deficit_pp = expected - observed` retains accumulated displacement.
- `expected_growth_pp` is frozen-model growth over the trailing horizon.
- `observed_growth_pp` is measured growth over that same horizon.
- `growth_deficit_pp = expected_growth_pp - observed_growth_pp` is positive for
  slower-than-reference growth, in percentage points.
- `growth_fraction = observed_growth_pp / expected_growth_pp` is a descriptive
  ratio, emitted only with adequate coverage and expected growth.

The default 12-hour horizon follows the proposed pilot research direction. The
6-hour allowed gap and 1-percentage-point denominator guard are explicit
exploratory settings, not learned thresholds or approved biological standards.
The guard suppresses unstable ratios near expected saturation; it does not
classify a culture as healthy or stalled. Negative observed growth and ratios
above one are preserved. There is no 50% alert, persistence rule, p-value,
z-score, calibrated interval or downstream decision in this module.

## Coverage and window boundaries

Inputs must be strictly increasing, unique, timezone-aware timestamps. The API
does not sort or deduplicate potentially ambiguous acquisitions. At minimum each
visit needs segment identity, nonempty `model_versions` and `config_hashes`, an
explicit passing quality flag and finite confluency in [0, 100]. Invalid or absent
quality is rejected; invalid numeric readings have a separate status. A missing
or null reported confluency SD is handled consistently with the existing
weighting primitive as zero; negative/nonfinite supplied values
reject the observation.

Lineage, segment, flask, model/config provenance, source dataset/sequence,
provenance markers, FOV count, pixel size, imager/setup and crop-fraction changes
invalidate this reference permanently for the rest of
the call, even if the old metadata returns. A quality-failed boundary still
invalidates subsequent use. Start a separate call with an explicitly chosen
baseline for a new window. Metadata consistency does not prove spatial
registration or specimen identity. Moving crop offsets do not invalidate the
window; changing the set of crop fractions does. Boolean, oversized or nonfinite
measurements/settings are rejected. Supplied SD outside [0, 100] is rejected.
Configuration parsing and reference hashes use the same captured bytes, so a
concurrent file replacement cannot label one parsed configuration as another.

The configured existing minimum baseline count/span must be met before freezing.
Quality-rejected baseline rows never enter the fit; gaps between remaining
eligible baseline visits and from the last baseline visit to the cutoff must
meet the declared gap limit. Later observations cannot rescue an inadequate
baseline by quietly extending it.

The trailing horizon uses its exact start time. When irregular cadence places
that start between acquisitions, linear interpolation uses only two already
observed eligible neighbors. Every acquisition in the relevant interval must be
eligible and every interval must meet the declared gap limit. No interpolation
crosses a rejected reading or oversized gap. A gap temporarily suppresses growth
scores until a fully covered trailing horizon is available. This treats the
gap setting as an explicit acquisition tolerance; without a scheduled-visit
manifest it cannot distinguish an absent scheduled visit from a permitted
irregular interval below that tolerance.

| Status | Interpretation |
|---|---|
| `BASELINE_WARMUP` | At/before the predeclared cutoff; no forecast or score |
| `QUALITY_FAILED` | Explicit quality gate did not pass; no score |
| `INVALID_OBSERVATION` | Invalid confluency or supplied SD; no score |
| `WINDOW_CHANGED` | Missing required provenance or changed acquisition window; new baseline required |
| `INSUFFICIENT_BASELINE` | Baseline count/span below existing fitting minimum |
| `INSUFFICIENT_BASELINE_COVERAGE` | Baseline has an excessive temporal gap |
| `FIT_FAILED` | Neither candidate fit succeeded; no invented zero deficit |
| `INSUFFICIENT_COVERAGE` | Trailing horizon unavailable/rejected/gapped; no growth fraction |
| `LOW_EXPECTED_GROWTH` | Expected growth below denominator guard; raw increments retained, ratio absent |
| `OK` | Descriptive signal computed; does not mean healthy |

For a valid current observation with inadequate trailing coverage, a frozen
forecast and level deficit can still be reported; trailing growth scores are
absent. Preserve status denominators when summarizing coverage and outcomes.

## Verification and limits

Regression tests cover sustained-stall retention, future-data independence,
baseline quality exclusion, exact irregular horizons, quality/gap recovery,
permanent window boundaries including failed-quality rows, missing provenance,
baseline insufficiency, saturation, numeric rejection, fit failures, JSON output,
input immutability, deterministic reference hashes, and independence from fault
labels. They also reject ambiguous timestamps and invalid settings.

Initial focused validation, before acquisition/numeric/configuration hardening:

```text
.venv/bin/python -m pytest tests/test_growth_signal.py tests/test_growth_one_step.py -q
46 passed in 19.70s
```

The hardened module has 55 regression cases. Final combined verification is
recorded in [the implementation handoff](2026-10-18-detection-signal-implementation.md).

The tests use synthetic logistic truth and a small fixture noise model; they do
not rerun inference, download models, or modify the historical cache. They cannot
establish real healthy forecast calibration, performance on C2C12, 24-hour
detection, or an acceptable false-review budget. Frozen extrapolation can drift
with cell-specific lag, treatment, differentiation, unexpected saturation,
measurement bias and changes in spatial coverage. A deficient baseline remains
deficient when frozen. Forecasts have no validated maximum extrapolation horizon.
Trailing endpoint differences remain vulnerable to FOV noise and interpolation
error. Confluency growth is area growth, not cell doubling or viability.

Next evidence work should compare frozen and rolling signals on predeclared
development windows, retain warmup/rejection/gap denominators, stratify expected
growth and acquisition conditions, and choose operating points on development
data before untouched evaluation. Independently labelled biological episodes,
matched healthy controls and a cell-specific protocol are required before any
alert policy or efficacy claim. The pilot proposals in
`2026-10-17-researched-pilot-thresholds.md` remain proposals.
