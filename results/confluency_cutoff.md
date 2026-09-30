# Cellpose-SAM probability cutoff, calibrated off the evaluation subset

Generated 2026-09-30T19:49:28Z by `scripts/confluency_cutoff.py`. EVICAN eval2019 (Parekh et al., *Bioinformatics* 36(12):3863, 2020; CC BY 4.0), 98 images with expert `Cell` masks; GT confluency as in `results/confluency_real_summary.md`. Full-resolution Cellpose-SAM (cpsam_v2) probability maps, the call `culture/seg.py::cpsam_confluency` makes. Nothing here changes the shipped default (cutoff 0.0).

## Rule

Fixed in the script before the full-resolution maps were scored: grid -4.0 to +1.0 logit in 0.5 steps; calibration = the 65 eval2019 images not in `results/confluency_real.csv` (includes the 6-image tuning split and 15_Caco-2.jpg); pick = lowest calibration MAE, no tie rule; evaluation = the 33 images of `results/confluency_real.csv`.

Disclosure: the cutoff hypothesis came from the error analysis on the 33, and a quarter-resolution sweep of the cached maps, showing the evaluation curve too, was seen before the rule was written. The 33 are all under 500,000 px (the original subset's time budget); 28 of the 65 calibration images are larger. The same scratch sweep also tried a linear correction fitted on the 65 (evaluation MAE 6.76 pp, quarter resolution); it is not part of this rule.

## Curve

| cutoff (logit) | calibration MAE, n=65 (pp) | evaluation MAE, n=33 (pp) |
|---|---:|---:|
| -4.0 | 7.13 | 4.58 |
| -3.5 (pick) | 6.95 | 3.78 |
| -3.0 | 7.00 | 3.40 |
| -2.5 | 7.00 | 3.56 |
| -2.0 | 7.15 | 4.02 |
| -1.5 | 7.79 | 4.70 |
| -1.0 | 8.57 | 5.64 |
| -0.5 | 9.41 | 6.88 |
| +0.0 (shipped) | 10.24 | 8.36 |
| +0.5 | 11.01 | 9.54 |
| +1.0 | 11.87 | 10.66 |

## Result on the 33 held-out images

| | shipped, cutoff 0.0 | calibrated, cutoff -3.5 |
|---|---:|---:|
| MAE (pp) | 8.36 | 3.78 |
| median absolute error (pp) | 5.49 | 2.78 |
| mean signed error (pp) | -8.33 | 1.63 |
| images off by more than 10 pp | 13 of 33 | 3 of 33 |
| images off by more than 15 pp | 8 of 33 | 1 of 33 |

By ground-truth band (evaluation images):

| GT band | n | MAE at 0.0 (pp) | MAE at pick (pp) |
|---|---:|---:|---:|
| 0-20% | 23 | 6.74 | 3.44 |
| 20-40% | 7 | 10.34 | 3.09 |
| 40-70% | 3 | 16.15 | 7.98 |

Calibration set, in-sample: MAE 10.24 → 6.95 pp, off by more than 10 pp 22 → 12 of 65.

Largest remaining errors on the 33 at the pick:

| image | GT (%) | at 0.0 (%) | at pick (%) |
|---|---:|---:|---:|
| 2_769p.jpg | 20.0 | 6.6 | 37.6 |
| 14_Caco-2.jpg | 54.9 | 31.5 | 40.6 |
| 54_MCF.jpg | 8.1 | 8.4 | 20.7 |
| 32_FADU.jpg | 58.6 | 55.8 | 67.0 |
| 70_RAW.jpg | 2.9 | 3.1 | 10.0 |
| 98_HT1080.jpg | 4.8 | 3.3 | 11.7 |

Largest swings between the two cutoffs, all 98 (the reading depends on the cutoff most where the map sits between them):

| image | split | GT (%) | at 0.0 (%) | at pick (%) |
|---|---|---:|---:|---:|
| 37_HEL299.jpg | calib65 | 21.3 | 0.1 | 60.6 |
| 38_HEL299.jpg | calib65 | 15.6 | 19.0 | 52.9 |
| 2_769p.jpg | eval33 | 20.0 | 6.6 | 37.6 |
| 49_HT29.jpg | calib65 | 57.6 | 18.5 | 45.4 |
| 24_DLD.jpg | calib65 | 50.9 | 42.8 | 66.9 |

## What the cutoff does not fix

- 15_Caco-2.jpg (GT 65.1%, the only eval2019 image above 60%): 0.0% at 0.0, 2.1% at the pick; the map's highest logit is -1.33, so no cutoff in the grid finds these cells.
- 48_HT29.jpg, the site's error case (GT 51.6%): 29.3% at confidence 0.265 at 0.0; 52.9% at confidence 0.829 at the pick (floor 0.3).
- The passage range stays untested on held-out real images: eval2019 has no image at or above 66%.

## Dense LIVECell frames (in Cellpose-SAM's training set; over-read check only)

GT is the union of the polygons rasterised with cv2.fillPoly, as for EVICAN. The first run of this script used pycocotools' annToMask, which gave GT 2-4 pp lower (a larger apparent over-read); it was switched to match the EVICAN measure after that output was seen.

| frame | GT (%) | at 0.0 (%) | at pick (%) | confidence at 0.0 | at pick |
|---|---:|---:|---:|---:|---:|
| A172_Phase_C7_2_01d16h00m_2.tif | 70.2 | 70.6 | 77.4 | 0.808 | 0.854 |
| A172_Phase_C7_2_02d00h00m_3.tif | 79.4 | 76.2 | 82.3 | 0.817 | 0.865 |
| A172_Phase_C7_1_03d00h00m_4.tif | 90.1 | 97.2 | 98.8 | 0.906 | 0.980 |
| SKOV3_Phase_E4_2_01d16h00m_4.tif | 69.5 | 68.1 | 74.3 | 0.839 | 0.849 |
| SKOV3_Phase_E4_1_01d16h00m_2.tif | 79.8 | 77.4 | 83.6 | 0.817 | 0.867 |
| SKOV3_Phase_F4_2_02d08h00m_1.tif | 90.1 | 90.7 | 94.0 | 0.862 | 0.937 |

## What changing the default would move (held-out C2C12, context)

1228 held-out frames, 14 sequences, scored from the cache's quarter-resolution maps (Ker et al., *Sci Data* 5:180237, 2018; CC BY 4.0). No C2C12 ground truth exists, so this says what moves, not what is right.

| cutoff | median confluency (%) | max (%) | below the confidence floor | at or above 50% | at or above 80% |
|---|---:|---:|---:|---:|---:|
| +0.0 | 15.4 | 56.9 | 69 | 44 | 0 |
| -3.5 | 25.3 | 86.5 | 0 | 224 | 25 |

Shift per frame: median +9.8 pp, 90th percentile +19.1 pp. 471 of 1228 frames change anomaly bank (0-20 / 20-40 / 40-100%), whose thresholds were set at cutoff 0.0. Confidence is 1 − 4 × the share of pixels within ±1.0 logit of the cutoff, and the floor (0.3) was set at 0.0.
