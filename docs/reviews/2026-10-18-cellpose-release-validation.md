# T06 local real-model release validation

Date: 2026-10-18. The next bounded gate after the detection-signal implementation
was validating the new segmentation loader with real weights, not another
synthetic model stand-in. No models, thresholds, approvals or historical results
were changed. No download, push or deployment was performed.

## Result: CPU loading parity passes

Added `tests/test_model_identity_live.py`, explicitly opt-in so ordinary CI does
not unexpectedly load a 1.2 GB model. It launches two sequential subprocesses:
direct loading of the existing local Cellpose weights, then the shipped verified
snapshot loader. Each processes the same existing 256×256 grayscale fixture
once, on CPU with two threads. Each worker has a 300-second timeout; inputs and
outputs are kept in pytest's temporary directory, never the scientific results.

```sh
CULTUREQC_RUN_MODEL_PARITY=1 \
  .venv/bin/python -m pytest tests/test_model_identity_live.py -q -s
```

**1 passed in 181.48 seconds.** Maximum probability-map difference: **0.0**.
Foreground masks match exactly. Both paths return confluency **86.68%** and the
existing uncalibrated boundary-based confidence **0.148**. The snapshot result's
approval and actual loaded-weight digests agree. Its private read-only file is
removed when the model is released.

| Measurement | Direct local loading | Verified snapshot loading |
|---|---:|---:|
| Preflight/hash + model load | 3.350 s | 4.990 s |
| Inference | 74.084 s | 74.050 s |
| Process peak resident memory | 2,070,118,400 bytes | 2,207,367,168 bytes |
| Additional snapshot file | 0 bytes | 1,233,586,851 bytes |

These are single-run observations, not a latency benchmark or a statistically
established overhead estimate. The timed preflight includes approval/source
hashing but excludes Python/dependency import time. The inference timer excludes
the extra snapshot hash used only by this validation. OS caches, process startup
and local load affect timings. Peak memory is process RSS, not a container limit
recommendation; snapshot size is logical file size, not measured disk blocks.

## Provenance

- Host: macOS 26.5.1, arm64; CPU execution, no GPU use.
- Python 3.14.7; torch 2.14.0; cellpose 4.2.1.1; NumPy 2.5.2.
- Input: `test-data/contam_00015.png`, an existing smoke fixture, not an untouched
  contamination test or a ground-truth confluency benchmark.
- Input SHA-256: `9656003a495246dda8a4148d72228f95436c73074863cf5b86337b7b956ae44a`.
- Weights SHA-256: `0f1cc3f7ecdd8a037a57c6c48d9d8921391be4cbce3fa9f13c3e3a2e1253c667`.
- Approval-chain head: `e326493673efa35c4deb514f5a916b8948a348102d517a6c9e7fb535e1ba5c2f`.
- Base commit: `01b8ead1ea09f7ebf442a9862d3113369614cdd1`, with uncommitted changes.
  The base commit alone does not identify the code tested; hashes below do.

| Tested file | SHA-256 |
|---|---|
| `culture/seg.py` | `33cd1f09bac03c0ec6116e0a5bdda38f3dcae85d04dac05b61c11396e53692b8` |
| `culture/weights.py` | `c62ce204b0f416d78bc658a91b65fe13eed40ee6af3e7019e36ffcdb4292a860` |
| `culture/approvals.py` | `16710f519e51274758b28ec450cba8ef455743f717392cd765ff74b1cc169b3b` |
| `culture/pipeline.py` | `bf44d596f9d19356dc98e0fe28cc1095b16448fd19a83c7a209654288e683f09` |
| `tests/test_model_identity_live.py` | `4b21ff4560e89f250120be7b3d8acf668bc01d632f0b11d9167d6f31db5e0ea2` |
| `tests/test_smoke_pipeline.py` | `718a2a5901f9a9b5a0bebdf3c4ed780f2c485bac116d2c2f390d1f7e7661a12f` |

## Other checks and remaining gates

The real full-pipeline smoke suite also passes, using existing local model
artifacts and a temporary event log:

```sh
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 CUDA_VISIBLE_DEVICES='' \
  CULTUREQC_DEVICE=cpu OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 \
  .venv/bin/python -m pytest tests/test_smoke_pipeline.py -q
```

**14 passed in 99.88 seconds.** Checks include recorded segmentation identity
matching the approved artifact, image hash, model/config provenance, record
schema, action/rationale contract and hash-chain verification. This is one
inference fixture shared by the tests, not 14 independent biological samples.
Cellpose/PyTorch emitted one warning about sparse tensor invariant checks being
implicitly disabled; the suite completed successfully. No unrelated dependency
or performance change was made to suppress it.

The fixture lifecycle, record-builder and approval suite passes **38 tests**;
the new real-model test skips unless explicitly enabled. Deployment mirror
consistency and whitespace checks pass.

This closes the bounded **local CPU** loading-parity check, not production
qualification. Before deployment, provision approved weights and test startup,
temporary storage, memory and latency on the actual target. A fresh Docker image
does not currently provision the shipped weights automatically. GPU parity,
larger-frame behavior and concurrency capacity were not tested here.

The E0 readiness checker still returns `ready: false`: actual acquisition setup,
owner approval, independently labelled samples and split custody are unresolved.
It is not appropriate to select contamination/growth thresholds or claim improved
sensitivity from the parity result. Next executable backend work can address
the remaining T03–T05/T07–T09 contracts while that data/approval packet is prepared.
