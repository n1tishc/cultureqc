# cultureQC — Upgrade Spec v2.1 (Temporal Architecture + Batched Compute) for Coding Agent

**Owner:** Nitish · **Code freeze:** Sun Oct 4, 2026 · **Demo (Teams, screen share):** Tue Oct 6, 2026, 3 PM PDT
**Audience:** a Celltrio engineer / cell-culture expert. Every claim must survive expert scrutiny.
**v2.1 change:** all expensive GPU inference runs **once** in a compute-cache pass (Slice 1b); Slices 2–5 run on the cache, on CPU.
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

## 2. Slice plan

| # | Slice | Why | Effort | Priority |
|---|---|---|---|---|
| 0 | Repo recon + baseline freeze | Safety net | 0.5 d | Must |
| 1 | Real-image confluency validation + FOV noise floor | Kills "all synthetic"; measures noise the temporal layer must respect | 1 d | Must |
| 1b | **Compute cache — one batched GPU pass** | Run expensive inference once; everything after iterates locally on CPU | 0.5–1 d | Must |
| 2 | Visit summary, per-flask history, quality gate, replay mode | Foundation for everything temporal | 1 d | Must |
| 3 | Growth model per segment + passage prediction | Sensor → decision tool | 1 d | Must |
| 4 | Density-conditioned open-set anomaly scoring | Catches unknown failure modes without firing on normal growth | 1 d | Must |
| 4b | Classifier calibration (required) + domain-shift test (+ conditional retrain) | Trended probabilities must be calibrated; defends the 98% | 0.5–1 d | Should (calibration: Must) |
| 5 | SPC monitors on residuals + risk flags + detectability matrix + mycoplasma *risk* | Honest temporal flags in GMP vocabulary | 1 d | Must (growth + anomaly EWMA); Should (rest) |
| 5b | Instrument-drift monitor (cross-flask) | Separates microscope problems from culture problems | 0.5 d | Should |
| 6 | Decision engine + decision events + analysis record | Speaks the scheduler's language | 0.5 d | Should |
| 7 | Tamper-evidence verifier | Makes Part 11 thinking concrete | 0.5 d | Could |
| 8 | Docs, claims table, demo script | What gets said on the call | 0.5 d | Must |
| S | Stretch: cell-line growth priors; motion heuristic | Only if all above stable | — | Could |

**Dependencies:** 0 → 1 (gate) → 1b (cache) → then 2 → 3 → 5, with 4 and 4b in parallel after 1b. 5b needs 4. 6 needs 3 + 5.

**Working rhythm after 1b:** code + tests locally on the Mac against the cache (CPU only) → merge → app. Colab is only needed again for live-inference latency checks, site-calibration demo, or a triggered 4b retrain. While any long Colab job runs, work on CPU-only modules (history, SPC, decision engine, quality gate).

**Cut order if time runs out:** S → 7 → 5b → 4b retrain part (keep calibration + shift *eval*) → 6.
**Core that must ship:** 0, 1, 1b, 2, 3, 4, 4b calibration, 5 (growth + anomaly EWMA, mycoplasma wording), 8.

**Stop rule:** if Slice 1 real-data confluency MAE > 10 pp, stop and report. Confluency is the foundation of the temporal layer.

---

## 3. Slice 0 — Repo recon and baseline freeze
1. Tag `v1.0-pre-upgrade`; confirm the HF Space runs from it.
2. `docs/REPO_MAP.md`: modules, entry points, where each model / Grad-CAM / templates / audit live, weight locations, app wiring, dependency versions. Note whether confluency runs per tile or per image, how Grad-CAM boxes are thresholded, and audit record fields.
3. Record CPU latency per image for the full pipeline (latency budget baseline).
4. `pytest` smoke test: full single-image pipeline on a fixture image.

**Acceptance:** tag, working Space, REPO_MAP, green smoke test, baseline latency.
⏸ Share REPO_MAP + latency.

---

## 4. Slice 1 — Real-image confluency validation + FOV noise floor

### 4.1 Datasets (verify license + Cellpose-SAM overlap for each)
| Dataset | Modality | Masks | Use |
|---|---|---|---|
| EVICAN | BF + PhC, ~30 lines | COCO + binary, partial | Primary held-out eval |
| Cell Tracking Challenge (adherent 2D PhC/DIC sets) | PhC, DIC | Seg GT on subset | Secondary eval. Skip `BF-C2DL-HSC` (suspension). |
| C2C12 time-lapse (Sci Data 2018) | PhC | Tracking GT | Slices 2–3; hand-label ~20 frames if used for Slice 1 |
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

## 4A. Slice 1b — Compute cache (one batched GPU pass)

**Goal:** run every expensive model over every image the project needs, **once**, and store **raw outputs** so later changes (thresholds, calibration, binning, crop choices) never force a recompute.

### 4A.1 What goes in
| Image set | Why |
|---|---|
| Synthetic tiles (train/val/test) | Anomaly banks, calibration, per-class AUROC |
| Shifted synthetic tiles (EVICAN + C2C12 backgrounds, see §8.2) | Domain-shift test — **generate them before this pass** using the existing artifact generators, so no second pass is needed |
| EVICAN (+ BriFiSeg if used) | Held-out eval, bank calibration on real normals |
| C2C12 sequences | Replay, growth backtest, density-confound check, SPC eval |
| Adherent Cell Tracking Challenge sequences | Secondary replay/eval |
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

## 5. Slice 2 — Visit summary, per-flask history, quality gate, replay mode

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
Builds realistic visit streams from C2C12 sequences (and adherent CTC sequences) **entirely from the compute cache — no model inference at replay time**, so replay runs on CPU in seconds:
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

## 6. Slice 3 — Growth model per segment + passage prediction

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

## 7. Slice 4 — Density-conditioned open-set anomaly scoring

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

## 8. Slice 4b — Classifier calibration (required) + domain-shift test

### 8.1 Calibration — required
Class probabilities are now trended over time, so they must be calibrated. Temperature scaling on the val split, **fit on cached logits (CPU, minutes)**; reliability diagram + ECE before/after in README. Store temperature in config; summaries record `calibrated: true`.

### 8.2 Domain-shift test (should)
- Apply the **existing** artifact generators to EVICAN and C2C12 backgrounds → `data/tiles_shift/` with its own `manifest_shift.csv` (source-image-level splits). Keep the original manifest untouched. **Generated before Slice 1b** so their logits are in the cache.
- Evaluate current classifier from cached logits: accuracy, per-class recall, contamination recall per severity, confusion matrix.
- Drop ≤ ~5 points → no retrain; report both. Larger drop → retrain on original + shifted train (same hyperparameters, fixed seed); report before/after on original test, shifted test, and **leave-one-background-out**. Deploy new weights only if no worse on original test. Re-check Grad-CAM on 10 shifted images.
- New weights → new version + SHA-256 → **new trend window** (per §5.3) → recompute **only the logits column** of the cache (short Colab run).

⏸ Reliability diagram + shift table (+ retrain before/after if triggered).

---

## 9. Slice 5 — SPC monitors, risk flags, detectability matrix, mycoplasma risk

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

## 10. Slice 5b — Instrument-drift monitor (cross-flask)
If many flasks on the same instrument drift together, the cause is the instrument (illumination, focus, optics), not the cultures.
- Per instrument, track the **median anomaly residual and quality metrics across all active flasks** per time window; EWMA on that population signal.
- If the population monitor fires, raise `INSTRUMENT_DRIFT` and **suppress per-flask anomaly-drift flags** in that window (still recorded, marked suppressed).
- Test with replay: gradual illumination dimming across all flasks → should raise `INSTRUMENT_DRIFT`, not N culture flags; single-flask injected fault → should still raise a culture flag.

**Acceptance:** both replay scenarios behave as described; README table.

---

## 11. Slice 6 — Decision engine, decision events, analysis records

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
- "Predicts time to target confluency with <median error> h and <coverage>% interval coverage in backtests on replayed <dataset> sequences."
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
- "Cell doubling time" for a confluency-derived rate.

---

## 13. Slice 7 — Tamper-evidence verifier (could)
- CLI `python -m culture.audit verify <chain>` → OK or first broken index + expected vs actual hash. Works for analysis records and history rows.
- App "Audit" tab: view chain; "Simulate tampering" flips one byte in a **copy** and re-verifies.
- Tests: single-byte change, reorder, deletion all detected at the right index.
- `docs/PART11_MAPPING.md`: what the chain addresses (tamper-evidence, attributability via hashes, contemporaneous timestamps) and what it doesn't (e-signatures, access control, system validation).

---

## 14. Slice 8 — Docs and demo readiness
1. README: Overview → Architecture diagram → **Results table with provenance column** → Real-image validation + measurement noise → Flask timeline (growth, SPC) → Anomaly (density-conditioned) → Calibration + domain shift → Detectability matrix → Decision events → Audit → Negative results (keep VLM section) → Limitations → Open questions for instrument integration → Next steps (real instrument images).
2. `docs/DEMO_SCRIPT.md` (8–10 min screen share): single visit → real-image example → anomaly heatmap → flask timeline replay (growth + passage prediction + SPC) → injected fault flagged → instrument-drift scenario flagged as instrument → decision event JSON → detectability matrix → (tamper demo if built). List exact example files/scenarios.
3. Warm-start instructions for the HF Space + local fallback (`PYTHONPATH=. python app.py`) with weights and banks available offline.
4. Tag `v2.0-demo` at freeze.

---

## 15. Notebook plan (Colab A100) — batched

Notebooks are **thin runners** around repo code: pinned commit, `pip install -r requirements.txt`, remount Drive, seeds, call `culture/` + `scripts/`, write artifacts to Drive with a SHA-256 manifest. After Slice 1b, most work needs **no** Colab.

| Notebook | Slice | GPU | When | Produces |
|---|---|---|---|---|
| `nb/00_download_datasets.ipynb` | 0 | No | Right after Slice 0 | EVICAN, C2C12, adherent CTC, AutoQC-Bench on Drive; licenses + overlap notes for `DATASETS.md` |
| `nb/01_eval_confluency_real.ipynb` | 1 | Yes (small) | Gate | Held-out full-frame confluency MAE, overlays |
| `nb/02_compute_cache.ipynb` | 1b | **Yes (the big one)** | Once, after the gate passes | Prob maps, confluency (full + crops), logits, DINOv2 embeddings, quality metrics, manifest, slim export |
| `nb/03_cache_additions.ipynb` | 2 / 4b / 4 | Yes (short) | Only if needed | Injected-fault set; logits for retrained weights; ViT-B comparison subset |
| `nb/04_live_latency.ipynb` | 4 / 8 | CPU runtime | Before freeze | End-to-end live pipeline latency on CPU (the Space's reality) |

Everything else — FOV-noise model, growth backtests, bank building, thresholds, calibration, shift evaluation, SPC and drift evaluation — runs as `scripts/` on the Mac against the slim cache (or on a CPU Colab runtime if the Mac is busy).

Existing training notebooks: don't rewrite; only extend if 4b triggers a retrain (new data behind a flag, default off). Validate `.ipynb` JSON after programmatic edits; clear outputs before commit; every README number regenerated by a script/notebook.

---

## 16. Stretch (only if everything above is stable)
- **S1. Cell-line growth priors:** fit a shared growth shape per cell line from past segments; per-segment fits then only adjust scale/shift → stabler early predictions. Report backtest gain.
- **S2. Motion heuristic:** frame-difference / optical flow on short bursts to separate motile particles from drifting debris. Blocked on data (no public contaminated adherent-culture videos); only as a clearly labelled simulated prototype.

## 17. Out of scope
Brightfield mycoplasma "detector"; label-free potency prediction (roadmap talking point); real vendor integrations; Cellpose-SAM re-fine-tune (revisit only if Slice 1 MAE > 10 pp, with human approval); generative text in QC outputs; live-camera processing.

---

## 18. Final acceptance checklist (before Oct 4)
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
- C2C12 time-lapse: https://www.nature.com/articles/sdata2018237
- Cell Tracking Challenge: https://celltrackingchallenge.net/datasets/
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
docs/{REPO_MAP,DATASETS,DECISION_LOGIC,PART11_MAPPING,DEMO_SCRIPT}.md
tests/ (smoke, cache parity + resume, quality, history chain, growth, anomaly bins, spc, drift, decision table, schemas, audit tamper, forbidden phrases)
```
Adapt names to the existing package structure found in Slice 0.
