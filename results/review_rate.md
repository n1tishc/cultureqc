# Human-review rate

Generated 2026-10-04T17:21:21Z by `scripts/review_rate.py`. No model runs: readings, confidences and maps are the compute cache's (Cellpose-SAM cpsam_v2, Colab GPU, nb/03), same formula as the live path. C2C12 images: Ker et al., *Sci Data* 5:180237 (2018), CC BY 4.0; fault frames are simulated from them. Frames within a sequence are not independent; n sequences is the sample size.

## `rules_v0.5`: error band and passage hold

C2C12 frames read with profile `c2c12_ker2018` (uncalibrated; cutoff +0.0, no band; `configs/confluency_profiles.yaml`, `results/confluency_profiles.md`). With no calibration profile, every reading at or above the target goes to review: the rules never passage on an uncalibrated reading alone. The quality gate calibrated for the setup (`configs/quality.yaml`, entry `c2c12`) runs first, on the cached metrics, and a frame that fails it returns REIMAGE. Time since passage is assumed long enough. Boundary ambiguity no longer decides.

| target | group | images | re-image (quality gate) | band includes the target | held by the anomaly flag | uncalibrated, at or above target | passage | total to review |
|---|---|---|---|---|---|---|---|---|
| 80% | C2C12 held-out, normal | 1228 | 149 | 0 | 0 | 0 | 0 | 0 (0.0%) |
| 80% | C2C12 tuning, normal (comparison only) | 860 | 36 | 0 | 0 | 0 | 0 | 0 (0.0%) |
| 80% | C2C12 simulated contamination, bacteria 16.5× too large | 97 | 91 | 0 | 0 | 0 | 0 | 0 (0.0%) |
| 80% | C2C12 simulated lamp dimming | 552 | 347 | 0 | 0 | 0 | 0 | 0 (0.0%) |
| 50% | C2C12 held-out, normal | 1228 | 149 | 0 | 0 | 42 | 0 | 42 (3.4%) |
| 50% | C2C12 tuning, normal (comparison only) | 860 | 36 | 0 | 0 | 21 | 0 | 21 (2.4%) |
| 50% | C2C12 simulated contamination, bacteria 16.5× too large | 97 | 91 | 0 | 0 | 1 | 0 | 1 (1.0%) |
| 50% | C2C12 simulated lamp dimming | 552 | 347 | 0 | 0 | 4 | 0 | 4 (0.7%) |

## rules_v0.4, for comparison: boundary-ambiguity trigger

With the classifier demoted, rules_v0.4 had two rules that return `human_review`: boundary ambiguity above 0.70 (the record's `confidence` below the 0.30 floor), a density-sensitive review trigger that does not predict the reading's error (`results/confidence_vs_error.md`), and, since `rules_v0.3`, the passage hold (confluency at or above the target, but the anomaly check flagged the image). Readings at cutoff 0.0, full resolution. Quality-gate failures return REIMAGE (`results/quality_gate_c2c12.md`).

| group | sequences | images | sent to review | note |
|---|---|---|---|---|
| C2C12 held-out, full frames | 14 | 1228 | 70 (5.7%) | — |
| C2C12 tuning, full frames | 10 | 860 | 47 (5.5%) | comparison only |
| C2C12 held-out, confluency 0-20% | 14 | 750 | 0 (0.0%) | — |
| C2C12 held-out, confluency 20-40% | 13 | 318 | 0 (0.0%) | — |
| C2C12 held-out, confluency 40-60% | 8 | 160 | 70 (43.8%) | — |
| EVICAN eval2019 (real, expert masks) | — | 98 | 3 (3.1%) | — |
| C2C12 simulated lamp dimming | 24 | 552 | 60 (10.9%) | simulated fault frames |
| C2C12 simulated contamination, bacteria 16.5× too large | 4 | 97 | 13 (13.4%) | simulated fault frames; at real size see results/contamination_scale.md |
| C2C12 held-out, 0.25-frame FOV crops | 14 | 4912 | 451 (9.2%) | each crop segmented on its own, as the replay visits are |

Held-out C2C12 review rate per sequence: 090303_exp1_F0003 8.2%, 090303_exp1_F0014 0%, 090318_exp1_F0001 0%, 090318_exp1_F0003 0%, 090318_exp1_F0005 0%, 090318_exp1_F0007 0%, 090318_exp1_F0011 31.5%, 090318_exp1_F0013 24.7%, 090318_exp1_F0016 0%, 090325_exp1_F0003 0%, 090325_exp1_F0007 0%, 090325_exp1_F0011 14.9%, 090325_exp1_F0013 0%, 090325_exp1_F0018 0%.

Highest held-out C2C12 confluency: 57.0%, so no frame reaches the 60-100% bins. Held-out frames at 40% or more, per sequence (sent to review / frames): 090303_exp1_F0003 7/9, 090318_exp1_F0001 0/14, 090318_exp1_F0003 0/11, 090318_exp1_F0011 28/38, 090318_exp1_F0013 22/44, 090325_exp1_F0003 0/16, 090325_exp1_F0011 13/16, 090325_exp1_F0013 0/12.

## rules_v0.4, for comparison: passage hold on an anomaly flag (since rules_v0.3)

Frames with an anomaly score (A4). Passage-eligible: boundary ambiguity at or below the trigger and confluency at or above the target (time since passage assumed long enough). Held: passage-eligible and flagged, so sent to review instead of passage. Total: ambiguity trigger or held.

| target | group | images | above the ambiguity trigger | passage-eligible | held by the anomaly flag | total to review |
|---|---|---|---|---|---|---|
| 80% | C2C12 held-out, normal | 1228 | 70 | 0 | 0 | 70 (5.7%) |
| 80% | C2C12 tuning, normal (comparison only) | 860 | 47 | 0 | 0 | 47 (5.5%) |
| 80% | C2C12 simulated contamination, bacteria 16.5× too large | 97 | 13 | 64 | 64 | 77 (79.4%) |
| 80% | C2C12 simulated lamp dimming | 552 | 60 | 0 | 0 | 60 (10.9%) |
| 50% | C2C12 held-out, normal | 1228 | 70 | 14 | 1 | 71 (5.8%) |
| 50% | C2C12 tuning, normal (comparison only) | 860 | 47 | 8 | 0 | 47 (5.5%) |
| 50% | C2C12 simulated contamination, bacteria 16.5× too large | 97 | 13 | 76 | 76 | 89 (91.8%) |
| 50% | C2C12 simulated lamp dimming | 552 | 60 | 11 | 0 | 60 (10.9%) |
