# T09 — Controlled image ingestion

Implemented locally, 2026-10-19. No scientific thresholds, model weights or
historical results changed. This is an input-integrity control, not evidence of
better detection sensitivity.

## Accepted input policy

`culture.ingestion.read_image(path)` reads a bounded immutable byte snapshot;
`decode_image(bytes)` validates and decodes that snapshot. The policy identifier
is **`uint8-single-frame-v1`**.

- Single-frame PNG, JPEG, TIFF, BMP or WebP, with decoded source mode `L` or
  `RGB` and native unsigned 8-bit pixels.
- Grayscale stays grayscale; RGB is converted using OpenCV's existing grayscale
  decoder. `IMREAD_IGNORE_ORIENTATION` is explicit. Native depth/channels are
  inspected with `IMREAD_UNCHANGED` before grayscale conversion, including RGB
  16-bit TIFFs that Pillow describes simply as `RGB`.
- EXIF orientation must be absent or 1. Non-default orientation is rejected
  rather than silently rotating/flipping the frame or its evidence coordinates.
- No alpha/transparency, paletted mode `P`, floating/signed/high-bit-depth input,
  animation, multiple TIFF pages or TIFF subimages. A setup must explicitly
  export its intended frame/channels/orientation before submitting it.
- The encoded format, not the filename suffix, determines the decoding policy.
  WebP encoders may store an originally grayscale image as RGB; provenance
  describes the actual encoded file, not the caller's original array mode.

Resource guards are **64 MiB encoded bytes**, **16,777,216 decoded pixels** and
**8192 pixels per side**. They are software resource limits, not biological
acceptance thresholds or target-host capacity validation. Corrupt/truncated
encodings and parser warnings/errors are reported as actionable `ValueError`s;
missing/unreadable paths remain filesystem errors.
These limits guard decoding; host ingress/upload storage limits, worker memory
budgets and request timeouts remain separate operational responsibilities.

## High-bit-depth decision

**Reject, do not guess.** Both a full-range uint16 frame and a 12-bit acquisition
stored in uint16 (maximum 4095) are refused before inference. A frame maximum is
not proof of sensor bit depth: it could instead be a dim 16-bit acquisition.
There is no right-shift, per-frame min/max scaling, auto-contrast or fallback to
OpenCV's implicit 16-to-8-bit conversion.

The host must define and validate a fixed setup-specific export/mapping before
using high-bit-depth data. Such a mapping needs its own versioned setup, range,
clipping/rounding convention and validation; it is **not implemented or approved
by this ticket**. A converted input's original bytes are the exported file sent
to cultureQC, not an unseen upstream sensor file. The host must retain and link
the upstream acquisition and conversion provenance separately.

## Live surfaces

The library and console share the same decoder. The console rejects unsupported
uploads before producing a preview; accepted previews use the same grayscale
pixels. Analysis reads the original upload, not the browser PNG. Its existing
array-taking interface checks equality with the controlled source decode and
then uses the privately decoded pixels, not a mutable caller array.

Both Gradio upload paths disable the Image component's image preprocessing at
the event, because its default RGB conversion can erase bit depth, orientation
or original-byte identity before our decoder sees the upload. Gradio's file
cache/path validation remains enabled; handlers extract the validated original
file path and reject inline data URLs. The raw demo no longer receives an array
and writes an intermediate PNG. A transport regression exercises Gradio's actual
cache/mapping stage and verifies that uint16 TIFF bytes remain unchanged and are
then refused, including preservation of the upload-folder access check.

The API validates uploaded bytes with this decoder before calling inference and
returns HTTP 400 for unsupported/corrupt encodings. Its privately held temporary
file is also validated by the standard pipeline. No successful reading is
written for a refused input. The legacy raw demo also passes through the same
library pipeline.

For supported, default-orientation 8-bit images, the old grayscale decoder's
pixels are preserved; there is no deliberate redefinition of RGB luminance.
Tests compare pixels exactly for accepted formats and modes. Decoder/library
versions must still be pinned and validated by the host for deployment.

## Record contract — schema 0.8

New live readings retain all schema 0.7 fields and require `preprocessing`:

- `policy`, detected `source_format`, `source_mode`, `source_dtype`,
  `source_shape` in height/width[/channels] order, `frame_count`, `orientation`.
- `source_sha256`, identical to the record's `image_hash`, computed from the
  **same bytes** passed to metadata validation and both OpenCV decodes.
- `transform` (`identity` or `opencv-grayscale`) and OpenCV `decoder_version`.
- `output_dtype`, `output_shape`, and `output_sha256` identifying the full-frame
  grayscale pixels entering the pipeline.
- `sha256`: canonical JSON SHA-256 of all preceding preprocessing fields.

The pixel digest hashes UTF-8 canonical JSON
`{"dtype":"uint8","shape":[height,width]}`, then one zero byte, then C-order
pixel bytes. Canonical JSON uses sorted keys and compact separators. The
preprocessing identity includes the source hash, so it is record-specific;
different encodings can have different source hashes and identical pixel hashes.

The writer checks schema, preprocessing digest, source-hash binding and
mode/transform/dimension consistency before file access. It does not reopen the
source after inference or recompute pixel hashes from an unrecorded current file.
Retain the original submitted bytes to independently verify a pixel hash later.
These hashes detect inconsistency, not an attacker who can replace all hashes.
The field covers ingestion only; model-specific normalization, crops and resizing
remain part of the pinned model/pipeline release, not a newly claimed transform log.

Historical schema 0.4–0.7 records/examples are not rewritten. `RecordWriter`
retains legacy compatibility and can therefore accept explicitly old-version
records without this field; it is not itself an authenticated ingestion endpoint.
Hosts must require **0.8 for new live captures from this release** and must not
treat arbitrary caller-constructed or downgraded records as decoder-validated.
Pure decision replay remains unchanged and does not re-run image inference.

## Validation scope

`tests/test_image_ingestion.py` covers valid modes/formats, 12/16-bit refusal,
float/alpha/palette/transparency, frame counts, orientation, truncation,
resource limits and hash identities. `tests/test_ingestion_records.py` covers
console/library parity, early refusal, RGB uint16, damaged TIFF directories,
source replacement during decoding/inference, writer validation and migration.
API tests cover unsupported-depth/multipage/corrupt HTTP requests. A real-model
smoke run checks the accepted uint8 path without changing thresholds.
