# Confluency in the passage range: dense regions of held-out MSC images

**Status: pre-registration.** This section was committed before any
probability map named below was read for this test. The results section is
added afterwards by `scripts/confluency_dense_tiles.py score`; the commit order
is the evidence that the method and the rules came first.

## Why

The calibration profiles (`results/confluency_profiles.md`) could not measure
A2–A4, the criteria in the passage range, on whole images: `msc_phase` has 4
test images with ground truth at 60–90% and `evican_mixed` has none. Passage
decisions are made in that range.

The MSC images (Solopov et al. 2025, 1000 × 1000 px) often hold dense regions
even when the whole image is moderately confluent. This test reads those
regions: does the calibrated cutoff, fixed beforehand, read dense cells within
the A2 and A3 limits?

It does not replace A2–A4. Those stay "not measurable" on whole images; this
is a separate, region-level measurement beside them.

## What was looked at before this was written

- The expert masks only, to count candidate regions (`count`, below): with
  the 2 × 2 grid, 39 quarters at 60–90% from 27 images, 6 / 24 / 9 from
  populations 218-4 / 218-5 / 218-6; with a 4 × 4 grid, 439 tiles from 162
  images. No probability map was read for this test.
- These 320 images are `msc_phase`'s test images, already scored once as
  whole images. This is their second use. The cutoffs and bands come from
  that study and are not refitted.

## Method (fixed now)

- **Images.** All 320 MSC images; masks `data/sources/msc/masks/` (0/255,
  ground truth = mask > 0, as in `msc_gt`).
- **Regions (primary).** Each image is cut into a 2 × 2 grid of quarters
  (500 × 500 px). A quarter is included when its ground truth is 60–90%
  inclusive.
- **Reading.** Cellpose-SAM's map is the full-frame map already cached for
  the profiles study (`cache/probmaps_full/msc/`, from the same call as
  `culture/seg.py`), cropped to the quarter; the image is not segmented
  again. Reading = 100 × share of the quarter's pixels with logit above the
  cutoff.
- **Cutoff and band: held out.** Each quarter is read with the cutoff and
  band of the fold that leaves its population out
  (`results/confluency_profiles.json`, `msc_phase` folds in population order
  218-4, 218-5, 218-6: cutoff −1.5 in all three; band 7.63, 6.42 and 7.70
  pp). Also reported at the shipped cutoff 0.0, for comparison.

## Reported once

Primary, on the included quarters:

| # | measure | passes when | measurable when |
|---|---|---|---|
| D2 | MAE | ≤ 5 pp (A2's limit) | ≥ 10 source images contribute a quarter (A2's minimum, counted in images, since quarters of one image are not independent) |
| D3 | mean signed error | \|bias\| ≤ 3 pp (A3's limit) | as D2 |

Verdicts are on the point estimates, as for A2 and A3. Each comes with a 95%
interval from a bootstrap that resamples source images with replacement
(10,000 resamples, `numpy.random.default_rng(0)`), plus the same numbers per
population.

Secondary, reported but not judged against a limit:

- Band coverage: the share of included quarters whose reading is within its
  fold's band of the ground truth. The bands were measured on whole
  1000 × 1000 images; a quarter is a smaller field and noisier, so a low
  coverage here may reflect field size, not the calibration.
- The passage call at T = 80% on quarters with ground truth 60–100% (A4's
  set): passage if reading − band ≥ 80, continue if reading + band < 80,
  otherwise review; agreement with ground truth on the quarters not sent to
  review, and how many go to review.
- The same D2 and D3 numbers at the shipped cutoff 0.0.
- Sensitivity to field size: D2 and D3 on a 4 × 4 grid (250 × 250 px).

## What it cannot show

- These are dense regions inside moderately confluent images, not dense
  cultures. A failure that depends on the whole image, such as EVICAN's
  `15_Caco-2.jpg` (expert 65.1%, no cutoff in the grid finds its cells;
  `results/confluency_cutoff.md`), cannot appear here.
- One setup, three cell populations, regions correlated within an image.
- The dataset's images are already tiles of larger acquisitions
  (`<population>_part_<p>_tile_<t>`), and its magnification is given as 10×
  in the paper and 40× on the dataset page, so the physical field size of a
  quarter is not stated.

## What changes downstream

Nothing in the product. No profile, cutoff, band or rule changes because of
this result, whichever way it goes. It is reported as scored.
