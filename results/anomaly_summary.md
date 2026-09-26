# A4: density-conditioned anomaly scoring (minimal)

Generated 2026-09-26T17:35:13Z by `scripts/eval_anomaly.py`. C2C12 images: Ker et al., *Sci Data* 5:180237 (2018), CC BY 4.0; fault frames are simulated from them.

**Method.** DINOv2-small patch embeddings of each frame's 256 px centre tile (`qctile`, about 4.5% of a 1392×1040 frame). Patch distance = cosine distance to the nearest normal patch; image score = mean of the top 1% of patch distances (AnomalyDINO). Banks = greedy k-center coresets (10% of patches; PatchCore) of the tuning sequences' normal frames, one per confluency bin (bin = full-frame Cellpose-SAM confluency) and one global. C2C12 only: no synthetic tiles in the banks. Every frame is scored against banks rebuilt without its own base sequence.

Bins: 0-20, 20-40, 40-100% (configured [0.0, 20.0, 40.0, 60.0, 80.0, 100.0]; bins with < 3 tuning sequences merge into a neighbour).

## Per-bin calibration (tuning normal frames)

| bin | tuning sequences | tuning frames | bank patches | mean | SD | threshold (5% FPR) | held-out normal frames | held-out flag rate |
|---|---|---|---|---|---|---|---|---|
| 0-20% | 10 | 569 | 14567 | 0.2333 | 0.0422 | 0.3076 | 750 | 14.7% |
| 20-40% | 10 | 226 | 5786 | 0.2525 | 0.0383 | 0.3290 | 318 | 3.8% |
| 40-100% | 6 | 65 | 1664 | 0.2856 | 0.0637 | 0.4274 | 160 | 0.6% |
| global | 10 | 860 | 22016 | 0.2303 | 0.0402 | 0.3025 | 1228 | 11.0% |

Held-out normal flag rate overall: binned 10.0%, global 11.0% (target 5%; 14 sequences). Per sequence (binned): 090303_exp1_F0003 4%, 090303_exp1_F0014 1%, 090318_exp1_F0001 9%, 090318_exp1_F0003 17%, 090318_exp1_F0005 2%, 090318_exp1_F0007 13%, 090318_exp1_F0011 2%, 090318_exp1_F0013 4%, 090318_exp1_F0016 69%, 090325_exp1_F0003 3%, 090325_exp1_F0007 5%, 090325_exp1_F0011 2%, 090325_exp1_F0013 3%, 090325_exp1_F0018 3%.

## V4: does density conditioning remove the growth confound?

Spearman ρ between anomaly score and full-frame confluency on held-out normal frames. Pass (spec): binned |ρ| ≤ 0.3 and clearly below global. Frames within a sequence follow time, so ρ per sequence is shown too.

| score | ρ over all frames | median ρ per sequence (IQR) |
|---|---|---|
| binned z (primary; what SPC trends) | -0.16 | -0.23 (-0.47 to +0.07) |
| global raw score | -0.09 | -0.18 (-0.43 to +0.19) |
| binned raw score (secondary) | +0.14 | — |

n = 1228 frames, 14 sequences (14 with a per-sequence ρ). **V4: fail** on these numbers (|ρ| binned 0.16 vs global 0.09). Plot: `results/anomaly_v4.png`.

**Shape diagnostic (not the V4 metric).** Spearman ρ only sees monotone trends. Mean z of held-out normal frames per 10-pp confluency band (global z uses the global bank's tuning mean/SD):

| confluency | frames | sequences | mean z, global | mean z, binned |
|---|---|---|---|---|
| 0–10% | 409 | 14 | +0.58 | +0.55 |
| 10–20% | 341 | 14 | +0.24 | +0.27 |
| 20–30% | 194 | 13 | -0.03 | +0.03 |
| 30–40% | 124 | 12 | -0.19 | -0.28 |
| 40–50% | 116 | 8 | +0.22 | -0.04 |
| ≥ 50% | 44 | 5 | +1.19 | +0.37 |

## V5(b): held-out contamination frames vs held-out normal frames

Severity = sprites per 256×256 px tile area (the ramp runs 20 → 400 after onset). Pass (spec): AUROC ≥ 0.85 at severity ≥ 150.

| severity | frames | fault sequences | AUROC (binned z) | AUROC (global score) | flagged at bin threshold |
|---|---|---|---|---|---|
| <150 | 8 | 2 | 0.99 | 0.99 | 100% |
| ≥150 | 41 | 2 | 1.00 | 1.00 | 100% |

**V5(b): pass** (n = 2 held-out contamination sequences; frames within a sequence are not independent). Contaminated frames are binned by their own Cellpose-SAM confluency, as the live system would: the sprites shift it by a median +59.4 pp from the base frame (IQR +50.0 to +69.7), and 88% of these frames land in a different bin than their base frame. Plot: `results/anomaly_v5.png`.

Lamp dimming (informational; V7 wants it handled as instrument drift, not per flask):

| intensity factor | frames | AUROC (binned z) | flagged |
|---|---|---|---|
| (0, 0.7] | 187 | 0.47 | 4% |
| (0.7, 0.8] | 56 | 0.49 | 7% |
| (0.8, 0.9] | 42 | 0.45 | 5% |
| (0.9, 1] | 42 | 0.41 | 12% |

## V5(a): synthetic test tiles (CLS-kNN — a different scorer)

Synthetic tiles have only CLS embeddings in the Mac cache, so this uses the image-level CLS vector (cosine distance to the nearest train-normal CLS), not the patch scorer above. It says how separable the synthetic classes are at image level; it does not validate the C2C12 path. Bank: 664 train normal tiles; threshold at 5% FPR on val normals (test normal FPR at it: 10.7%, n = 168). Pass (spec): AUROC ≥ 0.85 per class.

| class | severity | test tiles | AUROC | TPR at val threshold |
|---|---|---|---|---|
| all non-normal | all | 485 | 0.87 | 64% |
| contamination_suspected | early | 56 | 1.00 | 100% |
| contamination_suspected | late | 56 | 1.00 | 100% |
| contamination_suspected | mid | 56 | 1.00 | 100% |
| detachment | synthetic | 149 | 0.82 | 42% |
| contamination_suspected | all | 168 | 1.00 | 100% |
| detachment | all | 149 | 0.82 | 42% |
| image_quality | all | 168 | 0.78 | 47% |

**V5(a): fail** for the CLS-kNN scorer (per class: contamination_suspected 1.00, detachment 0.82, image_quality 0.78).

## Notes

- The confluency bin comes from the full frame, but the score from the centre tile only; a tile's local density can differ from its bin (STATUS item 11).
- Tuning frames were scored leave-one-sequence-out, with each fold's coresets rebuilt, so the calibration and the held-out scores use banks built the same way.
- Scores for every frame, tuning and held-out, faults included, are in `cache/anomaly/scores.parquet` for A6/A7 (regenerate with this script).
