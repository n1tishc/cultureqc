# Handoff — nb/03 (real sequences + Phase A fault set)

## Files to commit (branch `slice-1b-compute-cache`)
| File | Purpose |
|---|---|
| `nb/03_cache_additions.ipynb` | Colab runner: C2C12 fetch → fault set → one chunked GPU pass into the existing Drive cache → qctile embeddings → sidecars + slim export → replay smoke test |
| `scripts/fetch_c2c12.py` | OSF discovery (`discover`) + selective hourly-frame download and fixed 8-bit conversion (`fetch`, or `--local-src`) |
| `scripts/make_fault_set.py` | A3 fault set: contamination onset (reuses `synth_contamination.add_bacteria`), growth stall (metadata only), lamp dimming (raw-space) |
| `scripts/cache_tile_embeddings.py` | DINOv2 on the 256 px QC tile, stored as `crop_spec="qctile"` using the cache's existing conventions |

Then set `PINNED_SHA` in the notebook's clone cell to that commit.

## Why this was needed
The Slice 1b cache has **no time-lapse sequences** (C2C12 skipped, CTC blocked on permission). Replay and the
Slice 3 backtest therefore only ran on synthetic curves (`results/growth_backtest.md`). Phase A can't
validate anything temporal until real sequences are cached with `sequence_id`, `frame_idx`, `timestamp` set.

## Contracts produced (all under `cache/sidecars/` and `cache_slim/sidecars/`)
- `c2c12_sequences.csv` — one row per sequence: experiment, condition (`unknown` if folder names don't say), frames kept, span.
- `c2c12_frames.csv` — one row per cached frame incl. `hours_since_start`.
- `c2c12_normalization.json` — the single global map used for every C2C12 + fault frame (raw 0 → 0, raw p99.5 → 255).
- `fault_manifest.parquet` — the full composed timeline of each fault sequence: `fault_sequence_id, base_sequence_id,
  fault_type, onset_hours, frame_idx, timestamp, hours_since_start, image_sha256, is_modified, severity, provenance`.
  Pre-onset rows point at the original frame's sha; growth-stall rows point at dilated source frames.
- `fault_frames.csv`, `fault_config.json` — what was generated and with which parameters/sequences.

## Work needed in Phase A (small)
1. **A2 replay adapter.** `culture/replay.py::_sequence_frames` looks frames up by `sequence_id` in `images.parquet`,
   which holds one `sequence_id` per sha. Fault sequences share their pre-onset frames with the original sequence,
   so add an optional frames-table input (e.g. `build_replay_visits(..., frames=<fault_manifest rows>)`) instead of
   only `sequence_id`. Everything downstream (crops, logits, quality by sha) already works per sha.
2. **A4 uses `crop_spec="qctile"` embeddings** for C2C12/fault frames. Full-frame embeddings are a ~4–5x downscale
   on 1392x1040 frames: 2–5 px sprites vanish and scale no longer matches the 256 px synthetic-tile bank.
3. **Rerun `scripts/backtest_growth.py` on real sequences** and replace the synthetic-only table.
4. **Credit C2C12 (CC BY 4.0)**: Ker et al., Sci Data 5:180237 (2018), doi:10.1038/sdata.2018.237, OSF ysaq2.

## Issues found in existing code (not fixed here — worth fixing)
- **`Cache.build()` only flushes parquet tables at the end of a call.** A disconnect mid-call loses every table row
  from that call (probmaps/embeddings survive as files). The module docstring claims worst case is "one shard".
  nb/03 works around it by calling `build()` in chunks of 100; the proper fix is periodic flushing inside `build()`.
- **16-bit input trap.** `Cache.build()` reads with `cv2.IMREAD_GRAYSCALE`; a 16-bit TIFF holding 12-bit data comes out
  max ~10 (near black). `fetch_c2c12.py` converts to 8-bit first; any future 16-bit dataset needs the same.
- **Replay reads the whole confluency/logits/quality tables per visit** (`_sample_crops_for_frame` etc.). Fine at
  current size; cache the loaded tables once per stream if Phase A replays many fleets.

## Tested here (CPU sandbox, synthetic stand-in data, real repo code at e86ce93)
- fetch: condition parsed from the sequence folder only (experiment folder names list both factors); hourly selection;
  PNGs mid-grey via `IMREAD_GRAYSCALE` (raw 16-bit via the same call: max 10).
- faults: byte-identical output across runs and `PYTHONHASHSEED` values; pre-onset rows resolve to real cached frames;
  modified frames only after onset; dimmed 8-bit mean ratio equals the lamp factor exactly; contamination changes the frame.
- cache: `Cache.build()` (quality model) accepted all records, zero unset `frame_idx`/`timestamp`, chunked reruns add
  no duplicate rows; `replay._sequence_frames` accepts the new sequences, ordered.
- qctile: 256 px input to the embedder, resumable, readable via `load_embeddings(sha, crop_spec="qctile")`.
- **Not tested here:** OSF API calls (no network access to osf.io from the sandbox), Cellpose/QC/DINOv2 inference
  (no GPU / HF access). The notebook's checkpoints 1–3 exist to catch problems in exactly those steps.
