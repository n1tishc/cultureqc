# T07 — Effective approvals and explicit activation ownership

Implemented locally on `slice-1b-compute-cache`. No commit, push, publication,
approval-log edit, model activation or scientific threshold change.

## Outcome

The supported deployment mode is **host-managed configuration activation**.
This closes the ambiguity between recording a change and enforcing an approval;
it does not deliver a new locally managed release controller.

- Model approvals honor timezone-aware effective time, including future changes
  on an unchanged log. Last appended effective change wins. Rollback requires a
  new effective approval. Invalid structure, chain, timestamps and identities
  fail closed. Validation and selection use one byte snapshot rather than a
  verify-then-reopen race or mutable stat-keyed selection cache.
- The administrative CLI accepts an explicit `--effective-from` and records the
  predecessor effective at that time. It is not an authentication mechanism.
- Schema 0.7 adds `configuration_activation`: host-managed, not locally
  enforced, no authenticated host approval reference, and a reproducible identity
  for consumed configurations and effective policy. Both live record paths use
  it; the writer validates it before append. Previous schema 0.6 replay contracts
  and historical records remain accepted without invented activation metadata.
- T05's request-local snapshots continue to prevent stale profile/config hash
  combinations. Changes in configuration identity remain traceable, not silently
  labelled locally approved.
- Anomaly bank caches now bind expected content hash and opened-file identity.
  Replacement, deletion, corrupt archives and restored matching pairs are
  exercised. Arrays are read-only; scoring copies them when needed for safe
  PyTorch conversion. Missing/mismatched banks are not cached as permanent
  failures or treated as negative detections.
- Website technical evidence and live console copy distinguish locally checked
  segmentation weights from host-managed profile/rules activation and host-owned
  identity/signatures. Deployment mirrors are synchronized from source.

Contract and migration: [configuration activation](../specs/configuration-activation.md).

## Validation

Primary regression command:

```sh
.venv/bin/python -m pytest -p no:rerunfailures \
  tests/test_activation_timing.py tests/test_configuration_activation.py \
  tests/test_approvals.py tests/test_model_identity.py tests/test_record_model_identity.py \
  tests/test_decision_provenance.py tests/test_passage_eligibility.py \
  tests/test_rules_missing_checks.py tests/test_records_chain.py tests/test_record_events.py \
  tests/test_profiles_config.py tests/test_demo_examples.py tests/test_console_cards.py \
  tests/test_console_lab_demo.py tests/test_live_calibration.py -q
```

**330 passed**. Final timing/configuration/anomaly command:

```sh
.venv/bin/python -m pytest -p no:rerunfailures tests/test_activation_timing.py \
  tests/test_configuration_activation.py tests/test_anomaly_live.py -q
```

**36 passed**, including seven additional anomaly checks and actual local
DINO/frame parity. This overlaps the primary suite; it is not 36 additional
tests. The read-only-array warning found on the first anomaly run was fixed;
the final run has no warnings.

Deployment contract command:

```sh
.venv/bin/python -m pytest -p no:rerunfailures deploy/hf-space/test_api.py \
  tests/test_console_zerogpu.py -q
```

**33 passed**, with two existing Starlette/httpx/AnyIO deprecation warnings.
These are local contracts with stubbed inference/startup, not a remote deployment.
Combined non-overlapping Python coverage is **370 passed**.

- `node --test site/tests/*.test.js`: **11 passed**.
- `npm --prefix site run build`: passed.
- `deploy/sync_space.py --check`, compile checks and `git diff --check`: passed.
- Historical `results/`, `demo/examples/` and the approvals registry: unchanged.
- A separate agent reviewed approval selection, configuration identity and bank
  cache behavior against the host-managed contract; no concrete findings.

The rerunfailures plugin was disabled to avoid its sandbox socket requirement.
No new browser visual assessment was performed for these copy-only updates.
An initial isolated console-card run skipped; the final broad suite above ran
the console regression tests successfully.

## Remaining gates / next work

**T08: concurrent audit append** is next. Ordinary multi-writer JSONL appends are
not made transactional by this ticket. Host authentication, immutable release
activation, clock integrity, durable storage and external audit checkpoints
remain required. Loaded-model target-host capacity validation remains pending.
Human screen-reader and actual 200% zoom verification remain pending. This
ticket does not improve biological detection sensitivity or establish a new
passage-approved profile.
