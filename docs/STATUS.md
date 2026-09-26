# cultureQC — upgrade status

Governing spec: `cultureQC_upgrade_spec.md` (v3.1). Checked against the repo on
branch `slice-1b-compute-cache`, starting from `e86ce93`, on 2026-09-25;
updated 2026-09-26 after `nb/03` and the A2 fleet.
Nothing is merged to `main`.

## Slices (spec §2.1), confirmed against the repo

| Slice | Status | Evidence in repo | Notes |
|---|---|---|---|
| 0 Recon + baseline | Done | tag `v1.0-pre-upgrade`, `docs/REPO_MAP.md`, `results/baseline_latency.{csv,md}`, `tests/test_smoke_pipeline.py` | — |
| 1 Real-image confluency | Done, **V1 partly measured** | `results/confluency_real_summary.md`, `results/confluency_real.csv` | See "V1" below |
| 1b Compute cache | Done; C2C12 sequences added by `nb/03` (A0.5) | `cache/MANIFEST.json`: 4,246 images (4,000 `synth_tiles`, 148 `autoqc_bench_test`, 98 `evican_eval2019`); `configs/noise.yaml`, `results/fov_noise_summary.md` | After `nb/03` the local `cache/` holds 6,983 images: 2,088 `c2c12` (24 sequences), 552 `c2c12_fault_dim`, 97 `c2c12_fault_contam`, plus the sets above |
| 2 Visit summary, history, quality gate, replay | Done | `schemas/visit_summary.v1.json`, `culture/{quality,history,replay}.py`, tests for each, Flask Timeline tab in `demo/app.py` | Replay tested on fixture sequences only; needs the fault-sequence adapter (A2) |
| 3 Growth model + T* + timeline | Done, **backtest synthetic only** | `culture/growth.py`, `tests/test_growth.py`, `results/growth_backtest.md`, `results/growth_examples.*`, `results/growth_runtime.txt` | Backtest is a harness check; don't quote it until A1 reruns it on real sequences. Missing one §6.1 item, see below |
| 4, 4b, 5, 5b, 6, 7, 8 | Not started | — | Minimal versions in Phase A |

Tests: `pytest tests` → 112 passed, 1 xfailed (2026-09-26, after A7).

## Phase A progress

| Step | Status |
|---|---|
| A0.1 This file | Done |
| A0.2 `Cache.build()` flush fix | Done: flushes all tables every `flush_every` records (default 100) and at the end; `tests/test_cache_resume.py` (kill mid-build → flushed rows on disk → rerun computes only the rest, no duplicates, same result as an uninterrupted build). Checked that the key test fails with periodic flushing disabled. |
| A0.3 Commit the `nb/03` files | Done in `544861c` (the files arrived in `files/`); `nb/03` is pinned to `2f8b5d0`, which adds a stop-before-download check for colliding frame numbers and runs the GPU pass as a single `build()` call. Read against the repo: git remote, `requirements.txt`, `download_sources.py` / `extract_sprites.py` arguments, `synth_contamination.add_bacteria` / `get_cell_mask` / `SEVERITY_RANGES`, `Cache.build()` and `replay._sequence_frames` all match. Ran locally at `2f8b5d0` on fake 12-bit sequences: fetch (mid-grey 8-bit PNGs, conditions parsed from folder names, 85 hourly frames / 84 h) → fault set (all three types) → `Cache.build()` (quality only) → replay on a cached sequence, with no unset `frame_idx`. Not testable here: OSF API calls and GPU inference (the notebook's checkpoints 1–3 cover those). |
| A0.5 `nb/03` Colab run | Done (2026-09-26). Budget test measured 7.10 s/image for seg (GPU-bound). Output installed at `cache/` (1.4 GB); previous cache backed up to `~/Desktop/projs/cultureqc_cache_backup_nb02`. 24 sequences, 32 fault sequences (24 lamp dimming, 4 contamination, 4 growth stall) |
| A2 adapter | Done (`0807b65`). `build_replay_visits(..., frames=)` replays one fault sequence from its `fault_manifest.parquet` rows, ordered by timestamp, and copies each frame's ground truth into `visit["fault"]`. Tables load once per call (`ReplayTables`, shareable across a fleet). Per-call overrides for cadence, `n_fov` and `crop_frac`, recorded in `visit["replay_params"]`. Frames without cached seg rows raise instead of reading 0%. `split_sequences()` / `fault_split()` give a seeded 40/60 split by base sequence, with fault twins following their base. With calibration switched off, default outputs are identical to the old code (152 fixture visits, 10 seeds). **Since `fb37afe`, default replay output differs from older runs:** temperature-scaled `class_probs`, `calibrated: true`, and a `calibration.yaml` entry in `config_hashes`. When any override is set, it becomes part of the `visit_id` key, so streams at 1 vs 3 FOVs or 6 h vs 12 h no longer collide. The fleet run is the next row |
| A2 fleet | Done (2026-09-26). `scripts/replay_fleet.py`: 24 base + 32 fault streams at 6 h / 12 h (jitter ±25%) × 1 / 3 FOVs, all FOVs 0.25-frac crops, seed 0 for every stream. Split written to `results/replay_fleet_split.csv`, which A1/A4/A6 read. **Stratified by fault type** (drift item 15): 10 tuning / 14 held-out bases, 2 contamination + 2 growth stall on each side. 6 h: 14–15 visits per stream; 12 h: 8; 24 h: 5, reported as not testable. Every fault twin repeats its base's visits until onset (128/128). Summary: `results/replay_fleet_summary.md`; visits in `cache/replay_fleet/` (gitignored, regenerable in ~10 s) |
| A5 calibration | Done (`fb37afe`). T = **1.5536**, fit on synthetic val (n=645). Top-label ECE: val 0.0102 → **0.0057** (in-sample; V8 ≤ 0.05 passes, and passed before scaling too); test 0.0187 → 0.0139 (held out). Per-class ECE is in `results/calibration_summary.md`. Provenance: synthetic, so it says little about C2C12. Replay applies T when the logits' model_version matches `configs/calibration.yaml`. **`culture/qc.py` (live app) does not apply it yet** (Phase B) |
| §6.1 one-step-ahead | Done. `culture/growth.py`: `predict_next()`, `one_step_ahead_series()`; `predictive_sd = sqrt(fit_sd² + obs_sd²)`, with obs_sd = σ_fov at the *expected* confluency / √n_fov (config `one_step_ahead.fov_scaling`). Synthetic check with the model correct and a test noise model: SD(z) = **1.23**, mean 0.15, n=285 (fit_sd alone: 2.14; obs_sd alone: 1.72). So z is slightly over-dispersed even when the curve shape is right; A6 must check the z scale on the tuning fleet. A stall shows in the one-step residual for about 4 visits, then the refit bends into a plateau and absorbs it, so SPC must accumulate early (CUSUM) |
| A3 fault set | Done by `nb/03`. Lamp-dim onset frames are the originals, not modified (drift item 10, fixed) |
| A1 growth backtest | Done (2026-09-26), **thin**. `scripts/backtest_growth.py` (default `--source c2c12`) on the 14 held-out sequences, same streams as the A2 fleet. Truth = first crossing of the hourly full-frame Cellpose-SAM series. Held-out sequences reach at most 57.0%: **only the 50% target is testable (5 of 14 cross; 60/70/80%: 0)**, and 3 of the 5 cross by < 2 pp in their last 1–2 frames. At the target − 10 cut: median abs error 4.9 h (6 h, 1 crop), 9.0 h (6 h, 3 crops), 2.1 h (12 h, 1 crop, 3 predictions), 5.8 h (12 h, 3 crops); full frame 2.4 h / 1.9 h. **V3: no verdict at n=5.** Added 30% and 40% targets (not in the spec; 12 and 8 held-out crossings), reported separately. `results/growth_backtest.md`; the synthetic harness check moved to `results/growth_backtest_synthetic.*` (CSV regenerated: same predictions, interval bounds changed by `a5dd140`'s bootstrap; summary unchanged) |
| A4 anomaly | Done (2026-09-26). `culture/anomaly.py`, `scripts/eval_anomaly.py`, `configs/anomaly.yaml`: DINOv2 qctile patches, cosine nearest-patch distance, image score = mean of the top 1% (AnomalyDINO); greedy-coreset banks (10%, PatchCore) from the tuning normals, bins 0–20 / 20–40 / 40–100% (60–80 and 80–100 merged: < 3 tuning sequences); every frame scored without its own base sequence (per-fold coresets). Held-out normal flag rate at the 5% thresholds: **10.0%** (0–20% bin 14.7%; 090318 F0016 alone 69%). **V4 fails as written** (Spearman ρ binned z −0.16 vs global −0.09), but ρ misses the global score's U shape: mean z at ≥ 50% is +1.19 global vs +0.37 binned. **V5(b) passes, n=2** (AUROC 1.00 at ≥ 150 sprites), but the sprites also raise Cellpose confluency by a median +59 pp. **V5(a) fails** for the CLS-kNN stand-in on synthetic tiles (detachment 0.82, image_quality 0.78; contamination 1.00). Dimming doesn't move the score (AUROC 0.41–0.49). `results/anomaly_summary.md` |
| A6 SPC | Done (2026-09-26); **V6 fails on all three counts.** `culture/spc.py`, `scripts/eval_spc.py`, `configs/spc.yaml`: EWMA + one-sided CUSUM on growth (lower), anomaly and three class residuals (upper), each standardised on tuning normals; λ = 0.2, k = 0.5, limits scaled by one multiplier chosen on tuning false alarms only (≤ 1/100 → c = 1.8: L = 5.15, h = 7.2; at the spec's L = 2.86 tuning false alarms were 9.4/100). Held-out: **3.75 false alarms / 100 visits** (16 of 24 on 090318 F0016, the sequence A4 flags 69%); **contamination 0/2** by SPC in every cell (the gate REIMAGEs it 1–2 visits after onset, leaving SPC 0–1 eligible visits); **growth stall 0/2** (the one-step refit absorbs the plateau, and gate failures delay the first growth residual on 090303 F0014 to 68 h). Growth z on tuning normals: mean +0.69, SD 1.79 (biased and over-dispersed). `results/spc_summary.md` |
| A7 instrument drift | Done (2026-09-26); **V7 fails.** `culture/drift.py`, `scripts/eval_drift.py`, `configs/drift.yaml`: flasks aligned on hours since start; per visit, log exposure relative to the flask's first 24 h minus an age-dependent expected change (tuning frames), plus A4 anomaly z, every visit including gate failures; per window (= cadence) the fleet median, standardised by the tuning fleet's population series; EWMA (λ = 0.2, L = 2.86, c = 1 chosen on tuning with no power); INSTRUMENT_DRIFT = EWMA beyond limit (no restart); per-flask SPC flags in drift windows marked suppressed (all codes; spec names anomaly drift only). Held-out: **the normal fleet itself drifts** from 42 h (6 h) / 48 h (12 h), exposure side, because the population SD (0.034) is one fleet's window-to-window SD and misses fleet-to-fleet offset (held-out normals sit ≈ −0.2 per-flask z below the tuning reference; leave-one-flask-out checked: 0.032, not the cause). So **V7 (a) passes by the rule but is not evidence** (dimming detected 2 h / 8 h after onset, 0 unsuppressed post-onset flags, but the same windows are in drift on normal); **V7 (b) fails**: every single-flask fleet inherits the false drift (A7's own), and stall flasks have no flag at all (inherited from A6); contamination flasks flagged by REIMAGE 8/8. 16 real per-flask SPC flags on normal flasks hidden. Dimming still gives REIMAGE on 10/14 flasks (not suppressed; roll-up is a B5/B6 question). Post-hoc diagnostic (not a verdict): standardising by the standard error of a median of n flasks (1.2533·s/√n, s from tuning) gives 0 normal drift episodes, 0/16 single-flask fleets in drift, dimming at 2 h / 8 h; assumes independent flasks, which the experiment clustering breaks. `results/drift_summary.md`, `results/drift_fleet.png` |
| A8 latency | Done (2026-09-26); **V9 fails.** `scripts/benchmark_live_path.py` → `results/live_latency.{md,csv}`: live per-FOV path per model on the Mac (Apple M2 Pro) with torch/OpenCV at 2 threads to mimic the Space (HF CPU Basic, 2 vCPU); approximation, likely a lower bound. Input: a real LIVECell phase-contrast fixture tiled to the C2C12 frame size (no C2C12 frames on the Mac). Per FOV, median of 2: **Cellpose-SAM 689 s at 1392×1040**, 230 s at 704×520, 71 s at 348×260; classifier 0.67 s with Grad-CAM (0.17 s without); DINOv2-small qctile 0.03 s; patch kNN 0.003 s; quality gate < 0.01 s. Per visit at 1 FOV: 138× / 46× / 14× the 5 s budget; 3 FOVs triple it. Everything but Cellpose ≈ 0.7 s per FOV. The spec's levers (ViT-S, fewer crops, smaller input) don't close it; left: precomputed demo examples (spec), or a GPU Space / lighter live confluency model (Phase B decision, V1 rechecked) |
| V2, V10 | Done (2026-09-26); **V2 fails.** `scripts/eval_growth_signal.py` → `results/growth_signal_summary.md`: held-out normal streams, full-frame increment between visits at 30–70% (effectively 30–56%) ÷ σ_fov (C2C12, 0.25-frac)/√n_fov. Median ratio 0.35 (6 h) / 0.65 (12 h) at 1 FOV, 0.61 / 1.12 at 3 FOVs (pass ≥ 2 at 1 FOV); measured visit error SD 13.2 pp (1 FOV) agrees with the model. Context: 0.5-frac noise fit gives up to 2.71 (12 h / 3 FOVs), not replayed. V10 (informational): area doubling time per experiment 17.7 / 12.4 / 15.4 h (median) |
| Phase A report | Done (2026-09-26): `docs/ARCHITECTURE_VALIDATION.md` — summary table, one section per V1–V10, what it does and doesn't prove, next steps (decisions for the review, Phase B mapping, Celltrio questions). Also `results/classifier_c2c12.md` (classifier calls 5.0% of held-out normal C2C12 frames normal, 91.8% of contaminated frames contamination) and `results/growth_backtest_v3.png`. Deviation: no single `scripts/validate_architecture.py`; per-check scripts listed in the report |

## Schedule

The spec's target review date (Sat Sep 26) **can't be met**. Phase A's timebox
is "2 working days after `nb/03` completes"; `nb/03` output reached the Mac
on 2026-09-26. The date that actually binds is the **code freeze on Sun Oct 4**.

## Drift and gaps found (spec vs repo)

1. **No shifted synthetic tiles in the cache.** §4A.1 says to generate
   `data/tiles_shift/` (artifacts on EVICAN + C2C12 backgrounds) *before* the
   1b pass, so their logits are cached. They weren't generated, and no
   `tiles_shift` dataset is in the cache. B3's domain-shift test depends on
   those logits, so as things stand it needs a new GPU pass, which rule 10
   only allows if a slice says so. **Decision needed:** add it to the `nb/03`
   run, or scope B3's shift test out (it's already on the cut list).
2. **The Mac cache has no patch embeddings.** Local `cache/` is a copy of the
   slim export: `embeddings/` is empty, CLS only for all 4,246 images.
   `nb/02` kept full patch embeddings for synthetic `normal` tiles, EVICAN and
   AutoQC-Bench, but only in the Drive full cache. A4's patch-kNN needs
   patches: for C2C12 frames they come from `staged/c2c12_patch_embeddings.zip`
   (per `nb/03`); for the synthetic-tile side (V5a AUROC, optional bank
   normals) the synthetic tile patches have to be copied from Drive (see the
   open question below).
   Also, `export_slim()` drops *all* patch embeddings, while §4A.3 says the
   slim copy should keep the replay/eval subsets.
3. **V1 is only partly measured.** Held-out EVICAN MAE is **8.35 pp** (n=33,
   real (EVICAN eval2019)): passes ≤ 10 pp, not "strong" (≤ 5). The
   60–90% band can't be measured on EVICAN: 1 of 98 images is in it
   (`15_Caco-2.jpg`, GT 65.1%, predicted 0.0%). Mean signed error is
   **−8.32 pp** (systematic underestimate). Knock-on for A1: C2C12 series,
   already unlikely to reach 80% in ~85 h, will read lower still, so the
   higher targets may have few or no crossings. Report n per target, as A1
   says.
4. ~~§6.1 one-step-ahead expected value isn't built.~~ Built (see Phase A
   table).
5. **Replay default cadence doesn't fit C2C12.** `configs/replay.yaml` has
   `mean_interval_hours: 20`; on ~85 h sequences that's ≤ 4 visits, below the
   growth model's minimum of 5. A2 validates at 6 h and 12 h instead, passed
   per call (`mean_interval_hours=`, `jitter_hours=`) rather than by
   changing the config default.
6. **`cache_slim/` doesn't exist locally.** Phase A scripts read the slim
   cache; locally that is `cache/`. Scripts should take `--cache-dir`
   (e.g. `scripts/fov_noise.py` defaults to `cache_slim`).
7. **Bare `pytest` from the repo root fails at collection.**
   `deploy/hf-space/test_api.py` gets collected, and `deploy/hf-space/culture/`
   then shadows the real `culture/` package. Run `pytest tests`. (It was
   already like this before today; not fixed here.)
8. **Spec §0.3 names `app.py`;** the app is `demo/app.py`.
9. **`docs/DATASETS.md` still lists C2C12 as deferred.** It needs the
   CC BY 4.0 attribution entry once `nb/03` brings the data in.
10. **Dimmed frames at onset match the original frame byte for byte.** The
    lamp-dimming factor ramps from exactly 1.0, so each dimming sequence's
    first post-onset frame is identical to the original frame and is cached
    once, under the original sequence's `sequence_id`. Its manifest row still
    says `is_modified=True` (severity 1.0). Replay reads fault frames by hash
    from the manifest, so nothing breaks, but V7 should treat severity 1.0 as
    "not yet dimmed". **Fixed in `3d0c140`:** the onset row is now
    `is_modified=False`. The same happens for contamination if a frame gets 0
    sprites (only possible on very small test images).
11. **`qctile` is only the centre 256 px of each frame.** On a 1392x1040
    frame that is about 4.5% of the area. The confluency bin for A4 comes
    from the full frame, so a tile's local density can differ from its bin.
    Worth checking when V4's result comes in.

12. **`configs/noise.yaml` is measured almost entirely below 10%
    confluency.** It was fit on EVICAN/AutoQC-Bench crops whose predicted
    confluency has median 3.2% and 75th percentile 5.5%
    (`results/fov_noise.csv`). At 30–80%, where growth matters, the linear
    fit is extrapolated: for 0.25-frac crops σ_fov ≈ 0.27 + 1.06 × pct,
    i.e. about 40 pp at 37%. That affects the growth fit weights, the
    one-step obs_sd, and V2's denominator. **Re-measure σ_fov on C2C12
    frames** (8 cached crops per frame across the whole growth range) with
    `scripts/fov_noise.py` once `nb/03` is on the Mac, before A1/V2/A6.
    **Done:** measured on 2,088 C2C12 frames as the separate entry
    `entries.c2c12` (`results/fov_noise_c2c12_summary.md`); growth picks the
    entry by the visit's `source_dataset`. The top-level fit is unchanged.
13. **Calibration (A5) only covers replay.** The live app path
    (`culture/qc.py`) still reports raw softmax. Apply T there in Phase B.
14. **The quality gate rejects every real C2C12 frame.** On the held-out
    normal fleet (6 h, 1 FOV) 0/208 visits pass: uniformity above threshold
    208, exposure out of range 207, blur below floor 128.
    `configs/quality.yaml` was calibrated on synthetic tiles (exposure
    127.8–129.2, uniformity ≤ 2.23); visits of all 24 base sequences (6 h,
    1 FOV) sit at exposure 95–163 and uniformity 8.7–27.9. The QC
    classifier shows the same shift: 13/208 held-out normal visits (6%) are
    predicted `normal`. `fit_growth()` ignores the gate, so A1's backtest
    is unaffected, but `one_step_ahead_series()` and History's trend view
    skip failing visits, so the A6 growth residual has no C2C12 data until
    this is decided. **Decided 2026-09-26 (you: "proceed with a decision"):**
    per-dataset thresholds, following high-content-screening practice of
    calibrating QC per experiment/instrument. `configs/quality.yaml`
    `entries.c2c12` = percentiles 1/99 of the 10 tuning sequences' frames
    (`scripts/calibrate_quality_gate.py --entry c2c12`); replay picks it by
    `source_dataset`, the live app keeps the synthetic top level. Held-out
    normal frames fail 12.1% (in sample 4.2%), concentrated in 5 sequences,
    mostly from 090318, which has 1 tuning sequence. Held-out simulated
    faults: contamination 92%, lamp dimming 51% (70% at factor ≤ 0.7).
    `results/quality_gate_c2c12.md`. Held-out normal visits now pass 87%.
    Consequence for A6/A7: gate-failed visits get REIMAGE and leave the
    trend views, so contamination may surface mostly as REIMAGE rather than
    as an SPC alarm (V6), and dimming as per-flask gate failures, which V7
    says it shouldn't be. Anomaly scores (A4) are computed for every frame
    regardless of the gate.
    Also: at 12 h, fault streams have only 3–4 visits up to onset (fewer
    than the 5 a fit needs); at 6 h, 6–7.
15. **Fault-set bases and the fleet split collided.** `make_fault_set.py`
    picks its 8 contamination/stall bases as the first 8 of
    `rng(0).permutation` over the sorted ids; an unstratified
    `split_sequences(seed=0)` takes the first 10 of the same permutation
    for tuning, so every contamination and stall fault landed in tuning.
    The split is now stratified by fault type (your decision, 2026-09-26).
    Held-out still has only 2 of each, so V6 detection rates are n=2 per
    type. The held-out bases are also uneven across experiments (090303: 2,
    090318: 7, 090325: 5).

## Open questions for the human

Both were unanswered when `nb/03` started, so unless you stopped the run
the defaults hold: no shifted tiles (B3's shift test is scoped out) and
CLS-only for V5(a).

- Shifted tiles: fold into `nb/03`, or drop B3's shift test?
- `scripts/cache_tile_embeddings.py` only embeds the paths it's given (in
  `nb/03`, the C2C12 and fault frames). Synthetic-tile patch embeddings for
  V5(a) come from the Drive full cache (`nb/02` kept them for `normal` tiles
  only; V5(a) needs the anomaly classes too). Add synthetic test tiles to
  `nb/03`'s qctile step, or accept CLS-only for V5(a)?
