# Does the confluency confidence predict the reading's error?

**Status: pre-registration.** This section was committed before any of the
numbers below were computed. The results section is added by
`scripts/confidence_vs_error.py` in a later commit; the commit order is the
evidence that the rule came first.

## Question

The confluency `confidence` shown with every reading, and compared with the
rules' review floor (0.30), is computed in `culture/seg.py::cpsam_confluency`
(probability map, shipped cutoff 0.0, band 1.0) as

    confidence = clip(1 − 4 × mean(|p − 0.0| < 1.0), 0, 1)     rounded to 3 decimals

where `p` is Cellpose-SAM's cell-probability map (`flows[2]`, logits). That is
the share of pixels within ±1 logit of the cutoff. Denser cultures have more
cell edges, so the score may track density rather than the reading's error,
which would explain why review is far more frequent in the 40–60% band
(`results/review_rate.md`). If it does not predict error, "confidence" is the
wrong name for it.

## Data (fixed now)

- **Primary: the 33 held-out EVICAN images** of `results/confluency_real.csv`
  (the V1 set, 8.35 pp MAE). Per image: `cultureqc_confidence` and
  `cultureqc_pct`, both from the shipped call `culture.seg.cpsam_confluency(
  method="probmap")` at cutoff 0.0; `gt_pct`, the expert mask; and
  `width × height`. |error| = |`cultureqc_pct` − `gt_pct`| in pp. The decision
  is made on these 33 only.
- **Secondary, labelled as such: the 65 calibration images** of
  `results/confluency_cutoff.csv` (`split == calib65`): `conf_cut0`,
  `pct_cut0` and `gt_pct`. These are the cutoff study's rerun of the same call,
  with the same formula, from full-resolution maps stored as float16. They are
  not the stored pipeline outputs, and readings may differ from a fresh run in
  the first decimal. Image size from the EVICAN annotation files. Reported,
  not used for the decision.
- **Density check on held-out C2C12 frames (metric 3 only):** full frames of
  the held-out base sequences (`results/replay_fleet_split.csv`), with
  Cellpose-SAM's cached confidence and reading (`cache/confluency.parquet`,
  `cpsam_v2`, `crop_spec == "full"`, computed with the same formula). There is
  no expert ground truth, so the density proxy is **the model's own reading**,
  labelled as such. No model is run for any part of this study.
- Shipped cutoff (0.0) only. The calibrated cutoff (−3.5) is not studied here.

## Metrics (fixed now)

Ranks use average ranks for ties (`scipy.stats.spearmanr`). Every bootstrap and
permutation uses `numpy.random.default_rng(0)`.

1. **Spearman ρ(confidence, |error|)** on the 33, with a 95% percentile CI
   from 10,000 bootstrap resamples of the images. Resamples where ρ is
   undefined (a constant column) are dropped and counted. A useful score has
   ρ < 0: higher confidence, smaller error.
2. **Partial Spearman ρ(confidence, |error| · GT confluency)**: rank all three
   (average ranks), then the partial correlation of the ranks,
   (r_xy − r_xz·r_yz) / √((1 − r_xz²)(1 − r_yz²)). Same bootstrap resamples
   for a 95% CI. It asks whether the score carries anything about error beyond
   density.
3. **Spearman ρ(confidence, GT confluency)** on the 33 (bootstrap CI as in 1).
   On the held-out C2C12 frames, **Spearman ρ(confidence, Cellpose-SAM's own
   reading)**, with a 95% CI from 10,000 bootstrap resamples of **sequences**
   (frames within a sequence are not independent).
4. **Risk–coverage.** Sort by confidence, highest first. For k = 1…n, risk(k)
   is the mean |error| of the k kept images. AURC is the mean of risk(k) over
   k. Tied confidences are handled exactly: the expected AURC over random
   orderings within each tie group, computed by giving each tied image its
   group's mean |error|. Report AURC next to:
   - **random order**, whose expected AURC is the overall MAE;
   - **the oracle**, sorted by actual |error|, smallest first.

   Permutation p-value: shuffle the confidences against the errors 10,000
   times and compute each shuffle's tie-averaged AURC. p = (1 + number of
   shuffles with AURC ≤ the observed AURC) / 10,001. Plot the three curves:
   `results/confidence_vs_error.png`.

The same four metrics are computed on the 65 calibration images and reported
as secondary.

## Decision rule (fixed now)

Keep the name "confidence" only if, on the 33 held-out images, **both**:

- **(a)** ρ(confidence, |error|) ≤ −0.3 **and** its bootstrap 95% CI excludes 0
  (upper bound < 0); **and**
- **(b)** AURC beats random with permutation p < 0.05.

Otherwise rename the displayed label everywhere to **"Boundary ambiguity"**,
shown as 1 − confidence (higher = more ambiguous; the review floor of 0.30
confidence then reads "ambiguity above 0.70"), with the tooltip:
"share of pixels near the cell/background cutoff; rises with density; a review
trigger, not a probability that the reading is right." The record field stays
`confidence`, with its meaning documented in `docs/audit_mapping.md` and the
schema. The review floor and the rules are unchanged either way. The rule is
not re-run on other data or other cutoffs if it fails.

## Caveat, printed with the result

n = 33, most of them sparse (the count below 20% GT is printed with the
result); low power; the set does not cover the passage band. A pass would be
weak evidence; a fail on (a) or (b) is a failed check of the name, not proof
that the score carries no information.

## Results

Computed by `scripts/confidence_vs_error.py` after the pre-registration above (commit `3a15fda`); nothing above this section was changed. Per-image values: `results/confidence_vs_error.csv`. Curves: `results/confidence_vs_error.png`.

### Decision (on the 33 held-out images)

- (a) ρ(confidence, |error|) = **-0.36**, 95% CI [-0.69, +0.02]: fails (needs ≤ −0.30 with the CI below 0).
- (b) AURC **7.73** pp vs random 8.35 pp, permutation p = **0.303**: fails (needs p < 0.05).

**Rename: the displayed label becomes "Boundary ambiguity" (1 − confidence).**

### All metrics

| Metric | 33 held-out (primary) | 65 calibration (secondary) |
|---|---|---|
| ρ(confidence, \|error\|), 95% CI | -0.36 [-0.69, +0.02] | -0.18 [-0.44, +0.11] |
| Partial ρ, controlling for GT confluency | +0.02 [-0.42, +0.38] | +0.17 [-0.07, +0.38] |
| ρ(confidence, GT confluency) | -0.61 [-0.79, -0.31] | -0.41 [-0.64, -0.14] |
| AURC by confidence (pp) | 7.73 | 12.96 |
| AURC, random order = MAE (pp) | 8.35 | 10.24 |
| AURC, oracle (pp) | 3.26 | 3.32 |
| Permutation p, AURC vs random | 0.303 | 0.965 |
| Confidence range (distinct values) | 0.000–1.000 (28) | 0.230–1.000 (59) |
| GT confluency range; images below 20% | 2.9–58.6%; 23 | 1.3–65.1%; 43 |

The 65 are the cutoff study's rerun of the same call (float16 maps), reported, not used for the decision.

### Density on held-out C2C12 frames (metric 3)

Spearman ρ(confidence, Cellpose-SAM's own reading) = **-0.95**, 95% CI [-0.98, -0.93] (sequence bootstrap), on 1228 full frames from 14 held-out sequences, readings up to 57.0%. The density proxy is the model's reading, not an expert mask.

### Caveat

n = 33, 23 of them below 20% GT (range 2.9–58.6%); low power; the set does not cover the passage band. A pass would be weak evidence; a fail on (a) or (b) is a failed check of the name, not proof that the score carries no information.
