# T05 — reconstructible decision records

Implemented locally on `slice-1b-compute-cache`. Nothing committed, pushed or
deployed. Human screen-reader and actual 200% zoom checks remain pending.

## What changed

- Schema **0.6** stores detached effective rule inputs, their canonical hash and
  the named `rules_v0.7` policy. Target, timing, line configuration, checks,
  profile/scope and actual setup/model context are explicit.
- `culture.provenance.replay_decision(record, policy_version)` reproduces action,
  reason code and explanation without inference or mutable config/file reads.
  Missing historical inputs, unsupported policies and inconsistent records are
  refused rather than guessed.
- Config loaders retain exact consumed YAML bytes, source paths and hashes in a
  request-local context. This includes anomaly environment overrides. Repeated
  reads are pinned; profile/quality/calibration process caches cannot masquerade
  as the current consumed file inside a live request. Unused inventory files
  are no longer claimed as decision inputs.
- Anomaly bank cache keys include the expected content hash, preventing a new
  config from labeling old cached arrays with a different hash.
- Host capture timestamps round-trip unchanged. Missing capture time stays
  unknown/null, separate from analysis start/end and record finalization.
- Library and console retain the original image hash and hash maps from the
  same inference callback/representation. The console rejects a supplied image
  that does not match the source bytes. Missing maps remain explicitly unavailable.
- The writer validates new records before append, including schema, replay and
  config-content consistency. Deployment requirements now include `jsonschema`.
- `--verify-replay` and the deprecated `--rederive` alias verify examples without
  modifying/re-chaining history. Legacy examples without snapshots fail honestly;
  a fresh export requires a fresh analysis and does not invent capture time.

The policy's scientific thresholds and all shipped passage approvals remain
unchanged. All output is still advisory, not host-actionable.

Full contract: [decision replay](../specs/decision-replay.md).

## Validation

Primary focused suite:

```sh
.venv/bin/python -m pytest tests/test_decision_provenance.py tests/test_rules_missing_checks.py tests/test_passage_eligibility.py tests/test_rules_band.py tests/test_rules_anomaly.py tests/test_profiles_config.py tests/test_record_model_identity.py tests/test_demo_examples.py tests/test_console_cards.py tests/test_record_events.py tests/test_records_chain.py tests/test_live_calibration.py tests/test_console_lab_demo.py tests/test_anomaly_live.py -q
```

**291 passed**, 76.57s. Coverage includes consumed config replacement during
stand-in inference, stale caches, unknown capture time, offline replay with IO
disabled, target/timing distinctions, rejected inconsistent writes, library/
console parity and historical schema/chain compatibility.

```sh
.venv/bin/python -m pytest deploy/hf-space/test_api.py tests/test_console_zerogpu.py -q
```

**33 passed**, 101.36s. Two existing Starlette/httpx/AnyIO deprecation warnings.
Deployment startup/models are stubbed; no remote/ZeroGPU readiness claim.

```sh
.venv/bin/python -m pytest tests/test_smoke_pipeline.py tests/test_quality.py tests/test_calibration.py -q
```

**31 passed**, 114.13s, including actual local Cellpose-SAM/QC/anomaly pipeline
execution and a schema-valid, replay-checked record. One upstream Cellpose/PyTorch
sparse-invariant warning remains. The first run exposed two old smoke assertions
that assumed confluency/anomaly prose always overrode timing; these now check the
authoritative rule rationale and structured anomaly state. No model thresholds
were changed to make tests pass.

**355 passing tests across these three suites.** A final overlapping policy/
provenance/record/approval run also passed **200 tests** after tightening interval
consistency checks. Counts are not added again for this overlapping rerun.

Changed Python modules compile, `git diff --check` passes and both deployment
mirrors match. `results/` and `demo/examples/` have no changes. No browser or
assistive-technology verification was performed in this backend step.

## Limits and next step

Replay proves the recorded inputs produce the recorded policy result, not that
the input observations are scientifically correct or authenticated. Snapshots
are pinned per path at first use, not an atomic approved multi-file release.
They contain config text and paths and need host-managed access/retention.
The approvals log remains identified by the model check's verified head; full
DINO/QC loaded-artifact identity is not newly established here.

T06's segmentation loaded-model identity work was already completed. **Next is
T07: authenticated configuration/model approval and activation semantics**, with
effective-time enforcement and explicit restart/rollback behavior. Target-host
capacity, E0 detector validation and human accessibility remain release gates.
