---
title: cultureQC API
emoji: 🔬
colorFrom: green
colorTo: blue
sdk: docker
pinned: false
license: mit
app_port: 7860
---

# cultureQC API

Confluency, a QC flag with visual evidence, a recommended action, and a
hash-chained record — from one brightfield / phase-contrast image.

This Space runs `culture.pipeline.analyze()`, the same entry point an automation
platform would call. Nothing is approximated: every number in a response was
produced by Cellpose-SAM and the EfficientNet-B0 QC classifier on the image you
sent.

## Routes

| Route | Purpose |
|---|---|
| `GET /health` | readiness, including `models_loaded` while warming up |
| `POST /analyze` | multipart: `image`, `cell_line`, `target_confluency` |
| `GET /docs` | generated OpenAPI browser |

```bash
curl -X POST https://longgrainrice-cultureqc-api.hf.space/analyze \
  -F "image=@field.tif" \
  -F "cell_line=Huh7" \
  -F "target_confluency=80"
```

## Warm-up

Both models load at startup on a background thread, so `/health` answers
immediately and reports `models_loaded: false` until they are resident. While
warming, `/analyze` returns **503** with a `Retry-After` header rather than
queueing — a caller can show a warming state instead of appearing to hang.

Cold boot is roughly 60–90 seconds, most of it downloading the Cellpose-SAM
weights and the QC checkpoint from the Hub. A Space that has gone to sleep pays
this again on the next request.

Analysis itself is CPU-bound: expect **10–20 seconds** per image. Do not set a
short client timeout; 60 seconds is a sensible floor.

## Evidence boxes

`evidence_boxes` are `[x1, y1, x2, y2]` as **fractions of the full image**, not
pixels. The classifier reads a centred 256×256 crop, so a box is mapped back to
the whole field by offsetting its origin while its width and height stay in tile
pixels. `analysed_region` reports that crop size, so a caller can state which
region was actually read rather than implying the whole frame was.

`overlay_image_base64` is `null` unless you pass `include_overlay=true`. A client
that draws its own boxes gains nothing from it and would pay a few hundred KB per
image — which matters when a batch is 200 files.

## The audit log is per-boot

`analyze()` appends each record to a hash-chained JSONL log. **A Space's disk is
wiped when it restarts**, so that chain links records within one boot and no
further; `prev_record_hash` continuity across restarts is not something this
deployment can honestly claim, and `/health` says so in its `audit` field.

Each record remains independently verifiable — the canonical JSON hashes to
`record_hash` — and the browser client builds and verifies its own chain across
an upload batch, which is where continuity actually lives for a visitor.

For a durable chain, enable persistent storage on the Space and point
`CULTUREQC_LOG` at a path under `/data`.

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `CULTUREQC_LOG` | `/tmp/events_boot.jsonl` | where the per-boot chain is written |

CORS allows the production frontend, Vercel preview deployments, and localhost
dev servers. Uploads are capped at 64 MB.
