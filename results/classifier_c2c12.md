# QC classifier on real C2C12 frames (context, not a spec criterion)

Generated 2026-09-26T19:33:48Z by `scripts/eval_classifier_c2c12.py`. C2C12 images: Ker et al., *Sci Data* 5:180237 (2018), CC BY 4.0; fault frames are simulated. The classifier (`qc_effnetb0_v1`) was trained on synthetic tiles only. Calibrated probabilities (temperature from `configs/calibration.yaml`) on the 256 px centre tile; call = arg-max. Held-out sequences only.

| frames | n | called normal | called contamination_suspected | called detachment | called image_quality | mean p(normal) | mean p(contamination_suspected) | mean p(detachment) | mean p(image_quality) |
|---|---|---|---|---|---|---|---|---|---|
| normal (held-out base frames) | 1228 | 5.0% | 15.7% | 12.2% | 67.1% | 0.07 | 0.18 | 0.13 | 0.62 |
| contamination_onset (held-out, after onset) | 49 | 6.1% | 91.8% | 2.0% | 0.0% | 0.09 | 0.88 | 0.01 | 0.02 |
| lamp_dimming (held-out, after onset) | 327 | 9.8% | 29.4% | 21.1% | 39.8% | 0.10 | 0.29 | 0.21 | 0.39 |

Frames within a sequence are not independent (14 held-out base sequences; 2 contamination, 2 growth-stall and 14 dimming fault sequences). Growth-stall frames are re-timed copies of normal frames, so the classifier cannot see a stall by design.
