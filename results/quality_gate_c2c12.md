# Quality gate thresholds for `c2c12`

Generated 2026-09-26T17:02:28Z by `scripts/calibrate_quality_gate.py --entry c2c12`. Datasets: c2c12. C2C12 images: Ker et al., *Sci Data* 5:180237 (2018), CC BY 4.0; fault frames are simulated from them.

Thresholds = percentiles 1 and 99 of each metric over the 860 frames of the 10 *tuning* base sequences, the same rule as the synthetic-tile thresholds. Frames within a sequence are not independent; n sequences is the sample size.

| metric | synthetic tiles (top level) | this entry |
|---|---|---|
| blur floor | 100.88 | 46.57 |
| exposure range | 127.79–129.22 | 95.33–148.37 |
| uniformity ceiling | 2.231 | 25.305 |

## Fail rates

| frames | sequences | frames | fail rate | reasons |
|---|---|---|---|---|
| tuning normal (in sample) | 10 | 860 | 36 (4.2%) | blur_below_threshold 9, exposure_out_of_range 18, uniformity_above_threshold 9 |
| held-out normal | 14 | 1228 | 149 (12.1%) | blur_below_threshold 29, exposure_out_of_range 110, uniformity_above_threshold 45 |
| held-out contamination_onset (modified frames) | 2 | 49 | 45 (91.8%) | exposure_out_of_range 44, uniformity_above_threshold 6 |
| held-out lamp_dimming (modified frames) | 14 | 327 | 167 (51.1%) | blur_below_threshold 60, exposure_out_of_range 167 |

Held-out lamp dimming by severity (intensity factor; 1.0 = undimmed):

| factor | frames | fail rate |
|---|---|---|
| (0.6, 0.7] | 187 | 130 (69.5%) |
| (0.7, 0.8] | 56 | 26 (46.4%) |
| (0.8, 0.9] | 42 | 8 (19.0%) |
| (0.9, 1.0] | 42 | 3 (7.1%) |

Held-out normal fail rate per sequence: 090303_exp1_F0003_Data 0%, 090303_exp1_F0014_Data 34.1%, 090318_exp1_F0001_Data 22.5%, 090318_exp1_F0003_Data 31.5%, 090318_exp1_F0005_Data 30.3%, 090318_exp1_F0007_Data 39.3%, 090318_exp1_F0011_Data 0%, 090318_exp1_F0013_Data 0%, 090318_exp1_F0016_Data 0%, 090325_exp1_F0003_Data 0%, 090325_exp1_F0007_Data 11.5%, 090325_exp1_F0011_Data 0%, 090325_exp1_F0013_Data 0%, 090325_exp1_F0018_Data 0%.

Contamination is not an image-quality defect; its row shows only whether the gate reacts to it.
