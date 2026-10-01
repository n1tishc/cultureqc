# cultureQC

**One brightfield image in. Confluency, an anomaly check, a recommended action, and a record you can verify.**

[Live demo](https://cultureqc.vercel.app) · [v0.3 site](https://cultureqc-cvoy.vercel.app) · [API](https://longgrainrice-cultureqc-api.hf.space/docs)

[![tests](https://github.com/n1tishc/cultureqc/actions/workflows/tests.yml/badge.svg?branch=slice-1b-compute-cache)](https://github.com/n1tishc/cultureqc/actions/workflows/tests.yml?query=branch%3Aslice-1b-compute-cache)
[![license: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

cultureQC reads a phase-contrast image of a cell culture and returns a
confluency estimate, a per-image anomaly check, a recommended action and a
hash-chained audit record, from a single call. A QC classifier also runs, but
it is **demoted**: recorded, not used for the action (see
[Known limits](#known-limits)).

```python
from culture.pipeline import analyze

record = analyze("field.tif", flask_id="F-01", cell_line="Huh7")
record["confluency_pct"]            # 13.45
record["anomaly_flag"]              # True / False: shown for review; a flag holds a passage
record["anomaly_used_in_decision"]  # True whenever the check ran (rules_v0.3)
record["qc_used_in_decision"]       # False while the classifier is demoted
record["recommended_action"]        # "passage" / "feed" / "continue" / "human_review"
record["record_hash"]               # sha256 over the canonical JSON, linked to the previous record
```

It is built for **automation, not the bench**: something calls `analyze()` per
captured image, and a human steps in when it flags an exception or audits the
trail afterwards.

## Architecture validation (Phase A)

Before building product surface around the per-flask design (history, growth
forecast, SPC and drift monitoring), we tested it on **real time-lapse
sequences with simulated visits**: 24 C2C12 phase-contrast sequences (Ker et
al. 2018, CC BY 4.0), about 85 h each, replayed as visits every 6 or 12 h with
1 or 3 randomly placed fields of view (FOVs) per visit. Faults were simulated
on the recorded frames: contamination, growth stall, lamp dimming. Sequences
were split 10 tuning / 14 held-out; every threshold was set on tuning and
every result below is on held-out. Full report, with each number's script:
[`docs/ARCHITECTURE_VALIDATION.md`](docs/ARCHITECTURE_VALIDATION.md).

| Check | Held-out result | Verdict |
|---|---|---|
| V1 Confluency on real images (EVICAN) | MAE 8.35 pp (n = 33), reads low; the 60–90% band has one image, read 0% against 65% | Pass; the passage band is not measurable |
| V2 Growth between visits vs FOV noise | median growth step ÷ FOV noise 0.35 (6 h) and 0.65 (12 h) at 1 FOV; 0.61 and 1.12 at 3 FOVs; needs 2 | **Fail** |
| V3 Passage forecast | median absolute error 1.9–9.0 h across visit settings (n = 5 sequences, 50% target) | No verdict: too few sequences, none reach 60–80% |
| V4 Density-conditioned anomaly removes the growth confound | Spearman ρ −0.16 binned vs −0.09 global | **Fail** |
| V5 Per-image anomaly flag vs contamination | AUROC 1.00 on simulated faults (n = 2 sequences, bacteria pasted at 16.5× their real size); 0.48 with the same simulated bacteria at their real size | Pass, on a small and exaggerated test; **Fail** at real size |
| V6 SPC on residuals | 3.75 false alarms per 100 visits; simulated contamination 0/2 and growth stall 0/2 detected | **Fail** |
| V7 Instrument vs culture | simulated lamp dimming raised the drift signal, but so did the normal fleet | **Fail** for single flasks |
| V8 Classifier calibration | ECE 0.0139 on synthetic test tiles (T = 1.5536) | Pass, synthetic only |
| V9 Live latency | 689 s per FOV on a 2-thread CPU approximation of the Space (V9, `results/live_latency.md`) | **Fail** |
| V10 Growth per experiment | confluency-area doubling time 12.4–17.7 h (medians) | Informational |

The QC classifier also **does not transfer to real frames**: it calls 5.0% of
held-out normal C2C12 frames "normal" (`results/classifier_c2c12.md`), and
matching the training pixel size does not fix it (B0,
`results/classifier_scale_test.md`).

**What this does and doesn't prove.** It ran the per-flask logic end to end on
real phase-contrast sequences under a tuning/held-out split, and showed where
it breaks. It is not RoboCell or Celltrio data: one cell line, one microscope,
three experiments. Cadence, FOVs per visit and FOV size are assumptions. Faults
are simulated, and held-out has 2 sequences per fault type. Confluency "truth"
for C2C12 is Cellpose-SAM's own full-frame reading, which V1 found reads about
8 pp low.

**What changed because of it** (owner decisions, 2026-09-26):

- The QC classifier is demoted: recorded and shown collapsed, not used for the action.
- The anomaly check stays as a per-image flag, for review. Anomaly
  scores and class probabilities are no longer trended over time.
- Since 2026-09-28 (`rules_v0.3`), a flag holds a passage: an image at or
  above the target that the anomaly check flags goes to human review instead
  of passage. Continue and feed are unchanged. At the replays' 50% target this
  held 1 of 14 passage-eligible held-out normal frames (review 5.8% instead of
  5.7%) and all 76 passage-eligible simulated contamination frames
  (`results/review_rate.md`). Those frames have bacteria 16.5× too large; at
  their real size the flag is at chance and the hold gives no protection
  (`results/contamination_scale.md`).
- SPC and the instrument-drift monitor stay in code and in the report, not in
  product decisions.
- Growth stalls are a stated limitation at the tested setup, turned into an
  [imaging requirement](#imaging-requirement) for instrument integration.
- The demo runs on precomputed, labelled examples and replays, with a GPU Space
  for the call day.

## Results and where they come from

Every number in this README comes from a script in this repo. **Synthetic**:
the classifier's own generated tiles. **Real**: real microscopy images.
**Simulated visits**: recorded C2C12 frames replayed as visits. **Simulated
faults**: faults added to real frames. `tests/test_readme_provenance.py`
checks that every number in the "Number" column appears in its source file.

| Result | Number | Provenance | Source |
|---|---|---|---|
| Confluency error, Cellpose-SAM | MAE 8.35 pp (n = 33); threshold baseline 11.20 pp | real (EVICAN) | `results/confluency_real_summary.md` |
| Confluency error, calibrated cutoff (validated, not shipped) | MAE 8.36 → 3.78 pp on the same 33, cutoff −3.5 picked on the other 65 eval2019 images; off by more than 10 pp: 13 → 3 | real (EVICAN) | `results/confluency_cutoff.md` |
| FOV sampling noise, 0.25-frame field | σ_fov = 2.828 + 0.2072 × confluency | real (C2C12) | `results/growth_signal_summary.md` |
| Growth step ÷ FOV noise (V2) | 0.35 / 0.65 at 1 FOV; 0.61 / 1.12 at 3 FOVs (6 h / 12 h) | real, simulated visits | `results/growth_signal_summary.md` |
| Passage forecast, 6 h visits, 3 FOVs (V3) | median absolute error 9.0 h; 90% interval covered 4/5 (n = 5 sequences, 50% target) | real, simulated visits | `results/growth_backtest.md` |
| Anomaly flag rate, held-out normal frames | 10.0% (target 5%) | real (C2C12) | `results/anomaly_summary.md` |
| Anomaly flag vs contamination (V5), bacteria 16.5× too large | AUROC 1.00 (simulated faults, n = 2 sequences) | simulated faults | `results/anomaly_summary.md` |
| Anomaly flag vs contamination, bacteria at real size | AUROC 0.48 (simulated faults, n = 2 held-out sequences); flagged on 1 of 97 frames, 4 of 97 without the bacteria; confluency a median 4.3 pp lower | simulated faults | `results/contamination_scale.md` |
| Anomaly flag vs lamp dimming | AUROC 0.47 (simulated faults) | simulated faults | `results/anomaly_summary.md` |
| Quality gate fail rate | normal 12.1%; contamination 91.8%; dimming 51.1% | real + simulated faults | `results/quality_gate_c2c12.md` |
| Sent to human review, held-out frames: boundary ambiguity above 0.70 (record `confidence` below 0.30) | 5.7% of 1228; 43.8% of the 160 at 40-60% confluency (14 sequences) | real (C2C12) | `results/review_rate.md` |
| Boundary ambiguity vs the reading's error (pre-registered; the score was named "confidence") | does not predict error: Spearman ρ −0.36 (95% CI −0.69 to +0.02), AURC 7.73 vs 8.35 pp in random order (p = 0.303), n = 33; tracks density: ρ −0.61 with expert confluency, −0.95 with the reading on 1228 held-out C2C12 frames | real (EVICAN, C2C12) | `results/confidence_vs_error.md` |
| Sent to human review: passage hold on an anomaly flag (since `rules_v0.3`), 50% target | held-out normal frames: 1 of 14 passage-eligible, total 71 (5.8%); simulated contamination with bacteria 16.5× too large (4 sequences, both splits): 76 of 76 passage-eligible; at real size no frame reaches the target | real (C2C12) + simulated faults | `results/review_rate.md` |
| SPC (V6; not in the product) | 3.75 false alarms / 100 visits; contamination 0/2; stall 0/2 | simulated faults | `results/spc_summary.md` |
| QC classifier accuracy, synthetic test tiles | 0.9801 (n = 653) | synthetic | `results/calibration_summary.md` |
| QC classifier calibration (V8) | ECE 0.0139 (T = 1.5536) | synthetic | `results/calibration_summary.md` |
| QC classifier on real normal frames | 5.0% called normal (n = 1228) | real (C2C12) | `results/classifier_c2c12.md` |
| Live latency on CPU (V9) | 689 s per FOV at 1392 × 1040 | real-size input, 2-thread CPU | `results/live_latency.md` |
| Live latency, console Space on ZeroGPU (one Analyze as the viewer waits, with the owner's token) | median 3.28 s (n = 6, after a first of 6.45 s); flag and action the same as stored on 7 of 7 examples | real (C2C12, EVICAN) | `results/live_latency_zerogpu.md` |
| Live latency, Mac backup (Cellpose-SAM on Apple MPS) | median 16.43 s per 1392×1040 C2C12 frame (n = 5); flag and action the same as stored on 7 of 7 examples | real (C2C12, EVICAN) | `results/live_latency_mac_mps.md` |
| Live latency, Colab backup (Tesla T4) | median 12.06 s per 1392×1040 C2C12 frame (n = 5); flag and action the same as stored on 7 of 7 examples | real (C2C12, EVICAN) | `results/live_latency_colab_gpu.md` |

The contamination faults paste DeepBacs bacteria imaged at 79 nm/px into
1.3 µm/px frames, so they are 16.5× too large. Rebuilt with the bacteria at
their real size (same frames, seed and density, frozen thresholds), the flag is
at chance and confluency does not rise
([report, V5](docs/ARCHITECTURE_VALIDATION.md#v5--per-visit-anomaly-separation);
`results/contamination_scale.md`, with a side-by-side image in
`results/contamination_scale_examples.png`).

## The outputs

`analyze()` returns everything in one record, so a number, the decision it
drove, and the proof cannot drift apart.

| Output | Detail |
|---|---|
| **Confluency** | Cellpose-SAM (`cpsam_v2`) probability map. 8.35 pp mean absolute error on real held-out EVICAN images, reading low (V1). A threshold baseline is computed alongside for comparison. Shown with its **boundary ambiguity**, the share of pixels near the cutoff (min(1, 4 × share within ±1 logit); the record stores 1 − it as `confidence`). Above 0.70 the rules send the image to review. It is a density-sensitive review trigger, not an error estimate: it does not predict the reading's error ([below](#known-limits)). |
| **Anomaly check** | DINOv2-small patch distances on the 256 px centre tile against banks of normal C2C12 patches, one per confluency bin; flag = score above the bin's 5%-FPR threshold, with a patch heatmap (`culture/anomaly.py`, `configs/anomaly.yaml`). Shown for review; a flag turns `passage` into `human_review` (continue and feed unchanged). Uncalibrated outside the tested imaging setup; see [Site calibration](#site-calibration). |
| **Action** | Deterministic rules (`rules_v0.4`) over confluency, timing and the anomaly flag (plus the QC flag only when the classifier is not demoted): `passage`, `feed`, `continue`, `human_review`. No model decides this. `continue` (keep culturing, no action now) was called `hold` up to `rules_v0.3`; v0.4 changed the label only, and every decision is the same ([CHANGELOG](CHANGELOG.md)). |
| **QC classifier (demoted)** | EfficientNet-B0 over the centred 256 px tile: `normal`, `contamination_suspected`, `detachment`, `image_quality`. Trained on synthetic tiles only; accuracy 0.9801 on synthetic test tiles, but 5.0% of real held-out C2C12 normal frames are called normal. Temperature-scaled (`configs/calibration.yaml`). Recorded and shown collapsed; not used for the action, and no Grad-CAM evidence is drawn while demoted (`configs/qc.yaml`). |
| **Record** | Appended to a hash-chained JSONL log (`culture/records.py`, 40-field schema in `culture/schema.json`), with the model versions and the SHA-256 of every config it used. The console's records also carry `confluency_map_hash`, the SHA-256 of the Cellpose-SAM map the confluency was counted from (1/4 resolution, int16), so the 3D view below can be checked against the record. Every record carries the SHA-256 of the one before it. Editing a record breaks its own hash or, if that hash is recomputed, the next link. Rewriting every later record, or deleting the newest ones, is caught only against an anchored checkpoint: the record count and head hash, stored outside the log ([audit mapping](docs/audit_mapping.md#the-chain)). |

```bash
python -m culture.records verify events.jsonl                  # the chain alone
python -m culture.records checkpoint events.jsonl -o cp.json   # store cp.json outside the log
python -m culture.records verify events.jsonl --checkpoint cp.json
```

## Flask timeline: replays of recorded time-lapse

The console's **Flask Timeline** tab shows five replays of held-out C2C12
sequences (two normal, contamination onset, growth slowdown, lamp dimming),
precomputed by `scripts/export_demo_replays.py` into `demo/replays/*.json`, so
the tab needs no cache and no model. Every replay is labelled as a replay of
recorded time-lapse with simulated visits. Per visit it shows:

- confluency, the mean of 3 FOVs, with its FOV-noise band;
- the quality gate: a failed visit gets REIMAGE and leaves the trend;
- the per-image anomaly flag;
- one passage forecast, made when confluency first reaches target − 10 and
  captioned with its backtest (n = 5 sequences, 50% target).

The contamination replay is captioned as an exaggerated-scale stress test. The
slowdown replay shows no flag: at this setup, one visit's growth is smaller
than the FOV noise (V2).

**Growth model** (`culture/growth.py`): each segment's quality-passing visits
are fitted with a logistic and a Gompertz curve, weighted by
`1/(confluency_sd² + σ_fov²)`, chosen by AIC. Time to target comes in closed
form, with a 90% interval from a seeded residual bootstrap (500 resamples).
`NOT_REACHED` when the fitted plateau is below the target and
`INSUFFICIENT_DATA` below 5 visits are distinct outcomes, never a made-up
crossing. It also reports an area doubling time (`ln2 / r`, early phase): a
rate of confluency, not cell doubling time. `results/growth_backtest_synthetic.md`
is a harness check on synthetic curves, not an accuracy result.

**History and replay** (`culture/history.py`, `culture/replay.py`):
append-only, hash-chained lineage → segments → visits and events, one JSONL file
per lineage; trend functions refuse to mix visits across a `model_versions`
change. Replay builds visit streams from the compute cache (jittered
timestamps, repositioned FOVs, simulated passage) with no model inference;
every replayed visit is labelled `"provenance": "replay_simulated"`.

## Validation on real images

Confluency was checked with the *unretuned, shipped* pipeline on held-out
EVICAN images (CC BY 4.0) that the model was never tuned or trained on:

| Method | Real-image MAE (pp, n = 33) | Provenance |
|---|---:|---|
| **cultureQC** (`cpsam_v2`, probmap) | **8.35** | real (EVICAN eval2019 subset) |
| Global-threshold baseline | 11.20 | real (EVICAN eval2019 subset) |

cultureQC's error is **not random**: it under-reads, and more so as
confluency rises, with segmented boundaries sitting inside the true cell edge
once cells touch. EVICAN's held-out split has almost no images in the 60–90%
band where passage decisions are made (1 of 98); that one produced a **0.00%
reading against 65% ground truth**, reported rather than omitted. Full numbers
and the dataset licence check:
[`results/confluency_real_summary.md`](results/confluency_real_summary.md),
[`docs/DATASETS.md`](docs/DATASETS.md).

## Measurement noise

Moving the field of view on the same flask changes the confluency reading even
when nothing biological has changed. Measured from cached crops of 2,088 C2C12
frames (`results/fov_noise_c2c12_summary.md`), the mean SD across repositioned
crops is 6.593 pp for 0.25-frame fields and 2.891 pp for 0.5-frame fields, and
it rises with confluency. The 0.25-frame fit (`configs/noise.yaml`,
`entries.c2c12`) sets the replays' noise band and the growth fit's weights.

All model outputs come from one **compute cache**: every model run once over
every image on a Colab GPU, raw outputs (probability maps, logits, embeddings,
quality metrics) keyed by `(image_sha256, crop_spec, model_name,
model_version)`. Everything downstream reads it on CPU. A parity test confirmed
that the cache matches the live pipeline on the same images
(`tests/test_cache_parity.py`). Notebooks: `nb/02_compute_cache.ipynb`,
`nb/03_*`; provenance in [`docs/DATASETS.md`](docs/DATASETS.md).

## What it can and cannot detect

`configs/detectability.yaml` (shown in the console's **Detectability** tab; its
SHA-256 is recorded in every analysis record) lists each issue with the Phase A
check behind it, or "not tested". In short, at the tested setup (replayed
C2C12, 0.25-frame fields, 1–3 per visit, every 6–12 h): image-quality defects
are caught by the quality gate; growth stalls and instrument drift are **not**
reliably detectable; bacterial contamination was **not** detected per visit
with simulated bacteria at real size (up to 400 per 256 px tile area; heavier
contamination not tested), and was caught only in an exaggerated-scale simulation
(bacteria 16.5× real size); yeast, fungi and
detachment on real images are not tested; mycoplasma is not optically
detectable.

## Imaging requirement

At the imaging setup we could test, a single visit's growth is smaller than the
field-to-field sampling noise, so growth stalls aren't detectable. Our estimate
is that roughly half-frame fields, 3 per visit, twice a day, would make it
feasible, to be confirmed on real instrument data.

The estimate: with the 0.5-frame noise fit, the median growth step ÷ FOV noise
at a 12 h cadence would be 1.56 at 1 FOV and 2.71 at 3 FOVs, against 0.65 and
1.12 at the tested 0.25-frame fields
(`results/growth_signal_summary.md`). Those larger fields were **estimated,
never replayed**.

**Questions for instrument integration:**

- Imaging cadence per flask, and whether the flasks on one instrument are imaged in one round.
- FOVs per visit, and FOV size relative to the flask.
- Image format, bit depth and resolution.
- Could a few real RoboCell sequences be shared for validation? They would replace C2C12 as the primary test set.

## Demo

`python demo/app.py` opens the review console, with three tabs:

- **Analyze**: upload an image, or pick one of the precomputed examples (real
  C2C12 frames: normal, a simulated-contamination stress test with bacteria
  16.5× too large, and a frame with the bacteria at real size; and two EVICAN
  images). Examples come from `scripts/export_demo_examples.py`, which runs
  each image once through the same code as the Analyze button
  (`demo/analysis.py`) and stores the outputs in `demo/examples/`. They show
  instantly with no model loaded and are labelled as precomputed. Pressing
  Analyze runs the image live. The **3D** view draws the Cellpose-SAM
  cell-probability map as a surface: height is the map's logit, not cell
  thickness (phase contrast does not measure height). Points above the cutoff
  plane are counted as cell, and the borderline band around it is what sets
  the boundary ambiguity. The view recomputes the map's SHA-256 and shows whether it
  matches the record's `confluency_map_hash` (`demo/confluency_3d.py`).
- **Flask Timeline**: the five precomputed replays above, as a curve or in
  **3D space × time**: one layer per visit, showing where the frame's map
  counts cell, with the 3 FOV crops the visit's number came from. The maps
  are the compute cache's own, copied by `scripts/export_replay_maps.py` into
  `demo/replay_maps/`, and each layer's hash is checked when drawn. A visit's
  number is Cellpose-SAM run on each crop, so it is not read off the layer;
  each layer is labelled with both the 3-FOV mean and the full-frame value
  (`demo/replay_3d.py`).
- **Detectability**: the matrix above.

For the call, the console runs on a ZeroGPU Space (`deploy/hf-space-demo/`,
`LongGrainRice/cultureqc-console`): a live Analyze took a median 3.28 s as the
viewer waits for it, GPU attach included (`results/live_latency_zerogpu.md`,
`scripts/space_dry_run.py`). The backup is the same console on the Mac (`deploy/run_console_mac.sh`,
Cellpose-SAM on Apple's GPU, no Hugging Face at run time): median 16.43 s per
C2C12 frame (`results/live_latency_mac_mps.md`); a second backup on a Colab T4
(`nb/05_console_colab.ipynb`) took a median 12.06 s (`results/live_latency_colab_gpu.md`).
Behind all of them, the precomputed
examples and replays need no model at all.

## Site calibration

The anomaly banks and thresholds come from normal C2C12 frames (5× objective,
1.3 µm/px). For another instrument, rebuild them from its own known-good images:

```bash
python scripts/site_calibrate.py --normals path/to/good_images --out-dir site_cal \
    [--confluency-csv pct.csv | --single-bin]
CULTUREQC_ANOMALY_CONFIG=site_cal/anomaly.yaml CULTUREQC_ANOMALY_BANKS=site_cal/banks.npz python demo/app.py
```

A seeded split builds the banks from half the images and sets the thresholds
from the other half, so no image is scored against a bank that contains it.
Binning by confluency runs Cellpose-SAM on every image (minutes each on CPU;
use a GPU), unless you pass a CSV of confluencies or `--single-bin`. Aim for
dozens of images per bin. `configs/` is never overwritten.

## Known limits

Stated here rather than discovered later.

**The per-image score is a review trigger, not a confidence.** It was shown as
"confidence" until a pre-registered check of whether it predicts the reading's
error failed: on the 33 held-out EVICAN images, Spearman ρ with the absolute
error is −0.36 with a 95% CI reaching +0.02, sorting by it is no better than
random order (AURC 7.73 vs 8.35 pp, p = 0.303), and with expert confluency held fixed the correlation is +0.02.
It tracks density instead (ρ −0.61 with expert confluency, −0.95 with the
reading on held-out C2C12), which is why review piles up at 40–60%. It is now
shown as **boundary ambiguity** (1 − the record's `confidence`), with the
review trigger unchanged. Seen after the check, not tested: an image the model
reads as 0% scores as unambiguous, so a complete miss is not sent to review
(3 of the 33, all at 12–19% expert confluency; `results/confidence_vs_error.md`).

**The anomaly check is calibrated for one setup.** On held-out normal C2C12
frames it flags 10.0% against a 5% target, and one 090318 sequence 69%
(`results/anomaly_summary.md`); on other instruments it is uncalibrated. The
healthy EVICAN PC3 example in the console is flagged for that reason. The banks
(`cache/anomaly/banks.npz`, 67 MB) are not in git; they are regenerated by
`scripts/eval_anomaly.py` and shipped with the Space.

**Bacterial contamination was not detected per visit.** With the simulated
bacteria at their real size, up to 400 per 256 px tile area (heavier
contamination not tested), the anomaly flag is at chance (held-out AUROC 0.48;
flagged on 1 of 97 frames, against 4 of 97 for the same frames without them),
the quality gate fails no more often, and confluency reads a median 4.3 pp
lower (`results/contamination_scale.md`). So the passage hold (since `rules_v0.3`)
gives no protection against it: a realistically contaminated flask that
reached its target would be recommended for passage. Contamination has to be
confirmed by culture, Gram stain or PCR. The passage hold still stops a
passage when the flag fires for any reason; because the banks hold only C2C12
frames, on other cell types it can also stop a healthy flask's passage (it
fails safe: a person looks).

The oversized simulation behaves differently: Cellpose-SAM counts the 16.5×
bacteria as cells, which shifts measured confluency by a median +59.4 pp
(`results/anomaly_summary.md`), so confluency alone is above the passage target
and the flag holds it. That is what the stress-test example and the
contamination replay show; both are captioned as the exaggerated stress test.

**The QC classifier is demoted.** On held-out C2C12 frames it calls 2.9–5.0% of
normal frames normal, against an 80% bar, and rescaling the input to the
training pixel size does not fix it (B0, `results/classifier_scale_test.md`). It
still runs and its temperature-scaled output is written to every record
(`qc_flag`, `qc_confidence`, `qc_calibrated`), but `qc_used_in_decision` is
`false`: the action rules ignore it, the rationale does not mention it, no
Grad-CAM evidence is drawn, and the console shows it collapsed under "Trained on
synthetic tiles; known not to transfer to this imaging setup (see validation
report)". The switch is `classifier.demoted` in `configs/qc.yaml`. It was
trained entirely on synthetic contamination made with the same oversized
bacteria.

**A better confluency cutoff is validated but not shipped.** Much of V1's
under-read is Cellpose-SAM's cutoff: a pixel counts as cell only above logit 0.
A cutoff picked on the 65 eval2019 images outside the 33, by a rule fixed
before scoring, lowers held-out MAE from 8.36 to 3.78 pp
(`results/confluency_cutoff.md`; 8.36 is that study's rerun of V1's 8.35). It
is held for a release because it moves what was set at the old cutoff: on
held-out C2C12 the ambiguity trigger would send no frame to review (69 today on
the same quarter-resolution maps) and 471 of 1228 frames change anomaly bin.
The floor and bins have to be re-derived first; the steps are listed in
`docs/audit_mapping.md`. Everything else in this README, the site and the
console uses the shipped cutoff.

**The passage band is unvalidated.** C2C12 "50%" is 50% as Cellpose-SAM reads
it, about 8 pp below true coverage (V1), and no held-out sequence reaches
60–80%. The forecast interval also leaves out model-selection uncertainty: the
bootstrap refits only the AIC-chosen model, which understates the interval when
logistic and Gompertz are close.

**The Analyze tab runs no quality gate.** The gate (and REIMAGE) runs in the
replays only, so a dimmed or blurred single image is not flagged there.

**Analysis is slow on CPU.** Cellpose-SAM is almost all of it: 230 s for a
704×520 image and 689 s for a 1392×1040 C2C12 frame on an Apple M2 Pro limited
to 2 threads to approximate the 2-vCPU Space (V9, `results/live_latency.md`; an
approximation, not a measurement on the Space). `culture/seg.py` uses a GPU
when one is present; GPU latency has not been measured yet.

**`demo/analysis.py::_scale_bboxes` over-scales evidence boxes** on images
larger than 256 px (only drawn when the classifier is not demoted). The
Grad-CAM box is measured on a centred crop, so mapping it back should offset
the origin only. `deploy/hf-space/api.py` has the correct mapping.

**The hosted audit chain is per-boot.** HuggingFace Space storage is wiped on
restart, so `prev_record_hash` links within one boot only. Records stay
individually verifiable, and the browser builds its own chain over an upload
batch. A durable chain needs persistent storage and `CULTUREQC_LOG=/data/...`.

## Layout

```
culture/          the library: this is the product
  pipeline.py       analyze(): image -> record. The integration surface.
  seg.py            confluency (Cellpose-SAM, plus a threshold baseline)
  anomaly.py        per-image anomaly check (DINOv2-small patch distances)
  qc.py             the QC classifier (demoted) and its Grad-CAM evidence
  rules.py          deterministic action decisions
  growth.py, history.py, replay.py, quality.py   per-flask layer (replays)
  records.py        hash-chained JSONL writer + verifier
  schema.json       the output contract
configs/          qc, calibration, anomaly, noise, quality, detectability (hashed into records)

demo/             the review console (Gradio)
  app.py            Analyze, Flask Timeline, Detectability tabs
  analysis.py       the Analyze path, shared with the example export
  examples/         precomputed Analyze examples (scripts/export_demo_examples.py)
  replays/          precomputed timeline replays (scripts/export_demo_replays.py)
  replay_maps/      the replays' cached maps for the 3D view (scripts/export_replay_maps.py)
  confluency_3d.py, replay_3d.py   the 3D views

scripts/          every number's script: eval_*, backtest_growth, export_*, site_calibrate
results/          their outputs, cited next to each number in this README
docs/             ARCHITECTURE_VALIDATION.md (Phase A), DATASETS.md, STATUS.md, ...
nb/               Colab notebooks (thin runners around culture/ + scripts/)

deploy/           hf-space/ (FastAPI API), hf-space-demo/ (console Space), sync + publish scripts
site/             the landing page (React + Vite)
```

Training data and the compute cache are not tracked: they are downloaded and
derived. See [`docs/DATA.md`](docs/DATA.md).

## Getting started

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -c "from culture.pipeline import analyze; print(analyze('test-data/contam_00015.png'))"
.venv/bin/python demo/app.py
```

Model weights download on first use: Cellpose-SAM from its own package, the QC
classifier from [`LongGrainRice/cultureqc-qc-effnetb0-v1`](https://huggingface.co/LongGrainRice/cultureqc-qc-effnetb0-v1),
DINOv2-small from `facebook/dinov2-small`. Expect a slow first call.

**Run the page and the API together.** Two processes; the dev server proxies the
API calls, so the browser sees one origin:

```bash
python deploy/hf-space/api.py       # http://127.0.0.1:7860
cd site && npm install && npm run dev   # http://localhost:5173
```

## Tests

```bash
.venv/bin/python -m pytest tests                      # full suite, a few minutes
.venv/bin/python -m pytest deploy/hf-space/test_api.py -q   # API contract, models stubbed
```

`tests/` includes the claims-policy check over everything a viewer reads
(`tests/test_claims.py`), the provenance check on this README, replay and
example invariants, and one real-pipeline smoke test
(`tests/test_smoke_pipeline.py`). Tests that need the local compute cache or the
fetched C2C12 frames skip without them. One check (`test_record_matches_schema`)
is a documented `xfail`: `culture/schema.json`'s `confluency_method` enum and
its missing `record_hash` property don't match what the pipeline writes.

The API tests cover readiness, input validation, the response contract, the
evidence-box arithmetic, CORS, and that concurrent uploads cannot break the hash
chain. `.github/workflows/tests.yml` also checks that the Space mirrors still
match the repo and that `site/src/data.json` still matches the pipeline output
it was generated from.

## Deployment

The page is static on Vercel; the pipeline runs as a Docker Space on
HuggingFace. They are independent deployments joined by one URL, so neither can
break the other's build, and the page still hashes files and builds a verifiable
manifest when the API is asleep. See [`deploy/README.md`](deploy/README.md).

### The frontend

React 18 on Vite, in `site/`: one page that shows the pipeline's stored output
for real frames. A held-out C2C12 frame with the layers Cellpose-SAM and the
anomaly check computed, its readings and action; the five flask replays; the
detectability matrix; V1–V10; the seven chained records, re-hashed in the
browser; and what changed since v0.2. Live analysis is a link to the console
Space. Every number comes from `site/src/data.json`, which
`site/assets/build_data.py` generates from the repo's output; `site/README.md`
has the layout.

```bash
npm install
npm run dev      # http://localhost:5173
npm run build    # -> site/dist, which is what Vercel serves
python site/assets/build_data.py [--images]
```

## Credits

- **C2C12 time-lapse:** Ker et al., *Sci Data* 5:180237 (2018), OSF `ysaq2`, CC BY 4.0. Replays, anomaly banks and the precomputed examples.
- **EVICAN:** *Bioinformatics* 36(12):3863–3870 (2020), CC BY 4.0. Real-image confluency validation (V1) and two examples.
- **LIVECell:** Edlund et al., *Nature Methods* 18:1038–1045 (2021), CC BY-NC 4.0. Backgrounds of the synthetic classifier tiles.
- **DeepBacs** *E. coli* brightfield images ([Zenodo 5550935](https://zenodo.org/records/5550935)): the pasted contamination sprites.
- **Models:** Cellpose-SAM (`cpsam`), DINOv2-small (`facebook/dinov2-small`), EfficientNet-B0 via `timm`.

## License

MIT; see [LICENSE](LICENSE). Datasets keep their own licences, above.
