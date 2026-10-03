# Confluency calibration profiles

**Status: pre-registration.** This section was committed before any image
named below was scored against its ground truth with the method below. The
results section is added afterwards by `scripts/confluency_profiles.py`; the
commit order is the evidence that the method and the rules came first.

## Why

Confluency is read as the share of pixels where Cellpose-SAM's
cell-probability logit is above a cutoff (`culture/seg.py`, cutoff 0.0). Two
earlier results point to the cutoff, not the model, as the weak part:

- On EVICAN (mixed microscopes, 30 cell lines) the shipped cutoff reads low:
  mean signed error −8.33 pp on the 33 held-out images, and a cutoff of −3.5
  picked on the other 65 images lowers the MAE to 3.78 pp
  (`results/confluency_cutoff.md`; not fully blind, disclosed there).
- On six dense LIVECell frames (Incucyte, phase contrast) the shipped cutoff
  reads within −3.2 to +7.1 pp, and −3.5 over-reads all six by 2.9 to 8.7 pp
  (same file).

So the cutoff that fits depends on the imaging setup. A single fixed number
cannot be right for every setup. This study tests a calibration layer instead
of a new model: one **profile** per imaging setup, fitted on labelled images
from that setup, with a per-reading error band, and a passage rule that uses
the band.

The six LIVECell frames above come from LIVECell's test folder. That file
calls them part of Cellpose-SAM's training set; whether Cellpose-SAM's
training excluded LIVECell's test split is not confirmed here, so every
LIVECell number below is an **in-domain check**: same instrument and cell
lines as data the model was trained on, not held-out evidence.

## Setups and splits (fixed now)

| profile | images | ground truth | calibration | test | status |
|---|---|---|---|---|---|
| `evican_mixed` | EVICAN eval2019, 98 images, 30 cell lines, several microscopes (Parekh et al. 2020, CC BY 4.0) | union of the `Cell` polygons, as in `results/confluency_real_summary.md` | the 65 images outside `results/confluency_real.csv` | the 33 in it (their fourth use, after V1, a preview sweep and the cutoff study) | held-out |
| `livecell_incucyte` | LIVECell test split, 1,512 images, 8 cell lines, one instrument (Edlund et al. 2021, CC BY-NC 4.0) | union of the image's polygons (`cv2.fillPoly`) | per cell line, half of its fields (a field = line, well and position, all its time points and crops), chosen with `numpy.random.default_rng(0)` over the sorted field names | the other fields | in-domain check |
| `msc_phase` | Solopov et al. 2025, 320 phase-contrast images (1000 × 1000) of human MSCs (Kaggle `maximsolopov/msu-smooth-1-20`, CC BY-NC-SA 4.0) | the dataset's binary cell mask (one per image, made by three experts) | leave one population out (the file-name prefix: 218-4, 218-5, 218-6) | the left-out population in each fold, pooled | held-out |
| `c2c12_ker2018` | C2C12 frames of the replay fleet (Ker et al. 2018, CC BY 4.0), crops labelled cell/background by the repository owner, if labelled | the painted mask | crops from tuning sequences (`results/replay_fleet_split.csv`) | crops from held-out sequences | held-out; labels by a non-specialist |

What was already seen: the EVICAN calibration rule is the cutoff study's,
so `evican_mixed` will pick −3.5 again, and its results on the 33 are known
(`results/confluency_cutoff.md`). Six LIVECell test images were scored
against ground truth in that study; they stay in, in whichever split their
field falls, and are named in the results.

MSC dataset, checked after download and before scoring (labels only, no
model run): its licence on Kaggle is CC BY-NC-SA 4.0 (the paper is CC BY 4.0);
the files carry three population prefixes, where the paper describes five
donors; the paper says 10× and the dataset page 40×. It is not one of
Cellpose-SAM's 18 training datasets (`docs/DATASETS.md`). Its ground truth
spans 3.6–67.5%: 114 images below 20%, 140 at 20–40%, 62 at 40–60% and 4 at
60–70%, so A2–A4 are not measurable on it. Its images and masks are not
redistributed here. Crops
for the C2C12 labels are chosen without any model output: sequences in
turn, a frame drawn uniformly within each fifth of the sequence's frames, and
a crop position drawn uniformly, all with `default_rng(0)`.

## Method (fixed now)

- **Maps.** Full-resolution `flows[2]` from the call `culture/seg.py` makes
  (`diameter=None`), stored as float16 under `cache/probmaps_full/<setup>/`.
  For C2C12 the full frame is segmented, as the console does, and the map is
  cropped to the labelled area.
- **Reading at cutoff t.** 100 × share of pixels with logit > t.
- **Profile cutoff.** Grid −4.0 to +1.0 in 0.5 steps. Pick the value with
  the lowest MAE on the calibration images; on a tie, the value closest to 0.0.
- **Error band (90%).** Each calibration image gets a residual: the cutoff is
  picked again without that image's split unit (EVICAN: the image; LIVECell:
  its field; MSC: its donor, or the image; C2C12: its sequence), and the
  residual is |reading − ground truth| at that cutoff. The band q is the
  ⌈0.9 (n + 1)⌉-th smallest of the n residuals; with fewer than 9
  calibration images there is no band. One band per profile, in pp.
- **Passage call with the band, target T.** Passage if reading − q ≥ T;
  continue if reading + q < T; otherwise human review (the band straddles the
  target).
- **Shipped rule, for comparison.** Cutoff 0.0; human review when boundary
  ambiguity is above 0.70 (`culture/rules.py`); otherwise passage if
  reading ≥ T.

## Reported on each setup's test images (once)

- At the shipped cutoff, at the setup's own profile, and at each other
  profile's cutoff (the transfer matrix): MAE, median absolute error, mean
  signed error, images off by more than 10 pp.
- Per ground-truth band (0–20, 20–40, 40–60, 60–90, 90–100%): n, MAE, mean
  signed error.
- Linearity: least-squares slope, intercept and R² of reading on ground truth.
- Band coverage: share of test images within ± q, overall and per band.
- Passage call at T = 80% (primary; the console's target) and 70%: review
  rate, and agreement with ground truth (ground truth ≥ T) on the images not
  sent to review; the same for the shipped rule.
- Learning curve, reported only: for k = 2, 5, 10, 20 calibration images
  drawn at random (20 draws, `default_rng(0)`), the median and 90th-percentile
  test MAE of the cutoff picked by the rule above.
- Robustness, reported only: on up to 40 test images per setup
  (`default_rng(0)`), Cellpose-SAM re-run on the image with intensity × 0.7,
  × 1.3 (clipped) and a Gaussian blur of σ = 2 px; median |change in reading|
  at the profile's cutoff.

## Acceptance criteria (fixed now; approved by the owner on 2026-10-02)

For each profile, on its own test images:

| # | criterion | measurable when |
|---|---|---|
| A1 | MAE ≤ 5 pp | always |
| A2 | MAE ≤ 5 pp on images with ground truth 60–90% | ≥ 10 such images |
| A3 | \|mean signed error\| ≤ 3 pp on images with ground truth 60–90% | ≥ 10 such images |
| A4 | at T = 80%, the passage call agrees with ground truth on ≥ 95% of the images not sent to review | ≥ 10 test images with ground truth 60–100% |
| A5 | the 90% band covers ≥ 85% of test images | a band exists |

A profile passes when every measurable criterion passes; criteria that are not
measurable are reported as such, not as passes. LIVECell's are reported as an
in-domain check. The live path changes only for a setup whose profile passes,
and only with the owner's approval; otherwise both results are reported and
the owner decides.

## What would change downstream if a profile ships

A new cutoff for the C2C12 frames moves their readings, so the anomaly bins
and thresholds, the review rate, the stored examples, the replays, the record
hashes, the site data and the console text would all be re-derived on tuning
data and regenerated (`results/confluency_cutoff.md` measured the size: 471 of
1,228 held-out frames change anomaly bin at −3.5).

## Results

Generated 2026-10-03T00:13:11Z by `scripts/confluency_profiles.py score`, with the method and rules above unchanged. EVICAN: Parekh et al., *Bioinformatics* 36(12):3863 (2020), CC BY 4.0. LIVECell: Edlund et al., *Nat Methods* 18:1038 (2021), CC BY-NC 4.0. MSC: Solopov et al., *Int J Mol Sci* 26:2338 (2025), Kaggle copy CC BY-NC-SA 4.0. C2C12: Ker et al., *Sci Data* 5:180237 (2018), CC BY 4.0.

### Profiles

| profile | images (calibration / test) | cutoff (logit) | calibration MAE (pp) | 90% band (± pp) | status |
|---|---|---|---|---|---|
| `evican_mixed` | 65 / 33 | -3.5 | 6.95 | 29.40 | held-out |
| `livecell_incucyte` | 756 / 756 | -0.5 | 2.23 | 5.99 | in-domain check; test fields are other positions, mostly in the same well |
| `msc_phase` | 320 / 320 | -1.5 | 3.43 | 7.11 | held-out, leave one population out |

### Acceptance (each profile on its own test images)

| profile | A1 MAE ≤ 5 | A2 MAE ≤ 5 at 60–90% | A3 \|bias\| ≤ 3 at 60–90% | A4 passage call ≥ 95% at 80% | A5 band covers ≥ 85% |
|---|---|---|---|---|---|
| `evican_mixed` | **pass** (3.78 pp) | **not measurable** (n = 0) | **not measurable** (n = 0) | **not measurable** (0 test images at 60–100%) | **pass** (100.0%; at 60–90%: no images) |
| `livecell_incucyte` | **pass** (2.05 pp) | **pass** (2.78 pp, n = 91) | **pass** (+1.65 pp, n = 91) | **pass** (100.0% of 724, review 4.2%) | **pass** (94.8%; at 60–90%: 88% of 91) |
| `msc_phase` | **pass** (3.43 pp) | **not measurable** (n = 4) | **not measurable** (n = 4) | **not measurable** (4 test images at 60–100%) | **pass** (89.4%; at 60–90%: 75% of 4) |

### `evican_mixed` (held-out)

| | shipped, cutoff 0.0 | profile, cutoff -3.5 |
|---|---|---|
| MAE (pp) | 8.36 | 3.78 |
| median absolute error (pp) | 5.49 | 2.78 |
| mean signed error (pp) | -8.33 | 1.63 |
| off by more than 10 pp | 13 of 33 | 3 of 33 |
| slope, reading on ground truth | 0.73 | 0.93 |
| intercept (pp) | -3.02 | 2.90 |
| R² | 0.75 | 0.86 |

| ground truth | n | MAE at 0.0 | bias at 0.0 | MAE at profile | bias at profile | band coverage |
|---|---|---|---|---|---|---|
| 0-20% | 23 | 6.74 | -6.69 | 3.44 | +1.88 | 100% |
| 20-40% | 7 | 10.34 | -10.34 | 3.09 | +2.16 | 100% |
| 40-60% | 3 | 16.15 | -16.15 | 7.98 | -1.55 | 100% |
| 60-90% | 0 | — | — | — | — | — |
| 90-100% | 0 | — | — | — | — | — |

Band coverage, all test images: 100.0%.

| target | rule | sent to review | agrees with ground truth (of the rest) |
|---|---|---|---|
| 80% | profile band | 6.1% | 100.0% (n = 31) |
| 80% | shipped | 6.1% | 100.0% (n = 31) |
| 70% | profile band | 6.1% | 100.0% (n = 31) |
| 70% | shipped | 6.1% | 100.0% (n = 31) |

Learning curve (reported only): test MAE of the cutoff picked from k random calibration images, 20 draws.

| k | median MAE (pp) | 90th percentile (pp) |
|---|---|---|
| 2 | 4.58 | 4.79 |
| 5 | 4.30 | 4.58 |
| 10 | 4.58 | 4.58 |
| 20 | 4.02 | 4.58 |

Robustness (reported only): median |change in reading| at the profile's cutoff.

| perturbation | median change (pp) | images |
|---|---|---|
| intensity × 0.7 | 0.07 | 33 |
| intensity × 1.3 | 0.05 | 33 |
| Gaussian blur σ = 2 px | 3.98 | 33 |

### `livecell_incucyte` (in-domain check; test fields are other positions, mostly in the same well)

The six frames scored in the cutoff study (`results/confluency_cutoff.md`), and the split their field fell in: `A172_Phase_C7_2_01d16h00m_2.tif` (test), `A172_Phase_C7_2_02d00h00m_3.tif` (test), `A172_Phase_C7_1_03d00h00m_4.tif` (calibration), `SKOV3_Phase_E4_2_01d16h00m_4.tif` (test), `SKOV3_Phase_E4_1_01d16h00m_2.tif` (calibration), `SKOV3_Phase_F4_2_02d08h00m_1.tif` (calibration).

| | shipped, cutoff 0.0 | profile, cutoff -0.5 |
|---|---|---|
| MAE (pp) | 2.14 | 2.05 |
| median absolute error (pp) | 1.49 | 1.23 |
| mean signed error (pp) | -0.44 | 0.91 |
| off by more than 10 pp | 7 of 756 | 15 of 756 |
| slope, reading on ground truth | 1.00 | 1.01 |
| intercept (pp) | -0.63 | 0.40 |
| R² | 0.98 | 0.98 |

| ground truth | n | MAE at 0.0 | bias at 0.0 | MAE at profile | bias at profile | band coverage |
|---|---|---|---|---|---|---|
| 0-20% | 201 | 1.19 | -0.29 | 1.12 | +0.32 | 100% |
| 20-40% | 261 | 2.14 | -0.32 | 2.22 | +1.15 | 93% |
| 40-60% | 147 | 3.22 | -1.52 | 2.59 | +0.55 | 93% |
| 60-90% | 91 | 2.72 | -0.40 | 2.78 | +1.65 | 88% |
| 90-100% | 56 | 1.76 | +1.27 | 1.93 | +1.70 | 100% |

Band coverage, all test images: 94.8%.

| target | rule | sent to review | agrees with ground truth (of the rest) |
|---|---|---|---|
| 80% | profile band | 4.2% | 100.0% (n = 724) |
| 80% | shipped | 5.8% | 99.7% (n = 712) |
| 70% | profile band | 5.4% | 99.4% (n = 715) |
| 70% | shipped | 5.8% | 99.6% (n = 712) |

Learning curve (reported only): test MAE of the cutoff picked from k random calibration images, 20 draws.

| k | median MAE (pp) | 90th percentile (pp) |
|---|---|---|
| 2 | 2.14 | 2.81 |
| 5 | 2.14 | 2.76 |
| 10 | 2.14 | 2.59 |
| 20 | 2.09 | 2.18 |

Robustness (reported only): median |change in reading| at the profile's cutoff.

| perturbation | median change (pp) | images |
|---|---|---|
| intensity × 0.7 | 0.04 | 40 |
| intensity × 1.3 | 0.02 | 40 |
| Gaussian blur σ = 2 px | 3.33 | 40 |

### `msc_phase` (held-out, leave one population out)

Leave one population out: fold 1 cutoff -1.5, band ± 7.63 pp (208 calibration images); fold 2 cutoff -1.5, band ± 6.42 pp (208 calibration images); fold 3 cutoff -1.5, band ± 7.70 pp (224 calibration images).

| | shipped, cutoff 0.0 | profile, cutoff -1.5 |
|---|---|---|
| MAE (pp) | 8.19 | 3.43 |
| median absolute error (pp) | 6.75 | 2.60 |
| mean signed error (pp) | -7.92 | 0.22 |
| off by more than 10 pp | 94 of 320 | 13 of 320 |
| slope, reading on ground truth | 0.65 | 0.92 |
| intercept (pp) | 1.78 | 2.42 |
| R² | 0.80 | 0.89 |

| ground truth | n | MAE at 0.0 | bias at 0.0 | MAE at profile | bias at profile | band coverage |
|---|---|---|---|---|---|---|
| 0-20% | 114 | 3.86 | -3.14 | 3.13 | +1.22 | 88% |
| 20-40% | 140 | 8.03 | -8.01 | 3.26 | +0.24 | 92% |
| 40-60% | 62 | 15.37 | -15.37 | 4.19 | -1.30 | 87% |
| 60-90% | 4 | 25.66 | -25.66 | 5.75 | -5.75 | 75% |
| 90-100% | 0 | — | — | — | — | — |

Band coverage, all test images: 89.4%.

| target | rule | sent to review | agrees with ground truth (of the rest) |
|---|---|---|---|
| 80% | profile band | 0.0% | 100.0% (n = 320) |
| 80% | shipped | 16.9% | 100.0% (n = 266) |
| 70% | profile band | 0.9% | 100.0% (n = 317) |
| 70% | shipped | 16.9% | 100.0% (n = 266) |

Learning curve (reported only): test MAE of the cutoff picked from k random calibration images, 20 draws.

| k | median MAE (pp) | 90th percentile (pp) |
|---|---|---|
| 2 | 4.12 | 7.92 |
| 5 | 3.96 | 4.59 |
| 10 | 3.81 | 4.28 |
| 20 | 3.66 | 4.19 |

Robustness (reported only): median |change in reading| at the profile's cutoff.

| perturbation | median change (pp) | images |
|---|---|---|
| intensity × 0.7 | 0.23 | 40 |
| intensity × 1.3 | 0.11 | 40 |
| Gaussian blur σ = 2 px | 2.13 | 40 |

### Transfer: each setup's test images under each profile's cutoff

Own profile: the fold cutoffs, as above. Median absolute error and R² per cell are in `results/confluency_profiles.json`.

MAE (pp):

| test images ↓ / profile → | `evican_mixed` (-3.5) | `livecell_incucyte` (-0.5) | `msc_phase` (-1.5) |
|---|---|---|---|
| evican_mixed | 3.78 | 6.88 | 4.70 |
| livecell_incucyte | 6.70 | 2.05 | 3.28 |
| msc_phase | 9.84 | 5.80 | 3.43 |

Mean signed error (pp); images off by more than 10 pp:

| test images ↓ / profile → | `evican_mixed` (-3.5) | `livecell_incucyte` (-0.5) | `msc_phase` (-1.5) |
|---|---|---|---|
| evican_mixed | +1.63; 3 of 33 | -6.79; 9 of 33 | -3.92; 5 of 33 |
| livecell_incucyte | +6.70; 133 of 756 | +0.91; 15 of 756 | +3.12; 41 of 756 |
| msc_phase | +9.79; 166 of 320 | -5.18; 54 of 320 | +0.22; 13 of 320 |

