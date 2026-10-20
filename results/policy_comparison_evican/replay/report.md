# Internal EVICAN cached-policy replay

**Not an end-to-end v2/v4 benchmark. Not fine-tuning evidence. No host action authorized.**

33 previously reused evaluation images with expert-mask confluency; biological independent units unknown.
Same cached maps read at two cutoffs, with original unscaled classifier logits. Timing is unknown or explicitly assumed.
Quality/anomaly checks are missing, not passed. Current outputs remain advisory. `hold` is normalized to `continue` only for counting.

## Measurement, not a model upgrade

- pct_cut0: MAE 8.36 pp; bias -8.33 pp (n=33).
- pct_configured: MAE 3.78 pp; bias +1.63 pp (n=33).

The configured cutoff is −3.5 with a 29.4 pp band. Selection was not fully blind; no new tuning occurred.
The fine-tuned experimental model is not used. The original v2 synthetic headline cannot be regenerated.

## Full cohort and dense-subset burden

| Target | Timing | Subset | Variant | n | GT ready | Continue | Passage | Review | Reimage | Early passage | Ready → continue | Correct decided / all |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 80 | assumed_elapsed | all | baseline | 33 | 0 | 1 | 0 | 32 | 0 | 0 | 0 | 1/33 |
| 80 | assumed_elapsed | all | baseline_classifier_demoted | 33 | 0 | 31 | 0 | 2 | 0 | 0 | 0 | 31/33 |
| 80 | assumed_elapsed | all | current_uncalibrated | 33 | 0 | 33 | 0 | 0 | 0 | 0 | 0 | 33/33 |
| 80 | assumed_elapsed | all | current_configured | 33 | 0 | 31 | 0 | 2 | 0 | 0 | 0 | 31/33 |
| 80 | assumed_elapsed | dense_gt_ge_40 | baseline | 3 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0/3 |
| 80 | assumed_elapsed | dense_gt_ge_40 | baseline_classifier_demoted | 3 | 0 | 2 | 0 | 1 | 0 | 0 | 0 | 2/3 |
| 80 | assumed_elapsed | dense_gt_ge_40 | current_uncalibrated | 3 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 3/3 |
| 80 | assumed_elapsed | dense_gt_ge_40 | current_configured | 3 | 0 | 1 | 0 | 2 | 0 | 0 | 0 | 1/3 |
| 80 | assumed_elapsed | near_target_plus_minus_10 | baseline | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0/0 |
| 80 | assumed_elapsed | near_target_plus_minus_10 | baseline_classifier_demoted | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0/0 |
| 80 | assumed_elapsed | near_target_plus_minus_10 | current_uncalibrated | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0/0 |
| 80 | assumed_elapsed | near_target_plus_minus_10 | current_configured | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0/0 |
| 80 | unknown | all | baseline | 33 | 0 | 1 | 0 | 32 | 0 | 0 | 0 | 1/33 |
| 80 | unknown | all | baseline_classifier_demoted | 33 | 0 | 31 | 0 | 2 | 0 | 0 | 0 | 31/33 |
| 80 | unknown | all | current_uncalibrated | 33 | 0 | 33 | 0 | 0 | 0 | 0 | 0 | 33/33 |
| 80 | unknown | all | current_configured | 33 | 0 | 31 | 0 | 2 | 0 | 0 | 0 | 31/33 |
| 80 | unknown | dense_gt_ge_40 | baseline | 3 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0/3 |
| 80 | unknown | dense_gt_ge_40 | baseline_classifier_demoted | 3 | 0 | 2 | 0 | 1 | 0 | 0 | 0 | 2/3 |
| 80 | unknown | dense_gt_ge_40 | current_uncalibrated | 3 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 3/3 |
| 80 | unknown | dense_gt_ge_40 | current_configured | 3 | 0 | 1 | 0 | 2 | 0 | 0 | 0 | 1/3 |
| 80 | unknown | near_target_plus_minus_10 | baseline | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0/0 |
| 80 | unknown | near_target_plus_minus_10 | baseline_classifier_demoted | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0/0 |
| 80 | unknown | near_target_plus_minus_10 | current_uncalibrated | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0/0 |
| 80 | unknown | near_target_plus_minus_10 | current_configured | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0/0 |
| 50 | assumed_elapsed | all | baseline | 33 | 3 | 1 | 0 | 32 | 0 | 0 | 0 | 1/33 |
| 50 | assumed_elapsed | all | baseline_classifier_demoted | 33 | 3 | 30 | 1 | 2 | 0 | 0 | 1 | 30/33 |
| 50 | assumed_elapsed | all | current_uncalibrated | 33 | 3 | 32 | 0 | 1 | 0 | 0 | 2 | 30/33 |
| 50 | assumed_elapsed | all | current_configured | 33 | 3 | 22 | 0 | 11 | 0 | 0 | 0 | 22/33 |
| 50 | assumed_elapsed | dense_gt_ge_40 | baseline | 3 | 3 | 0 | 0 | 3 | 0 | 0 | 0 | 0/3 |
| 50 | assumed_elapsed | dense_gt_ge_40 | baseline_classifier_demoted | 3 | 3 | 1 | 1 | 1 | 0 | 0 | 1 | 1/3 |
| 50 | assumed_elapsed | dense_gt_ge_40 | current_uncalibrated | 3 | 3 | 2 | 0 | 1 | 0 | 0 | 2 | 0/3 |
| 50 | assumed_elapsed | dense_gt_ge_40 | current_configured | 3 | 3 | 0 | 0 | 3 | 0 | 0 | 0 | 0/3 |
| 50 | assumed_elapsed | near_target_plus_minus_10 | baseline | 3 | 3 | 0 | 0 | 3 | 0 | 0 | 0 | 0/3 |
| 50 | assumed_elapsed | near_target_plus_minus_10 | baseline_classifier_demoted | 3 | 3 | 1 | 1 | 1 | 0 | 0 | 1 | 1/3 |
| 50 | assumed_elapsed | near_target_plus_minus_10 | current_uncalibrated | 3 | 3 | 2 | 0 | 1 | 0 | 0 | 2 | 0/3 |
| 50 | assumed_elapsed | near_target_plus_minus_10 | current_configured | 3 | 3 | 0 | 0 | 3 | 0 | 0 | 0 | 0/3 |
| 50 | unknown | all | baseline | 33 | 3 | 1 | 0 | 32 | 0 | 0 | 0 | 1/33 |
| 50 | unknown | all | baseline_classifier_demoted | 33 | 3 | 30 | 1 | 2 | 0 | 0 | 1 | 30/33 |
| 50 | unknown | all | current_uncalibrated | 33 | 3 | 32 | 0 | 1 | 0 | 0 | 2 | 30/33 |
| 50 | unknown | all | current_configured | 33 | 3 | 22 | 0 | 11 | 0 | 0 | 0 | 22/33 |
| 50 | unknown | dense_gt_ge_40 | baseline | 3 | 3 | 0 | 0 | 3 | 0 | 0 | 0 | 0/3 |
| 50 | unknown | dense_gt_ge_40 | baseline_classifier_demoted | 3 | 3 | 1 | 1 | 1 | 0 | 0 | 1 | 1/3 |
| 50 | unknown | dense_gt_ge_40 | current_uncalibrated | 3 | 3 | 2 | 0 | 1 | 0 | 0 | 2 | 0/3 |
| 50 | unknown | dense_gt_ge_40 | current_configured | 3 | 3 | 0 | 0 | 3 | 0 | 0 | 0 | 0/3 |
| 50 | unknown | near_target_plus_minus_10 | baseline | 3 | 3 | 0 | 0 | 3 | 0 | 0 | 0 | 0/3 |
| 50 | unknown | near_target_plus_minus_10 | baseline_classifier_demoted | 3 | 3 | 1 | 1 | 1 | 0 | 0 | 1 | 1/3 |
| 50 | unknown | near_target_plus_minus_10 | current_uncalibrated | 3 | 3 | 2 | 0 | 1 | 0 | 0 | 2 | 0/3 |
| 50 | unknown | near_target_plus_minus_10 | current_configured | 3 | 3 | 0 | 0 | 3 | 0 | 0 | 0 | 0/3 |

Threshold agreement only. A mask is not an independent adjudication of feeding, health, passage timing or action eligibility. Correct continue coverage is not automation coverage.

Empty subsets have null rates, not a zero-error success. At 80% there are no target-reaching cases.
Dense means expert GT ≥40%; near-target means within ±10 pp. These are descriptive slices, not new acceptance thresholds.
Uncertainty intervals are withheld: biological unit IDs and an independent prospective sample are absent.
Review and reimage counts are separate; unavailable quality checks cannot establish a good reimage rate.

## Sequential ablations

1. baseline → baseline_classifier_demoted: only the classifier trigger is neutralized with normal/1.0.
2. baseline_classifier_demoted → current_uncalibrated: current policy at the same zero-cutoff reading, with unavailable checks explicit.
3. current_uncalibrated → current_configured: configured reading and band together; not a new model or isolated band effect.

Full action transitions, confusion counts and denominators are in `report.json`; every paired output/reason is in `decisions.jsonl`.

## Limits and remaining evidence

- Not an end-to-end v2/v4 benchmark or a fine-tuning comparison.
- Classifier demotion and policy/calibration changes are sequential ablations, not causal attribution.
- Quality and anomaly checks are unavailable on these images, not assumed to pass.
- No target-reaching ground truth at 80%; zero early passage cannot establish passage safety.
- 50% is a diagnostic scenario, not a recommended culture passage threshold.
- No review-time measurement, workload saving, pilot approval or host action is established.
- v2's missing synthetic headline artifacts are not reconstructed.
- C2C12 cached readings are not independent truth and are outside this first bundle.
