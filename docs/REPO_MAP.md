# REPO_MAP

Slice 0 deliverable for `cultureQC_upgrade.md` (Upgrade Spec v2.1). Written
before any upgrade code lands, at tag `v1.0-pre-upgrade` (commit `e2274dd`).
Purpose: orient the temporal-architecture work; not a general architecture doc.

## 1. What exists today

cultureQC v1 is a **stateless, single-image** pipeline: one brightfield/phase-
contrast image in, one auditable record out. There is no history, no
per-flask state, no time series anywhere in the codebase. Everything in the
upgrade spec (visit summaries, lineage, growth models, SPC, decision engine)
is new.

There are three surfaces around the same library, all calling
`culture.pipeline.analyze()` or the model functions directly:

| Surface | Entry point | Role |
|---|---|---|
| Library | `culture/pipeline.py::analyze()` | The integration surface. Everything below calls this or its sub-functions. |
| API Space (product backend) | `deploy/hf-space/api.py` | FastAPI; `POST /analyze`. What the Vercel site calls. |
| Demo console | `demo/app.py` | Gradio Blocks app; human-facing single-image review UI. |
| Gradio+ZeroGPU Space | `deploy/hf-space-demo/app.py` | A copy of the demo console, deployed separately (raw model output, no product UI). |
| Product site | `site/` (React+Vite, on Vercel) | Calls the API Space's `/analyze` over HTTP; not Python. |

**`deploy/hf-space/culture/` and `deploy/hf-space-demo/culture/` are generated
copies** of the root `culture/` package (plus `config/`), refreshed by
`python deploy/sync_space.py` and checked for drift in CI
(`deploy/sync_space.py --check`). Confirmed in sync with root `culture/` as of
this tag (only `__pycache__` differs). **Any new module the upgrade adds under
`culture/` needs a `sync_space.py` run before either Space is pushed** — the
sync script copies whatever exists, so no changes to `sync_space.py` itself
should be needed unless new top-level files are added outside `culture/`/`config/`.

## 2. Package layout — spec vs. reality

The upgrade spec was written before seeing the repo and assumes some paths
that don't match. Noting the real names so the agent doesn't create parallel
ones:

| Spec assumes | Repo actually has | Note |
|---|---|---|
| `configs/` | `config/` (singular) | `config/lines/{cell_line}.yaml`, loaded by `culture/rules.py::load_line_config` / `load_all_configs`. New slice configs (`noise.yaml`, `quality.yaml`, etc.) should decide: extend `config/` or add `configs/` alongside it. Recommend reusing `config/` for consistency — see open question in §7. |
| `app.py` at repo root, `PYTHONPATH=.` gotcha | No root `app.py`. Three separate entry points instead (`demo/app.py`, `deploy/hf-space/api.py`, `deploy/hf-space-demo/app.py`), each already handling its own `sys.path` (e.g. `demo/app.py:22`). | The `PYTHONPATH=.` gotcha in the spec's §0.3 is stale — doesn't apply to the current entry points, which already insert the repo root. |
| `data/tiles/{class}/{tile_id}.png`, `data/tiles/manifest.csv` | Not present in this checkout — `docs/DATA.md` says training data is **downloaded/derived, not committed** (`scripts/download_sources.py`, `scripts/extract_sprites.py`, `scripts/synth_contamination.py`). | Slice 1/1b work against real held-out datasets (EVICAN, C2C12, CTC) fetched fresh, not this synthetic tile set. If Slice 4/4b need the synthetic manifest for bank-building/calibration, regenerate it first per `docs/DATA.md`. |
| `LongGrainRice/cultureqc-demo` (HF Space name) | Two separate Spaces: `LongGrainRice/cultureqc-api` (FastAPI backend, product) and the Gradio+ZeroGPU demo Space (`deploy/hf-space-demo/`, name not hardcoded in-repo — check the HF org before assuming a slug). | `deploy/README.md` is the source of truth for both. |
| `culture/` (noted as correct) | Confirmed: `culture/` (underscore-free but lowercase), matches spec's own note. | No action needed. |

## 3. Where each model / component lives

### 3.1 Confluency — `culture/seg.py`
- **`cpsam_confluency(img, method="probmap")`** (default, recommended): Cellpose-SAM
  (`cpsam_v2`), lazy-loaded singleton (`_get_model()`, module-level `_cp_model`).
  Device selection: `models.CellposeModel(gpu=torch.cuda.is_available())` — CUDA
  only, **no MPS branch**, so on this Apple Silicon dev machine it runs CPU even
  though `torch.backends.mps.is_available()` is `True`. This is intentional per
  the code comment (deployment target is CPU-only HF Space) but means Mac dev
  runs are CPU, matching production, not MPS-accelerated.
- Runs **per full image, not per tile**. `flows[2]` is the raw cell-probability
  map at full-image resolution; confluency = `(prob > thr).mean() * 100`.
  Confidence = fraction of pixels *not* within `±band` of the threshold (fewer
  borderline pixels → higher confidence).
- `method="instance"` (union of instance masks) is kept for comparison only —
  known to under-segment by 4–9 pp (docstring). Not used by any current caller.
- `method="threshold"` (`threshold_confluency()`) is a classical local-variance
  Otsu baseline. `demo/app.py:154` computes it for parity but doesn't display it.
- Model version string: `"cpsam_v2"`.

**Slice 1b implication:** the cache needs to store the full-resolution
probability map (`flows[2]`) per image, since that's what `cpsam_confluency`
already computes and what crop-based FOV-noise sampling (§4.3 of the spec)
needs to re-threshold without a second Cellpose-SAM pass.

### 3.2 QC classification — `culture/qc.py`
- EfficientNet-B0 (`timm.create_model("efficientnet_b0", ...)`), 4-way softmax:
  `CLASS_NAMES = ["normal", "contamination_suspected", "detachment", "image_quality"]`.
- Weights pulled from the Hub at runtime: `HF_REPO_ID = "LongGrainRice/cultureqc-qc-effnetb0-v1"`,
  file `best.pt`, loaded via `hf_hub_download` + `torch.load(..., map_location="cpu")`.
  **Not committed to the repo** — the upgrade's cache manifest (§4A.3 of the
  spec, "weight hashes") needs to hash this downloaded file, not a repo path.
- **Runs per tile, not per full image.** Callers (`pipeline.py:62-70`,
  `demo/app.py:156-161`, `deploy/hf-space/api.py:339-345`) each independently
  center-crop (or resize-up, if the image is smaller than the tile) to 256×256
  before calling `qc_classify`. This center-crop-only tiling is duplicated in
  three places — worth a single shared helper before the upgrade adds a fourth
  caller (visit-summary builder), but out of scope for Slice 0 itself.
- Device selection mirrors `seg.py`: `torch.cuda.is_available()`, plus a note
  that `import spaces` (ZeroGPU) makes this evaluate `True` inside `@spaces.GPU`
  calls on the demo Space specifically.
- Model version string: `"qc_effnetb0_v1"`.

### 3.3 Grad-CAM evidence boxes — `culture/qc.py::_gradcam_bboxes`
- `pytorch_grad_cam.GradCAM`, target layer `model.conv_head` (EfficientNet-B0's
  last conv layer before pooling), one CAM per call targeted at the *predicted*
  class only (`ClassifierOutputTarget(pred_idx)` in `qc_classify`).
- Thresholding: CAM heatmap binarized at `threshold=0.3` (fixed, not
  configurable via `qc_classify`'s signature — would need a code change to
  tune), then `cv2.connectedComponentsWithStats` finds separate blobs.
  `min_area_frac=0.005` (0.5% of tile area) filters tiny specks;
  `max_boxes=8` caps the count; boxes are sorted by area, largest first.
  Returns `[]` (not an error) if Grad-CAM raises or nothing survives — see
  `qc_classify`'s `try/except Exception: bboxes = []` at `qc.py:181-184`,
  which is broad and silently swallows any Grad-CAM failure mode, not just
  "no activation region."
- Boxes are in **256×256 tile coordinates**. Two different rescale-to-full-image
  implementations exist and disagree:
  - `deploy/hf-space/api.py::_boxes_normalised` — **correct**: offsets the
    origin by the tile's centering offset, keeps width/height in tile pixels
    (fractional `[x1,y1,x2,y2]` output).
  - `demo/app.py::_scale_bboxes` — **known bug** (documented in root
    `README.md`'s "Known limits"): also scales width/height by the full-image
    factor, drawing boxes far wider than the region actually analyzed. Not
    fixed as of this tag; flagged here because any new temporal/visit-summary
    code that needs evidence boxes in full-image coordinates should copy the
    API's version, not the demo's.

### 3.4 Rationale — `culture/rationale.py`
- `template_rationale()`: deterministic, always used in production
  (`use_vlm=False` hardcoded at both `pipeline.py:102` and `demo/app.py:196`).
  Builds a fixed two-sentence string from `_FLAG_PHRASES` / `_ACTION_PHRASES` /
  `_TREND_PHRASES` lookup dicts plus the bbox-to-quadrant helper
  (`_bbox_quadrant`). Purely a function of values it's handed — never invents
  numbers, which is what makes it GMP-defensible per the spec's rule 3.
- `vlm_rationale()`: Qwen2-VL-2B zero-shot experiment, gated behind
  `use_vlm=True` (never set True in any current caller) and validated (≤3
  sentences, must mention the flag class, no hallucinated numbers). Falls back
  to the template on any failure or `ImportError` (transformers/accelerate
  are commented out of `requirements.txt` — not installed by default).
  **Note:** the spec's §0.1 cites "Qwen3-VL-8B zero-shot ~29%" as the rejected
  VLM baseline; the code path still wired up is Qwen2-VL-2B, a different,
  smaller model. The 29% figure in the spec is presumably from a separate
  eval notebook/script not in this repo checkout — flag for Slice 1/8 to trace
  its source before restating it, per rule 3 (never invent numbers) — this
  repo alone doesn't substantiate it.
- `growth_trend` parameter already exists in `template_rationale`'s signature
  and `_TREND_PHRASES` dict (`"rising"/"flat"/"falling"/"unknown"`) but every
  current caller passes `growth_trend=None` — this is a ready-made hook for
  Slice 3's growth model to plug into without changing `rationale.py`.

### 3.5 Rules / decision — `culture/rules.py`
- `decide()`: precedence order documented in the module docstring — QC flag
  (if non-normal and confident) → low confluency confidence → passage-ready →
  feed-due → hold. Returns `(action, reason)`, `action ∈ {human_review,
  passage, feed, hold}`.
- `LineConfig` dataclass: per-cell-line thresholds, loaded from
  `config/lines/{name}.yaml` via `load_line_config`/`load_all_configs`.
  Fields: `target_confluency`, `min_hours_since_passage`, `feed_interval_h`,
  `qc_review_threshold`, `confluency_confidence_floor`. Only `config/lines/A172.yaml`
  exists in this checkout; `demo/app.py`'s `CELL_LINES` list names eight others
  with no matching YAML — they fall back to `DEFAULT_CONFIG` values with the
  `cell_line` field overridden (see `demo/app.py:165`), not to a per-line file.
- This is v1's decision engine — much simpler than the spec's Slice 6 truth
  table (`REIMAGE` / `QUARANTINE_RECOMMENDED` / `HOLD_FOR_REVIEW` /
  `PASSAGE_RECOMMENDED` / `CONTINUE`). Slice 6 replaces/extends this rather
  than starting from nothing; the four-action vocabulary here doesn't map
  1:1 onto the spec's five-decision vocabulary and that mapping should be an
  explicit decision when Slice 6 starts.

### 3.6 Audit record — `culture/records.py` + `culture/schema.json`
- `RecordWriter`: append-only JSONL, hash-chained. Each `append()` call reads
  the *previous* record's `record_hash` from the tail of the file (by
  scanning it in `__init__` — **O(n) per writer construction**, fine for a
  demo log, a concern if the upgrade's per-flask history log grows large — see
  §7), sets it as `prev_record_hash`, computes SHA-256 over canonical JSON
  (sorted keys, compact separators) excluding `record_hash` itself, and
  appends one line. Genesis hash is 64 zeros.
- `verify_chain(path)`: replays the file, recomputes each hash, returns
  `(True, None)` or `(False, first_bad_line)`.
- **Known limitation already documented** (`deploy/hf-space/api.py`'s module
  docstring, `README.md`'s "Known limits"): the API Space's chain is
  **per-boot only** — HF Space disks are ephemeral, so `prev_record_hash`
  links reset on every restart. The spec's Slice 2 `culture/history.py`
  (lineage → segments → visits, append-only, hash-chained) is new
  infrastructure, not an extension of `RecordWriter` — but should reuse
  `records.py`'s canonical-JSON + SHA-256 pattern for consistency, and needs
  its own durable-storage answer (the spec suggests SQLite or JSONL) since the
  same ephemeral-disk problem applies to any new history store deployed on
  the same Space.
- `culture/schema.json`: JSON Schema (draft-07) for the 28-ish-field record,
  `schema_version: "0.2"` (`const`), `additionalProperties: false`. Not
  currently validated against at runtime anywhere in `culture/` — no
  `jsonschema.validate()` call found in the pipeline; only used for
  documentation/potential external validation. The spec's Slice 2 visit-summary
  schema (`schemas/visit_summary.v1.json`) should decide whether to actually
  wire up runtime validation, since the audit record's schema currently
  doesn't.
  **Two real drifts found by actually validating a live record against it**
  (`tests/test_smoke_pipeline.py::test_record_matches_schema`, xfail'd rather
  than fixed in this recon-only slice):
  1. `additionalProperties: false` but `record_hash` isn't in `properties` —
     `RecordWriter.append()` always adds it, so a strict validation of any
     real record fails on this alone.
  2. `confluency_method`'s enum is `["cpsam_v2_probmap", "cpsam_v2_instance",
     "threshold_baseline"]`; `seg.py` actually writes `"probmap"` /
     `"instance"` / `"threshold"` (see §3.1) — none of the three enum values
     match anything the code produces. This is exactly the kind of thing
     "nothing validates the schema at runtime" lets drift silently; worth
     fixing whenever `schema.json` or `seg.py` is next touched (Slice 2's
     visit-summary schema work is the natural place).
- Record fields relevant to the upgrade's lineage/versioning needs: `flask_id`,
  `cell_line`, `protocol_stage`, `image_hash`, `model_versions` (dict of
  `seg`/`qc`/`vlm` version strings — **no weight hash**, despite a
  `model_weights_hash` field existing in the schema; it's always `None` in
  every current caller). The spec's cache key `(image_sha256, crop_spec,
  model_name, model_version)` and manifest "weight hashes" requirement (§4A.2,
  §4A.3) will need `model_weights_hash` actually populated — it's a schema
  field that exists but nothing fills in today.

### 3.7 Visuals — `culture/visuals.py`
Display-only overlay rendering (raw image / probability heatmap / mask /
contour PNGs, Grad-CAM heatmap composited back onto the tile region).
Explicitly documented as "never used to compute records" — pure UI
side-channel. Not relevant to the upgrade's compute cache (which stores raw
model outputs, not rendered overlays) except as a reminder that any new
replay/timeline UI (Slice 2's "Flask timeline" tab) will likely want a
similar visuals module rather than recomputing overlays from cached raw
outputs inline.

## 4. Dependency versions (this checkout, `.venv`)

Built fresh from `requirements.txt` at this tag, Python 3.14.7 (matches
`deploy/README.md`'s "host venv" row):

| Package | Installed | requirements.txt floor |
|---|---|---|
| torch | 2.14.0 | >=2.0 |
| torchvision | (matching) | >=0.15 |
| cellpose | 4.2.1.1 | >=4.0 |
| timm | 1.0.29 | >=0.9 |
| opencv-python-headless | 5.0.0.93 | >=4.8 |
| scikit-image | (installed) | >=0.21 |
| huggingface_hub | (installed) | >=0.20 |
| jsonschema | (installed) | >=4.17 |
| gradio | (installed) | >=4.0 |
| pytest | 8.x | >=8.0 |

`torch.cuda.is_available()` → `False` on this machine (Apple Silicon, no
CUDA). `torch.backends.mps.is_available()` → `True`, but unused (see §3.1) —
**both Cellpose-SAM and the classifier run on CPU here**, same as the target
HF Space, which is the reason Mac dev latency is a meaningful stand-in for
the deployed Space's CPU latency (per `deploy/README.md`'s existing
comparison table) rather than an MPS-accelerated number that wouldn't
transfer.

`pip install -r requirements.txt` into a clean `.venv` completed with no
conflicts.

## 5. Baseline CPU latency

Measured by `scripts/benchmark_latency.py` (Slice 0 deliverable, this repo),
run against every fixture in `test-data/`, models already resident (warm-up
cost reported separately). See `results/baseline_latency.csv` and the summary
in the ⏸ checkpoint message for numbers — not restated here to avoid a stale
copy drifting from the CSV that's the actual source of truth (rule 3: every
metric comes from a script in the repo, and the script + its output are that
source).

This is consistent with the already-documented figures in `deploy/README.md`
("host venv (Python 3.14, torch 2.14): ~50s for a 256×256 tile, >180s for a
704×520 field") and `README.md`'s "Known limits" ("about a minute per image
on 2 vCPU; roughly 20s on a fast laptop") — those numbers predate this repo
map and weren't reproduced by a committed script until now.

## 6. Existing tests

Only `deploy/hf-space/test_api.py` existed before this slice — **28 tests
pass** as of this tag (`.venv/bin/python -m pytest deploy/hf-space/test_api.py -q`),
not the 23 that `README.md` and `deploy/README.md` currently cite; the test
count has drifted from the docs at some point. Minor, but noted per rule 3
(numbers come from a script, not restated from memory) —
API **contract** tests with both models stubbed (`types.SimpleNamespace`
fakes swapped in for `_get_model`/`qc_classify`/`cpsam_confluency`), so they
run in seconds and need neither torch nor cellpose. They cover HTTP status
codes, response shape, the evidence-box coordinate math (`_boxes_normalised`),
CORS allowlist behavior, and that concurrent uploads don't corrupt the hash
chain (the one test that drives a real `RecordWriter`, deliberately).

**Nothing exercised the real pipeline end-to-end before this slice** — no
test imported `culture.pipeline.analyze()` and ran actual inference. Slice 0
adds `tests/test_smoke_pipeline.py` to close that gap: one real
`analyze()` call on a `test-data/` fixture, asserting the record is
schema-shaped and self-consistent (hash chain verifies, confluency/confidence
in range, `qc_flag` in `CLASS_NAMES`). This is slow (real Cellpose-SAM +
EfficientNet-B0 inference) by design — it's the one place in the suite that's
supposed to prove the shipped models actually run, matching the CI split
already established (light/stubbed suite on every push, heavy/real pipeline
run manually or CI-optional).

## 7. Open questions for the upgrade (flag, don't resolve here)

1. **`config/` vs `configs/`.** Spec assumes `configs/`; repo has `config/`.
   Recommend the upgrade extends `config/` (adds `config/noise.yaml`,
   `config/quality.yaml`, etc. alongside `config/lines/`) rather than
   introducing a second, near-identical top-level directory — but this is a
   naming call for the human, not made unilaterally here.
2. **Where does `culture/cache.py` and friends live relative to the two Space
   copies?** New `culture/` modules need a `sync_space.py` run before either
   Space is pushed (§1). The compute cache itself (Slice 1b) should almost
   certainly **not** be synced into either Space — it's a Mac/Colab-side
   artifact store, not something the CPU-only product API needs at request
   time. Worth being explicit in Slice 1b about what stays local vs. what (if
   anything) ships to a Space.
3. **`RecordWriter`'s O(n) tail-hash scan** (§3.6) — fine for today's
   demo-scale logs, worth watching once per-flask history logs accumulate
   many visits per lineage over the life of the demo/pilot.
4. **The Qwen2-VL-2B vs. Qwen3-VL-8B mismatch** (§3.4) between what's wired
   in code and what the spec's §0.1 cites as the rejected VLM baseline —
   trace the 29% figure's source before Slice 8 restates it.
5. **`model_weights_hash` is schema-present but always `None`** (§3.6) — the
   upgrade's cache keying and manifest both need real weight hashes; decide
   where that hash gets computed (at model-load time, into a module-level
   constant both `pipeline.py` and the new `cache.py` can read) rather than
   each new module reimplementing it.
6. **Eight of the nine cell lines in `demo/app.py`'s dropdown have no
   `config/lines/*.yaml`** — they silently use `DEFAULT_CONFIG` thresholds
   under their own name. Not a bug today (demo-only), but the spec's
   lineage/segment model (Slice 2) stores `cell_line` per segment and may
   want real per-line configs to exist before growth-model defaults
   (Slice 3) are tuned per line.
