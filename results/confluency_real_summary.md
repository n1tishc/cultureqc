# Real-image confluency validation — Slice 1

**Dataset:** EVICAN (CC BY 4.0), `eval2019` split — the dataset's own
designated held-out evaluation set, 98 images. Verified not to overlap with
Cellpose-SAM's training corpus (see `docs/DATASETS.md`). Cell Tracking
Challenge was not used — blocked on organizer permission (also in
`docs/DATASETS.md`).

**Eval subset:** 33 of the 98 `eval2019` images (stratified across all three
difficulty tiers and 30 of the ~30 distinct cell lines represented in the
split), chosen under a local-CPU time budget rather than running the full 98
(estimated ~4.7 hr — see the compute-budget discussion this slice started
with). Selection is deterministic (`scripts/eval_confluency_real.py --seed
0`); the full image list is in `results/confluency_real.csv`. 6 further
images were held out as a **tuning split**, used only to freeze the
local-contrast baseline's threshold, and are excluded from every number below.

**Methods, no retuning on the eval set** (only the local-contrast baseline's
own threshold was tuned, on the separate 6-image tuning split, then frozen):

| Method | What it is |
|---|---|
| `cultureqc` | `culture.seg.cpsam_confluency(method="probmap")` — shipped default |
| `threshold_baseline` | `culture.seg.threshold_confluency` — shipped classical baseline |
| `local_contrast_halo` | Jaccard et al. (PMC4260842) **-inspired, simplified** — local contrast (std/mean) thresholding as the paper describes, but halo suppression by morphological opening rather than the paper's iterative Kirsch-filter gradient tracking. Not a faithful reimplementation; see `scripts/eval_confluency_real.py`'s docstring. |

## Headline numbers (n=33)

| Method | MAE (pp) | Median AE (pp) | Mean signed error (pp) |
|---|---:|---:|---:|
| **cultureQC** (cpsam_v2, probmap) | **8.35** | 5.49 | **−8.32** |
| Global-threshold baseline | 11.20 | 8.37 | −10.21 |
| Local-contrast + halo (simplified) | 23.42 | 13.50 | +10.19 |

**Decision rule (spec §4.5): MAE ≲5pp → proceed; 5–10pp → proceed + error
analysis; >10pp → stop and report.** cultureQC's real-data MAE is **8.35pp —
in the 5–10pp band. Proceeding to Slice 1b, with the error analysis below
read before trusting any downstream number derived from `cpsam_v2`.**

This is **~3.6× the synthetic-only 2.34pp MAE** the product currently cites.
Both are true statements about different things — synthetic tiles at their
composited scale vs. real, independently-collected microscopy this model was
never tuned on — but only the real number should anchor any claim made to a
domain expert. See §12 of `cultureQC_upgrade.md` (claims policy) — the
synthetic figure already requires "synthetic" beside it; this result is the
reason that rule exists.

## The 60–90% band the spec asks for — a genuine dataset gap, not a bug

Spec §4.2 asks for MAE within the 60–90% GT confluency band specifically,
because that's the range passage decisions get made in. **EVICAN's `eval2019`
split has exactly one image in that band across all 98** (`15_Caco-2.jpg`,
GT=65.11%) — the split is heavily skewed low (median GT 16.1%, max 65.1%,
zero images ≥66%). Bucket counts across all 98: 0–20%: 66, 20–40%: 26,
40–60%: 5, 60–80%: 1, 80–100%: 0.

That one image was run anyway rather than reported as "N/A":

**`15_Caco-2.jpg` — GT=65.11%, cultureQC=0.00%, threshold_baseline=6.16%.**

cultureQC predicts **total absence of cells** on the one real image in this
sample that most resembles a "ready to passage" flask. n=1 is not a real
estimate of the 60–90% band's MAE and isn't reported as one — but a single
catastrophic miss on exactly the decision this product exists to support is
worth more attention than a missing table cell. The image itself is severely
underexposed (mean pixel intensity 35.6/255) — see the overlay gallery.

**Recommendation carried into Slice 1b and beyond:** don't treat the overall
8.35pp MAE as covering the passage-decision range. If Cell Tracking Challenge
access is obtained (see `docs/DATASETS.md`), or C2C12 hand-labeling happens
early (Slice 2/3), prioritize real images in the 60–90% band specifically —
this is the one place Slice 1's real-data check couldn't actually test the
product's core claim.

## Error analysis (the 5–10pp tier requires this)

**Systematic under-prediction, not random noise.** 30 of 33 images (91%) have
negative signed error — cultureQC almost always reports *less* confluency
than the real mask. Linear fit: `cultureqc ≈ -3.0 + 0.73 × GT` (r=0.865
correlation with GT, so the model does track real confluency directionally —
it's a scale-down, not noise). The bias **worsens as GT confluency rises**
(corr(GT, signed error) = −0.54): the higher the true confluency, the more
`cpsam_v2`'s probmap method under-reports it. This is the same direction as
the 60–90%-band failure above, not a separate phenomenon — it's the extreme
end of a trend visible across the whole sample.

**3 of 33 images (9%) predict exactly 0.00%** despite non-trivial GT
(15.8%, 12.3%, 19.4%): `74_RKO.jpg`, `52_MCC.jpg`, `51_LNCaP.jpg`. Total
segmentation failure, not a small miss. `74_RKO.jpg` is severely
underexposed (mean intensity 10.2/255, visibly near-black even to a human
eye) — plausibly image quality, something Slice 2's quality gate is meant to
catch before a real record even reaches the temporal layer. The other two
were not individually re-examined at this depth; worth a second look before
Slice 1b if time allows, but not blocking.

**Not primarily an exposure/brightness effect across the full sample** —
correlation between mean pixel intensity and signed error is weak (r=0.125)
once all 33 images are considered, even though the single worst 0.00%
failure and the 60–90%-band failure both happen to be dark images. Image
brightness alone doesn't explain the broader systematic under-prediction;
that looks tied to confluency itself (density), not exposure.

**13 of 33 (39%) have |error| > 10pp; 8 of 33 (24%) have |error| > 15pp.**
A meaningful tail of large misses, not just a few outliers.

**Visual confirmation, not just a numeric pattern.** The overlay gallery
(`results/confluency_real_overlays/`) draws cultureQC's predicted cell
boundary directly on each image. At low density
(`best_66_PC3.jpg`, GT=5.5%, sparse well-separated cells), the boundaries
closely hug each cell's true visible edge — accurate to within 0.4pp. At
higher density (`worst_48_HT29.jpg`, GT=51.6%, cultureQC=29.4%, many
touching/adjacent cells), the model still finds and circles almost every
cell — recall looks fine — but each individual boundary sits visibly
*inside* the true cell edge, especially where cells touch or overlap. That's
consistent with Cellpose's instance-separation behavior at touching
boundaries (it places a boundary between adjacent cells even where the true
edge is further out, to keep them as separate instances) compounding as
density rises — matching both the negative-and-worsening-with-GT bias above
and the catastrophic 60-90%-band failure, which is the density extreme of
the same effect.

## What this means for `cpsam_confluency`'s current `thr=0.0` default

`culture/seg.py::cpsam_confluency` thresholds the cell-probability map at
`thr=0.0` (the sign of the raw logit) with no calibration against real data —
that default was presumably chosen for the synthetic/LIVECell-adjacent
distribution it was validated on originally, not against EVICAN. The
systematic negative bias found here is consistent with that threshold being
too conservative (too high) for at least some of these real cell lines and
morphologies. **Not fixed in this slice** — Slice 1 is a measurement pass,
not a retuning pass (rule 10: no model changes without an explicit slice
sign-off), but this is the most actionable lead for whoever looks at this
next: refitting `thr` against real GT (or making it configurable per
cell-line, matching `LineConfig`'s existing per-line pattern) is a cheap
experiment relative to anything else on the slice plan.

## Baseline comparison

Both baselines are worse than cultureQC by MAE, which is expected and
consistent with the product's own claim (§0.1: "~31 pp classical" vs
"~2.34 pp synthetic" — directionally holds on real data too, just with a
smaller real-data gap than the synthetic claim implies). The local-contrast
baseline's positive bias (+10.19pp, opposite direction from the other two
methods) is likely an artifact of its threshold being tuned on only 6 images
— not a claim that local-contrast methods are inherently biased positive.

## Files

- `results/confluency_real.csv` — all 33 rows, every method's per-image output
- `results/confluency_real_tuning.json` — tuning split, frozen threshold, subset selection parameters
- `results/confluency_real_scatter.png` — GT vs. predicted, all three methods, colored by difficulty tier
- `results/confluency_real_overlays/{best,median,worst}_*.png` — 3 best, 3 median, 3 worst cases by cultureQC absolute error, with the predicted cell boundary drawn on the image
