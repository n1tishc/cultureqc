# Growth model backtest on real C2C12 sequences (A1)

Generated 2026-09-26 16:53 UTC by `scripts/backtest_growth.py` from `cache`. Data: C2C12 time-lapse, Ker et al., *Sci Data* 5:180237 (2018), CC BY 4.0. Visits are simulated from the recorded frames (replay); no model runs at replay time.

**Held-out fleet only:** 14 base sequences from `results/replay_fleet_split.csv`. Replayed exactly as the A2 fleet: mean cadence 6 h, 12 h (jitter ±25%), 0.25 crops, seed 0. Bootstrap: 500 resamples.

**Truth** is the first crossing of the target in each sequence's hourly *full-frame* confluency as Cellpose-SAM reads it (not a manual annotation). V1 found Cellpose-SAM reads about 8 pp low on EVICAN, so "50%" here means 50% as Cellpose-SAM measures it.

**FOV settings.** *with repositioning*: each visit reads 1 or 3 randomly placed 0.25 crops of the frame (crop positions differ from frame to frame). *without repositioning*: the full-frame reading at the same visit times. That is the same measurement the truth comes from, so it is a ceiling: extrapolation error with perfect measurement. Its fit weights use the 0.5-crop noise fit (`fallback_crop_frac`), a proxy; there is no measured full-frame noise.

Crop vs full frame on the held-out frames: the mean of a frame's 0.25 crops is a median -0.71 pp from its full-frame reading (n=1228 frames), -1.86 pp on frames at ≥ 30% (n=284).

## Which targets can be tested

| target | held-out sequences that cross it |
|---|---|
| 50% | 5 of 14 |
| 60% | 0 of 14 |
| 70% | 0 of 14 |
| 80% | 0 of 14 |

## Truth per crossing sequence

| target | sequence | first crossing (h) | max (%) | margin over target (pp) | frames at or above target after crossing | last frame (%) |
|---|---|---|---|---|---|---|
| 50% | c2c12_090303_exp1_F0003_Data | 83.2 | 50.5 | 0.5 | 1/1 | 50.5 |
| 50% | c2c12_090318_exp1_F0003_Data | 86.6 | 51.8 | 1.8 | 2/2 | 51.8 |
| 50% | c2c12_090318_exp1_F0011_Data | 69.9 | 54.8 | 4.8 | 7/19 | 47.1 |
| 50% | c2c12_090318_exp1_F0013_Data | 52.7 | 57.0 | 7.0 | 32/36 | 52.9 |
| 50% | c2c12_090325_exp1_F0003_Data | 84.7 | 50.7 | 0.7 | 2/2 | 50.7 |

## Outcomes and errors

Every crossing sequence is counted in every row. *cut not reached*: the observed series never reaches the cut. *cut at/after crossing*: it reaches the cut only at or after the true crossing, so there is nothing left to predict. *too few visits at cut*: fewer than the growth model's minimum (a noisy reading hit the cut early). *not reached*: the fit levels off below the target (a miss). Error = predicted − true (h); negative means predicted too early. *Lead*: true crossing − cut (h), how far ahead the prediction was made. A prediction whose bootstrap gave too few crossings has no interval. Medians only for ≥ 3 predictions; coverage is a count.

| target | cut | cadence | FOVs | sequences | cut not reached | cut at/after crossing | too few visits at cut | fit failed | not reached | predicted | median abs error (h) | median signed error (h) | median lead (h) | 90% interval covers truth |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 50% | target-20 | 6 h | 1 crop | 5 | 0 | 1 | 0 | 0 | 1 | 3 | 17.0 | -15.2 | 29.0 | 0/2 (1 without interval) |
| 50% | target-20 | 6 h | 3 crops | 5 | 0 | 0 | 0 | 0 | 0 | 5 | 9.2 | -7.7 | 16.3 | 4/5 |
| 50% | target-20 | 6 h | full frame | 5 | 0 | 0 | 0 | 0 | 1 | 4 | 5.5 | 5.5 | 20.7 | 3/4 |
| 50% | target-20 | 12 h | 1 crop | 5 | 0 | 0 | 1 | 0 | 1 | 3 | 2.1 | -2.1 | 14.6 | 3/3 |
| 50% | target-20 | 12 h | 3 crops | 5 | 0 | 0 | 0 | 0 | 1 | 4 | 4.4 | 0.2 | 12.7 | 3/4 |
| 50% | target-20 | 12 h | full frame | 5 | 0 | 0 | 0 | 0 | 0 | 5 | 3.2 | 3.2 | 14.6 | 4/5 |
| 50% | target-10 | 6 h | 1 crop | 5 | 0 | 1 | 0 | 0 | 0 | 4 | 4.9 | -2.4 | 14.7 | 3/4 |
| 50% | target-10 | 6 h | 3 crops | 5 | 0 | 0 | 0 | 0 | 0 | 5 | 9.0 | 9.0 | 10.2 | 4/5 |
| 50% | target-10 | 6 h | full frame | 5 | 0 | 0 | 0 | 0 | 0 | 5 | 2.4 | 2.4 | 6.6 | 3/5 |
| 50% | target-10 | 12 h | 1 crop | 5 | 0 | 0 | 1 | 0 | 1 | 3 | 2.1 | -2.1 | 14.6 | 3/3 |
| 50% | target-10 | 12 h | 3 crops | 5 | 0 | 1 | 0 | 0 | 0 | 4 | 5.8 | 4.4 | 8.1 | 3/4 |
| 50% | target-10 | 12 h | full frame | 5 | 0 | 1 | 0 | 0 | 0 | 4 | 1.9 | 0.7 | 2.9 | 3/4 |

## V3

V3 asks for median abs T* error ≤ 12 h and 90% coverage of 80–95% at the target − 10 cut. At most 5 held-out sequences cross any target, so coverage moves in steps of 20 pp or more; **V3 has no verdict at this n.** The numbers above are reported as measured.

## Notes

- Visits within a sequence are not independent, and the cadences and FOV settings reuse the same sequences: the sample size is the number of sequences.
- `fit_growth()` fits every visit it is given. The live trend path (`one_step_ahead_series()`, History's trend view) drops visits that fail the quality gate, and the gate currently fails every C2C12 frame (docs/STATUS.md, item 14).
- The bootstrap resamples residuals within the AIC-chosen model only, so it misses model-selection uncertainty (see `results/growth_backtest_synthetic.md` and V3's fix).
- 24 h cadence is not testable on the C2C12 span (`results/replay_fleet_summary.md`).
- Raw rows: `results/growth_backtest.csv`; per-sequence truth: `results/growth_backtest_truth.csv`.
