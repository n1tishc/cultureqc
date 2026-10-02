# v0.2's QC classifier vs v0.3's anomaly check, on the same real frames

Generated 2026-10-02T14:57:16Z by `scripts/compare_v02_v03_flags.py` from the compute cache; no model run, nothing tuned. C2C12 images: Ker et al., *Sci Data* 5:180237 (2018), CC BY 4.0; fault frames are simulated from them. AutoQC-Bench: BioStudies S-BIAD2133 (doi:10.6019/S-BIAD2133), MIT; human and mouse neutrophil granulocytes, with real anomalies.

**v0.2** = the QC classifier `qc_effnetb0_v1` as v0.2 used it: plain softmax over its cached logits and v0.2's rule 1 (`main:culture/rules.py`), a call other than normal at confidence ≥ 0.7 sends the image to `human_review`. **v0.3** = the anomaly check's flag and binned z-score (`cache/anomaly/scores.parquet`, the scores behind `results/anomaly_summary.md`). Since `rules_v0.3` the flag acts only at passage: an image at or above the target that it flags goes to review instead of passage.

## 1. Held-out C2C12 frames

| frames | n | sequences | v0.2: not called normal | v0.2: sent to review by rule 1 | v0.2: called contamination | v0.3: anomaly flag |
|---|---|---|---|---|---|---|
| healthy | 1228 | 14 | 95.0% | 77.0% | 15.7% | 10.0% (123 of 1228) |
| simulated contamination, bacteria 16.5× too large, after onset | 49 | 2 | 93.9% | 87.8% | 91.8% | 100.0% (49 of 49) |
| simulated lamp dimming, after onset | 327 | 14 | 90.2% | 63.0% | 29.4% | 5.8% (19 of 327) |

AUROC of the simulated faults against the held-out healthy frames (0.5 = chance):

| frames | v0.2: 1 − p(normal), any problem | v0.2: p(contamination) | v0.3: anomaly z |
|---|---|---|---|
| simulated contamination, bacteria 16.5× too large, after onset | 0.52 | 0.97 | 1.00 |
| simulated lamp dimming, after onset | 0.40 | 0.67 | 0.46 |

Simulated lamp dimming is pooled over every intensity after onset; `results/anomaly_summary.md` gives v0.3's AUROC per intensity band (0.41 to 0.49).

v0.2's rule 1 alone sends 77.0% of held-out healthy frames to review; its rule 2 (confluency confidence below 0.3) sends more, so v0.2's total is at least that. v0.3's total review rate on the same frames, and the one frame the anomaly flag adds to it, are in `results/review_rate.md`.

## 2. Per held-out sequence, healthy frames

| experiment | sequence | frames | v0.2: not called normal | v0.3: anomaly flag | gap (pp) |
|---|---|---|---|---|---|
| 090303 | c2c12_090303_exp1_F0003_Data | 85 | 95.3% | 3.5% | 91.8 |
| 090303 | c2c12_090303_exp1_F0014_Data | 85 | 89.4% | 1.2% | 88.2 |
| 090318 | c2c12_090318_exp1_F0001_Data | 89 | 97.8% | 9.0% | 88.8 |
| 090318 | c2c12_090318_exp1_F0003_Data | 89 | 96.6% | 16.9% | 79.8 |
| 090318 | c2c12_090318_exp1_F0005_Data | 89 | 89.9% | 2.2% | 87.6 |
| 090318 | c2c12_090318_exp1_F0007_Data | 89 | 91.0% | 13.5% | 77.5 |
| 090318 | c2c12_090318_exp1_F0011_Data | 89 | 88.8% | 2.2% | 86.5 |
| 090318 | c2c12_090318_exp1_F0013_Data | 89 | 96.6% | 4.5% | 92.1 |
| 090318 | c2c12_090318_exp1_F0016_Data | 89 | 100.0% | 68.5% | 31.5 |
| 090325 | c2c12_090325_exp1_F0003_Data | 87 | 97.7% | 3.4% | 94.3 |
| 090325 | c2c12_090325_exp1_F0007_Data | 87 | 96.6% | 4.6% | 92.0 |
| 090325 | c2c12_090325_exp1_F0011_Data | 87 | 93.1% | 2.3% | 90.8 |
| 090325 | c2c12_090325_exp1_F0013_Data | 87 | 97.7% | 3.4% | 94.3 |
| 090325 | c2c12_090325_exp1_F0018_Data | 87 | 100.0% | 3.4% | 96.6 |

The anomaly flag rate is lower in 14 of 14 sequences; the smallest gap is c2c12_090318_exp1_F0016_Data (100.0% vs 68.5%). The 14 sequences are fields of view from 3 experiments, not 14 independent cultures. Per-sequence rows: `results/v02_vs_v03_flags_per_sequence.csv`.

## 3. The classifier on all C2C12 sequences

6.5% of 2088 frames from 24 sequences are called normal (the classifier never saw C2C12). The anomaly check is not scored on the tuning sequences: its banks and thresholds come from them.

## 4. AutoQC-Bench test set: real anomalies from another lab (classifier only)

| group | n | called normal | called contamination_suspected | called detachment | called image_quality | v0.2: sent to review by rule 1 |
|---|---|---|---|---|---|---|
| good | 100 | 52 | 0 | 2 | 46 | 40.0% |
| contamination | 10 | 5 | 0 | 0 | 5 | 40.0% |
| air_bubble | 10 | 4 | 0 | 0 | 6 | 40.0% |
| artifacts | 8 | 2 | 0 | 0 | 6 | 75.0% |
| illumination | 10 | 4 | 0 | 0 | 6 | 60.0% |
| z-shift | 10 | 0 | 0 | 0 | 10 | 100.0% |

AUROC against the good images: any anomaly, 1 − p(normal), 0.70; real contamination, p(contamination), 0.59.

**Not run: v0.3's anomaly check.** Its banks are C2C12 patches, so scoring these images against them would measure the change of microscope and cell type, not the method. A fair test builds the bank from AutoQC-Bench's own normal training split; not done here.

## Limits

- On C2C12 the comparison is on v0.3's home ground: the anomaly banks and thresholds come from tuning sequences of the same three experiments, while the classifier never saw C2C12. It shows that calibrating to the setup's real healthy images beats training on synthetic faults; it does not show that the anomaly check transfers to another setup.
- Frames within a sequence are not independent. Held-out contamination is 2 sequences, with bacteria 16.5× too large; at their real size the anomaly flag is at chance (`results/contamination_scale.md`), and the classifier was not scored at real size.
- Both models read only the 256 px centre tile: about 4.5% of a C2C12 frame and 6.4% of an AutoQC-Bench frame (1280 × 800), so an anomaly outside it is invisible to both. AutoQC-Bench's neutrophils are not a cell type in LIVECell, which the classifier's training tiles came from, and its pixel size is not matched to them.
- This compares the problem detectors only. Confluency is measured separately (`results/confluency_real_summary.md`, n = 33).
