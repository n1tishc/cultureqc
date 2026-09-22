# cultureQC

**One brightfield image in. Four bound outputs, and a record you can verify.**

[Live demo](https://cultureqc.vercel.app) · [API](https://longgrainrice-cultureqc-api.hf.space/docs)

[![tests](https://github.com/n1tishc/cultureqc/actions/workflows/tests.yml/badge.svg)](https://github.com/n1tishc/cultureqc/actions/workflows/tests.yml)
[![license: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

cultureQC reads a phase-contrast image of a cell culture and returns a confluency
estimate, a QC flag with visual evidence of *where* it is looking, a recommended
action, and a hash-chained audit record — from a single call.

```python
from culture.pipeline import analyze

record = analyze("field.tif", flask_id="F-01", cell_line="Huh7")
record["confluency_pct"]        # 13.45
record["qc_flag"]               # "contamination_suspected"
record["recommended_action"]    # "human_review"
record["record_hash"]           # sha256 over the canonical JSON, linked to the previous record
```

It is built for **automation, not the bench**: something calls `analyze()` per
captured image, and a human only steps in when it flags an exception or audits
the trail afterwards.

## Why it exists

Classical thresholding measures brightness, and confluency is not brightness.
On the same **synthetic** benchmark, thresholding is off by ~31 percentage
points where this is off by 2.3 — the difference between passaging a flask
and doing nothing. On real, independently-collected microscopy the gap is
narrower but still real: 11.2pp vs. 8.4pp — see
[Validation on real images](#validation-on-real-images).

The differentiator is not raw accuracy though; it is **explainability and
auditability**. Comparable tools show a mask and a number. This draws the
Grad-CAM regions that caused the flag, and writes every decision to a
tamper-evident log you can re-verify later.

## The four outputs

`analyze()` returns all four in one record, so a number, its evidence, the
decision it drove, and the proof cannot drift apart.

| Output | Detail |
|---|---|
| **Confluency** | Cellpose-SAM (`cpsam_v2`) probability map. 2.3 pp mean absolute error on a **synthetic** benchmark, zero-shot across morphologies; 8.4 pp on real held-out microscopy (see below). A threshold baseline is computed alongside for comparison. |
| **QC flag** | EfficientNet-B0 over a centred 256×256 tile: `normal`, `contamination_suspected`, `detachment`, `image_quality`. 98% test accuracy, 100% contamination recall at every severity. |
| **Evidence** | Up to 8 Grad-CAM bounding boxes showing the regions behind the flag, mapped back to full-image coordinates. |
| **Action** | Deterministic rules over confluency + flag + timing: `passage`, `feed`, `hold`, `human_review`. No model decides this. |

Each analysis is appended to a hash-chained JSONL log (`culture/records.py`,
28-field schema in `culture/schema.json`). Every record carries the SHA-256 of
the one before it, so altering any record breaks every link after it.

```bash
python -m culture.records events.jsonl
```

## Validation on real images

`analyze()`'s confluency figures above are measured two ways: 2.3 pp MAE is
**synthetic** (LIVECell backgrounds + composited artifacts); a second pass
runs the *unretuned, shipped* pipeline against **real (EVICAN, CC BY 4.0)**
held-out microscopy this model was never tuned or trained on:

| Method | Real-image MAE (pp, n=33) | Provenance |
|---|---:|---|
| **cultureQC** (`cpsam_v2`, probmap) | **8.35** | real (EVICAN eval2019 subset) |
| Global-threshold baseline | 11.20 | real (EVICAN eval2019 subset) |

Both real-data numbers are markedly higher than their synthetic counterparts
(2.3 pp and ~31 pp respectively) — expected, and the reason this repo runs a
separate real-data pass rather than resting on the synthetic figure alone.
cultureQC's error is **not random noise**: it's a systematic under-prediction
that gets worse as true confluency rises (fit: `predicted ≈ -3.0 + 0.73 ×
GT`), visible in the overlay gallery as segmented cell boundaries sitting
measurably inside the true cell edge once cells start touching. EVICAN's
held-out split has almost no images in the 60–90% confluency band passage
decisions are actually made in (1 of 98); the one that exists produced a
**0.00% prediction against a 65% ground truth** — reported rather than
omitted. Full numbers, error analysis, and the dataset/license verification:
[`results/confluency_real_summary.md`](results/confluency_real_summary.md),
[`docs/DATASETS.md`](docs/DATASETS.md).

Try it yourself: the demo console (`python demo/app.py`) has a "Real images
(EVICAN)" example row showing one accurate case and one real error case
side by side, ground truth included.

## Compute cache & FOV noise

Slice 1b runs every model over every image the project needs once, on a
Colab GPU, and stores raw outputs (prob maps, logits, embeddings, quality
metrics) keyed by `(image_sha256, crop_spec, model_name, model_version)` —
everything downstream (thresholds, calibration, crop choices) reads from
this cache on CPU with zero recompute:

| | |
|---|---:|
| Images cached | 4,246 (4,000 synthetic tiles + 98 EVICAN + 148 AutoQC-Bench test) |
| Confluency rows (full-frame + FOV-noise crops) | 72,182 |
| Full-pass wall time (Colab GPU) | 147.7 min |
| Cache size (full / slim no-GPU Mac copy) | 0.30 GB / 0.06 GB |

Before any GPU time was spent, a parity test confirmed the cache's numbers
exactly match the live (unretuned) pipeline on the same images
(`tests/test_cache_parity.py`, 4/4 pass) — the cache stores raw model
output, never a retuned one. Full provenance, per-model budget-test timing,
and the notebooks themselves: [`docs/DATASETS.md`](docs/DATASETS.md),
`nb/00_download_datasets.ipynb`, `nb/02_compute_cache.ipynb`.

**FOV noise floor** (§4.3): repositioning the same flask produces confluency
swings even when nothing biologically different has happened — this is the
measurement noise the temporal layer (Slices 2-5) must exceed before
flagging a real change, computed entirely from cached crops (no separate
GPU pass). On 246 real images (EVICAN + AutoQC-Bench test):

| crop size (frac of FOV) | mean noise (pp) | fit |
|---:|---:|---|
| 0.25 | 6.1 | `sigma_fov = 0.27 + 1.06 × confluency_pct` (R²=0.73) |
| 0.5 | 2.9 | `sigma_fov = 0.51 + 0.42 × confluency_pct` (R²=0.53) |

Smaller crops are noisier (expected — less area per estimate), and noise
rises with confluency in both cases. Full numbers, plot, and fit details:
[`results/fov_noise_summary.md`](results/fov_noise_summary.md). Model saved
to `configs/noise.yaml` for later slices to import directly.

## Layout

```
culture/          the library — this is the product
  pipeline.py       analyze(): image -> record. The integration surface.
  seg.py            confluency (Cellpose-SAM, plus a threshold baseline)
  qc.py             the classifier and its Grad-CAM evidence
  rules.py          deterministic action decisions
  records.py        hash-chained JSONL writer + verifier
  rationale.py      plain-language explanation of a decision
  schema.json       the output contract

deploy/           how it ships
  hf-space/         FastAPI service; the HuggingFace Space, pushable as-is
  hf-space-demo/    Gradio + ZeroGPU demo Space, raw model output, no product UI
  sync_space.py     mirrors culture/ + config/ into both Spaces
  publish_space.py, publish_demo_space.py   push each Space via the Hub API
  README.md         deployment runbook

site/             the landing page — React + Vite
  src/              components, hooks, styles.css + refinements.css + instrument.css
  src/data.json     generated: real pipeline output the page renders
  assets/           source images, fonts and the scripts that build them
  public/           what ships as-is: og.png, favicon.png, img/

demo/app.py       Gradio console, the human review surface
scripts/          dataset prep and contamination synthesis
config/lines/     per-cell-line thresholds
test-data/        real phase-contrast tiles + synthetic challenge cases

docs/
  DATA.md           training data: what it is, how to regenerate it
  DATASETS.md       real-data license/overlap verification (EVICAN, LIVECell, AutoQC-Bench, ...)
  REPO_MAP.md       repo recon: what's where, as of the v2.1 upgrade's start
  audit_mapping.md  record fields mapped to audit requirements
  PRODUCT.md, DESIGN.md, UI_PLAN.md   working documents for the demo surfaces

nb/               Colab notebooks (thin runners around culture/ + scripts/)
  00_download_datasets.ipynb   fetch/regenerate real + synthetic image sets
  02_compute_cache.ipynb       the batched GPU pass (Slice 1b)
```

Training data is not tracked — it is downloaded and derived, and regenerating it
is two commands. See [`docs/DATA.md`](docs/DATA.md). Nothing in the library, the
API or the site build depends on it.

## Getting started

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -c "from culture.pipeline import analyze; print(analyze('test-data/contam_00015.png'))"
```

Model weights download on first use — Cellpose-SAM from its own package, the QC
classifier from [`LongGrainRice/cultureqc-qc-effnetb0-v1`](https://huggingface.co/LongGrainRice/cultureqc-qc-effnetb0-v1).
Expect a slow first call.

**Run the page and the API together.** Two processes; the dev server proxies the
API calls, so the browser sees one origin:

```bash
python deploy/hf-space/api.py       # http://127.0.0.1:7860
cd site && npm install && npm run dev   # http://localhost:5173
```

**Run the console:**

```bash
python demo/app.py
```

## Tests

```bash
python -m pytest deploy/hf-space/test_api.py -q     # 28 API contract tests
```

These cover readiness semantics, input validation, the response contract, the
evidence-box arithmetic, the CORS allowlist, and that concurrent uploads cannot
break the hash chain. Models are stubbed — the concurrency test is the exception
and drives the real `RecordWriter`, because the bug it guards is in the write
path rather than in inference.

Because the models are stubbed, the suite needs no torch and no cellpose and
runs in seconds. `.github/workflows/tests.yml` lists the light dependency set,
and adds two drift checks on every push: that the Space mirror still matches
`culture/`, and that `site/src/data.json` still matches the pipeline output it
was generated from.

```bash
.venv/bin/python -m pytest tests/test_smoke_pipeline.py -v   # real pipeline, ~1 min
```

This one drives real Cellpose-SAM + EfficientNet-B0 inference on a `test-data/`
fixture through `culture.pipeline.analyze()` — the one place the suite proves
the shipped models actually run and produce a self-consistent record (range
checks, hash chain, schema shape). Slow by design; not part of the fast CI
job. One check (`test_record_matches_schema`) is a documented `xfail`: it
found that `culture/schema.json`'s `confluency_method` enum and its
`additionalProperties: false` + missing `record_hash` property don't match
what the pipeline actually writes — a pre-existing drift, not a regression,
left for whoever next touches `schema.json`.

## Known limits

Stated here rather than discovered later.

**The QC classifier is trained entirely on synthetic contamination**, and the
100% recall above is measured at the sprites' native scale. Bacterial sprites are
composited onto real microscopy at their source optical scale, which is larger
relative to the cells than a real objective would show, so that figure is bounded
to that distribution rather than to real contaminated cultures. Rescaling the
sprite library and re-running the shipped classifier: at 0.45× only 6 of 12
contaminated tiles in the severity ladder were flagged, and at 0.2× the model
reads contamination as an image-quality artifact instead.

**Analysis is slow on CPU.** About a minute per image on 2 vCPU; roughly 20 s on
a fast laptop. A GPU changes this by about an order of magnitude, and
`culture/seg.py` selects the device automatically.

**`demo/app.py::_scale_bboxes` over-scales evidence boxes** on images larger than
256px. The Grad-CAM box is measured on a centred crop, so mapping it back should
offset the origin only — the box's own width and height stay in tile pixels. The
console still multiplies them by the full-image factor, drawing a box far wider
than the region actually read. `deploy/hf-space/api.py` has the correct mapping.

**The hosted audit chain is per-boot.** HuggingFace Space storage is wiped on
restart, so `prev_record_hash` links within one boot only. Records stay
individually verifiable, and the browser builds its own chain over an upload
batch. A durable chain needs persistent storage and `CULTUREQC_LOG=/data/...`.

## Deployment

The page is static on Vercel; the pipeline runs as a Docker Space on
HuggingFace. They are independent deployments joined by one URL, so neither can
break the other's build, and the page still hashes files and builds a verifiable
manifest when the API is asleep.

See [`deploy/README.md`](deploy/README.md).

### The frontend

React 18 on Vite, in `site/`. Nine routes behind a hash router (see
[`site/README.md`](site/README.md#workspace-views) for the table), and the
pieces worth naming: `Plate` (the specimen viewer with its mask, evidence boxes
and scan sweep), `Upload` (drop, unzip, hash, analyse, verify — all in the
browser), and `Chain` (recomputes nine SHA-256 digests on demand, and breaks
them on purpose so you can watch it fail).

```bash
cd site
npm install
npm run dev      # http://localhost:5173, proxying /health and /analyze to :7860
npm run build    # -> site/dist, which is what Vercel serves
npm run data     # regenerate src/data.json + public/img from pipeline output
```

Two rules the code depends on. `site/src/styles.css` drives state through
`data-*` attributes and CSS custom properties (`[data-mask]`, `[data-flagged]`,
`--nw`), so renaming a class or an attribute in a component breaks the design
silently. And `src/data.json` is generated by
`site/assets/build_data.py` from committed pipeline output — editing it by hand
would make the page show records that never existed.

## License

MIT — see [LICENSE](LICENSE).
