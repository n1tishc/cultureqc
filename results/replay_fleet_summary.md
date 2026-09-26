# A2 replay fleet

Generated 2026-09-26 16:35 UTC by `scripts/replay_fleet.py` from `cache`; seed 0, split seed 0, crop_frac 0.25. Visits are replayed from the compute cache (C2C12 time-lapse, Ker et al. 2018, CC BY 4.0; fault sequences are simulated from it). No model runs at replay time.

## Split

By base sequence, stratified by the fault type built on it, 40% tuning. Fault twins follow their base. Tuning is for fitting thresholds only; nothing below reports a rate on it.

| stratum | tuning | held-out |
|---|---|---|
| contamination_onset (base sequences) | 2 | 2 |
| growth_stall (base sequences) | 2 | 2 |
| none (base sequences) | 6 | 10 |
| contamination_onset (fault sequences) | 2 | 2 |
| growth_stall (fault sequences) | 2 | 2 |
| lamp_dimming (fault sequences) | 10 | 14 |

Base sequences per experiment: 90303: 6 tuning / 2 held-out; 90318: 1 tuning / 7 held-out; 90325: 3 tuning / 5 held-out.

Held-out fault sequences: contamination_onset 2, growth_stall 2, lamp_dimming 14. A detection rate on a type is over that many sequences.

## Visits per stream

Jitter ±25% of the mean interval. The growth model needs at least 5 visits.

| cadence | FOVs | streams | visits per stream (min / median / max) | streams below 5 visits |
|---|---|---|---|---|
| 6 h | 1 | 56 | 14 / 15 / 15 | 0 |
| 6 h | 3 | 56 | 14 / 15 / 15 | 0 |
| 12 h | 1 | 56 | 8 / 8 / 8 | 0 |
| 12 h | 3 | 56 | 8 / 8 / 8 | 0 |

24 h cadence (jitter ±6 h, measured on the 24 base sequences, 1 FOV): 5–5 visits per stream, median 5; 0 of 24 below the growth model's minimum of 5. A backtest cut point or a one-step-ahead prediction fits only the visits before it, so with at most 5 visits it never has 5 before the one it scores: 24 h is reported as **not testable on the C2C12 span** (spec §2A.3). Celltrio's real cadence is an open question.

## Fault twins match their base before onset

Same seed for every stream, so a twin should repeat its base's visits (time, frame, crops) until onset.

| fault type | twins that match, over all cadence × FOV cells |
|---|---|
| contamination_onset | 16/16 |
| growth_stall | 16/16 |
| lamp_dimming | 96/96 |

## Held-out rates (6 h, 1 FOV)

Per visit, so visits within a stream are not independent: n sequences is the sample size.
Class probabilities are temperature-scaled (configs/calibration.yaml, fit on synthetic tiles).

| streams | sequences | visits | quality gate pass | QC class_pred |
|---|---|---|---|---|
| normal (base) | 14 | 208 | 0/208 (0%) | contamination_suspected 37/208 (18%), detachment 22/208 (11%), image_quality 136/208 (65%), normal 13/208 (6%) |
| contamination_onset after onset | 2 | 16 | 0/16 (0%) | contamination_suspected 15/16 (94%), normal 1/16 (6%) |
| growth_stall after onset | 2 | 17 | 0/17 (0%) | contamination_suspected 3/17 (18%), image_quality 14/17 (82%) |
| lamp_dimming after onset | 14 | 110 | 0/110 (0%) | contamination_suspected 32/110 (29%), detachment 20/110 (18%), image_quality 47/110 (43%), normal 11/110 (10%) |

Fault rows count visits after onset (`fault.hours_since_start > onset_hours`). Growth-stall frames are real earlier frames replayed on a slowed clock, so they are never `is_modified`.

Quality gate reasons on the held-out normal visits (a visit can fail several): uniformity_above_threshold 208, exposure_out_of_range 207, blur_below_threshold 128. The gate's thresholds (configs/quality.yaml) were calibrated on synthetic tiles.
