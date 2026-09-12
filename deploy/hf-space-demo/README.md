---
title: cultureQC Demo
emoji: 🧫
colorFrom: green
colorTo: blue
sdk: gradio
sdk_version: "5.50.0"
app_file: app.py
python_version: "3.11"
pinned: false
license: mit
short_description: Upload a brightfield image, see the raw model output
---

# cultureQC — raw model demo

Upload one brightfield / phase-contrast image and see exactly what
`culture.pipeline.analyze()` produces: the segmentation mask, the Grad-CAM
heatmap, the confluency estimate, the QC verdict, and the full JSON record —
no branding, no dashboard, just the model's own output.

This is not the product. The product frontend is
[cultureqc.vercel.app](https://cultureqc.vercel.app); its backend is the
separate `LongGrainRice/cultureqc-api` Space (`deploy/hf-space/`, plain FastAPI
on CPU Basic, no ZeroGPU). This Space exists so a link can go to one person and
they can see raw output directly in the browser, and — because it is a Gradio
SDK Space — it can run on ZeroGPU instead of CPU.

## Why a second Space instead of one

ZeroGPU is a Gradio-only feature — Docker Spaces cannot schedule onto it — and
its quota is per visitor, not a shared budget a backend can draw on for every
request the product frontend makes. Sharing this one Space between "the
product's API" and "a demo with GPU bursts for whoever opens the link" would
mean the product loses reliability for a hardware model that fits neither use
case well. Splitting them means each Space does one job on the hardware suited
to it.

## Running it yourself

```bash
python deploy/sync_space.py   # refreshes culture/ and config/ from the repo root
cd deploy/hf-space-demo
pip install -r requirements.txt
python app.py                  # http://127.0.0.1:7860
```

`@spaces.GPU` is a no-op outside an actual ZeroGPU Space — locally, and on any
other hardware tier, this just runs on CPU (or a local GPU, if `torch.cuda`
finds one), same as `deploy/hf-space/api.py` does today.

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `CULTUREQC_LOG` | `/tmp/events_boot.jsonl` | where the per-boot chain is written |

Same per-boot audit-log caveat as `hf-space`: this Space's disk is wiped on
restart, so `prev_record_hash` links records within one boot only.

## Why `sdk_version: "5.50.0"` specifically

An earlier build pinned `5.9.1` and its `get_api_info()` raised
`TypeError: argument of type 'bool' is not iterable` on this app's own
`gr.JSON` output — a real bug in that release, reproduced locally against the
exact component set. It breaks `gradio_client`/the "Use via API" tab, not the
interactive Blocks UI. `5.50.0` (the last release before 6.0) does not have
it, confirmed the same way; `requirements.txt` deliberately does not list
`gradio` at all so this version stays pinned to whatever `sdk_version` says
instead of drifting on the next rebuild.
