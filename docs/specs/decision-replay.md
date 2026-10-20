# T05 — immutable decision inputs and replay

## Contract

T05 introduced **schema 0.6**, retaining the `rules_v0.7` decision policy.
Current live records use **schema 0.8**, adding explicit host-managed activation
and [controlled ingestion provenance](controlled-image-ingestion.md) without
changing this offline decision-replay contract.
No scientific thresholds, passage approvals or operational permissions change.

`decision_inputs` stores the named policy, every effective rule argument and a
canonical SHA-256. It includes target and line configuration, elapsed times,
quality/QC/anomaly inputs, complete measurement profile and approval scope,
actual setup/model context and check requirements. The rule evaluates a detached
copy of these same values. Numeric rule inputs normalize equivalent integers and
floats consistently; booleans are not coerced into numbers.

```python
from culture.provenance import replay_decision

decision = replay_decision(record, "rules_v0.7")
assert decision.action == record["recommended_action"]
assert decision.reason_code == record["decision"]["reason_code"]
```

Replay does not run inference, read configuration, inspect model files or access
the filesystem/network. It checks the snapshot digest, named policy, relevant
record observations/profile/scope and stored action/reason/decision metadata.
Unknown policies and legacy records without snapshots fail explicitly, never
fall back to today's configuration. Currently only `rules_v0.7` is supported;
future policy changes need an explicit preserved evaluator or a documented
unsupported-policy error. Replay is not model rerunning or biological validation.

The digest and record chain detect inconsistency, not an actor who can rewrite
all hashes. Checkpoint trust, access control and signed approvals remain host
responsibilities. Replay does not independently authenticate the record chain.

## Configurations actually consumed

`culture.provenance.capture_configs` provides a request-local read context for
both library and console analysis. YAML loaders retain exact UTF-8 text, its
SHA-256, effective source path and read/missing status. A repeated read of that
path during the same request uses the retained bytes, even if the file changes
or appears after a missing first read. Configuration parsing returns independent
objects; request context resets on return or exception.

The profile, image-quality and QC-calibration loaders bypass stale process-level
configuration caches inside this context. Anomaly configuration records the
actual `CULTUREQC_ANOMALY_CONFIG` override path. Fine-tuned model configuration is
captured only when requested. Anomaly bank caching is keyed by path **and expected
content hash**, so a new config cannot claim a different bank hash for old cached
arrays. This does not add transactional bank/model activation.

`config_snapshot` contains only YAML files actually read by that analysis;
`config_hashes` indexes those snapshots by source path. It no longer hashes a
generic inventory after inference. Unused detectability/config files are not
claimed as consumed. The approvals log is not a YAML input: its verified head
and loaded segmentation identity remain in `model_check`. Raw approval-log
hashes, arbitrary on-disk weight inventories and the full DINO/QC model lifecycle
are **not** established by this snapshot facility.

Snapshots happen at each path's first use, not as an atomic multi-file release.
The host still needs T07 activation control; request-local consistency is not
authenticated configuration approval. Consumers should secure these records:
they include configuration text and source paths. Do not put secrets into these
calibration/config files. Test stand-ins may legitimately consume no real YAML;
their empty ledger is not a claim that deployed inference uses no configuration.

## Image, maps and timestamps

- Library inference decodes the same image bytes it hashes. The console checks
  that supplied grayscale pixels/dtype match the file bytes at analysis start,
  then retains that original image hash. Neither hashes a later replacement at
  record construction time.
- Both paths hash the segmentation map from the same inference callback using
  `culture.cache.downsample_probmap`: every fourth pixel, logits ×1000 clipped
  to ±32000, int16; the digest includes shape and little-endian values. This is
  not a hash of a PNG overlay or a new full-resolution inference.
- `map_provenance.status` is `captured` or `unavailable`; missing maps are not
  invented. The library hashes the map even without a visual observer, but does
  not persist an image/map artifact automatically. Console overlays are separate
  presentation artifacts. Artifact storage/retention belongs to the host.
- `captured_at` is a host-supplied timezone-aware timestamp, preserved verbatim.
  Missing means null with `capture_time_source: unknown`, not analysis time.
  `analysis_started_at` / `analysis_completed_at` bracket analysis; `analysed_at`
  remains the writer's record-finalization timestamp. Capture provenance declares
  the source; it cannot independently verify the host's clock or claim.

## Validation and migration

`RecordWriter.append` validates schema 0.6 records before writing a line, including
timestamp formats, replay consistency, snapshot/content hashes and required
provenance. Rejection leaves the log and writer head unchanged. JSON nonfinite
values remain forbidden. Review/change events also accept schema 0.6; valid
historical 0.4/0.5 records retain their original contract and hashes.

Hosts must update closed-schema consumers for schema 0.6, nullable capture time
and source-path-keyed consumed configuration hashes before deployment. The old
`pipeline.config_hashes()` remains an inventory utility for compatibility, not
the evidence source for live records. No deployment is authorized by this patch.

`scripts/export_demo_examples.py --verify-replay` verifies snapshot-bearing
examples read-only. The old `--rederive` flag is now an alias: it no longer
rewrites/re-chains historical records or relabels them as current-policy evidence.
Existing legacy examples deliberately cannot pass replay without missing inputs;
they remain intact, schema-valid historical examples. Fresh exports must use a
new analysis; export time is not substituted for unknown image capture time.

Tests cover replay without IO, wrong policy/snapshot/output refusal, schema
rejection before append, config replacement during stand-in inference, stale
caches, missing files, host timestamps, target/timing distinctions and equivalent
library/console decision and map provenance. No new scientific accuracy claim or
human accessibility verification follows from these software tests.
