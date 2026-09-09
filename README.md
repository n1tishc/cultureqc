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
On the same benchmark, thresholding is off by ~31 percentage points where this
is off by 2.3 — the difference between passaging a flask and doing nothing.

The differentiator is not raw accuracy though; it is **explainability and
auditability**. Comparable tools show a mask and a number. This draws the
Grad-CAM regions that caused the flag, and writes every decision to a
tamper-evident log you can re-verify later.

## The four outputs

`analyze()` returns all four in one record, so a number, its evidence, the
decision it drove, and the proof cannot drift apart.

| Output | Detail |
|---|---|
| **Confluency** | Cellpose-SAM (`cpsam_v2`) probability map. 2.3 pp mean absolute error, zero-shot across morphologies. A threshold baseline is computed alongside for comparison. |
| **QC flag** | EfficientNet-B0 over a centred 256×256 tile: `normal`, `contamination_suspected`, `detachment`, `image_quality`. 98% test accuracy, 100% contamination recall at every severity. |
| **Evidence** | Up to 8 Grad-CAM bounding boxes showing the regions behind the flag, mapped back to full-image coordinates. |
| **Action** | Deterministic rules over confluency + flag + timing: `passage`, `feed`, `hold`, `human_review`. No model decides this. |

Each analysis is appended to a hash-chained JSONL log (`culture/records.py`,
28-field schema in `culture/schema.json`). Every record carries the SHA-256 of
the one before it, so altering any record breaks every link after it.

```bash
python -m culture.records events.jsonl
```

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
  sync_space.py     mirrors culture/ + config/ into the Space
  README.md         deployment runbook

site/             the landing page
  src/template.html the readable source — edit here, never index.html
  src/assemble.py   inlines fonts, images and data into one file
  index.html        generated. What Vercel serves.

demo/app.py       Gradio console, the human review surface
scripts/          dataset prep and contamination synthesis
config/lines/     per-cell-line thresholds
test-data/        real phase-contrast tiles + synthetic challenge cases

docs/
  DATA.md           training data: what it is, how to regenerate it
  audit_mapping.md  record fields mapped to audit requirements
  PRODUCT.md, DESIGN.md, UI_PLAN.md   working documents for the demo surfaces
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

**Run the page and the API together**, on one origin:

```bash
python deploy/hf-space/api.py     # http://127.0.0.1:7860
```

**Run the console:**

```bash
python demo/app.py
```

## Tests

```bash
python -m pytest deploy/hf-space/test_api.py -q     # 23 API contract tests
```

These cover readiness semantics, input validation, the response contract, the
evidence-box arithmetic, the CORS allowlist, and that concurrent uploads cannot
break the hash chain. Models are stubbed — the concurrency test is the exception
and drives the real `RecordWriter`, because the bug it guards is in the write
path rather than in inference.

Because the models are stubbed, the suite needs no torch and no cellpose and
runs in seconds; `.github/workflows/tests.yml` lists the light dependency set and
also checks that the Space mirror and `site/index.html` are in sync with their
sources on every push.

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

### Why the frontend is one HTML file and not a React app

There is one interactive surface — drop images, watch them hash, read the
verdicts, verify the chain — and no routing, no shared state worth a store, and
no component reuse across pages. A bundler would add `node_modules`, a build
step, and a second thing that can fail on deploy, to render markup that a
single file already renders. `site/src/assemble.py` is the build step: it inlines
the fonts, images and reference data into `site/index.html`, which is what Vercel
serves. Edit `site/src/template.html` and rebuild; never edit `index.html`.

## License

MIT — see [LICENSE](LICENSE).
