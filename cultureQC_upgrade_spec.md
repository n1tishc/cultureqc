# cultureQC — Upgrade Spec v3.1 (Two Phases: Validate, then Productize) for Coding Agent

**Owner:** Nitish · **Code freeze:** Sun Oct 4, 2026 · **Demo (Teams, screen share):** Tue Oct 6, 2026, 3 PM PDT
**Audience:** a Celltrio engineer / cell-culture expert. Every claim must survive expert scrutiny.
**v3 change:** work is split into **Phase A — Architecture validation** (timeboxed, scripts + modules, no product polish, ends in a go/no-go review) and **Phase B — Productization** (the remaining slices, adjusted by Phase A findings).
**Current status (verified against branch `slice-1b-compute-cache` @ `e86ce93`, 2026-09-23):** Slices 0, 1, 1b, 2 and 3 are committed (incl. the Flask Timeline tab). **Gap:** the cache holds no time-lapse sequences, so replay and the Slice 3 backtest have only run on synthetic curves. Phase A starts by closing that gap with `nb/03`.
**v3.1 change:** Phase A rewritten around real C2C12 sequences + fault set (`nb/03_cache_additions.ipynb`), tile-level DINOv2 embeddings (`crop_spec="qctile"`), a replay adapter for fault sequences, and cadences that fit ~85 h sequences.
**v2.1 change (still applies):** all expensive GPU inference runs **once** in a compute-cache pass (Slice 1b); later work runs on the cache, on CPU.
**Supersedes:** v1 of this spec. Main changes: per-visit → per-flask temporal architecture, measurement-noise handling, density-conditioned anomaly scoring, SPC monitoring on residuals, lineage-aware history, reworded audit claims.

---

## 0. Read this first

### 0.1 What cultureQC is today
Vendor-neutral brightfield/phase-contrast QC for adherent culture (T-flask images). Per image it returns:
1. **Confluency %** — Cellpose-SAM (`cpsam_v2`) probability map. ~2.34 pp MAE vs ~31 pp classical — **synthetic only**.
2. **QC class** — EfficientNet-B0, 4 classes (normal / contamination / detachment / image-quality) + Grad-CAM multi-box evidence. 98% test accuracy — **synthetic only**.
3. **Rationale** — deterministic templates (VLM rejected: Qwen3-VL-8B zero-shot ~29%).
4. **Audit record** — hash-chained, Part 11-oriented.
Demo: Gradio on Hugging Face Spaces (`LongGrainRice/cultureqc-demo`).

### 0.2 How the target instrument actually works (design driver)
Celltrio's RoboCell keeps flasks in an incubator (Robo-I). A gantry robot brings a flask to the Robo-LH liquid handler, which houses a **brightfield confluency microscope**; the flask is imaged, handled (feed / passage / harvest), and returned. Their BioFlow software already logs **time-stamped images and audit trails** (Part 11) and works with Green Button Go / Momentum schedulers.

Consequences for this design:
- Data arrives as **discrete visits per flask**, at **irregular intervals** — not video, not real-time.
- The flask is repositioned every visit → **field of view differs between visits** → never compare pixels across visits; compare per-visit *summaries*.
- Passaging **resets** confluency and usually creates new flasks → history must be **lineage-aware**.
- BioFlow already has image storage + audit trails → cultureQC is an **analysis layer on their data**, not a replacement for their compliance system.

Unknowns (make them config parameters, do not hard-code): imaging cadence, FOVs per visit, image size/format/bit depth, flask ID scheme, how passage decisions are made today.

### 0.3 Known repo facts and gotchas
- Package folder `culture/` (underscore). `app.py` needs `PYTHONPATH=.` or a `sys.path` fix.
- Tiles are flat: `data/tiles/{class}/{tile_id}.png`; splits via `split` column in `data/tiles/manifest.csv` (no `test/` folder).
- Training sources: LIVECell + DeepBacs (Zenodo 5550935) + synthetic artifact generation.
- 60-epoch Cellpose-SAM fine-tune gave flat loss → **LIVECell likely in Cellpose-SAM pretraining** (matters for held-out eval).
- COCO `file_name` needs `os.path.basename()`. PyPI package is `grad-cam`.
- Colab A100 for GPU work (remount Drive after runtime restart). Mac for local dev (`curl -L`).
- Negative results are first-class outputs.
- Working branch: `slice-1b-compute-cache`. Cache on Drive at `MyDrive/cultureqc/cache` (+ `cache_slim`), built by `nb/02`.
- **16-bit trap:** `Cache.build()` reads images with `cv2.IMREAD_GRAYSCALE`; 16-bit TIFFs holding 12-bit data come out near-black. Convert to 8-bit with one fixed per-dataset map first (`scripts/fetch_c2c12.py` does this for C2C12).
- **Flush bug:** `Cache.build()` flushes parquet tables only at the end of a call — a Colab disconnect loses all table rows from that call. Call it in chunks until fixed (A0).
- **Full-frame DINOv2 is a ~4–5x downscale** on 1392x1040 frames (processor resizes to 224). Use `crop_spec="qctile"` embeddings (256 px QC tile, native resolution) for anomaly work on large frames.

### 0.4 Rules for the agent
1. **Start with Slice 0.** Write `docs/REPO_MAP.md` before changing anything.
2. **Vertical slices.** Each slice ends runnable in the Gradio app with a README update. Never leave the app broken. One branch per slice; merge only when acceptance passes.
3. **Never invent numbers.** Every metric comes from a script/notebook in the repo, with dataset + split named.
4. **Label provenance:** every metric tagged `synthetic`, `simulated`, or `real (<dataset>)`.
5. **⏸ Checkpoints:** stop, show numbers + 5–10 visual examples, wait for the human.
6. **Verify dataset licenses and Cellpose-SAM training overlap**; record in `docs/DATASETS.md`.
7. **Pin dependencies.** Must run on CPU in the HF Space; GPU paths are Colab-only.
8. **Deterministic:** fixed seeds, versioned configs, no generative text in any QC output.
9. **Forbidden claims** (§12) enforced by a unit test.
10. **No new GPU passes after Slice 1b** unless a slice explicitly says so (only: live app inference, site-calibration mode, conditional 4b retrain). Evaluation, replay, fitting, and tuning read from the cache.

---

## 1. Target architecture

```
RoboCell visit ──► [Per-visit analysis — stateless]
(image(s), flask ID,     Cellpose-SAM → confluency per FOV
 timestamp)              EfficientNet-B0 (temperature-scaled) → class probs + Grad-CAM
                         DINOv2 + kNN (density-conditioned) → anomaly score + heatmap
                              │
                              ▼
                     [Quality gate] ── fail ──► REIMAGE (immediate)
                              │ pass
                              ▼
                     [Visit summary]  numbers only, model versions stamped
                              │                         │
                              │                  immediate flags (contamination, OOD)
                              ▼                         │
                     [Per-flask history]  lineage → segments → visits + events
                              │                         │
                              ▼                         │
                     [Temporal engine]                  │
                       expected-value layer             │
                       growth model per segment         │
                       SPC monitors on residuals        │
                       instrument-drift monitor         │
                       risk flags (+ detectability)     │
                              │                         │
                              ▼                         ▼
                     [Decision engine]  deterministic truth table
                              │
               ┌──────────────┴──────────────┐
               ▼                             ▼
   Analysis record (hash-chained,     Decision event (JSON) for
   designed to attach to BioFlow      BioFlow / scheduler
   audit trail)                       → next visit
```

Design invariants:
- **Per-visit models never see history.** Stateless, independently testable.
- **History stores numbers, never pixels.** Images live in BioFlow (or local storage in the demo).
- **Temporal logic runs on residuals from an expected value**, never on raw growing series.
- **Trends are only computed within one model-version set.**

---

## 2. Plan — two phases

### 2.1 Status of previously specified slices (verified in repo)
| Slice | Status | Notes |
|---|---|---|
| 0 Repo recon + baseline freeze | Done | `docs/REPO_MAP.md`, `results/baseline_latency.*` |
| 1 Real-image confluency validation | Done | EVICAN; `results/confluency_real_summary.md` (V1 input) |
| 1b Compute cache | Done — **no sequences** | synthetic tiles, EVICAN, AutoQC-Bench `test/`; FOV noise → `configs/noise.yaml` (V2 input) |
| 2 Visit summary, history, quality gate, replay | Done | replay tested on fixtures only; needs fault-sequence adapter (A2) |
| 3 Growth model + T* + timeline tab | Done — **backtest synthetic only** | `results/growth_backtest.md` must not be quoted until A1 reruns it on real sequences |
| 4, 4b, 5, 5b, 6, 7, 8 | Not started | minimal versions in Phase A; full versions in Phase B |

Do **not** redo completed slices. Patch them only where Phase A needs a hook, and log each patch in `docs/STATUS.md`.

**Datasets:** Cell Tracking Challenge stays **out** (organizers' permission required — see `docs/DATASETS.md`). Real time-lapse = **C2C12** (Ker et al., Sci Data 2018, OSF `ysaq2`, **CC BY 4.0** — attribution required).

### 2.2 Phase A — Architecture validation (timeboxed)
**Goal:** prove, with numbers on real sequences, that the temporal architecture separates signal from measurement noise and fires on faults without crying wolf — **before** building product surface around it.
**Timebox:** 2 working days after `nb/03` completes. **Target review: Sat Sep 26.** If time runs out, write the report with what's measured and mark the rest "not measured".
**Rules:** minimal implementations as real modules in `culture/` with basic tests (Phase B hardens, never rewrites). **No** new app tabs, schemas, decision events, or audit work. All numbers from `scripts/validate_architecture.py` on the cache (CPU). The only GPU work is `nb/03` (one run).

### 2.3 Phase B — Productization
**Goal:** turn validated components into the demo: app, schemas, decision engine, events, records, docs.
**Window:** after the Phase A review → **code freeze Sun Oct 4**.
**Rule:** each Phase B slice starts by reading `docs/ARCHITECTURE_VALIDATION.md` and applying the design changes mapped to any failed criterion (§2A.9).

| # | Phase B slice | Builds on | Priority |
|---|---|---|---|
| B1 | Timeline tab on **real** C2C12 replays: normal + fault scenarios selectable, labelled "Replay of recorded time-lapse (simulated visits)", C2C12 credited | A1, A2 | Must |
| B2 | Slice 4 full: density-conditioned anomaly (qctile) in the live app, heatmaps, site-calibration mode, AutoQC-Bench eval | A4 | Must |
| B3 | Slice 4b: calibration in the live path; domain-shift test (+ conditional retrain) | A5 | Must (calibration) / Should (shift) |
| B4 | Slice 5 full: SPC in the app, risk flags, detectability matrix, mycoplasma wording + forbidden-phrase test | A6 | Must |
| B5 | Slice 5b full: instrument-drift monitor in the app with suppression | A7 | Should |
| B6 | Slice 6: decision engine, decision events, analysis records | B1–B5 | Should |
| B7 | Slice 7: tamper verifier | B6 | Could |
| B8 | Slice 8: docs, claims, demo script (**Phase A report as a README section**) | all | Must |
| S | Stretch | — | Could |

**Cut order:** S → B7 → B5 → B3 shift/retrain part → B6.
**Core that must ship:** Phase A report, B1, B2 (AutoQC-Bench optional), B3 calibration, B4, B8.

---

## 2A. Phase A — Architecture validation (detail)

### 2A.0 A0 — Status + two small fixes (≤ 3 h)
1. Write `docs/STATUS.md` from §2.1 (confirm against the repo; note any drift).
2. **Fix `Cache.build()` flushing:** flush all tables every N records (config, e.g. 100) and at the end, not only at the end. Add a test: kill mid-build (simulate with an exception after N+k records) → rerun → no lost rows, no duplicates. Update the module docstring's resumability claim to match.
3. Commit `scripts/fetch_c2c12.py`, `scripts/make_fault_set.py`, `scripts/cache_tile_embeddings.py`, `nb/03_cache_additions.ipynb` (provided); set `PINNED_SHA` in `nb/03`.
⏸ Share `STATUS.md`.

### 2A.1 A0.5 — `nb/03` run (human runs it on Colab; the one GPU run)
Adds to the existing Drive cache: ~24 C2C12 sequences at hourly frames (real `sequence_id`/`frame_idx`/`timestamp`), the A3 fault set (contamination onset ×4 sequences, growth stall ×4 — metadata only, lamp dimming × all sequences), and `qctile` embeddings for all of them. Sidecars land in `cache/sidecars/` and `cache_slim/sidecars/`: `c2c12_sequences.csv`, `c2c12_frames.csv`, `c2c12_normalization.json`, `fault_manifest.parquet`, `fault_frames.csv`, `fault_config.json`. Patch embeddings for these frames: `staged/c2c12_patch_embeddings.zip` (unzip into the Mac cache's `embeddings/`).
The notebook has three human checkpoints (OSF layout, sample frames, budget test). If OSF packages the data as archives, it has a fallback path; see `HANDOFF_nb03.md`.

### 2A.2 A1 — Growth backtest on real sequences
Rerun `scripts/backtest_growth.py` on replayed C2C12 streams (normal fleet, held-out split). C2C12 sequences span ~85 h and may not reach 80% confluency, so:
- targets: evaluate each of {50, 60, 70, 80}% **only on sequences whose observed series actually crosses it**; report n per target.
- cut points: fit on visits until observed confluency first reaches `target − 20` / `target − 10` points.
- report median abs error (h) and 90% interval coverage, with and without simulated repositioning, per cadence (§2A.3).
Replace `results/growth_backtest.md`. Keep the known model-selection-uncertainty caveat if coverage is still low (and see V3's fix).

### 2A.3 A2 — Replay fleet + fault-sequence adapter
- **Adapter:** `build_replay_visits(..., frames=None)` — when a frames table is given (rows of `fault_manifest.parquet` for one `fault_sequence_id`), replay from it instead of looking up `images.parquet` by `sequence_id`. Everything downstream is per-sha and unchanged. Unit test with a fixture manifest.
- **Performance:** load confluency/logits/quality tables once per stream (not per visit).
- **Fleet:** normal fleet = all C2C12 sequences; fault fleet = fault sequences from the manifest. Seeded split by **sequence** into tuning (≈40%) and held-out (≈60%). Never report on tuning.
- **Cadences:** sequences are ~85 h, so a 20 h mean gives ≤ 4 visits (below the growth model's minimum). Validate at **mean 6 h and 12 h** (jitter ±25%). Report 24 h as "not testable on C2C12 span" — an open question for Celltrio's real cadence.
- **FOVs per visit:** 1 and 3.

### 2A.4 A3 — Fault set
Produced by `nb/03` (see A0.5). Onsets are recorded in the manifest (`onset_hours`) for detection-delay measurement. All fault rows are `provenance="simulated"`.

### 2A.5 A4 — Minimal density-conditioned anomaly (qctile)
- Embeddings: `crop_spec="qctile"` for C2C12/fault frames; `full` for synthetic 256 px tiles (same scale).
- Banks per confluency bin (bin from cached confluency), from **normal** frames of the **tuning** fleet (site-calibration style) — optionally plus synthetic normal tiles; report which. Per-bin mean/SD of normal scores; per-bin threshold at 5% FPR on tuning normals.
- Also build one **global** bank (no bins) for the V4 comparison.
- Patch-kNN image score (max or top-k mean of patch NN distances); residual `z = (score − bin_mean) / bin_sd`.

### 2A.6 A5 — Minimal calibration
Temperature scaling on cached val logits (synthetic tiles); ECE before/after.

### 2A.7 A6 — Minimal SPC
EWMA (λ = 0.2, L = 2.86 to start) + one-sided tabular CUSUM on: growth residual (A1's one-step-ahead expected value + predictive SD), anomaly residual (A4), failure-class residual (A5). Reset at segment boundaries. Tune λ/L only on the tuning fleet.

### 2A.8 A7 — Minimal instrument-drift monitor
Align fleet sequences on **hours since sequence start** (the three C2C12 experiments ran on different dates; the dimming fault is defined on that relative clock). Population EWMA on the median anomaly residual + quality metrics (exposure) across active flasks per time window; raise `INSTRUMENT_DRIFT` and mark per-flask anomaly flags in that window as suppressed.

### 2A.9 A8 — Latency
Live per-visit path (Cellpose-SAM + classifier + DINOv2 qctile kNN + quality gate) on a CPU runtime comparable to the HF Space. Per model.

### 2A.10 Go/no-go criteria
Thresholds are **provisional starting points** — report actual values regardless; never tune on the held-out fleet.

| ID | Question | Metric | Pass | If it fails → Phase B design change |
|---|---|---|---|---|
| V1 | Is confluency good enough on real images? | Held-out EVICAN MAE (Slice 1), incl. 60–90% band | ≤ 10 pp overall (≤ 5 = strong) | > 10 pp: stop; confluency work replaces Phase B scope (human decision) |
| V2 | Does growth between visits beat FOV noise? | Median per-visit confluency increment (30–70% range, C2C12) ÷ σ_fov, per cadence (6 h, 12 h) and FOV count | ≥ 2 at 1 FOV | Pass only at ≥ k FOVs → require k FOVs per visit (config default + README + Celltrio question). Fails at 3 FOVs → growth-deviation flags only at the longer cadence |
| V3 | Is passage prediction useful and honest? | A1: median abs T* error at the `target − 10` cut; 90% coverage | Error ≤ 12 h; coverage 80–95% | Under-coverage → add model-selection uncertainty (bootstrap over both models / AIC weights) or inflate SD; high error → show T* only after the later cut |
| V4 | Does density conditioning remove the growth confound? | Spearman ρ(anomaly score, confluency) on held-out normal C2C12 frames: binned vs global | Binned \|ρ\| ≤ 0.3 and clearly below global | Drop anomaly *trend* monitoring; keep per-visit OOD flag only |
| V5 | Does the per-visit anomaly score separate faults? | AUROC (a) synthetic test: normal vs each class; (b) C2C12: held-out normal frames vs contamination-fault frames by severity | (a) ≥ 0.85 per class; (b) ≥ 0.85 at severity ≥ 150 sprites/tile-area | Weak classes/severities listed as limitations; classifier stays primary for them |
| V6 | Does SPC catch faults without alarm fatigue? | Held-out fleet: false alarms per 100 flask-visits (normal); detection rate + median delay (visits after onset) for contamination and growth-stall faults | ≤ 1 per 100; detection ≥ 90%; median delay ≤ 3 visits | Too many alarms → raise L / require CUSUM+EWMA agreement; too slow → lower λ; report the trade-off curve |
| V7 | Can it tell instrument from culture? | Lamp-dimming fleet vs single-flask faults | Dimming → `INSTRUMENT_DRIFT`, not per-flask flags; single-flask faults still flagged | Monitor informational only; README limitation |
| V8 | Are trended probabilities calibrated? | ECE on val after temperature scaling | ≤ 0.05 | Trend only anomaly + growth residuals; drop class-residual SPC |
| V9 | Does the live path fit the Space? | CPU seconds per visit | ≤ 5 s (config) | ViT-S / fewer crops / smaller input; or precompute demo examples and say so |
| V10 | Sanity: do media conditions produce distinguishable growth? | Fitted rates per condition (if conditions resolved; else per experiment) | Informational | — |

### 2A.11 Deliverable — `docs/ARCHITECTURE_VALIDATION.md`
One section per criterion: setup, number, pass/fail, plot, and the Phase B design change triggered. Summary table first. A **"What this does and doesn't prove"** section: logic validated on real C2C12 phase-contrast sequences with simulated visits, repositioning and faults — not on RoboCell images; one cell line, one microscope, ~85 h span; cadence and FOVs per visit are assumptions to confirm with Celltrio. Credit C2C12 (CC BY 4.0).
Required plots: V2 increment-vs-noise; V3 predicted vs actual crossing; V4 score-vs-confluency (global vs binned); V5 AUROC by severity; V6 example EWMA charts (one normal, one contaminated, one stalled flask) + alarm/delay trade-off; V7 fleet view during dimming.

⏸ **Phase A review (human):** read the report, confirm design changes, then start Phase B.

---

## 3. Slice 0 — Repo recon and baseline freeze *(DONE — reference only)*
1. Tag `v1.0-pre-upgrade`; confirm the HF Space runs from it.
2. `docs/REPO_MAP.md`: modules, entry points, where each model / Grad-CAM / templates / audit live, weight locations, app wiring, dependency versions. Note whether confluency runs per tile or per image, how Grad-CAM boxes are thresholded, and audit record fields.
3. Record CPU latency per image for the full pipeline (latency budget baseline).
4. `pytest` smoke test: full single-image pipeline on a fixture image.

**Acceptance:** tag, working Space, REPO_MAP, green smoke test, baseline latency.
⏸ Share REPO_MAP + latency.

---

## 4. Slice 1 — Real-image confluency validation + FOV noise floor *(DONE — reference; numbers feed V1/V2)*

### 4.1 Datasets (verify license + Cellpose-SAM overlap for each)
| Dataset | Modality | Masks | Use |
|---|---|---|---|
| EVICAN | BF + PhC, ~30 lines | COCO + binary, partial | Primary held-out eval |
| Cell Tracking Challenge | PhC, DIC | Seg GT on subset | **Not used** — scientific use outside CTC needs organizers' permission. |
| C2C12 time-lapse (Sci Data 2018, OSF ysaq2, CC BY 4.0) | PhC, 16-bit/12-bit | Tracking GT | Phase A sequences via `nb/03` (hourly frames, fixed 8-bit map) |
| BriFiSeg | BF | Yes | Optional |

Do not use LIVECell (likely in pretraining) or DeepBacs as held-out.

### 4.2 Evaluation
- GT confluency = union of GT masks / image area. For partially annotated images, restrict to fully annotated images/regions; document the rule.
- Methods: cultureQC (no retuning on eval sets), global-threshold baseline, fairer local-contrast + halo-correction baseline (Jaccard et al., PMC4260842; tune on a small tuning split, then freeze).
- Report MAE, median AE, and **MAE within the 60–90% GT band** per dataset per method, with n.

### 4.3 FOV noise floor (new, needed by Slices 2–5)
**Computed right after Slice 1b from cached crop confluency — do not run a separate GPU pass for it.** Report it under Slice 1 in the README.

Simulate repositioning: for real images at several densities, sample K random sub-crops (K ≥ 20) at a crop size representing one FOV (configurable fractions of the image, e.g., 25%, 50%) and compute confluency per crop. Report **SD of confluency across crops as a function of mean confluency and crop size**. Fit a simple noise model `sigma_fov(confluency, crop_frac)` and save it to `configs/noise.yaml`. This is the measurement noise the temporal layer must exceed before flagging.

### 4.4 Outputs
- `scripts/eval_confluency_real.py` → `results/confluency_real.csv`, `results/confluency_real_summary.md`
- `scripts/fov_noise.py` → `results/fov_noise.csv`, plot, `configs/noise.yaml`
- Scatter plots, overlay gallery (best / median / worst).
- App: "Real images" example row with GT shown.
- README: "Validation on real images" + "Measurement noise" sections.

### 4.5 Decision rule
MAE ≲ 5 pp → proceed. 5–10 pp → proceed + error analysis. > 10 pp → **stop and report** (do not start Slice 1b — the cache would be built on a model we may change).

Keep Slice 1 small: full-frame confluency on the held-out eval images only. It's the gate, not the bulk compute.

⏸ Summary table, worst-case overlays. (FOV-noise plot follows after 1b.)

---

## 4A. Slice 1b — Compute cache (one batched GPU pass) *(DONE; sequences + faults + qctile added by `nb/03` in A0.5; flush fix in A0)*

**Goal:** run every expensive model over every image the project needs, **once**, and store **raw outputs** so later changes (thresholds, calibration, binning, crop choices) never force a recompute.

### 4A.1 What goes in
| Image set | Why |
|---|---|
| Synthetic tiles (train/val/test) | Anomaly banks, calibration, per-class AUROC |
| Shifted synthetic tiles (EVICAN + C2C12 backgrounds, see §8.2) | Domain-shift test — **generate them before this pass** using the existing artifact generators, so no second pass is needed |
| EVICAN (+ BriFiSeg if used) | Held-out eval, bank calibration on real normals |
| C2C12 sequences | Replay, growth backtest, density-confound check, SPC eval |
| AutoQC-Bench | External anomaly benchmark |

For time-lapse sequences, cache frames at a fine enough interval to support jittered replay (config; start: every 30 min). Not every 5-min frame.

### 4A.2 What gets computed (raw outputs, not derived values)
| Output | Stored as | Why raw |
|---|---|---|
| Cellpose-SAM **cell-probability map**, downsampled (config, e.g., 1/4 res, uint8) | compressed `.npz` shards | Confluency thresholds can change without recompute |
| Confluency at the current default threshold | Parquet | Convenience; recomputable from the map |
| Confluency on **deterministic random crops** at crop fractions {0.25, 0.5} (K per frame, config; start K = 8) | Parquet (crop spec = frac + seed + offsets) | FOV-noise model and repositioning replay use these |
| EfficientNet-B0 **logits** (not probabilities), on the same inputs the app uses (check REPO_MAP for tile/whole-image handling) | Parquet | Temperature scaling never forces a recompute |
| DINOv2 **patch embeddings + CLS** (ViT-S/14, float16; ViT-B/14 only for the subset used in the backbone comparison) | `.npy` shards | Anomaly banks, bins, thresholds, and scores all derive from these |
| Quality metrics (blur, exposure, uniformity) | Parquet | Cheap; lets the quality gate be tuned offline |

Every row is keyed by **(image_sha256, crop_spec, model_name, model_version)**. An `images` table records dataset, source path, sequence id, frame index, timestamp, shape, bit depth, and the normalization applied.

### 4A.3 Engineering requirements
- `culture/cache.py`: `build(...)`, `load_confluency(...)`, `load_logits(...)`, `load_embeddings(...)`, `load_quality(...)`. Everything downstream reads through this API.
- **Resumable + idempotent:** process in shards, skip keys that already exist, write each shard atomically. Colab will disconnect; a rerun must pick up where it stopped.
- **Budget first:** run on 100 images, report per-image time for each model and projected total runtime + storage. ⏸ **Wait for approval before the full run.**
- **Storage:** patch embeddings dominate (ViT-S/14 at 224 px ≈ 256 × 384 float16 ≈ 0.2 MB/image). Keep full patch embeddings only where needed (bank-source normals, eval sets, replay frames); store CLS-only elsewhere. Provide `export_slim(...)`, a Mac-sized copy with no patch embeddings except the replay/eval subsets.
- **Manifest:** `cache/MANIFEST.json` with row counts, model versions + weight hashes, config hashes, and SHA-256 per shard.
- **Invalidation:** if a model changes (e.g., 4b retrain), only that model's columns are recomputed. Old rows stay, keyed by old version.
- **Normalization parity:** the cache must use exactly the same preprocessing as the live app path. Add a test: for 10 images, live pipeline output == cache output (within float tolerance).

### 4A.4 Acceptance
- Full cache built; manifest complete; parity test green.
- FOV-noise analysis (§4.3) produced from cached crops.
- A local (Mac) run of `load_*` on the slim export works without a GPU.

⏸ Report runtime, storage, row counts, and the FOV-noise plot.

---

## 5. Slice 2 — Visit summary, per-flask history, quality gate, replay mode *(DONE — fault-sequence adapter in A2)*

### 5.1 Visit summary (`schemas/visit_summary.v1.json`)
Numbers only. Required fields:
- `visit_id`, `lineage_id`, `segment_id`, `flask_id`, `timestamp` (UTC), `image_sha256[]` (one per FOV)
- `fov_confluency[]`, `confluency_mean`, `confluency_sd`, `n_fov`
- `class_probs` (calibrated, from Slice 4b; until then mark `calibrated: false`), `class_pred`
- `anomaly_score`, `anomaly_score_density_bin` (Slice 4; null until then)
- `quality`: blur metric, mean intensity, intensity uniformity, pass/fail + reasons
- `model_versions`: name + weights SHA-256 for every model; `config_hashes`

### 5.2 Quality gate (`culture/quality.py`)
Deterministic checks before a visit enters history: focus/blur (e.g., variance of Laplacian), exposure (mean/percentile intensity), illumination uniformity. Thresholds in `configs/quality.yaml`, calibrated on normal tiles. Failing visits are recorded with reason codes and produce an immediate `REIMAGE` decision; they **do not** enter trend computations.

### 5.3 Per-flask history (`culture/history.py`)
- Structure: **lineage → segments → visits**, plus an **events** table (`SEEDED` with seeding density, `FED`, `PASSAGED` with split ratio + child segment IDs, `HARVESTED`, `NOTE`). Passage number and cell line stored per segment.
- Storage: SQLite (or JSONL) — **append-only**; each row hash-chained to the previous row of the same lineage. Corrections are new rows referencing the corrected one, never edits.
- API: `append_visit`, `append_event`, `get_segment(segment_id)`, `get_lineage(lineage_id)`.
- Trend functions must refuse to mix visits with different `model_versions`; return `MODEL_VERSION_CHANGE` and start a new trend window (or recompute from stored images if available).

### 5.4 Replay mode (demo + test harness)
Builds realistic visit streams from C2C12 sequences (and, via the A2 adapter, fault sequences from `fault_manifest.parquet`) **entirely from the compute cache — no model inference at replay time**, so replay runs on CPU in seconds:
- **Irregular timestamps:** sample visit times with jitter (config: mean interval, jitter), not every frame.
- **Simulated repositioning:** each visit samples 1–N of the **cached** crops for that frame, per `configs/replay.yaml`.
- **Simulated passage:** optionally end a segment at a target confluency and start a child segment from an earlier frame of another sequence (labelled simulated).
- **Injected faults (for testing Slice 5):** gradual illumination dimming across all flasks; synthetic artifact injection into later visits of one flask. All injected faults labelled. These need new inference: generate a **small, fixed fault set** once and add it to the cache in a single short Colab run (not per experiment).

App: new **"Flask timeline"** tab. Pick a replay scenario, press play; visits arrive one by one and the timeline (confluency ± SD, anomaly score, flags) updates. UI must label it **"Replay of recorded time-lapse (simulated visits)"**.

### 5.5 Acceptance
- Schema-validated summaries; history append-only with hash chain verified in tests.
- Quality-gate unit tests (blurred, dark, uneven images fail).
- Replay produces irregular, repositioned, lineage-aware visit streams; deterministic given a seed.

⏸ Show a replayed flask timeline and the raw history table.

---

## 6. Slice 3 — Growth model per segment + passage prediction *(DONE on synthetic; real-sequence backtest → A1; timeline on real replays → B1)*

### 6.1 Model (`culture/growth.py`, numpy/scipy, deterministic)
- Fit **per segment**, on real timestamps (hours since segment start), weighted by `1 / (confluency_sd² + sigma_fov²)`.
- Logistic `C(t) = K / (1 + exp(-r (t - t0)))`, `0 < K ≤ 100`; Gompertz `C(t) = K * exp(-b * exp(-c t))`. Bounded `curve_fit`; choose by AIC; report both.
- **Time to target** `T*` (default 80%): closed form / numeric root. If target ≥ K → `NOT_REACHED` (never fabricate a time).
- **Uncertainty:** Monte Carlo from fit covariance or residual bootstrap (≥ 500) → 90% interval on `T*` and a prediction band.
- **Minimum data:** ≥ N visits spanning ≥ M hours (config; start N=5, M=12) → else `INSUFFICIENT_DATA`.
- Report **"area doubling time"** (`ln2 / r`, early phase), never "cell doubling time".
- **Expected value for SPC:** for each new visit, the one-step-ahead prediction from a fit on prior visits of the same segment, plus its predictive SD (fit uncertainty + FOV noise). This feeds Slice 5.

### 6.2 Backtest (credibility piece)
Runs on CPU from the cache. On replayed C2C12 streams (with repositioning + irregular timing): fit on visits until observed confluency first reaches 40 / 50 / 60%, predict the 80% crossing, compare to the true crossing. Report median absolute error (hours) and **90% interval coverage**, with and without simulated repositioning (shows the effect of FOV noise).

### 6.3 App
Flask timeline tab shows fitted curve + band, target line, `T*` with interval, chosen model + AIC, area doubling time, per segment.

### 6.4 Acceptance
Backtest table in README; `NOT_REACHED` / `INSUFFICIENT_DATA` / multi-segment unit tests; CPU runtime for a ~20-visit segment recorded.

⏸ Backtest table + 3 example segments (good, poor, plateau).

---

## 7. Slice 4 — Density-conditioned open-set anomaly scoring *(minimal → A4 on qctile embeddings; full → B2; skip trend use if V4 fails)*

### 7.1 Why density-conditioned
Cell morphology changes with density. A single memory bank of "normal" makes a healthy flask look increasingly "anomalous" as it grows, which would fire the temporal anomaly monitor on normal growth. Compare each image only against normals at similar confluency.

### 7.2 Method (training-free)
- **Backbone:** DINOv2 ViT-S/14 (CPU) — compare ViT-B/14 on Colab. Pin version.
- **Memory banks per confluency bin** (config, e.g., 0–20, 20–40, 40–60, 60–80, 80–100%), built **from cached embeddings** of normal tiles (train split) and real normal images where licensed. Bin assignment uses cached confluency. Rebinning or re-thresholding is CPU-only. Greedy coreset per bin. `faiss-cpu` index per bin.
- **Scoring:** patch score = NN distance within the image's confluency bin (bin from Cellpose-SAM); image score = max or top-k mean. Heatmap = upsampled patch scores.
- **Per-bin calibration:** threshold per bin at a fixed FPR on val normals (start 5%); store in `configs/anomaly.yaml`. Also store per-bin mean/SD of normal scores → used as the expected value for SPC.
- **Site calibration mode** (the one place new embeddings are extracted outside 1b): a function to rebuild banks and thresholds from a user-supplied folder of known-good images (the path to adapting to a new instrument). Document it; demo it on EVICAN or C2C12 early frames.
- Optional OpenPhenom comparison — check license first.

### 7.3 Evaluation
- Synthetic test: AUROC + TPR@5%FPR per anomaly class.
- **Density confound check:** on normal C2C12 sequences, plot anomaly score vs confluency with a single global bank vs density-conditioned banks. The conditioned version should be roughly flat for normal growth. This plot goes in the README.
- **Illumination robustness:** score normal images under synthetic brightness/contrast shifts; report how fast false positives grow. Document the result honestly.
- **AutoQC-Bench** (`github.com/MMV-Lab/mmv_AutoQC`): run per its protocol (verify license), report AUROC next to published baselines. Don't tune on its test set.
- CPU latency + bank size (HF storage; Git LFS if needed).

### 7.4 Integration
Classifier says normal (or low confidence) + anomaly above bin threshold → immediate flag `OUT_OF_DISTRIBUTION` → decision engine. Deterministic template sentence. Summary stores score, bin, backbone + bank hashes.

### 7.5 Acceptance
Per-class AUROC, density-confound plot, illumination robustness table, AutoQC-Bench AUROC, latency within ~2× baseline (record actual).

⏸ AUROC table, density-confound plot, 10 heatmaps (5 TP, 3 FP, 2 misses).

---

## 8. Slice 4b — Classifier calibration (required) + domain-shift test *(calibration → A5; full → B3)*

### 8.1 Calibration — required
Class probabilities are now trended over time, so they must be calibrated. Temperature scaling on the val split, **fit on cached logits (CPU, minutes)**; reliability diagram + ECE before/after in README. Store temperature in config; summaries record `calibrated: true`.

### 8.2 Domain-shift test (should)
- Apply the **existing** artifact generators to EVICAN and C2C12 backgrounds → `data/tiles_shift/` with its own `manifest_shift.csv` (source-image-level splits). Keep the original manifest untouched. **Generated before Slice 1b** so their logits are in the cache.
- Evaluate current classifier from cached logits: accuracy, per-class recall, contamination recall per severity, confusion matrix.
- Drop ≤ ~5 points → no retrain; report both. Larger drop → retrain on original + shifted train (same hyperparameters, fixed seed); report before/after on original test, shifted test, and **leave-one-background-out**. Deploy new weights only if no worse on original test. Re-check Grad-CAM on 10 shifted images.
- New weights → new version + SHA-256 → **new trend window** (per §5.3) → recompute **only the logits column** of the cache (short Colab run).

⏸ Reliability diagram + shift table (+ retrain before/after if triggered).

---

## 9. Slice 5 — SPC monitors, risk flags, detectability matrix, mycoplasma risk *(minimal SPC → A6; full → B4; apply V2/V6/V8 changes)*

### 9.1 SPC on residuals (`culture/spc.py`)
Monitor **residuals, not raw series** (raw confluency is non-stationary by design; SPC on it produces false alarms).
- **Growth residual:** `z = (observed − expected) / predictive_sd` per visit (from Slice 3).
- **Anomaly residual:** `z = (score − bin_mean) / bin_sd` (from Slice 4).
- **Class residual:** calibrated probability of each failure class vs its normal-reference mean.
- Monitors: **EWMA** (start λ = 0.2, L ≈ 2.86 — standard choice matching an in-control ARL ≈ 370) and **one-sided tabular CUSUM** for sustained shifts; plus a Shewhart-style single-point rule for large jumps. All parameters in `configs/spc.yaml`.
- Monitors reset at segment boundaries and model-version changes.
- Reason codes: `GROWTH_BELOW_EXPECTED`, `EARLY_PLATEAU`, `ANOMALY_DRIFT`, `FAILURE_CLASS_DRIFT`.
- Evaluation on replay (CPU, from cache): in-control false-alarm rate on normal streams; detection delay (visits) on injected faults. Parameter sweeps are cheap — tune λ/L on a tuning set of streams, report on held-out streams. README table.

### 9.2 Detectability matrix (`configs/detectability.yaml`, hashed into records)
| Contaminant / issue | Brightfield-detectable | Primary cue | cultureQC signal | Confirmatory test |
|---|---|---|---|---|
| Bacteria | Yes (sufficient load/mag) | Granular particles; motility over time | Classifier + anomaly + drift | Culture / Gram / PCR |
| Yeast | Yes | Ovoid, budding particles | Classifier + anomaly + drift | Culture |
| Fungi / mold | Yes (often localized) | Filamentous hyphae | Classifier + anomaly | Culture |
| Mycoplasma | **No** | None optically | Indirect growth-residual risk only | PCR; Hoechst indicator-cell assay; enzymatic kits |
| Detachment | Yes | Rounded / lifting cells, gaps | Classifier + growth residual | — |
| Image quality | Yes | Blur, exposure, illumination | Quality gate | Re-image |

Shown in the app; hash in every record.

### 9.3 Mycoplasma risk indicator
- Levels `NONE` / `LOW` / `ELEVATED`, rule-based from growth-residual SPC signals (+ optionally rising detachment residual). Thresholds in config.
- **Fixed template wording only:**
  - ELEVATED: "Growth is below expected for this culture (reasons: …). This is non-specific and has many possible causes, including mycoplasma. Brightfield imaging cannot detect mycoplasma. Recommend confirmatory testing (e.g., PCR)."
  - NONE: "Growth is within expected range. Brightfield imaging cannot rule out mycoplasma."
- C2C12 sanity check: the 4 media conditions produce different growth; show the detector separates slower conditions from the reference condition. Present as a sanity check, not contamination detection.

### 9.4 Acceptance
SPC unit tests on synthetic residual streams; false-alarm + delay table from replay; matrix in app; forbidden-phrase test green.

⏸ Exact wording, SPC chart for one normal and one faulty replay, false-alarm/delay table.

---

## 10. Slice 5b — Instrument-drift monitor (cross-flask) *(minimal → A7; full → B5)*
If many flasks on the same instrument drift together, the cause is the instrument (illumination, focus, optics), not the cultures.
- Per instrument, track the **median anomaly residual and quality metrics across all active flasks** per time window; EWMA on that population signal.
- If the population monitor fires, raise `INSTRUMENT_DRIFT` and **suppress per-flask anomaly-drift flags** in that window (still recorded, marked suppressed).
- Test with replay: gradual illumination dimming across all flasks → should raise `INSTRUMENT_DRIFT`, not N culture flags; single-flask injected fault → should still raise a culture flag.

**Acceptance:** both replay scenarios behave as described; README table.

---

## 11. Slice 6 — Decision engine, decision events, analysis records *(Phase B6)*

### 11.1 Decision logic (`culture/decision.py`, documented in `docs/DECISION_LOGIC.md`)
Precedence: quality-gate fail → `REIMAGE`; contamination suspected (immediate) → `QUARANTINE_RECOMMENDED`; `INSTRUMENT_DRIFT` → `HOLD_FOR_REVIEW` (instrument); OOD or SPC culture flag → `HOLD_FOR_REVIEW`; predicted target crossing inside the configured window → `PASSAGE_RECOMMENDED`; else `CONTINUE`. Exhaustive truth-table tests. Anything other than `CONTINUE` sets `requires_human_signoff: true`.

### 11.2 Decision event (`schemas/decision_event.v1.json`)
`schema_version`, `event_id`, `created_at`, `lineage_id`, `segment_id`, `flask_id`, `visit_id`, `decision`, `recommended_action_window {earliest, latest}` (from `T*` interval), `reason_codes[]`, `metrics` (confluency mean/SD, class + calibrated prob, anomaly score/bin/threshold, growth params, SPC statistics, mycoplasma risk level), `requires_human_signoff`, `models` (versions + hashes), `config_hashes`, `analysis_record_hash`.
Written as JSON Lines; downloadable from the app. `culture/adapters/scheduler_stub.py` shows a documented webhook POST — **no real vendor endpoints**.

### 11.3 Analysis record
Hash-chained record of each analysis: inputs (image hashes), outputs, model/config hashes, timestamp, previous-record hash. README wording: **"designed to attach to an existing Part 11 audit trail such as BioFlow's"** — cultureQC does not replace it.

**Acceptance:** schema-valid events in tests; truth table fully tested.

---

## 12. Claims policy (enforced by unit test over UI strings, templates, README)

### Allowed (when backed by a script + number)
- "Confluency validated on held-out real datasets: <names, MAE>."
- "Temporal monitoring accounts for field-of-view measurement noise (<value>)."
- "Density-conditioned anomaly scoring evaluated on AutoQC-Bench: AUROC <x>."
- "Predicts time to target confluency with <median error> h and <coverage>% interval coverage in backtests on replayed C2C12 sequences (real images, simulated visits)." — only from the A1 real-sequence backtest, never the synthetic one.
- "Uses SPC (EWMA/CUSUM) on residuals; in-control false-alarm rate <x> in replay."
- "Brightfield can flag bacterial/yeast/fungal contamination and image-quality issues."
- "Mycoplasma is not optically detectable; cultureQC gives an indirect growth-based risk flag that recommends confirmatory testing."
- "Decision support with human sign-off; analysis records designed to attach to an existing Part 11 audit trail."

### Forbidden
- Any phrasing that cultureQC detects / identifies / confirms mycoplasma ("mycoplasma detected", "mycoplasma positive", "mycoplasma-free").
- "Real-time" or "live" contamination detection. Replay must always be labelled as replay.
- "Replaces sterility testing / PCR / compendial methods."
- "Part 11 compliant", "GMP validated".
- Implying Celltrio/BioFlow lacks audit trails, or claiming integration with BioFlow, Momentum, Green Button Go, or RoboCell.
- 98% or 2.34 pp without "synthetic" beside it.
- Any fault-detection number without "simulated faults" beside it.
- "Cell doubling time" for a confluency-derived rate.

---

## 13. Slice 7 — Tamper-evidence verifier (could) *(Phase B7)*
- CLI `python -m culture.audit verify <chain>` → OK or first broken index + expected vs actual hash. Works for analysis records and history rows.
- App "Audit" tab: view chain; "Simulate tampering" flips one byte in a **copy** and re-verifies.
- Tests: single-byte change, reorder, deletion all detected at the right index.
- `docs/PART11_MAPPING.md`: what the chain addresses (tamper-evidence, attributability via hashes, contemporaneous timestamps) and what it doesn't (e-signatures, access control, system validation).

---

## 14. Slice 8 — Docs and demo readiness *(Phase B8)*
1. README: Overview → Architecture diagram → **Architecture validation summary (from Phase A)** → **Results table with provenance column** → Real-image validation + measurement noise → Flask timeline (growth, SPC) → Anomaly (density-conditioned) → Calibration + domain shift → Detectability matrix → Decision events → Audit → Negative results (keep VLM section) → Limitations → Open questions for instrument integration → Next steps (real instrument images).
2. `docs/DEMO_SCRIPT.md` (8–10 min screen share): 60-second Phase A validation summary (what was tested, what failed, what changed) → single visit → real-image example → anomaly heatmap → flask timeline replay (growth + passage prediction + SPC) → injected fault flagged → instrument-drift scenario flagged as instrument → decision event JSON → detectability matrix → (tamper demo if built). List exact example files/scenarios.
3. Warm-start instructions for the HF Space + local fallback (`PYTHONPATH=. python app.py`) with weights and banks available offline.
4. Tag `v2.0-demo` at freeze.

---

## 15. Notebook plan (Colab A100) — batched

Notebooks are **thin runners** around repo code: pinned commit, `pip install -r requirements.txt`, remount Drive, seeds, call `culture/` + `scripts/`, write artifacts to Drive with a manifest.

| Notebook | Status | GPU | Produces |
|---|---|---|---|
| `nb/00_download_datasets.ipynb` | Done | No | EVICAN, tiles, AutoQC-Bench staged on Drive |
| `nb/02_compute_cache.ipynb` | Done | Yes | The Slice 1b cache |
| `nb/03_cache_additions.ipynb` | **Phase A0.5 — run once** | Yes (short) | C2C12 sequences, fault set, qctile embeddings, sidecars, slim export, replay smoke test |
| `nb/04_live_latency.ipynb` | Phase A8 | CPU runtime | Live per-visit latency (can also run on the Mac) |

Later GPU work only if triggered: 4b retrain (+ its logits), ViT-B comparison subset — both via small additions to the cache, never a full re-pass.

Everything else runs as `scripts/` on the Mac against the slim cache (+ unzipped C2C12 patch embeddings). Existing training notebooks: don't rewrite; only extend if 4b triggers a retrain (new data behind a flag, default off). Validate `.ipynb` JSON after programmatic edits; clear outputs before commit.

---

## 16. Stretch (only if everything above is stable)
- **S1. Cell-line growth priors:** fit a shared growth shape per cell line from past segments; per-segment fits then only adjust scale/shift → stabler early predictions. Report backtest gain.
- **S2. Motion heuristic:** frame-difference / optical flow on short bursts to separate motile particles from drifting debris. Blocked on data (no public contaminated adherent-culture videos); only as a clearly labelled simulated prototype.

## 17. Out of scope
Brightfield mycoplasma "detector"; label-free potency prediction (roadmap talking point); real vendor integrations; Cellpose-SAM re-fine-tune (revisit only if Slice 1 MAE > 10 pp, with human approval); generative text in QC outputs; live-camera processing.

---

## 18. Final acceptance checklist (before Oct 4)
- [ ] `Cache.build()` flush fix merged with test.
- [ ] `nb/03` run: C2C12 sequences + fault set + qctile in the cache; sidecars present.
- [ ] `docs/STATUS.md` and `docs/ARCHITECTURE_VALIDATION.md` complete; Phase A review done; design changes applied.
- [ ] Growth backtest table regenerated on real sequences; synthetic-only table retired.
- [ ] C2C12 credited (CC BY 4.0) in README and report.
- [ ] App runs on HF Space and locally from `v2.0-demo`.
- [ ] Every README metric reproducible; provenance labelled (synthetic / simulated / real).
- [ ] Real-image confluency (incl. 60–90% band) + FOV noise model.
- [ ] Compute cache built once; manifest + parity test green; slim export works on the Mac.
- [ ] History: lineage/segments/events, append-only, hash-chained; quality gate.
- [ ] Flask timeline replay (labelled), growth fits per segment, backtest table.
- [ ] Density-conditioned anomaly + confound plot + AutoQC-Bench AUROC.
- [ ] Calibrated classifier (reliability diagram); shift table.
- [ ] SPC on residuals with false-alarm/delay table; mycoplasma wording; forbidden-phrase test green.
- [ ] (Should) instrument-drift scenario; decision events; (Could) tamper verifier.
- [ ] Docs: REPO_MAP, DATASETS, DECISION_LOGIC, PART11_MAPPING, DEMO_SCRIPT.
- [ ] Negative results section intact and updated.

---

## Appendix A — References
- Celltrio RoboCell: https://celltrio.com/robocell/ · brochure: http://celltrio.com/wp-content/uploads/2024/01/Celltrio_RoboCell_Brochure2024.pdf
- Multipoint confluency validation (Evident CM30 white paper): https://evidentscientific.com/en/learn/white-papers/validation-of-multipoint-observations-using-an-incubation-monitoring-system
- EWMA/CUSUM parameters in bioprocess SPC: https://www.bioprocessintl.com/economics/statistical-properties-of-weco-rule-combinations-through-simulations
- SPC pitfalls with bioprocess data (Heigl et al., PDA J 2021): https://journal.pda.org/content/75/5/425
- Anomaly detection under domain shift (AeBAD / MMR): https://arxiv.org/pdf/2304.02216
- EVICAN: https://academic.oup.com/bioinformatics/article/36/12/3863/5814923
- C2C12 time-lapse (Ker et al. 2018, CC BY 4.0): https://www.nature.com/articles/sdata2018237 · data: https://doi.org/10.17605/OSF.IO/YSAQ2
- Cell Tracking Challenge (not used — permission required): https://celltrackingchallenge.net/datasets/
- AutoQC-Bench: https://www.nature.com/articles/s44303-025-00117-8 · https://github.com/MMV-Lab/mmv_AutoQC
- Jaccard et al. (halo correction): https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4260842/
- Mycoplasma stained-image DL (Iseoka et al.): https://pmc.ncbi.nlm.nih.gov/articles/PMC8866286/
- DINOv2: https://github.com/facebookresearch/dinov2

## Appendix B — Suggested files
```
culture/cache.py       culture/quality.py    culture/history.py    culture/growth.py
culture/anomaly.py     culture/spc.py        culture/drift.py
culture/decision.py    culture/audit.py      culture/replay.py
culture/adapters/scheduler_stub.py
configs/{noise,quality,replay,anomaly,spc,detectability}.yaml
schemas/visit_summary.v1.json   schemas/decision_event.v1.json
scripts/{eval_confluency_real,fov_noise,backtest_growth,eval_anomaly,eval_spc}.py
nb/00..04 (see §15)
docs/{REPO_MAP,STATUS,ARCHITECTURE_VALIDATION,DATASETS,DECISION_LOGIC,PART11_MAPPING,DEMO_SCRIPT}.md
scripts/validate_architecture.py   # runs A1–A8 on the held-out fleet, writes report tables + plots
scripts/fetch_c2c12.py  scripts/make_fault_set.py  scripts/cache_tile_embeddings.py   # provided with nb/03
nb/03_cache_additions.ipynb  HANDOFF_nb03.md   # provided
tests/ (smoke, cache parity + resume, quality, history chain, growth, anomaly bins, spc, drift, decision table, schemas, audit tamper, forbidden phrases)
```
Adapt names to the existing package structure found in Slice 0.
