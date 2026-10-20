# Detection signal implementation and handoff

Status: 2026-10-18. Offline experimental signal paths implemented; no new
biological efficacy result, active detector threshold, approval or website claim.
Nothing pushed or deployed. Human screen-reader/200% zoom checks remain pending.

Follow-up: [real-Cellpose local CPU parity and full-pipeline smoke validation](2026-10-18-cellpose-release-validation.md)
now pass. Target-host provisioning/capacity checks remain pending; this does not
replace the data-dependent E0–E4 evaluation.

## What changed

### E1 preparation: preserve spatial coverage

`culture/anomaly_coverage.py` covers a uint8 grayscale/RGB frame with native
224-pixel windows, including anchored edge windows. It does not resize or
center-crop those windows. Tile budgets are checked before scoring; unsupported
small, high-bit-depth or malformed inputs are rejected instead of silently
rescaled. Outputs retain each tile's bounds/score and frame maximum/median.

The original-path reproduction placed a bright marker outside the center crop:
input maximum 255, `qc_tile_from` maximum 0 on a 512×512 fixture. The existing
256×256 tile sampled only 25% of that fixture before model preprocessing. New
regressions verify full pixel coverage and preserve a peripheral signal. This
proves the coverage defect, not that the marker resembles bacteria.

The scorer disables processor resizing/cropping, checks tensor/token geometry,
validates reference banks and safely normalizes large finite bank values. Its
frame score explicitly has `flag: null`, `threshold: null` and
`used_in_decision: false`. Existing center-tile cutoffs are not transferable to
the maximum of many tiles. DINO's patch scale and the microscope's resolving
power still limit sensitivity. Spatially representative healthy banks and
target-scale independently labelled episodes remain necessary.

### E2 preparation: do not learn a stall as normal

`culture/growth_signal.py` fits once from an explicitly selected baseline prefix
and retains that reference. It reports raw level/growth deficits and a descriptive
trailing-horizon growth fraction, with explicit warmup, boundary, quality, gap
and low-expected-growth statuses. Post-cutoff values cannot change the reference.
No alert/persistence policy is enabled. See the [growth implementation note](2026-10-17-growth-signal-implementation.md)
for the reproduced rolling-fit failure, acquisition boundaries and limitations.

The deterministic stalled fixture preserves a late level deficit exceeding 30
percentage points and a zero growth fraction, while its healthy counterpart
remains near one. This is synthetic mechanism validation, not measured recall.

### Runtime provenance: T06

The shipped segmentation model uses an approved private snapshot. Records bind
to the identity from that specific inference, including replacement races.
See [the T06 handoff](2026-10-18-model-identity-fix.md). This is the direct audit-trail
improvement; it does not resolve every remaining runtime correctness finding.

## Read-only probe commands

`scripts/probe_detection_signals.py` prints JSON and does not write inputs,
results, configurations or logs. Coverage defaults to a plan without loading a
model. Scoring requires explicit existing local artifacts; downloads are disabled.

```sh
.venv/bin/python scripts/probe_detection_signals.py coverage IMAGE.png --max-tiles 64

HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 \
  .venv/bin/python scripts/probe_detection_signals.py coverage IMAGE.png \
  --max-tiles 64 --score --model-dir LOCAL_DINOV2_SMALL_SNAPSHOT \
  --banks cache/anomaly/banks.npz --config configs/anomaly.yaml --confluency 33.23

.venv/bin/python scripts/probe_detection_signals.py growth VISITS_PACKET.json
```

The growth packet contains `visits`, `baseline_end`, `baseline_reason`,
`horizon_hours`, `max_gap_hours` and `min_expected_growth_pp`. Set these before
outcome review; the API cannot authenticate that a baseline really was healthy.
The example confluency above belongs only to the smoke input below, not a default.

## Bounded smoke checks

One already-reviewed lamp-dimming image was scored on CPU, offline, with the
existing center-reference bank. Input SHA-256:
`00ee04b2cc49a7a0b234de40cfd2382938b474179b8120401ec0f5a508c89631`.
It is **not a contamination validation example or untouched test**.

- Shape 1040×1392; 35 native tiles; full spatial coverage; no resize.
- Raw maximum 0.3221946061; median 0.2425214052. No classification/threshold.
- Supplied cached confluency 33.23%; reference bin 20–40.
- Bank SHA: `870ff30ce3339db29bb9dd7aae35713c154f24b7a3a0980b7b19bf559813463a`.
- Config SHA: `2776ce48025a554c2d3487c0d98433ef376ee4b9de1f5b25d48508bf82721184`.
- DINO weights SHA: `ae1e99fcefd534ed978cdeb8326f08030c96e28b7a81ffcbc98a857c84d14be1`.
- Local snapshot: `facebook/dinov2-small`, revision `ed25f3a31f01632728cabb09d1542f84ab7b0056`.

An exploratory cached healthy tuning lineage, `c2c12_090303_exp1_F0001_Data`,
also exercised the growth API with 14 visits, a first-36-hour cutoff
(`2009-03-04T12:00:00+00:00`), 12-hour horizon, 9-hour gap limit and 1-point
denominator guard. It returned seven warmup and seven `LOW_EXPECTED_GROWTH`
rows. There was no usable growth ratio: the selected prefix does not establish
a useful healthy growth expectation. Do not count unscorable visits as detected
stalls or healthy successes. No historical results were overwritten.

## Verification

```sh
.venv/bin/python -m pytest -q \
  tests/test_anomaly_coverage.py tests/test_detection_probe.py \
  tests/test_growth_signal.py tests/test_growth_one_step.py \
  tests/test_model_identity.py tests/test_record_model_identity.py \
  tests/test_approvals.py tests/test_anomaly.py tests/test_anomaly_live.py \
  tests/test_experiment_protocol.py \
  -k 'not live_embedding_parity and not live_scoring_reproduces'
```

Result: **187 passed, 2 deselected**. The excluded cases are existing cached/live
anomaly parity checks; the bounded native-tile smoke above is separate, not a
replacement for full parity validation. These regression passes do not change
the historical contamination or growth-stall performance figures.

`compileall` on changed source/new tests and `git diff --check` pass. Generated
local Space copies were synchronized with `deploy/sync_space.py`; `--check`
passes for both copies. This only updates local files, not remote Spaces.
Scientific configuration and results files have no changes from this work.

Adjacent regression validation: **132 passed** across console cards/lab/ZeroGPU,
stored demo examples, live calibration, record events/chains, existing growth
and anomaly/band rules. These use their existing fixture/stub contracts, not a
new biological study. Command:

```sh
.venv/bin/python -m pytest -q tests/test_console_cards.py \
  tests/test_console_lab_demo.py tests/test_console_zerogpu.py \
  tests/test_demo_examples.py tests/test_live_calibration.py \
  tests/test_record_events.py tests/test_records_chain.py \
  tests/test_growth.py tests/test_rules_anomaly.py tests/test_rules_band.py
```

API contract tests also pass: `.venv/bin/python -m pytest -q deploy/hf-space/test_api.py`
returns **28 passed**, with two dependency deprecation warnings. Total across
these three runs: **347 passed, 2 deselected**. The API tests stub model inference.

## Next implementable work

1. Finish E0: approve setup, cadence, FOV/registration, labels, alert/delay costs,
   sample plan and independently retained split allocation. Research proposals
   remain proposals, not automatically accepted operating requirements.
2. E1: collect target-scale controls/confirmed visible contamination, build
   representative banks and compare center/native multi-tile operating curves.
   Tune on development/tuning data only; include tile-count/setup strata.
3. E2: compare frozen versus rolling baselines and 12-hour accumulation on
   labelled growth windows with matched healthy controls. Include rejected,
   warmup, low-growth and missing observations in coverage denominators.
4. E3: retain exact fine-tuned artifacts and run dense-range measurement/action
   confirmation. Existing benchmark gains do not replace this step.
5. Complete remaining runtime contracts and target-host T06 deployment checks.
   Lock candidates before untouched evaluation and obtain separate activation
   approval. Do not lower thresholds solely to improve a demo result.
