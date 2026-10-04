---
title: cultureQC Review Console
emoji: 🧫
colorFrom: green
colorTo: blue
sdk: gradio
sdk_version: "6.26.0"
app_file: console.py
python_version: "3.11"
pinned: false
license: mit
short_description: cultureQC v0.4 review console (ZeroGPU)
---

# cultureQC v0.4 — review console

One phase-contrast image in: a Cellpose-SAM confluency reading at the cutoff
calibrated for the imaging setup, with the 90% error band measured for it, a
per-image anomaly check, a recommended action from `rules_v0.5`, and a
hash-chained record.

- **v0.4 site:** https://cultureqc-cvoy.vercel.app
- **Source:** https://github.com/n1tishc/cultureqc/tree/slice-1b-compute-cache
  (the README's results table gives every number below its source file)

## What it shows

- **Analyze.** Seven precomputed examples: held-out C2C12 frames, including a
  contamination stress test with bacteria pasted 16.5× too large and the same
  kind of frame at real size, and two EVICAN images with expert masks. The
  EVICAN images are read with the EVICAN calibration profile and its error
  band; the C2C12 microscope has no labelled images, so it has no profile and
  its readings carry no band. Each example is labelled "Precomputed example"
  with the script, device and date that made it; they open instantly and use
  no GPU. **Analyze** runs any image live, with the setup picked in the
  console, on a GPU attached for that call only (ZeroGPU): median 3.28 s,
  measured before the calibration profiles (`results/live_latency_zerogpu.md`).
- **Calibration profiles.** One per imaging setup (`configs/confluency_profiles.yaml`):
  a cutoff fitted on labelled images from that setup and a 90% error band
  measured on images left out of the fit (`results/confluency_profiles.md`).
  A passage needs the band to clear the target; otherwise a person decides.
- **Flask Timeline.** Five held-out C2C12 time-lapse recordings replayed as
  visits (two normal, three with simulated faults): 3-FOV confluency with its
  noise band, the quality gate, the anomaly flag and the passage forecast.
  Precomputed; no model runs.
- **Detectability.** Per fault type, what was tested, on what, and what was
  not detected.

**The QC classifier is demoted.** The EfficientNet-B0 classifier was trained
on synthetic tiles and calls 5.0% of real held-out C2C12 normal frames normal
(`results/classifier_c2c12.md`). It still runs and is written into each record
(`qc_used_in_decision: false`), is shown collapsed, and never feeds the action.

**Records.** Each live Analyze appends a record to a per-boot chain
(`CULTUREQC_LOG`, default `/tmp/events_boot.jsonl`). Space storage is wiped on
restart, so links run within one boot only. A chain alone doesn't catch a full
rewrite or a deleted tail; that takes an anchored checkpoint
(`python -m culture.records checkpoint`; `docs/audit_mapping.md`).

**Licences.** `license: mit` above covers the code. Model weights and datasets
carry their own licences: the Cellpose-SAM weights are trained on CC BY-NC
data, so the pipeline as built is not cleared for commercial use pending
review (README, "Licences and commercial use").

## Running and publishing

```bash
python deploy/sync_space.py   # mirrors culture/, config/, configs/, demo/ and the anomaly banks in
cd deploy/hf-space-demo
pip install -r requirements.txt
python console.py              # http://127.0.0.1:7860
```

- **Publish:** `.venv/bin/python deploy/publish_demo_space.py` from the repo
  root. It syncs first and refuses to upload unless the anomaly banks match
  `configs/anomaly.yaml`. Then run `scripts/space_dry_run.py`.
- **Hardware:** ZeroGPU. `zerogpu.py` is used only when `SPACES_ZERO_GPU` is
  set; a dedicated GPU tier, CPU, and the Mac (`deploy/run_console_mac.sh`)
  and Colab (`nb/05_console_colab.ipynb`) backups run `console.py` without it.
  On CPU the precomputed examples and replays still work; a live Analyze
  takes minutes (V9: 689 s per FOV).
- **Startup log:** `cuda: True`, `anomaly banks verified`, and the model
  warm-up time. Anything else means the call runs on the precomputed examples.
- **Gradio:** the console uses Gradio 6 APIs, so `sdk_version` is 6.26.0.

## The raw-output page (`app.py`)

`app.py`, kept beside `console.py`, is the v0.2 raw-output page that runs,
unchanged, on `LongGrainRice/cultureqc-demo`; the console publish doesn't
touch that Space or `LongGrainRice/cultureqc-api`. To run it here instead, set
`app_file: app.py` **and** `sdk_version: "5.50.0"` (below).

## Why `sdk_version: "5.50.0"` specifically

An earlier build pinned `5.9.1` and its `get_api_info()` raised
`TypeError: argument of type 'bool' is not iterable` on this app's own
`gr.JSON` output — a real bug in that release, reproduced locally against the
exact component set. It breaks `gradio_client`/the "Use via API" tab, not the
interactive Blocks UI. `5.50.0` (the last release before 6.0) does not have
it, confirmed the same way; `requirements.txt` deliberately does not list
`gradio` at all so this version stays pinned to whatever `sdk_version` says
instead of drifting on the next rebuild.
