# Live microscopy instrument

The Home and Demo pages feature one precomputed Huh7 synthetic-contamination field. Its replay uses actual model artifacts; the four-second reveal is playback, not an inference benchmark. Upload uses the actual server stream. Dark green/gray surfaces, microscopy imagery, monospaced readouts, five inspection stages, and toggled overlays establish the instrument identity.

## Contract and evidence

`POST /analyze` accepts optional form field `stream=true`. It returns NDJSON:

- `queued`: waiting for the shared model lock.
- `segmentation/running`, then `segmentation/complete` with confluency and visual artifacts.
- `qc/running`, then `qc/complete` with Grad-CAM evidence if available.
- `result`: the existing full response plus `visuals`.
- `error`: terminal failure, with no final verdict.
- `heartbeat`: keeps the connection active every ten seconds during long stages.

The original JSON contract remains available without the stream flag. The frontend also accepts JSON for compatibility during deployment. It never synthesizes a model progress percentage. Number and layer animations only reveal completed model outputs. Batch requests run sequentially because the shared models and record writer require serialization; completed fields and their re-chained ingest manifests appear after each result. Stop skips pending fields after the current field finishes. Failed fields can be reset for retry.

`culture.visuals` encodes source-derived artifacts as bounded PNG previews:

- `raw`: grayscale source, including browser-unsupported TIFF files.
- `probability`: sigmoid of Cellpose's raw score; explicitly uncalibrated.
- `mask`: the exact `score > 0` foreground used to measure area.
- `contour`: morphological boundary of that foreground, not individual-cell outlines.
- `heatmap`: actual normalized Grad-CAM activation, positioned in the central 256×256 classifier crop (resized to the source only for smaller images).

These display artifacts do not change numerical inference, thresholds, classification, rules or record schema. The API obtains the QC details from the pipeline's first classifier pass, eliminating the former duplicate classification/Grad-CAM pass. Shared models and hash writes remain locked. A missing CAM stays unavailable rather than displaying a fabricated heatmap.

The visible instrument log shows the actual previous/current hashes, full record, and browser verification of canonical bytes. The audit page still demonstrates verification and tamper detection of the original nine-record sample chain. The new Huh7 playback record is a separate standalone chain. Hosted logs remain per-boot and this is not GMP certification or validation.

## Reproducibility

Run `.venv/bin/python scripts/generate_instrument_demo.py` to regenerate the Huh7 artifacts and standalone signed record from the tracked source image. This takes several minutes on CPU. Original `site/src/data.json` and its audit chain remain unchanged.

The negative-results section cites pipeline code and the audit mapping. The VLM evaluation numbers and fine-tuning learning curve are not present in this checkout; both metrics are explicitly unreported pending the source results.

## Validation

- 28 API tests, including stage ordering, streamed errors, readiness, mask threshold and exact heatmap crop mapping.
- Three Node stream parser tests, including fragmented network chunks, heartbeat handling, incomplete responses and legacy JSON.
- Real local inference: 256×256 normal fixture, 45.5 seconds; all five artifacts and image/record hashes verified. This is not a hosted timing claim.
- Chrome: replay/skip, overlay switches, probability inspection, record hashing, reduced motion, audit tampering; Home/Demo/Upload/Audit layouts at 375/768/1440 pixels.
- Real Chrome upload against the local API: preview, streamed completion, overlays, canonical digest verification and clear all passed.
- Progressive batch test: a completed field appears while the next request is pending; streamed failure resets for retry.
- `npm run build` and generated Space mirror check.
