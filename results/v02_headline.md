# v0.2's headline confluency numbers, and where they came from

v0.2 is the version on `main` (last commit `e2274dd`, 2026-09-12) and on the
v0.2 site, cultureqc.vercel.app. It stated, in `main:README.md`:

- line 31–32: "On the same benchmark, thresholding is off by ~31 percentage
  points where this is off by 2.3";
- line 46: "Cellpose-SAM (`cpsam_v2`) probability map. 2.3 pp mean absolute
  error, zero-shot across morphologies";
- line 47 (the QC classifier): "98% test accuracy, 100% contamination recall
  at every severity".

Read them with `git show e2274dd:README.md`.

**What they were measured on: synthetic tiles.** The script and per-tile
results behind 2.3 pp and ~31 pp are not in this repository. The upgrade
spec written from the v0.2 code (`cultureQC_upgrade.md`, in history:
`git show 4a82657:cultureQC_upgrade.md`, line 14) records them as "~2.34 pp
MAE vs ~31 pp classical — synthetic only", and
`results/confluency_real_summary.md` puts its real-image result at "~3.6× the
synthetic-only 2.34pp MAE" the product cited. The 98% and 100% are
the classifier's results on synthetic test tiles, with contamination pasted at
16.5× the bacteria's real size (`results/contamination_scale.md`).

**What replaced them, on real images:** 8.35 pp mean absolute error on 33
held-out EVICAN images with expert masks, against 11.20 pp for the threshold
baseline (`results/confluency_real_summary.md`, V1). The classifier calls
5.0% of real held-out C2C12 normal frames normal (`results/classifier_c2c12.md`)
and is demoted.
