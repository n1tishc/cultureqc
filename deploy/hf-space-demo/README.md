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

Local source (2026-10-19): one supported microscopy image in, a confluency
reading and setup-specific error band when available, explicit check status,
an advisory result from `rules_v0.7`, and a schema `0.8` hash-chained record.
All current decisions have `host_actionable: false`; no shipped profile is
eligible to authorize passage. Calibration alone does not validate an action.
The precomputed examples retain historical schema `0.4` / `rules_v0.5`.
This README does not verify the deployed Space revision or authorize publishing.
See `docs/specs/release-state.md` in the source repository for the surface map.

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
  no GPU. **Analyze** accepts supported single-frame uint8 grayscale/RGB files,
  with the setup picked in the console; unsupported encoding is refused before
  inference. A configured C2C12 quality gate runs; profiles without one report
  it unavailable, not passed. On ZeroGPU, a GPU is attached for that call only.
  Historical latency (2026-10-11, not a benchmark of current local source): median 3.27 s in
  the first run after a restart and 6.22 s in the second, where two took 17–19 s
  (`results/space_dry_run_712a9e54.md`, `results/space_dry_run_712a9e54_run2.md`).
- **Fine-tuned demo set.** Four test images from one lab (mCellSeg, Alam et al.
  2026, CC BY 4.0, Zenodo record 20174259) have buttons under the examples.
  For these four only, a Cellpose-SAM model fine-tuned on 79 other images from
  that lab (`mcellseg_ftF_r2`) reads the image too, and its reading is shown
  in a second card beside the shipped one: "not validated", it decides
  nothing, and the record keeps it in `finetuned_reading`. The images are
  matched by the SHA-256 of the exact file: any other image, including a
  changed copy of one of them, gets no fine-tuned reading. Before every reading its weights are checked against the
  approved change record (`configs/approved_changes.jsonl`); a mismatch shows
  "No reading". Results: `results/confluency_mcellseg.md`.
- **Calibration profiles.** One per imaging setup (`configs/confluency_profiles.yaml`):
  a cutoff fitted on labelled images from that setup and a 90% error band
  measured on images left out of the fit (`results/confluency_profiles.md`).
  A band clearing the target is not enough: approved decision scope, eligibility,
  required checks and timing are separate policy gates. Shipped profiles remain
  passage-ineligible, and every current output is advisory.
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
review (README, "Licences and commercial use"). The fine-tuned weights inherit
those terms; they are not in this Space and not published. The four demo
images are mCellSeg's, CC BY 4.0.

## Running and publishing

```bash
python deploy/sync_space.py   # mirrors culture/, config/, configs/, demo/, the anomaly banks and the demo images in
cd deploy/hf-space-demo
pip install -r requirements.txt
python console.py              # http://127.0.0.1:7860
```

- **Publish only after explicit owner approval:** `.venv/bin/python deploy/publish_demo_space.py` from the repo
  root. It syncs first and refuses to upload unless the anomaly banks match
  `configs/anomaly.yaml` and the four demo images are the listed files, or if
  any file over 500 MB (weights) is in the folder. Then run
  `scripts/space_dry_run.py`.
- **Fine-tuned weights:** downloaded at startup from the private model repo
  `LongGrainRice/cultureqc-finetuned` (uploaded once with
  `scripts/upload_finetuned_weights.py`), read with the Space secret
  `CULTUREQC_HF_TOKEN` (a read-only token for that repo). Without them the
  demo set stays off and the console runs as before. The Space variable
  `CULTUREQC_FINETUNED` set to empty turns the demo set off without a
  republish.
- **Hardware:** ZeroGPU. `zerogpu.py` is used only when `SPACES_ZERO_GPU` is
  set; a dedicated GPU tier, CPU, and the Mac (`deploy/run_console_mac.sh`)
  and Colab (`nb/05_console_colab.ipynb`) backups run `console.py` without it.
  On CPU the precomputed examples and replays still work; a live Analyze
  takes minutes (V9: 689 s per FOV).
- **Startup log:** `cuda: True`, `anomaly banks verified`,
  `fine-tuned demo set on: … weights match, 4 of 4 demo images present`, and
  the model warm-up time. Anything else means a demo runs on the precomputed
  examples, or without the demo set.
- **Gradio:** the console uses Gradio 6 APIs, so `sdk_version` is 6.26.0.

## The raw-output page (`app.py`)

`app.py`, kept beside `console.py`, is the legacy raw-output entry point. Local
ingestion fixes do not establish what is running on `LongGrainRice/cultureqc-demo`;
its remote revision has not been reverified. The console publish doesn't
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
