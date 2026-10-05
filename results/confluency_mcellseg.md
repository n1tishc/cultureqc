# Confluency in the passage range on a dense, held-out dataset (mCellSeg)

**Status: pre-registration.** This section was committed before any probability map of the images below
was computed. The results section is added afterwards by `scripts/confluency_mcellseg.py score`; the commit
order is the evidence that the method and the rules came first.

## Why

No held-out test so far could measure the passage range on whole images. `msc_phase` has 4 test images at
60–90% and `evican_mixed` has none (`results/confluency_profiles.md`). Dense regions of the MSC images read
7.8 pp low on average (`results/confluency_dense_tiles.md`), and that test could not tell density apart
from how the regions were selected. A search of public data on 2026-10-04 found no other dense set with
full masks.

mCellSeg (Alam, Jackson, Lord & Meijering, *Computer Methods and Programs in Biomedicine* 2026; Zenodo
10.5281/zenodo.20174259) was published on 2026-05-15. It holds 200 manually annotated transmitted-light
images of HEK-293T and HUVEC cultures, 46 of them at 60–90% by their masks. It postdates Cellpose-SAM (April
2025), and it is not among Cellpose-SAM's 18 training sets (`docs/DATASETS.md`).

Three questions:

1. Does the shipped method, the zero-shot model with a calibration profile per setup, meet the
   passage-range criteria on setups it has never seen?
2. Does fine-tuning the model on the same calibration images read dense cultures better than calibration
   alone?
3. Secondary: does rescaling each setup's images to the model's nominal cell size help?

## Data

- **Source.** `mCellSeg.zip` from the Zenodo record, licence CC BY 4.0. The MD5 matched the record
  (`ed06d6e4c10e93b81703984cef852246`). Stored under `data/sources/mcellseg/` (gitignored); images and
  masks are not redistributed, and only summary numbers appear in `results/`.
- **Images.** All 200 annotated images (`labeled/`). Per the dataset README they were acquired by DIC and
  fluorescence microscopy on a Zeiss LSM 880 (20×/0.8 or 40×/1.3) or a Zeiss Cell Discoverer 7 (20×/0.95).
  The 200 annotated images were checked on contact sheets before this was written: all are
  transmitted-light (DIC or bright-field), saved as grey RGB.
- **Ground truth.** Instance masks (TIFF, 0 = background). Expert confluency = 100 × share of pixels
  with a label above 0. The README says annotators traced each cell by hand, using the nuclear and
  cytoplasmic fluorescence channels to help, and a senior cell biologist reviewed every mask. Overlays of
  four dense images (one per large setup) were checked before this was written: the masks are exhaustive.
- **Not used.** The 100 unlabelled images.

## What was looked at before this was written

- Contact sheets of all 200 images, to check modality, and mask overlays on 4 dense images.
- Expert masks only: the setups, units, split and counts below (`count`, which writes
  `results/confluency_mcellseg_split.json`), and the cells' diameters in the calibration masks.
- No probability map of any image in this dataset, or in the supplementary set below, has been computed.
- The fine-tuning recipe has not been run on these images or any other. Development runs on the MSC
  images (`scripts/confluency_finetune.py`, already-scored images, reported as a development result in
  `results/confluency_finetune_dev.md`) run in the same Colab session as this test. The recipe below is
  the one Cellpose documents, and nothing in this test changes because of them.

## Setups and split (masks and file names only)

**Setups.** The TIFFs carry no instrument tags (they were re-saved by `tifffile`), so a setup is an image
format plus a file family (`setup_of`). That gives 8 setups.

**Units.** Images that may share a field, well or z-stack share a unit, and a unit never straddles the
split (`unit_of`).
- In `cd7_huvec_dic` a unit is condition + well. There is one image per well, and the two frames of well
  09 share a unit.
- Elsewhere a unit is the condition, with positions, z-planes, frames, channels, magnifications and time
  points stripped. Every image of a condition therefore falls in one unit, which is conservative.

**Split.** Within each setup, units are ranked by mean expert confluency (then by name) and alternate
calibration, test, calibration, and so on, so that both halves span the density range.

**Calibrated setups.** A setup is calibrated when it has at least 9 calibration images, the minimum for a
band (`confluency_profiles.band`). The other four setups have too few, and they are read the way the
product reads an uncalibrated setup (below).

| setup | calibration images (units) | test images (units) | test at 60–90% | test at ≥ 80% | calibrated |
|---|---|---|---|---|---|
| `cd7_huvec_dic` (HUVEC, Cell Discoverer 7, DIC) | 18 (18) | 18 (17) | 4 | 2 | yes |
| `lsm_hek_1024` (HEK-293T, LSM 880, 1024 px) | 14 (7) | 18 (6) | 9 | 2 | yes |
| `oir_1024` (1024 px, `.oir` export) | 14 (6) | 17 (6) | 8 | 0 | yes |
| `lsm_2796` (HEK-293T and HUVEC, 2796 px) | 33 (10) | 37 (10) | 1 | 0 | yes |
| `jp_bf_2048` | 3 (2) | 3 (2) | 3 | 1 | no |
| `bf_20x_3440` | 5 (3) | 3 (3) | 1 | 0 | no |
| `polymer_lowmag` | 4 (1) | 9 (1) | 3 | 1 | no |
| `huvec_bf_2752` | 4 (1) | 0 | 0 | 0 | no |

**Primary test set:** the 90 test images of the four calibrated setups. 22 are at 60–90%, 22 at 60–100%,
and 4 at or above 80%.

## Arms

Every arm reads confluency the way the product does: 100 × the share of pixels whose Cellpose-SAM cell
probability (`flows[2]`, the same call as `culture/seg.py`, with instance masks not computed because the
reading does not use them) is above the cutoff. Each arm reads the same
test images.

- **Z: zero-shot, shipped cutoff 0.0, no band.** The product with no profile for these setups.
- **C: zero-shot plus a calibration profile per setup (primary; the shipped method).** For each calibrated
  setup, the cutoff on the grid −4.0 … +1.0 (step 0.5) with the lowest MAE on that setup's calibration
  images, ties going to the cutoff nearest 0.0 (`confluency_profiles.pick`). The band is the 90% quantile of
  leave-one-unit-out errors on the calibration images (`confluency_profiles.band`).
- **F: fine-tuned, then calibrated (primary comparison).**
  - Cellpose-SAM (`cpsam_v2`) is fine-tuned on the 79 calibration images of the four calibrated setups,
    pooled into one model for this lab. It trains on their instance masks with the recipe Cellpose
    documents for fine-tuning Cellpose-SAM (learning rate 1e-5, weight decay 0.1, 100 epochs, batch size
    1), not tuned here.
  - The cutoff and band need readings the model has not trained on, so they come from cross-fitting.
    Calibration units of each setup, ranked by mean expert confluency, alternate between folds A and B.
    One model is fine-tuned on B and reads A, and another is fine-tuned on A and reads B.
  - Each setup's cutoff and band are then fitted on those out-of-fold readings exactly as in C.
  - A third model, fine-tuned on all 79, reads the test images.
  - The weights' SHA-256 values are recorded in `cache/finetune/<run>/manifest.json`.
- **R: zero-shot, rescaled, then calibrated (secondary).** Each image is read with `diameter` set to its
  setup's median equivalent cell diameter in the calibration masks: 119.6 px (`cd7_huvec_dic`), 73.0
  (`lsm_hek_1024`), 119.2 (`oir_1024`) and 215.1 (`lsm_2796`). Cellpose resizes the image so that cells are
  about 30 px and returns the map at full size. Cutoff and band are fitted as in C.

**Compute.**
- The maps and the fine-tuning run on a Colab GPU (`nb/06_confluency_evidence.ipynb`), from a bundle of
  this commit.
- On the GPU side each map is reduced to its reading at every grid cutoff
  (`results/confluency_mcellseg_curves.json`, with the fine-tuned runs' manifests). `score` reads only
  that file, on the Mac, once.

Calls use rules_v0.5 at T = 80%:
- With a band, passage if reading − band ≥ 80, continue if reading + band < 80, and review otherwise.
- With no band (Z), review if reading ≥ 80, and continue otherwise.

## Criteria (pooled over the 90 test images; the limits of A1–A5)

| # | measure | passes when | measurable when |
|---|---|---|---|
| B1 | MAE, all test images | ≤ 5 pp | always |
| B2 | MAE, test images at 60–90% | ≤ 5 pp | ≥ 10 such images (22) |
| B3 | mean signed error, test images at 60–90% | \|bias\| ≤ 3 pp | as B2 |
| B4 | at T = 80%, calls that agree with the experts among test images at 60–100% not sent to review | ≥ 95% | ≥ 10 such images (22) |
| B5 | test images whose reading is within the band | ≥ 85% | the arm has a band |

- Verdicts are on the point estimates.
- Each estimate gets a 95% interval from a bootstrap that resamples units with replacement (10,000
  resamples, `numpy.random.default_rng(0)`).
- B4 is measurable, but only 4 of its 22 images are at or above 80%. It therefore mostly tests continue
  calls. The results also report how many ready flasks (≥ 80%) each arm called continue.

**Pre-registered comparison.**
- Fine-tuning reads the passage range better than calibration alone if the 95% interval of
  MAE(C) − MAE(F) on the 60–90% test images lies entirely above zero.
- The same rule applies to R against C, as a secondary comparison.
- The difference on all test images is reported beside it.

## Reported, not judged

- Every measure per setup, for each arm.
- The uncalibrated setups' test images (15), read as Z.
- **Supplementary, an incubator imager: MSC on a CytoSmart Lux** (Joas et al. 2025, Zenodo
  10.5281/zenodo.15421541, CC BY 4.0, the in-house `Aufnahme-*` images in its `livecell/` folder; none is a
  LIVECell image).
  - 19 images of 1280 × 960 px, with ground truth from the authors' confluence-oriented "lazy" masks (cell
    clusters drawn as one object; `LC_GENERALPREP_LAZY/Instance_prep`).
  - Split by alternation over expert confluency: 10 calibration, 9 test. One zero-shot profile is fitted on
    the calibration images as in C.
  - Reported: test MAE, bias and band coverage.
  - Only 2 test images are at 60–90%, so nothing in the passage range is measurable there.
  - On the dense images, the dataset's own instance masks give 29–31 pp less confluency than its lazy masks
    (53.3% against 82.2%, and 58.0% against 88.5%). In dense cultures, how the masks are drawn moves the
    ground truth by that much.

## What it cannot show

- These are 20× and 40× images on a confocal microscope and a Cell Discoverer 7, with cells 73–215 px
  across. They are dense and held-out, but they come from neither an incubator imager nor a 4–10×
  objective.
- One lab, two cell lines. The HEK-293T cultures were fixed before imaging, according to the README.
- Setups are inferred from formats, because the files carry no instrument tags.
- Only 4 test images are at or above 80%, and the 22 dense test images come from 17 units, so the
  intervals will be wide.
- The masks were drawn with fluorescence to help; the model sees the transmitted-light image only.

## What changes downstream

- Nothing in the product, whichever way this goes. No profile, cutoff, band, rule or model changes because
  of this result.
- The fine-tuned weights are a measurement, not a release. They inherit Cellpose-SAM's non-commercial
  status (`README.md`, "Licences and commercial use").
- If F passes where C fails, adding fine-tuning to the calibration procedure becomes a proposal for the
  repository owner to decide on: a fine-tuned model per setup, with its weights' hash in the profile and the
  change record.
