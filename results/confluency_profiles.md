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
| `msc_phase` | Solopov et al. 2025, 320 phase-contrast images of human MSCs from 5 donors, 10× (CC BY 4.0), if downloaded | the dataset's binary cell mask; if each expert's mask is provided, the pixel-wise majority, with the spread between experts' confluency reported as the label-noise floor | leave one donor out, if donors can be identified from the files; otherwise half of the images, `default_rng(0)` | the left-out donor in each fold, pooled; otherwise the other half | held-out |
| `c2c12_ker2018` | C2C12 frames of the replay fleet (Ker et al. 2018, CC BY 4.0), crops labelled cell/background by the repository owner, if labelled | the painted mask | crops from tuning sequences (`results/replay_fleet_split.csv`) | crops from held-out sequences | held-out; labels by a non-specialist |

What was already seen: the EVICAN calibration rule is the cutoff study's,
so `evican_mixed` will pick −3.5 again, and its results on the 33 are known
(`results/confluency_cutoff.md`). Six LIVECell test images were scored
against ground truth in that study; they stay in, in whichever split their
field falls, and are named in the results.

The MSC dataset is checked against Cellpose-SAM's 18 training datasets
(`docs/DATASETS.md`) before use, and its confluency range is reported. Crops
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
