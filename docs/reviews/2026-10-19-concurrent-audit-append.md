# T08 — Concurrent audit append validation

Implemented locally on `slice-1b-compute-cache`, 2026-10-19. Nothing committed,
pushed or deployed. Historical results, examples and approval records are unchanged.

## What changed

- `RecordWriter` no longer caches a predecessor at construction. It validates a
  deep copy of the new record before opening the log, then exclusively locks the
  actual log inode across full-chain verification, head selection, final hash,
  append, file synchronization and parent-directory synchronization.
- Cooperating threads and processes on a local POSIX filesystem serialize their
  appends. Direct `os.write` avoids pending Python-buffered bytes being flushed
  after a failed operation releases the lock.
- Malformed/partial tails, invalid UTF-8, non-object JSON, broken hashes and
  unterminated final records are refused without altering existing evidence.
  The verifier reports malformed content as `broken` instead of crashing.
- Verification, checkpoints and record counts take shared locks and see complete
  cooperating appends. Invalid input still cannot create an empty log; the first
  integration run caught that regression and input preflight was moved before
  file access without reintroducing cached-head behavior.
- The API's inference lock remains for model safety; its obsolete explanation
  about the writer's cached head was removed. Both deployment mirrors are synced.

The record schema stays at **0.7**. See the
[writer/storage/recovery contract](../specs/concurrent-audit-append.md).

## Validation

An independent test agent first reproduced nine failures in the old writer:
interleaved/threaded/multiprocess chain breaks, silent extension of corrupt/torn
tails, and verifier exceptions for malformed content. The final dedicated suite
has **14 passing cases**, including:

- Two writers constructed before either append.
- Twelve barrier-synchronized threads sharing a writer.
- Four spawned, barrier-synchronized processes writing eight unique records each;
  count, uniqueness and every link verify, including an additional restart append.
- Exact-byte preservation after refused corrupt/partial/no-newline tails.
- Injected short writes and both file/directory `fsync` failures.
- File-then-directory synchronization before success.
- Verification/checkpoint readers waiting behind an exclusive writer lock.

Full relevant regression run:

```sh
.venv/bin/python -m pytest -p no:rerunfailures \
  tests/test_records_concurrency.py tests/test_records_chain.py tests/test_record_events.py \
  tests/test_activation_timing.py tests/test_configuration_activation.py tests/test_approvals.py \
  tests/test_decision_provenance.py tests/test_record_model_identity.py tests/test_passage_eligibility.py \
  tests/test_rules_missing_checks.py tests/test_demo_examples.py tests/test_console_cards.py \
  tests/test_console_lab_demo.py tests/test_live_calibration.py tests/test_profiles_config.py \
  tests/test_model_identity.py -q
```

**344 passed**. Existing single-record tamper, full rewrite, anchored rewrite,
anchored truncation and historical-example checks remain green. The dedicated
14-case suite is included in this count, not additional.

```sh
.venv/bin/python -m pytest -p no:rerunfailures deploy/hf-space/test_api.py \
  tests/test_console_zerogpu.py -q
```

**33 passed**, with two existing Starlette/httpx/AnyIO deprecation warnings.
These are local deployment contracts with stubbed inference/startup, not remote
deployment tests. Total non-overlapping Python coverage: **377 passed**.

`compileall`, `deploy/sync_space.py --check`, and `git diff --check` pass.
The rerunfailures plugin is disabled to avoid its sandbox socket requirement.
No website visuals changed and no new browser/human accessibility check was run.

## Limits and next step

This validates cooperating local POSIX writers, not distributed/network storage,
uncooperative file mutation, live rotation, physical power-loss recovery or
high-volume throughput. Success means file and directory `fsync` returned; `/tmp`
is still ephemeral. An I/O exception can follow a complete append, so the host
owns stable IDs, reconciliation and coordinated retry/idempotency. No automatic
repair, rollback or exactly-once delivery is claimed. Authentication, durable
retention and externally held checkpoints remain host responsibilities.

Next: **T09 — controlled image ingestion**, especially preventing silent
12-bit-in-16-bit TIFF scaling. Human screen-reader and actual 200% zoom verification,
scientific detector evaluation and target-host capacity validation remain pending.
