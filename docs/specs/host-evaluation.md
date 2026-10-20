# Local host contract evaluation

Status: T11 implementation, 2026-10-19. **Non-actuating evaluation only.**
The callable remains `culture.pipeline.analyze`; no HTTP service, deployment,
partner approval or commercial clearance is created. See the
[release-state map](release-state.md) and [proposed pilot](partner-pilot.md).

## Two separate exercises

`scripts/host_evaluation.py` wraps the current Python library in a disposable
POSIX worker process. It never writes to a host production log or schedules an
operation. It accepts only a fixed list of library request fields; arbitrary
log paths and optional fine-tuned models are excluded.

- **Record mode:** inspect one existing schema `0.8` / `rules_v0.7` reading JSON.
  No inference, weight download or image decoding. Checks the stored canonical
  hash and reuses the writer's validation preparation: schema, deterministic
  decision replay, consumed configs, activation identity and preprocessing
  consistency. The returned original record is not rewritten. This does **not**
  establish membership in its original chain, source-image authenticity or
  scientific validity. Verify that chain against an external checkpoint separately.
- **Live mode (explicit opt-in):** copy the input image into the evaluation
  directory, then call `analyze` against that copy. Validate its returned record,
  check its image hash against the copied bytes and verify the evaluation log.
  No existing audit log is reused. Existing model/config approval checks still
  apply; missing or unapproved artifacts cannot become a negative check.

Historical website examples remain historical; they are intentionally refused
by this current-record harness, not upgraded by adding fields or re-hashing.
An advisory result, including `continue`, is never proof of culture health.

## Clean contract environment: no models required

From a complete checkout of the candidate source, using POSIX and CPython 3.14:

```sh
python3.14 -m venv /tmp/cultureqc-host-eval
/tmp/cultureqc-host-eval/bin/python -m pip install -r requirements-host-eval.txt
/tmp/cultureqc-host-eval/bin/python -m pytest tests/test_host_evaluation.py -q
```

Use a new environment path if one exists. `requirements-host-eval.txt` pins the
direct and transitive dependencies of the reference contract suite; it is not
the full inference environment. Installation needs an allowed package index or
a pre-provisioned wheelhouse. The tests stub model measurements and approvals
in temporary directories. Their results prove contract behavior, **not accuracy**.
They exercise current records, altered records, missing input, invalid image,
required checks, check failure, worker deadlines and manifest failure.

The dedicated CI job uses this dependency file without model packages. Adding
the job does not claim that remote CI has run before publication.

After obtaining a real current reading from a separately authorized run:

```sh
/tmp/cultureqc-host-eval/bin/python -m scripts.host_evaluation \
  --record /absolute/path/current-reading.json \
  --output-dir /tmp/cultureqc-record-evaluation-001 --timeout-seconds 30
```

The output directory must not exist. Contract tests generate **synthetic**
current-schema records without private data; there is no new approved biological
fixture bundled with this task. An absent example path produces a missing-input
outcome rather than a demo result. Commands do not send inputs to an external API.

## Optional live-library run

Use a separately provisioned full inference environment (`requirements.txt`,
resolved and frozen by the evaluation owner), not the lightweight contract venv.
Prepare a request JSON with **actual approved** host values:

```json
{
  "image_path": "/absolute/path/approved-frame.png",
  "flask_id": "HOST-SUPPLIED-VESSEL",
  "cell_line": "HOST-SUPPLIED-LINE",
  "profile_id": "uncalibrated",
  "setup_id": "HOST-SUPPLIED-SETUP",
  "captured_at": null,
  "hours_since_passage": null,
  "hours_since_feed": null
}
```

These identifiers are placeholders, not approval or evidence. Unknown timing
remains null; `uncalibrated` means no approved setup band or passage eligibility.
Pass a justified `check_policy` or `line_config` object only under the frozen
protocol. Do not infer capture metadata from analysis time.

```sh
python -m scripts.host_evaluation --live-request /absolute/path/request.json \
  --output-dir /tmp/cultureqc-live-evaluation-001 --timeout-seconds 120
```

The 120-second default is a configurable **demo worker budget**, not an acceptable
scientific detection delay or an observed latency. Live inference may need
Cellpose-SAM and QC weights, their effective approvals, transformers/DINO weights
and anomaly banks as configured. Model loaders may download uncached public
artifacts: pre-provision/pin them under the evaluation owner's network policy.
This wrapper does not sandbox network access. Offline evaluation does not mean
the dependency/model installers are automatically offline.

Private `mcellseg_ftF_r2` inference is disabled in this harness: no credential or
private-model download is requested. VLM inference remains off in the existing
pipeline. Demoted QC is still computed/recorded by the full library, not removed
from its dependencies or licensing gate. Anomaly availability follows the actual
configured runtime; absent optional checks stay explicitly unavailable.

## Host outcomes

Every outcome has `host_actionable: false`, `host_next_step: operator_review`
and `retry_automatically: false`. No outcome executes its next step. The original
recommendation and recovery request remain inside a validated reading.

| Status | Meaning and handling |
|---|---|
| `advisory_reading` | Current reading validated; no failed check or unavailable required check. Optional unavailable checks, unknown timing and unsupported scope can still exist. Inspect all warnings; no health clearance. |
| `check_failed` | At least one applicable check failed. Preserve original reason; a quality failure retains the advisory `reimage` request. Host decides any bounded recovery. |
| `required_check_unavailable` | Required evidence is missing, never passed. Preserve measured values but escalate for review. |
| `input_or_dependency_missing` | Missing input/artifact file; no reading. Identify the absent item before a new attempt. |
| `dependency_unavailable` | Required Python import unavailable; no valid evaluation result. Repair the frozen environment. |
| `model_not_approved` | Library model approval refused. Do not bypass approval or substitute weights silently. |
| `refused` | Malformed input/current-contract mismatch, including a historical record. Preserve diagnostic; do not synthesize missing fields. |
| `evaluation_error` / `worker_failed` | Library/validation/runtime error or incomplete worker response. No inferred negative/continue result. |
| `manifest_failed` / `source_changed` | Inventory could not be recorded or source/config inventory changed during execution. Freeze and preserve evidence before a new attempt. |
| `timeout` | Kill the worker process group and wait for termination; ignore any late/partial result. Preserve partial log and reconcile its outcome before retrying. |

Failed checks take precedence over unavailable checks in the **host summary**;
the underlying policy reason and all check states remain unchanged. This summary
is not a new scientific decision policy. Exit `0` means a validated advisory
reading was returned, even when it reports failure/missing checks; exit `1`
means no validated reading; exit `2` indicates CLI/configuration/storage failure.
Do not map process exit `0` to “culture passed.”

## Evidence bundle and limits

Each new directory retains:

- Original-byte input copy, `request.json` with its source/hash and actual options.
- `worker.stdout`, `worker.stderr`, and completed `worker-result.json`, if any.
- `evaluation.jsonl` for live calls that reached append; it may be partial on a
  timeout/crash. Do not silently repair, delete or treat it as absent.
- `outcome.json`, including the unchanged reading when validation succeeds.
- `manifest.json`: local Git HEAD/dirty status, SHA-256 inventory of Python
  source/schema/config and requirement files, installed distributions, interpreter,
  OS/platform, input/output artifact hashes, worker budget and elapsed wall time.
  Successful reading identities include recorded model hashes, policy/schema and
  consumed configuration identity; these are not fresh verification of stored
  inference. The manifest does not hash itself or authenticate its author.

Preserve the full candidate checkout including untracked files alongside the
manifest; Git HEAD alone does not describe this dirty working tree. Freeze files
during evaluation. Start/end source inventories catch ordinary changes, not a
malicious change-and-restore race. For model execution, also retain the actual
permitted weight/bank bundle, package wheels, dependency freeze, hardware/GPU/
driver details and independently held audit checkpoints. Hashes do not retain
artifacts, establish rights or confer approval. Do not upload the bundle by
default: it may contain images, vessel identifiers, local paths and diagnostics.

The timeout bounds the **worker**, not input copy, source inventory or local
filesystem operations. This is a trusted local pilot utility, not an untrusted
multi-tenant service or memory/CPU quota. Disk exhaustion can prevent even an
outcome file being written; the CLI fails, and the host must treat absence as
unknown. Process-group termination covers ordinary child processes, not a
deliberately detached process. No retries, queue, batching, stable event delivery
or distributed exactly-once guarantee is implemented.

Elapsed time includes inventory/copy/worker startup and is not an inference
benchmark. p95, warm/cold target-hardware capacity, queue and batch throughput
remain **unmeasured**. Actual host approval, authentication, stale-result rejection,
durable storage, idempotency, recovery limits and actuation remain host-owned.
