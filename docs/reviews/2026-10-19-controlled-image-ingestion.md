# T09 — Controlled image ingestion validation

Implemented locally on `slice-1b-compute-cache`, 2026-10-19. Nothing committed,
pushed or deployed. Historical results, examples and approval records are unchanged.

## What changed

- A shared decoder validates the actual encoding, native depth, dimensions,
  channels, frame count and orientation before inference. Supported single-frame
  uint8 images retain the existing OpenCV grayscale pixels.
- Both full-range uint16 and 12-bit acquisitions stored in uint16 are refused
  rather than silently darkened, scaled or assigned an inferred sensor range.
  Floating-point, alpha/palette, multiframe and non-default-orientation inputs
  also require an explicit upstream export policy.
- Metadata inspection, native-depth checking, grayscale decoding and source
  hashing consume the same immutable encoded-byte snapshot. Schema **0.8**
  records the original-byte hash, decoding policy, transform, decoder version
  and grayscale-pixel hash. The writer checks provenance consistency.
- Library, console, API and legacy raw demo enforce this contract. API refusals
  return HTTP 400; console refusals clear the input/preview before inference.
- Gradio's default Image preprocessing was a second ingestion bypass: RGB
  conversion could erase source bit depth and identity before validation. Both
  upload event paths now preserve original file bytes without disabling
  Gradio's file-cache/path validation. The raw demo no longer re-encodes an
  intermediate PNG. Inline data URLs are refused.
- Both deployment mirrors are synchronized locally.

See the [input and provenance contract](../specs/controlled-image-ingestion.md).
This closes an input-integrity defect; it does not establish a scientific
detection improvement or change any threshold, model weight or approval.

## Validation

The dedicated decoder suite has **25 passing tests**, including exact supported
pixel equivalence, encoded modes, 12/16-bit rejection, transparency, multiframe
inputs, orientation, malformed files, resource caps and hash identities.
Record/transport tests additionally cover console/library parity, refusal before
inference or record creation, RGB uint16 TIFFs, file mutation during decoding and
inference, invalid provenance and historical-schema compatibility.

An actual Gradio preprocessing/cache regression preserves uploaded uint16 TIFF
bytes before refusal and verifies the upload-folder access check. The legacy raw
demo transport is tested separately. Four representative local mCellSeg RGB TIFFs
also decoded byte-for-byte identically to the previous grayscale path.

The broad relevant Python regression run passed **389 tests**, covering ingestion,
audit concurrency/chains, approvals/activation, replay/provenance, model identity,
rules, profiles, calibration and console examples/cards. This includes the
dedicated decoder suite; it is not an additional count.

The local API and ZeroGPU contract suite passed **37 tests**, including new
unsupported-depth, multipage and corrupt-upload HTTP cases. Its two existing
Starlette/httpx/AnyIO deprecation warnings do not indicate remote deployment
validation; inference/startup are stubbed in those contracts.

The real-model smoke suite passed **14 tests** using the local Cellpose-SAM and
QC/anomaly path with supported uint8 input and schema 0.8. It emitted one upstream
Cellpose/PyTorch sparse-invariant warning. This is not a target-host capacity test.

These three non-overlapping runs total **440 passing tests**. After the final
Gradio `image_mode=None` safeguard, the combined ingestion-record, console-lab,
demo-example, API and ZeroGPU recheck passed **111 tests** with the same two
deprecation warnings. This overlaps the preceding suites and is not additive.

```sh
.venv/bin/python -m pytest -p no:rerunfailures \
  tests/test_ingestion_records.py tests/test_console_lab_demo.py \
  tests/test_demo_examples.py deploy/hf-space/test_api.py \
  tests/test_console_zerogpu.py -q
```

`deploy/sync_space.py --check`, `git diff --check` and changed-module `compileall`
pass. Tests disable the rerunfailures plugin to avoid its sandbox socket requirement.

## Limits and next step

- High-bit-depth support remains intentionally unavailable until a fixed,
  setup-specific mapping is defined and validated. Exported-file provenance does
  not establish the identity of an unseen upstream sensor acquisition.
- Resource caps protect decoding, not host upload storage, worker memory budgets
  or request timeouts. Those need separate operational controls.
- Historical schemas 0.4–0.7 remain readable and writable for compatibility;
  hosts must require 0.8 for new live captures. Arbitrary caller-created legacy
  records are not authenticated decoder outputs.
- Hashes detect inconsistency, not replacement of all evidence by an attacker.
  Independent pixel verification needs retained original submitted bytes.
- Human screen-reader and actual 200% zoom verification remain pending. No new
  browser visual check was performed for this backend/transport change.

Next: **T10 — target-instrument partner pilot protocol**, with explicit ownership,
annotation, independent-unit splits, acceptance criteria and offline/shadow gates.
Scientific detector evaluation and deployment approval remain separate work.
