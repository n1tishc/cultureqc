# Growth model backtest on real C2C12 sequences (A1)

Generated 2026-09-26 17:05 UTC by `scripts/backtest_growth.py` from `cache`. Data: C2C12 time-lapse, Ker et al., *Sci Data* 5:180237 (2018), CC BY 4.0. Visits are simulated from the recorded frames (replay); no model runs at replay time.

**Held-out fleet only:** 14 base sequences from `results/replay_fleet_split.csv`. Replayed exactly as the A2 fleet: mean cadence 6 h, 12 h (jitter ±25%), 0.25 crops, seed 0. Bootstrap: 500 resamples.

**Truth** is the first crossing of the target in each sequence's hourly *full-frame* confluency as Cellpose-SAM reads it (not a manual annotation). V1 found Cellpose-SAM reads about 8 pp low on EVICAN, so "50%" here means 50% as Cellpose-SAM measures it.

**FOV settings.** *with repositioning*: each visit reads 1 or 3 randomly placed 0.25 crops of the frame (crop positions differ from frame to frame). *without repositioning*: the full-frame reading at the same visit times. That is the same measurement the truth comes from, so it is a ceiling: extrapolation error with perfect measurement. Its fit weights use the 0.5-crop noise fit (`fallback_crop_frac`), a proxy; there is no measured full-frame noise.

Crop vs full frame on the held-out frames: the mean of a frame's 0.25 crops is a median -0.71 pp from its full-frame reading (n=1228 frames), -1.86 pp on frames at ≥ 30% (n=284).

## Which targets can be tested

| target | in spec | held-out sequences that cross it |
|---|---|---|
| 30% | **no, added** | 12 of 14 |
| 40% | **no, added** | 8 of 14 |
| 50% | yes | 5 of 14 |
| 60% | yes | 0 of 14 |
| 70% | yes | 0 of 14 |
| 80% | yes | 0 of 14 |

30% and 40% are not A1 targets. They were added because only 50% is crossed by the held-out sequences; they test the same fit and extrapolation on more sequences, at lower confluency (cuts at 10–30%), and never count toward V3.

## Truth per crossing sequence

| target | sequence | first crossing (h) | max (%) | margin over target (pp) | frames at or above target after crossing | last frame (%) |
|---|---|---|---|---|---|---|
| 30% | c2c12_090303_exp1_F0003_Data | 62.4 | 50.5 | 20.5 | 22/22 | 50.5 |
| 30% | c2c12_090303_exp1_F0014_Data | 78.0 | 36.3 | 6.3 | 7/7 | 36.3 |
| 30% | c2c12_090318_exp1_F0001_Data | 58.7 | 48.3 | 18.3 | 27/30 | 47.1 |
| 30% | c2c12_090318_exp1_F0003_Data | 67.8 | 51.8 | 21.8 | 21/21 | 51.8 |
| 30% | c2c12_090318_exp1_F0007_Data | 73.2 | 36.2 | 6.2 | 15/15 | 35.1 |
| 30% | c2c12_090318_exp1_F0011_Data | 39.4 | 54.8 | 24.8 | 49/49 | 47.1 |
| 30% | c2c12_090318_exp1_F0013_Data | 34.8 | 57.0 | 27.0 | 54/54 | 52.9 |
| 30% | c2c12_090325_exp1_F0003_Data | 57.4 | 50.7 | 20.7 | 29/29 | 50.7 |
| 30% | c2c12_090325_exp1_F0007_Data | 85.1 | 30.6 | 0.6 | 1/1 | 30.6 |
| 30% | c2c12_090325_exp1_F0011_Data | 57.6 | 45.0 | 15.0 | 29/29 | 43.9 |
| 30% | c2c12_090325_exp1_F0013_Data | 57.5 | 43.1 | 13.1 | 29/29 | 43.1 |
| 30% | c2c12_090325_exp1_F0018_Data | 85.9 | 30.1 | 0.1 | 1/1 | 30.1 |
| 40% | c2c12_090303_exp1_F0003_Data | 75.5 | 50.5 | 10.5 | 9/9 | 50.5 |
| 40% | c2c12_090318_exp1_F0001_Data | 74.0 | 48.3 | 8.3 | 14/15 | 47.1 |
| 40% | c2c12_090318_exp1_F0003_Data | 77.3 | 51.8 | 11.8 | 11/11 | 51.8 |
| 40% | c2c12_090318_exp1_F0011_Data | 51.0 | 54.8 | 14.8 | 38/38 | 47.1 |
| 40% | c2c12_090318_exp1_F0013_Data | 44.4 | 57.0 | 17.0 | 44/44 | 52.9 |
| 40% | c2c12_090325_exp1_F0003_Data | 70.3 | 50.7 | 10.7 | 16/16 | 50.7 |
| 40% | c2c12_090325_exp1_F0011_Data | 70.5 | 45.0 | 5.0 | 16/16 | 43.9 |
| 40% | c2c12_090325_exp1_F0013_Data | 74.7 | 43.1 | 3.1 | 12/12 | 43.1 |
| 50% | c2c12_090303_exp1_F0003_Data | 83.2 | 50.5 | 0.5 | 1/1 | 50.5 |
| 50% | c2c12_090318_exp1_F0003_Data | 86.6 | 51.8 | 1.8 | 2/2 | 51.8 |
| 50% | c2c12_090318_exp1_F0011_Data | 69.9 | 54.8 | 4.8 | 7/19 | 47.1 |
| 50% | c2c12_090318_exp1_F0013_Data | 52.7 | 57.0 | 7.0 | 32/36 | 52.9 |
| 50% | c2c12_090325_exp1_F0003_Data | 84.7 | 50.7 | 0.7 | 2/2 | 50.7 |

## Outcomes and errors

Every crossing sequence is counted in every row. *cut not reached*: the observed series never reaches the cut. *cut at/after crossing*: it reaches the cut only at or after the true crossing, so there is nothing left to predict. *too few visits at cut*: fewer than the growth model's minimum (a noisy reading hit the cut early). *not reached*: the fit levels off below the target (a miss). Error = predicted − true (h); negative means predicted too early. *Lead*: true crossing − cut (h), how far ahead the prediction was made. A prediction whose bootstrap gave too few crossings has no interval. Medians only for ≥ 3 predictions; coverage is a count.

| target | cut | cadence | FOVs | sequences | cut not reached | cut at/after crossing | too few visits at cut | fit failed | not reached | predicted | median abs error (h) | median signed error (h) | median lead (h) | 90% interval covers truth |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 30% | target-20 | 6 h | 1 crop | 12 | 0 | 0 | 4 | 0 | 3 | 5 | 28.7 | -28.7 | 36.7 | 1/3 (2 without interval) |
| 30% | target-20 | 6 h | 3 crops | 12 | 0 | 0 | 5 | 0 | 2 | 5 | 10.6 | -10.6 | 42.9 | 2/4 (1 without interval) |
| 30% | target-20 | 6 h | full frame | 12 | 0 | 0 | 2 | 0 | 7 | 3 | 18.1 | -11.8 | 36.6 | 2/3 |
| 30% | target-20 | 12 h | 1 crop | 12 | 0 | 0 | 8 | 0 | 2 | 2 | — | — | — | 1/2 |
| 30% | target-20 | 12 h | 3 crops | 12 | 0 | 0 | 9 | 0 | 0 | 3 | 5.5 | 1.2 | 36.2 | 2/3 |
| 30% | target-20 | 12 h | full frame | 12 | 0 | 0 | 9 | 0 | 2 | 1 | — | — | — | 1/1 |
| 30% | target-10 | 6 h | 1 crop | 12 | 0 | 1 | 1 | 0 | 1 | 9 | 11.4 | -10.1 | 22.5 | 6/9 |
| 30% | target-10 | 6 h | 3 crops | 12 | 0 | 1 | 0 | 0 | 2 | 9 | 9.1 | -1.3 | 9.3 | 8/9 |
| 30% | target-10 | 6 h | full frame | 12 | 0 | 0 | 0 | 0 | 1 | 11 | 4.6 | 4.6 | 10.7 | 4/11 |
| 30% | target-10 | 12 h | 1 crop | 12 | 0 | 3 | 3 | 0 | 1 | 5 | 7.2 | -2.6 | 17.5 | 2/4 (1 without interval) |
| 30% | target-10 | 12 h | 3 crops | 12 | 0 | 4 | 1 | 0 | 0 | 7 | 11.1 | 1.2 | 15.6 | 6/7 |
| 30% | target-10 | 12 h | full frame | 12 | 0 | 1 | 2 | 0 | 1 | 8 | 4.4 | 4.4 | 4.9 | 6/8 |
| 40% | target-20 | 6 h | 1 crop | 8 | 0 | 0 | 1 | 0 | 1 | 6 | 9.7 | -9.0 | 28.3 | 4/6 |
| 40% | target-20 | 6 h | 3 crops | 8 | 0 | 0 | 0 | 0 | 2 | 6 | 6.9 | 0.9 | 16.2 | 6/6 |
| 40% | target-20 | 6 h | full frame | 8 | 0 | 0 | 0 | 0 | 2 | 6 | 9.8 | 9.8 | 22.7 | 2/6 |
| 40% | target-20 | 12 h | 1 crop | 8 | 0 | 1 | 3 | 0 | 0 | 4 | 5.0 | -0.8 | 10.9 | 3/4 |
| 40% | target-20 | 12 h | 3 crops | 8 | 0 | 0 | 1 | 0 | 0 | 7 | 5.7 | -1.0 | 7.1 | 5/7 |
| 40% | target-20 | 12 h | full frame | 8 | 0 | 0 | 2 | 0 | 0 | 6 | 3.7 | 3.5 | 16.6 | 3/6 |
| 40% | target-10 | 6 h | 1 crop | 8 | 0 | 1 | 0 | 0 | 2 | 5 | 16.3 | -6.8 | 16.3 | 3/5 |
| 40% | target-10 | 6 h | 3 crops | 8 | 0 | 0 | 0 | 0 | 1 | 7 | 4.5 | -0.7 | 7.1 | 6/7 |
| 40% | target-10 | 6 h | full frame | 8 | 0 | 0 | 0 | 0 | 0 | 8 | 2.0 | 1.9 | 9.1 | 6/8 |
| 40% | target-10 | 12 h | 1 crop | 8 | 0 | 2 | 1 | 0 | 1 | 4 | 2.0 | -1.5 | 4.9 | 4/4 |
| 40% | target-10 | 12 h | 3 crops | 8 | 0 | 2 | 0 | 0 | 0 | 6 | 3.6 | -0.1 | 5.8 | 6/6 |
| 40% | target-10 | 12 h | full frame | 8 | 0 | 0 | 0 | 0 | 0 | 8 | 2.5 | 2.5 | 4.2 | 6/8 |
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

V3 asks for median abs T* error ≤ 12 h and 90% coverage of 80–95% at the target − 10 cut, on the spec targets. At most 5 held-out sequences cross any target, so coverage moves in steps of 20 pp or more; **V3 has no verdict at this n.** The numbers above are reported as measured.

## Notes

- Visits within a sequence are not independent, and the cadences and FOV settings reuse the same sequences: the sample size is the number of sequences.
- `fit_growth()` fits every visit it is given. The live trend path (`one_step_ahead_series()`, History's trend view) drops visits that fail the quality gate; with the C2C12 gate entry, 12.1% of held-out normal frames fail it (`results/quality_gate_c2c12.md`).
- The bootstrap resamples residuals within the AIC-chosen model only, so it misses model-selection uncertainty (see `results/growth_backtest_synthetic.md` and V3's fix).
- 24 h cadence is not testable on the C2C12 span (`results/replay_fleet_summary.md`).
- Raw rows: `results/growth_backtest.csv`; per-sequence truth: `results/growth_backtest_truth.csv`.
