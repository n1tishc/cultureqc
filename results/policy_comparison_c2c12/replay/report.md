# C2C12 cached-policy workload comparison

**No independent confluency/action truth. Not a detection or automation validation.**

1228 unmodified held-out frames, 14 sequence groups, 3 experiment groups; 4912 repeated-context rows.
The split holds out sequences, not experiments. All experiment groups also occur in tuning.
Maximum cached reading: 56.98%. A reading is not ground truth.

Explicit rule-action burden only, not measured human workload. Current continue/feed outputs still require host review/authorization. Anomaly flag rate is not human-review rate.

## Pooled action counts, with dense-reading burden

| Target | Timing | Subset | Policy | Frames | Continue | Passage | Review | Reimage |
|---|---|---|---|---:|---:|---:|---:|---:|
| 80 | assumed_elapsed | all | baseline | 1228 | 251 | 0 | 977 | 0 |
| 80 | assumed_elapsed | all | baseline_classifier_demoted | 1228 | 1158 | 0 | 70 | 0 |
| 80 | assumed_elapsed | all | current_configured | 1228 | 1079 | 0 | 0 | 149 |
| 80 | assumed_elapsed | dense_reading_ge_40 | baseline | 160 | 30 | 0 | 130 | 0 |
| 80 | assumed_elapsed | dense_reading_ge_40 | baseline_classifier_demoted | 160 | 90 | 0 | 70 | 0 |
| 80 | assumed_elapsed | dense_reading_ge_40 | current_configured | 160 | 135 | 0 | 0 | 25 |
| 80 | unknown | all | baseline | 1228 | 251 | 0 | 977 | 0 |
| 80 | unknown | all | baseline_classifier_demoted | 1228 | 1158 | 0 | 70 | 0 |
| 80 | unknown | all | current_configured | 1228 | 1079 | 0 | 0 | 149 |
| 80 | unknown | dense_reading_ge_40 | baseline | 160 | 30 | 0 | 130 | 0 |
| 80 | unknown | dense_reading_ge_40 | baseline_classifier_demoted | 160 | 90 | 0 | 70 | 0 |
| 80 | unknown | dense_reading_ge_40 | current_configured | 160 | 135 | 0 | 0 | 25 |
| 50 | assumed_elapsed | all | baseline | 1228 | 246 | 5 | 977 | 0 |
| 50 | assumed_elapsed | all | baseline_classifier_demoted | 1228 | 1144 | 14 | 70 | 0 |
| 50 | assumed_elapsed | all | current_configured | 1228 | 1037 | 0 | 42 | 149 |
| 50 | assumed_elapsed | dense_reading_ge_40 | baseline | 160 | 25 | 5 | 130 | 0 |
| 50 | assumed_elapsed | dense_reading_ge_40 | baseline_classifier_demoted | 160 | 76 | 14 | 70 | 0 |
| 50 | assumed_elapsed | dense_reading_ge_40 | current_configured | 160 | 93 | 0 | 42 | 25 |
| 50 | unknown | all | baseline | 1228 | 246 | 5 | 977 | 0 |
| 50 | unknown | all | baseline_classifier_demoted | 1228 | 1144 | 14 | 70 | 0 |
| 50 | unknown | all | current_configured | 1228 | 1037 | 0 | 42 | 149 |
| 50 | unknown | dense_reading_ge_40 | baseline | 160 | 25 | 5 | 130 | 0 |
| 50 | unknown | dense_reading_ge_40 | baseline_classifier_demoted | 160 | 76 | 14 | 70 | 0 |
| 50 | unknown | dense_reading_ge_40 | current_configured | 160 | 93 | 0 | 42 | 25 |

Dense means cached reading ≥40%, not annotated density. 50% is a diagnostic target only.
No cached reading reaches 80%; zero passage does not demonstrate passage safety.
Review and reimage are separate; their sum is explicit deferred-output burden, not elapsed work.

## Grouping and provenance

`report.json` includes every sequence and experiment at both targets/timings and both subsets.
It also supplies equal-sequence and equal-experiment mean rates alongside frame-weighted pooled counts.
Empty dense subsets retain zero counts and null rates; group averages exclude them and disclose denominators.
No confidence intervals or decision-accuracy estimates are inferred from correlated frames.
The three policies isolate classifier neutralization, then current rules plus quality/anomaly policy.
C2C12 remains uncalibrated (cutoff 0, no band); no calibration or model gain is claimed.
Historical centre-tile anomaly flags are replayed, not new whole-frame detection signals.
Bank array identity and NPZ file identity are distinct hashes. Score-to-bank binding is not authenticated per row.
Bundle checksums establish reproducibility, not signed custody: the manifest itself has no independent trusted anchor.
Quality is reevaluated from frozen metrics/config; anomaly flags are checked against serialized thresholds, not rescored.

## Limits

- Workload-only cached-policy replay, not end-to-end v2/v4 or fine-tuned model evidence.
- Normal means unmodified source frames, not independently adjudicated healthy cultures.
- No independent confluency truth: no accuracy, early-passage or ready-called-continue metrics.
- The 14 sequence groups share 3 experiment groups; all 3 occur in tuning too. Not experiment-held-out.
- Frames and repeated contexts are correlated; no frame-independent confidence intervals.
- 50% is diagnostic, not a recommended passage threshold; no cached reading reaches 80%.
- No synthetic faults or growth-stall resampling; their absence does not imply detection success.
- No exact historical weight authentication or per-row score-to-bank binding; raw images are not rehashed.
- No observed review duration, workflow retry cost, saved time or ROI.
- Current outputs are advisory and the shipped C2C12 profile cannot authorize passage.
