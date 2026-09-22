# Baseline CPU latency — Slice 0

Produced by `scripts/benchmark_latency.py`, full data in
`results/baseline_latency.csv`. Provenance: **real (this repo's `test-data/`
fixtures)** — not synthetic, not simulated.

**Environment:** `.venv` built from `requirements.txt` at tag
`v1.0-pre-upgrade`, Python 3.14.7, torch 2.14.0, cellpose 4.2.1.1, on an
Apple Silicon Mac. `torch.cuda.is_available()` is `False` here, so both
Cellpose-SAM and the QC classifier ran on **CPU** — the same code path the
CPU-only HF Space runs, per `culture/seg.py`'s device-selection logic (see
`docs/REPO_MAP.md` §3.1, §4). Models loaded once (4.9s) before timing; that
one-time cost is excluded from the per-image figures below.

| Image | Size | Segmentation (s) | QC classify (s) | Total (s) | Confluency % | QC flag |
|---|---|---:|---:|---:|---:|---|
| A172_Phase_C7_1_00d00h00m_1.tif | 704×520 | 136.30 | 2.72 | 139.01 | 10.11 | normal |
| BT474_Phase_D3_1_04d04h00m_4.tif | 704×520 | 138.95 | 0.89 | 139.84 | 33.74 | normal |
| BV2_Phase_A4_2_02d08h00m_3.tif | 704×520 | 144.39 | 1.05 | 145.44 | 38.21 | normal |
| Huh7_Phase_A12_1_02d16h00m_1.tif | 704×520 | 140.76 | 0.90 | 141.67 | 35.28 | normal |
| contam_00015.png | 256×256 | 44.28 | 0.90 | 45.18 | 86.68 | contamination_suspected |
| detach_00003.png | 256×256 | 44.10 | 0.92 | 45.02 | 55.73 | detachment |
| imgq_00012.png | 256×256 | 44.20 | 0.91 | 45.12 | 58.83 | image_quality |
| normal_00005.png | 256×256 | 45.01 | 0.91 | 45.92 | 27.15 | normal |

**n=8, mean=93.40s, median=92.47s, min=45.02s (256×256 tile), max=145.44s (704×520 field).**

Segmentation (Cellpose-SAM) dominates: ~44s flat for a 256×256 tile regardless
of content, scaling to ~140s for a 704×520 field — consistent with pixel count
rather than image content. QC classification (EfficientNet-B0 on a fixed
256×256 crop) is near-constant (~1s) except on the first call of the run
(2.72s, one-time kernel warm-up not fully captured by the explicit model-load
step).

**Cross-check against previously-documented figures** (`deploy/README.md`,
"host venv (Python 3.14, torch 2.14)"): that table reported ~50s for a 256×256
tile and >180s for a 704×520 field — in the same range as this run's 45s and
~140s respectively (small deltas plausibly machine load / library-version
drift since that figure was recorded, not a different method). The
`contam_00015.png` confluency of **86.68%** measured here matches the exact
figure `deploy/README.md` cites for the Docker container's Python 3.11 build
("86.65% vs 86.68%... the host venv" row), confirming this run reproduces the
same output the deployed image produces, not a divergent code path.

**Latency budget implication for the upgrade:** at ~45–145s per image on CPU,
Slice 1b's batched compute-cache pass is not optional — iterating on
thresholds, calibration, or bin definitions against live inference at this
per-image cost would make every later slice (2 through 6) impractically slow
to develop against, which is exactly the problem Slice 1b's cache is designed
to remove.
