# cultureQC — upgrade status

Governing spec: `cultureQC_upgrade_spec.md` (v3.1). Checked against the repo on
branch `slice-1b-compute-cache`, starting from `e86ce93`, on 2026-09-25.
Nothing is merged to `main`.

## Slices (spec §2.1), confirmed against the repo

| Slice | Status | Evidence in repo | Notes |
|---|---|---|---|
| 0 Recon + baseline | Done | tag `v1.0-pre-upgrade`, `docs/REPO_MAP.md`, `results/baseline_latency.{csv,md}`, `tests/test_smoke_pipeline.py` | — |
| 1 Real-image confluency | Done, **V1 partly measured** | `results/confluency_real_summary.md`, `results/confluency_real.csv` | See "V1" below |
| 1b Compute cache | Done, **no sequences** | `cache/MANIFEST.json`: 4,246 images (4,000 `synth_tiles`, 148 `autoqc_bench_test`, 98 `evican_eval2019`); `configs/noise.yaml`, `results/fov_noise_summary.md` | 0 of 4,246 rows have `sequence_id` / `frame_idx` set |
| 2 Visit summary, history, quality gate, replay | Done | `schemas/visit_summary.v1.json`, `culture/{quality,history,replay}.py`, tests for each, Flask Timeline tab in `demo/app.py` | Replay tested on fixture sequences only; needs the fault-sequence adapter (A2) |
| 3 Growth model + T* + timeline | Done, **backtest synthetic only** | `culture/growth.py`, `tests/test_growth.py`, `results/growth_backtest.md`, `results/growth_examples.*`, `results/growth_runtime.txt` | Backtest is a harness check; don't quote it until A1 reruns it on real sequences. Missing one §6.1 item, see below |
| 4, 4b, 5, 5b, 6, 7, 8 | Not started | — | Minimal versions in Phase A |

Tests: `pytest tests` → 56 passed, 1 xfailed (2026-09-25, after A0.2).

## Phase A progress

| Step | Status |
|---|---|
| A0.1 This file | Done |
| A0.2 `Cache.build()` flush fix | Done: flushes all tables every `flush_every` records (default 100) and at the end; `tests/test_cache_resume.py` (kill mid-build → flushed rows on disk → rerun computes only the rest, no duplicates, same result as an uninterrupted build). Checked that the key test fails with periodic flushing disabled. |
| A0.3 Commit the `nb/03` files | Done in `544861c` (the files arrived in `files/`); `PINNED_SHA = '544861c'` in `nb/03`. Read against the repo: git remote, `requirements.txt`, `download_sources.py` / `extract_sprites.py` arguments, `synth_contamination.add_bacteria` / `get_cell_mask` / `SEVERITY_RANGES`, `Cache.build()` and `replay._sequence_frames` all match. Ran locally at `544861c` on fake 12-bit sequences: fetch (mid-grey 8-bit PNGs, conditions parsed from folder names, 85 hourly frames / 84 h) → fault set (all three types) → `Cache.build()` (quality only) → replay on a cached sequence, with no unset `frame_idx`. Not testable here: OSF API calls and GPU inference (the notebook's checkpoints 1–3 cover those). |
| A0.5 `nb/03` Colab run | **Ready for you to run** (Colab, GPU). Three checkpoints: OSF layout, sample frames, budget test |
| A1–A8 | Not started. A1, A2's fleet, A4, A6, A7 and V2 need `nb/03` output. Work that can start without it: A2's adapter (fixture test), A5 calibration (cached val logits exist), A8 latency, the §6.1 one-step-ahead prediction |

## Schedule

The spec's target review date (Sat Sep 26) **can't be met**. Phase A's timebox
is "2 working days after `nb/03` completes", and `nb/03` hasn't run yet. The
date that actually binds is the **code freeze on Sun Oct 4**. Each day
`nb/03` slips comes out of Phase B.

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
4. **§6.1 one-step-ahead expected value isn't built.** `culture/growth.py`
   has no per-visit prediction + predictive SD from prior visits. A6's growth
   residual needs it. Small addition to `growth.py`, no rewrite.
5. **Replay default cadence doesn't fit C2C12.** `configs/replay.yaml` has
   `mean_interval_hours: 20`; on ~85 h sequences that's ≤ 4 visits, below the
   growth model's minimum of 5. A2 validates at 6 h and 12 h instead, passed
   per run rather than by changing the config default.
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
    "not yet dimmed". The same happens for contamination if a frame gets 0
    sprites (only possible on very small test images).
11. **`qctile` is only the centre 256 px of each frame.** On a 1392x1040
    frame that is about 4.5% of the area. The confluency bin for A4 comes
    from the full frame, so a tile's local density can differ from its bin.
    Worth checking when V4's result comes in.

## Open questions for the human

- Shifted tiles: fold into `nb/03`, or drop B3's shift test?
- `scripts/cache_tile_embeddings.py` only embeds the paths it's given (in
  `nb/03`, the C2C12 and fault frames). Synthetic-tile patch embeddings for
  V5(a) come from the Drive full cache (`nb/02` kept them for `normal` tiles
  only; V5(a) needs the anomaly classes too). Add synthetic test tiles to
  `nb/03`'s qctile step, or accept CLS-only for V5(a)?
