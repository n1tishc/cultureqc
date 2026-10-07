# More training images: does fine-tuning on 169 images read new setups better than on 79?

**Status: pre-registration.** This file, `scripts/confluency_more_images.py` and the training sets in
`results/confluency_more_images_plan.json` were committed before any model below was trained and before any
fine-tuned model read any of the test images. The results section is added afterwards by
`scripts/confluency_more_images.py score`, run once.

## Why

The approved fine-tuned model (`mcellseg_ftF_r2`, `configs/approved_changes.jsonl`) was trained on 79 images: the
calibration half of the sealed mCellSeg test's four setups, 5,723 outlined cells. Only 14 of them are at 60% or
above, the range where it fell short (`results/confluency_mcellseg.md`, `results/confluency_mcellseg_swap.md`).
All 169 labelled images of those setups hold 12,185 outlined cells, 36 of them at 60% or above.

Every one of the 169 has now been trained on or scored, so a model trained on all of them cannot be measured on
any of them. The questions are asked of the only mCellSeg images no fine-tuned model has read:

1. **(Primary)** Does a model fine-tuned on all 169 images read the 31 images of four other setups better than the
   approved model, trained on 79?
2. **(Reported, whatever it shows)** How does the approved model read setups it never trained on, against the
   shipped model? This is the question a lab adding a microscope would ask.
3. **(Reported, not judged)** How does the error change with the number of training images (about 40, 120, 169)?

## What was looked at before this was written

- All results of the sealed test and its swapped replication, per image.
- The 31 test images' expert confluency, from the masks: 11 at 60–90%, 2 at or above 80%, from 13 units; one
  unit (`polymer|test`) holds 9 of the 31 images.
- The shipped model's readings of the 31 at every cutoff are committed (`results/confluency_mcellseg_curves.json`,
  the zero-shot map, computed in `007422d`), and have been seen: a dry run of `score` on made-up fine-tuned
  readings used them. At cutoff 0.0 they read low on nearly every image (MAE 33.78 pp, 2 of 31 within 5 pp).
  They are an arm reported whatever it shows; nothing below was chosen after seeing them.
- No fine-tuned model has read any of the 31: they appear in none of the fine-tuned maps, the swapped
  replication's maps, the before/after picture's readings or the product-path records.

## Test images

The 31 mCellSeg images outside the four calibrated setups, both halves of the committed split
(`results/confluency_mcellseg_split.json`):

| Setup | Images | Grouped by (the TIFFs carry no instrument tags; `confluency_mcellseg.setup_of`) |
|---|---|---|
| `polymer_lowmag` | 13 | file names `CellsOnly_Polymer*`, `Polymer_Test*` |
| `bf_20x_3440` | 8 | 3440 × 3440 images |
| `jp_bf_2048` | 6 | 2048 × 2048 images |
| `huvec_bf_2752` | 4 | file names `BF-HUVEC*` |

None of these setups is among the four that any model here trained on. They are the same lab as the training
images, so this measures transfer to other microscope setups and formats of one lab, not to another lab.

## Models

All fine-tuned from Cellpose-SAM (`cpsam_v2`) with the function, labels and recipe that trained the approved model
(`confluency_finetune.train_run`, instance masks, learning rate 1e-5, weight decay 0.1, 100 epochs, batch size 1),
so the training images are the only difference.

| Run | Training images | How they are chosen |
|---|---|---|
| `mcellseg_ftF_r2` (approved) | 79 | the sealed test's calibration half; already trained, not retrained |
| `mcellseg_more_n169` (primary) | 169 | all labelled images of the four setups |
| `mcellseg_more_n40_s0`, `_s1` | 41, 42 | two seeded draws |
| `mcellseg_more_n120_s0` | 120 | seed 0; contains `n40_s0` |

- Draws are of whole units, in a seeded random order interleaved by setup, so every draw spans the four setups in
  proportion to their image counts, and sizes from one seed are nested.
- The approved model's 79 are not a random draw (one half of a density-balanced split). It is reported as its own
  point, not as part of the curve.
- **No separate "more varied" arm.** In these 169 images, setup and density go together (`lsm_2796` has 70 images,
  2 of them at 60% or above; `lsm_hek_1024` has 32, 15 of them). A comparison of equal size across fewer setups
  could not separate more setups from more dense images, and 31 test images could not resolve it. Every model is
  tested on four setups it never trained on, which is the variation this data can measure.

## Readings

Every reading is the share of pixels whose cell-probability logit is above 0.0, the cutoff the product reads a
fine-tuned model at (`configs/finetuned_models.yaml`). These setups have no calibration profile and too few
images for one, so no arm is calibrated. The shipped readings are the committed zero-shot readings at 0.0. Images
are read as in the sealed test (`confluency_mcellseg.gray`).

## Analysis, fixed now

- **Primary.** MAE(approved) − MAE(`mcellseg_more_n169`) on all 31 images, with a 95% interval from 10,000
  bootstrap resamples of units (`confluency_mcellseg.clustered`, seed 0).
  - Interval entirely above zero: **more images read these setups better.**
  - Interval entirely below zero: **more images read these setups worse.**
  - Interval includes zero: **not shown with these 31 images.** That is not evidence that more images do not
    help: with 13 units, one of them holding 9 images, a real gain can leave an interval that includes zero.
- **Reported beside it, not judged:**
  - the same contrast on the 11 images at 60–90% (7 units);
  - MAE(shipped) − MAE(approved) on all 31 and at 60–90%, reported whatever it shows;
  - for every model: MAE with its interval, mean signed error, images within 5 pp, MAE at 60–90%, and MAE per
    setup, so one setup cannot carry the headline unseen;
  - MAE against the number of training images, for the curve's draws and the approved model;
  - every image's reading from every model.
- Passage calls are not judged: 2 test images are at or above 80%.

## What follows, fixed now

- Nothing changes before the call, whatever the result: the product, the approved model, the demo and the site
  stay as they are.
- If more images read these setups better, `mcellseg_more_n169` becomes at most a proposal to the repository
  owner, and these 31 images are its only evidence. It would need its own change record before the product could
  show it.
- These are the last mCellSeg images that no fine-tuned model has read. They are scored once.
- Weights stay on the Colab runtime and in the owner's Drive. The results that come back are the curves file and
  the training manifests, no weights or images.

## How it runs

- Training and readings run on a Colab GPU (`nb/10_more_images.ipynb`), from a bundle of the commit that adds this
  file. The notebook checks the committed files byte for byte and the approved weights by SHA-256.
- Order: the approved model reads the 31 first (no training), then `mcellseg_more_n169` is trained and read, then
  the curve's runs. The curves file is rewritten and copied to Drive after each model, so a dropped session loses
  at most one model.
- Scoring runs once on the Mac: `.venv/bin/python scripts/confluency_more_images.py score`.
