# T02 — Matched cached-policy comparison

Status: EVICAN policy replay and C2C12 workload companion implemented locally,
2026-10-20. T02 remains partial: independent decision evidence and end-to-end
inference reconstruction are not delivered by these replays.
This is internal validation, not a comparison-first product presentation.
No model inference, threshold tuning, source-history rewrite or release is required.

## Implemented cohort and protocol

`results/policy_comparison_evican/` freezes the 33 EVICAN eval2019 images in the
original confluency study. Each has independently annotated expert-mask confluency,
cached full-resolution Cellpose-SAM readings at cutoffs 0 and −3.5, and historical
QC logits joined by image SHA-256. These are previously reused, selected images,
not a fresh blind test. Independent biological culture/experiment IDs are absent.

The two readings come from the **same maps**, not two segmentation models. Exact
historical weight hashes are unavailable. Report the model cache identifiers and
that limitation; do not associate current local weights with historical runs.
Raw-image hashes are historical cache identities, not freshly verified image bytes.
Inputs contain rounded historical CSV values; their precision is in the manifest.

Replay each image at two targets:

- 80%: the historical default, with no target-reaching ground truth in this cohort.
- 50%: a diagnostic sensitivity scenario, not an approved biological threshold.

Each target has unknown timing and an explicitly assumed 48-hour passage / 12-hour
feed scenario. Neither scenario is measured operational timing. Missing quality
and anomaly results remain unavailable. No C2C12 anomaly bank is applied to EVICAN.

## Sequential variants

| Variant | Reading | Classifier | Decision policy |
|---|---|---|---|
| `baseline` | Cutoff 0 | Historical unscaled softmax | Exact `e2274dd:culture/rules.py`, archived without modification |
| `baseline_classifier_demoted` | Same cutoff 0 | Neutralized with normal/1.0 | Same historical policy |
| `current_uncalibrated` | Same cutoff 0 | Not applicable | Current `rules_v0.7`, no band/profile, unavailable quality/anomaly |
| `current_configured` | Cutoff −3.5 | Not applicable | Current `rules_v0.7`, configured `evican_mixed` band 29.4 pp; action scope unsupported |

These are sequential diagnostic ablations, not causal attribution. The last step
changes both reading and error band; it does not isolate a band-only effect.
`hold` is normalized to `continue` for comparisons while preserving original action
and reason. Current structured reasons, timing, checks and advisory status persist
in every row. Historical outputs are not retrospectively represented as
host-authorized actions.

## Frozen identity and regeneration

The manifest includes baseline commit, current parent commit, actual local source
hashes, frozen input and baseline-module hashes, original source artifact hashes,
effective profile/check/line policies, timing/target/split/setup and unknowns.
The parent commit does **not** identify the dirty implementation; source hashes do.
These hashes establish reproducibility relative to the bundle, not an externally
signed chain of custody. Only replay trusted repository bundles: the archived
baseline is executable Python.

One cache-free replay command, from the repository root:

```sh
.venv/bin/python scripts/compare_decision_policies.py --out /tmp/cultureqc-policy-replay
```

The output directory must not exist. Python and PyYAML suffice; no torch, pandas,
model weights, raw images, compute cache, Git executable/history or network is
needed for replay. `inputs.json`, `manifest.json` and `baseline_rules.py` are the
inputs. Outputs are `decisions.jsonl`, `report.json` and `report.md`.
Compare them with the checked-in bundle's `replay/` directory.

Source drift or modified frozen artifacts cause refusal, not silently relabelled
results. A future code change requires a separately named bundle and review of
whether the same inputs still support the changed policy. Do not overwrite this
bundle or simply update a checksum to bypass that review.

The optional freeze command needs local pandas/parquet support, the exact source
files named in the manifest, and historical Git commit `e2274dd`:

```sh
.venv/bin/python scripts/compare_decision_policies.py \
  --freeze --bundle /tmp/cultureqc-new-policy-bundle
```

Freeze refuses an existing directory, validates unique joins, the original cohort
and matching expert-mask truth, then writes a new manifest and replay. Source caches
are never rewritten. It is not an inference command.

## Metric contract

- Per image/context: all four outputs and reasons, original measurements and
  identity. Repeated contexts are **not** additional independent images.
- Per target/timing/variant: action counts, ground-truth-threshold/action confusion,
  below-target passage, target-ready called continue, review and reimage separately.
- Threshold-correct decided coverage = correct direct passage/continue calls divided
  by **all** images, including deferred images in the denominator.
- Threshold accuracy among decided = correct direct passage/continue calls divided
  by direct passage/continue calls. Feed is not adjudicated by a confluency mask.
- Report all images, dense GT ≥40%, and GT within ±10 pp of target separately.
  Empty subsets have null rates. No target-reaching cases means insufficient
  passage evidence, even if every below-target reading says continue.
- Threshold agreement is **not** operational action correctness, safe automation,
  culture-health clearance or independent validation of passage timing.
- No population confidence interval: biological independent-unit IDs are missing
  and the selected cohort was reused. Counts and missing uncertainty are explicit.
- No saved-time/ROI calculation without measured review time and stated workload.

## Implemented C2C12 workload companion

`scripts/compare_c2c12_workload.py` and `results/policy_comparison_c2c12/` freeze the
complete **1,228 unmodified held-out frames**, with 14 base-sequence groups across
3 experiment groups. Source: C2C12, Ker et al. (2018), CC BY 4.0; dataset provenance
is retained in `results/replay_fleet_summary.md` and `results/review_rate.md`.
The existing split holds out sequences, **not experiments**: all three experiment
groups also occur in tuning. “Normal” is the historical cache's unmodified-source
category, not independently verified culture health.

The cohort excludes synthetic contamination/dimming images and growth-stall
resampling. Every row joins by image SHA-256 to the pinned full-frame segmentation,
classifier and quality versions; sequence/frame lineage and reading parity with
the anomaly cache are checked. Independent confluency truth is explicitly null.
Do not interpret a model's own reading as an annotation.

Three variants reuse the exact archived v2 baseline, classifier-neutralized
baseline and current configured C2C12 policy. The last step changes decision
policy and adds the quality/anomaly inputs together; it is not a causal isolation
of each component. C2C12 still uses cutoff 0, no error band and unsupported action
scope. There is no calibration gain or fine-tuned model comparison in this arm.
The same 80%/50% targets and unknown/assumed timing scenarios apply. Current
quality reimage reasons are retained; advisory outputs are never actuation permission.

Run from the repository root with a new output directory:

```sh
.venv/bin/python scripts/compare_c2c12_workload.py --out /tmp/cultureqc-c2c12-replay
```

Replay needs Python, NumPy and PyYAML, but no compute cache, models, raw images,
root config tree, Git history/executable or network. The bundle holds frozen
inputs, baseline source, quality/anomaly configs, split CSV and provenance
manifest. The bank itself is **not** needed or re-scored during replay. Optional
`--freeze --bundle /tmp/cultureqc-new-c2c12-bundle` requires the original local
parquet/cache files, pandas and historical Git baseline, and refuses existing
directories. Never overwrite or relabel an old bundle after source drift.

### Workload metrics and grouping

- `decisions.jsonl` contains all three outputs/reasons for every paired context.
  Its 4,912 rows represent only 1,228 unique frames, not independent replicates.
- `report.json` reports pooled, per-sequence and per-experiment action counts
  for all images and a cached-reading ≥40% subset, at both targets/timings.
- Review and reimage rates are separate. Their sum is explicit deferred-output
  burden, **not measured human work**. Current continue/feed outputs also retain
  host review/authorization requirements.
- Equal-sequence and equal-experiment averages are separate from frame-weighted
  pooled rates. Empty dense-reading groups remain visible with null rates; group
  averages exclude them and report nonempty/total group denominators.
- Anomaly-flag counts are not human-review counts. Model reading ≥target is not
  “ground truth ready.” No action confusion, early-passage, missed-readiness,
  accuracy, population confidence interval or saved-time estimate is supplied.
- No reading reaches 80% (maximum 56.98%). Zero passage or zero explicit review
  therefore cannot demonstrate successful safe passage.

### Anomaly and integrity limitations

The bundle preserves historical **centre-tile** anomaly scores, not the later
experimental whole-frame detector. Frozen flags are checked against their
serialized bin thresholds; no embeddings or scores are recomputed.

The config's bank digest is the concatenated contiguous arrays in sorted key
order (`culture.anomaly.bank_hash`), **not the NPZ file digest**. Freeze verifies
the configured array hash and records both identities separately. However, the
score parquet has no per-row bank/config hash; bank identity cannot retroactively
authenticate which bank produced every score. The original scoring script says
held-out frames used the full tuning bank. Tuning leave-one-sequence-out scores
are excluded. Exact historical model-weight authentication remains unavailable.

Checksums establish reproducibility relative to the manifest, not signed custody.
The manifest has no independently protected anchor; changing it and all matching
artifacts is outside this integrity check. Only execute trusted repo bundles,
because the historical baseline is executable Python. Raw-image identities are
cache-provided and are not freshly verified by either replay.

See [C2C12 results and verification](../reviews/2026-10-20-c2c12-workload-replay.md).

## Remaining T02 work

1. **Independent decision evidence:** obtain an approved target-setup evaluation
   cohort spanning both sides of the target, including dense images. Supply
   biological grouping, independent masks/decision adjudication, real timing,
   applicable quality/anomaly evidence and authenticated model identities.
   Use the [partner-pilot protocol](partner-pilot.md) and
   [approval worksheet](partner-pilot-approvals.md); no thresholds or approvals
   are invented here.
2. **End-to-end comparison only if justified:** document exact inputs, weight
   availability/hashes, preprocessing, hardware/time/resource bounds and expected
   outputs before requesting model computation. If old inference cannot be
   reconstructed, keep the result labelled cached-policy replay.

Human screen-reader/actual 200% zoom, fresh T12 visual/pointer acceptance and the
V3 timed VP walkthrough remain separate pending tasks. Nothing here authorizes
commit, push, deployment, automatic passage or changes to the public website.
