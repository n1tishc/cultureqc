# Live deployment verification — September 9, 2026

The Hugging Face CPU Basic Space runs Cellpose-SAM and the EfficientNet-B0 QC
checkpoint. The full React application is now served by the same Space:
https://longgrainrice-cultureqc-api.hf.space/#/home

## Repairs

- The documented Vercel URL returned `DEPLOYMENT_NOT_FOUND`; the built frontend
  is now bundled with the Space deployment.
- The API previously replaced `image_ref` after the pipeline signed the record.
  It now supplies the public filename before signing, preserving log and response
  identity. A regression assertion failed before the fix and passes afterward.
- Exact canonical JSON is returned alongside the record to preserve numeric
  serialization across Python and JavaScript. The frontend rejects mismatched
  image digests and altered canonical records.

## Real model checks

| Repository input | Returned QC class | Confluency |
| --- | --- | --- |
| `normal_00005.png` | normal | 27.15% |
| `contam_00015.png` | contamination_suspected | 86.69% |
| `detach_00003.png` | detachment | 55.72% |
| `imgq_00012.png` | image_quality | 58.82% |

All four synthetic fixtures returned their expected class. The smoke run checked
image hashes, server record hashes, probability totals, confluency bounds, and
normalized evidence coordinates. Unqueued 256×256 cases took about 60 seconds;
a concurrent request took about 120 seconds. A 704×520 Huh7 WebP request took
194 seconds before the repair and returned normal, 11.28% confluency. This was a
different input from the synthetic normal fixture.

The hosted browser uploaded a contamination fixture, received real inference,
rendered the returned verdict, and verified its browser manifest. Malformed
image bytes returned HTTP 400. All 23 API contract tests passed, including the
new returned-record integrity assertions; the production frontend build passed.
Local browser interception checks confirmed rejection of mismatched images and
altered canonical records.

## CV scope

These are deployment/regression checks, not an accuracy benchmark. QC training
uses synthetic examples. For larger images, QC currently reads only the central
256×256 crop; Grad-CAM boxes indicate classifier evidence rather than individual
object detections. Confluency uses the full image. The upload UI shows numerical
verdicts; the demo's segmentation overlays are precomputed assets.

The Space uses ephemeral storage and serializes inference. A successful health
check alone is insufficient, and CPU latency grows with image size and queueing.
Run `.venv/bin/python deploy/smoke_space.py` to repeat the real-model checks.
