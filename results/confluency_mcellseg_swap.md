# Replication with the halves swapped: the mCellSeg passage-range test, run the other way round

**Status: pre-registration.** This section was committed before any fine-tuned model was trained on the
images below, and before any swapped reading was computed. The results section is added afterwards by
`scripts/confluency_mcellseg_swap.py score`.

## Why

The sealed test (`results/confluency_mcellseg.md`) was scored once, on 2026-10-06. Its pre-registered
comparison held: fine-tuning read the 60–90% test images closer to the experts than calibration alone,
MAE(C) − MAE(F) = +4.45 pp (95% interval +0.83 to +7.94). That rests on 22 dense images from 17 units, and only
4 test images were at or above 80%.

The obvious next step would be to adjust the recipe where it fell short, and that would be tuning on a test set
that has now been seen. This replication changes nothing. It runs the same procedure with the roles of the two
halves exchanged, so every number comes from images that the models being scored never trained on. The
question:

1. Does fine-tuning again read the passage range better than calibration alone, when the models are trained on
   the other half?

## What was looked at before this was written

Disclosed in full, because it bears on how new this evidence is:

- **All of the sealed test's results**, per image (`results/confluency_mcellseg.csv`).
- **The zero-shot readings of all 200 images** at every cutoff, committed in `007422d`. C's readings of the
  images tested here can therefore be computed from committed files. They have not been computed or looked at
  as a test, but C's calibration MAE on these images, at the sealed test's cutoffs, is in that test's results
  (`cd7_huvec_dic` 5.52, `lsm_hek_1024` 2.71, `oir_1024` 10.73 and `lsm_2796` 8.77 pp).
- **F's out-of-fold readings of these images.** In the sealed test, these 79 images were read by fine-tuned
  models trained on the other half of the same 79 (folds A and B). Their calibration MAEs are in that test's
  results (`cd7_huvec_dic` 0.97, `lsm_hek_1024` 1.23, `oir_1024` 2.76 and `lsm_2796` 2.71 pp). The models scored here are different: they train on the other 90
  images and have never seen any of these 79.
- **Counts from the masks** (below).

## What stays the same

Everything in `results/confluency_mcellseg.md` except the roles of the halves:

- The same four setups (`cd7_huvec_dic`, `lsm_hek_1024`, `oir_1024`, `lsm_2796`) and the committed units
  (`results/confluency_mcellseg_split.json`). After the swap `polymer_lowmag` would have 9 calibration
  images, all from one unit; it stays out, as before.
- The same reading, grid (−4.0 … +1.0, step 0.5), cutoff choice (`confluency_profiles.pick`), band
  (`confluency_profiles.band`), rules_v0.5 at T = 80, criteria B1–B5 with the same limits, and the same
  bootstrap (units resampled, 10,000 resamples, `numpy.random.default_rng(0)`).
- The same fine-tuning recipe (Cellpose-SAM `cpsam_v2`; learning rate 1e-5, weight decay 0.1, 100 epochs,
  batch size 1), not tuned in reaction to the sealed test. The same cross-fit: units of each setup, ranked by
  mean expert confluency, alternate folds A and B. One model trains on B and reads A, another trains on A and
  reads B, and a third trains on all 90 and reads the test images.
- The functions are imported from `scripts/confluency_mcellseg.py`, unchanged since `001a256`.

## Arms

- **Z: zero-shot, cutoff 0.0, no band.**
- **C: zero-shot plus a calibration profile per setup** (the shipped method), fitted on the 90 swapped
  calibration images.
- **F: fine-tuned on the 90 swapped calibration images, then calibrated**, with the cutoff and band from the
  out-of-fold readings.
- R is dropped: it was secondary in the sealed test and did not help.

## Test set (masks and file names only)

| setup | calibration images (units) | test images (units) | test at 60–90% | test at ≥ 80% |
|---|---|---|---|---|
| `cd7_huvec_dic` | 18 (17) | 18 (18) | 2 | 2 |
| `lsm_hek_1024` | 18 (6) | 14 (7) | 6 | 4 |
| `oir_1024` | 17 (6) | 14 (6) | 4 | 0 |
| `lsm_2796` | 37 (10) | 33 (10) | 1 | 0 |

79 test images: 13 at 60–90% (from 10 units), 14 at 60–100%, and 6 at or above 80% (from 6 units).

## Pre-registered comparison

- **Primary.** Fine-tuning replicates if the 95% interval of MAE(C) − MAE(F) on the 13 test images at 60–90%
  lies entirely above zero.
  - With 10 dense units the interval will be wide. A replication that does not exclude zero may say more about
    the size of this half than about fine-tuning; both outcomes are reported as they come.
- B1–B5 are judged for each arm exactly as in the sealed test. B2, B3 and B4 are measurable here (13 and 14
  images).
- **Secondary, both halves together.** Every one of the 169 images has now been read by models that never
  trained on it: the sealed test's 90 by the sealed test's models, and these 79 by this replication's models.
  B1–B5 and the same contrast are reported over all 169, with units resampled. The sealed test's rows are
  recomputed from its committed curves and checked against its committed CSV.

## Compute

- The three fine-tuning runs and their maps run on a Colab GPU (`nb/07_confluency_replication.ipynb`), from a
  bundle of this commit. The maps are reduced to readings at every grid cutoff
  (`results/confluency_mcellseg_swap_curves.json`, with the runs' manifests).
- `score` reads only that file and the committed `results/confluency_mcellseg_curves.json`, on the Mac, once.

## What it cannot show

- Everything the sealed test could not show still applies: 20× and 40× images, one lab, two cell lines, setups
  inferred from formats, and masks drawn with fluorescence to help.
- This is the same dataset cut the other way. It can show that the result does not depend on which half
  trained the models, but it is not a second lab or microscope.
- The two halves were split to span the density range, so the two estimates are not independent draws.

## What changes downstream

Nothing in the product. The fine-tuned weights are a measurement only: they inherit Cellpose-SAM's
non-commercial status (`README.md`, "Licences and commercial use").

## Also in this Colab run (not part of this test)

A fine-tuned model for the MSC setup the product already reads, trained so the repository owner can decide
whether to propose a fine-tuned MSC profile. Its training set is fixed here, before training: 20 images drawn
at random (`numpy.random.default_rng(0)`) from all 320 MSC images (8 from 218-5, 6 each from 218-4 and 218-6;
`scripts/confluency_finetune.py final`). None is a product example image. Any cutoff and band for such a
profile would come from the development runs' out-of-population readings, which are already committed
(`results/confluency_finetune_dev_curves.json`). Nothing in the product loads this model.
