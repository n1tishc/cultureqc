# T11 handoff — release boundary and host evaluation

Date: 2026-10-19. Status: **implemented and checked locally; not published**.

## Delivered

- [Release-state map](../specs/release-state.md): local library, stored product
  site, console, local API versus unverified remote API, raw demo and experimental
  model are distinct. Exact schema/policy provenance stays with each artifact;
  current schema `0.8` is not retrospectively applied to stored site examples.
- [Host evaluation contract](../specs/host-evaluation.md) and
  [`scripts/host_evaluation.py`](../../scripts/host_evaluation.py): current-record
  inspection or explicit live-library execution in a bounded worker. All outcomes
  are non-actuating and require operator review; failures/timeouts are not
  implicit continues. A new directory retains input, request, diagnostics,
  optional evaluation log, outcome and source/dependency/artifact manifest.
- [`requirements-host-eval.txt`](../../requirements-host-eval.txt) and a separate
  CI contract job: no model weights or private credentials required. The full
  live-model environment remains separately provisioned and approved.
- Website opening and footer disclose **Code: MIT**, stored walkthrough execution,
  unresolved pipeline commercial status and the legacy API boundary. Licensing
  links target the upgrade branch, not the default branch. A local preview's
  footer explicitly notes that HEAD does not identify uncommitted changes.
- README/deployment/host docs link the release map. Named owner roles and required
  rights/deployment evidence are specified, not falsely completed.

## Review findings addressed

An independent read-only review flagged inventory failures outside the exception
path, an exit-versus-timeout process race, and overstatement risk around a
manifest's reproducibility. The harness now records manifest failure, tolerates
an already-exited process group while retaining timeout status, bounds Git
inventory commands and refuses a changed source/config inventory. Documentation
distinguishes an inventory from a retained, approved reproducible model bundle.

Current-record assessment checks the **original** JSON against the schema before
writer preparation: it cannot silently fill missing record identity or replace
an invalid previous hash. It then exercises existing semantic validation without
appending or rewriting the original. Standalone assessment does not verify the
original chain or authenticate a record; live mode verifies its separate log.

## Validation

- Fresh `/tmp/cultureqc-t11-clean` environment, CPython **3.14.7**, installed all
  25 pinned lightweight dependencies. Initial offline-cache install lacked a
  wheel; package installation then succeeded with authorized network access.
- Final clean-environment host suite: **26 passed**, no skips. Verified `torch`,
  `cellpose`, `gradio`, `transformers` and `huggingface_hub` are absent there.
  Measurements/approvals in these tests are synthetic stubs, not scientific data.
- Related local run before the final five additional harness cases:
  `tests/test_host_evaluation.py`, `tests/test_decision_provenance.py`,
  `tests/test_ingestion_records.py`: **75 passed**. These overlap the clean suite;
  do not add the counts as independent coverage.
- Site unit tests: **11 passed**; production build passed.
- Both generated Space trees match root: `deploy/sync_space.py --check` passed.
- `git diff --check` passed.
- Local browser checks at **1440 px** and **390 px** confirmed visible opening
  disclosures, correctly formed licensing/release links and no horizontal page
  overflow. Desktop screenshot capture timed out; no screenshot-based visual
  approval is claimed. The scoped browser task was closed without deployment.

New repository documentation links will only become publicly available after
the user's publication approval; browser checks verified link construction, not
remote publication. No actual model inference or target-host benchmark was run
for this task. Remote CI has not been claimed as passed.

## Still owner-held / pending

- Commercial rights clearance or a reviewed replacement-model/data plan.
- Actual partner setup, sample counts, budget and pilot authorization (T10/E0).
- Target-host inference environment, signed bundle identity, hardware/driver
  inventory, latency distribution, queues, batching and recovery validation.
- Remote source/default-branch/deployment reconciliation, only after approval.
- Human screen-reader and actual 200% zoom checks remain intentionally pending;
  timed VP rehearsal is separate. Nothing here closes them.

No commit, push, merge, deployment, approval-template change or historical
result regeneration occurred. Existing worktree edits were preserved.

## Next step

**T12 — proof journey and current documentation consistency.** Reconcile current
schema/policy guidance and evidence links without rewriting archived examples.
The matched internal v2/v4 study (T02), independent biological validation and
owner approvals remain distinct work; none is implied by the host harness.

Tooling notes: Impeccable reported stale surface-target/build-path metadata;
repair was not folded into this task. Ego Lite offered an update; no upgrade was
performed without user approval.
