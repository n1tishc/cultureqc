# T07 — Explicit activation ownership

Implemented locally, 2026-10-19. No approval, deployment or threshold change is
created by this implementation.

## Supported deployment contract

**Configuration activation is host-managed.** cultureQC does not implement a
local approved-release registry for profiles, rules, quality/QC settings, anomaly
thresholds, or the complete model stack. Merely appending a `change` record does
not authorize or activate these settings. Do not describe this as a
cultureQC-managed configuration deployment.

The host must approve, authenticate and freeze the complete release before
accepting images: code/rules, configuration files, eligible profile scope,
required checks, model artifacts and matching anomaly banks. Protect these
artifacts from concurrent edits; activate a complete versioned directory and
restart workers rather than editing an in-flight deployment. Reject unapproved
profile changes at that host seam. Existing shipped profiles remain ineligible
for passage; a configured `approval_ref` alone is not an authenticated approval.

All decision outputs remain advisory and `host_actionable: false`. The host owns
final action, identity/signatures, authenticated approval references, clock
synchronization, access control and externally retained audit checkpoints.

## What cultureQC enforces locally

- Shipped Cellpose-SAM and the optional fine-tuned segmentation model must match
  the effective model identity in `configs/approved_changes.jsonl` before use.
  This is not approval enforcement for QC/DINO or the whole release.
- One registry byte snapshot is parsed and hash-chain-checked. Selection does
  not reopen a potentially replaced file. Missing, empty, malformed or broken
  registries authorize nothing. No stat-based decision cache survives a time
  boundary or an on-disk replacement.
- `effective_from` must include a timezone. At check time, the **last appended
  record whose effective time is not later than now** wins per subject/id.
  Future records are ignored until their inclusive time boundary, even when the
  file does not change. UTC offsets are respected. Registry order, not sorting
  by date, breaks ties and defines supersession. The log head may include future
  changes; it is not itself the effective model record.
- A rollback needs a new effective approval naming the earlier hash. Copying old
  weights back while a different hash is effective is refused. Shipped model
  replacement still requires the T06 reload/restart contract; a new approval
  does not magically replace an already loaded instance.
- Anomaly bank caches bind file identity and the expected array-content hash.
  Replacements are revalidated against the consumed config; mismatches or
  corrupt/missing banks are unavailable, never a successful negative check.
  Matching replacements can load on the next request; unavailable results are
  not permanently cached. Loaded arrays are read-only. This is not atomic
  multi-file release activation or protection against a malicious process.

Scheduled model approvals can be prepared with the existing approval CLI's
`--effective-from '2099-01-01T00:00:00+00:00'`. Omitting it means current UTC.
The CLI records the identity it supersedes as of the requested effective time.
It is an administrative writer, not an authenticated approver. Do not invoke it
to fabricate an owner's approval. Ordinary concurrent log writes remain T08.

## Record and migration contract

New readings use schema **0.7**, retaining all schema 0.6 replay fields and adding
`configuration_activation`:

```json
{
  "mode": "host_managed",
  "local_enforcement": false,
  "host_approval_ref": null,
  "configuration_sha256": "<64 hexadecimal characters>"
}
```

The identity hashes canonical JSON of sorted consumed configuration
path/status/hash entries (including absent optional files), the named policy,
effective line configuration, check policy, and full selected profile. It does
not include the changing image measurements or clock. Source paths are part of
the identity: relocating a release changes it. It is not a hash of every Python
source file and does not replace a pinned host code release. The writer verifies
the identity before append and refuses a local-enforcement claim. The null
reference means no authenticated host approval was supplied or verified.

T05 pins each config on first consumption for the request and captures the exact
bytes parsed, avoiding old profile-cache/new-file-hash combinations. Together,
full snapshots and configuration identities trace before/after changes. They
do not enforce activation or provide an atomic snapshot of multiple mutable
files. Offline replay remains model/config-file independent.

Historical schema 0.4/0.5/0.6 readings and profile-change records are not rewritten
or assigned retroactive approvals. Consumers must accept 0.7 explicitly. There
is no new approval registry to seed and no automatic baseline approval. Any
future locally managed mode requires a separately specified authenticated
release-manifest resolver, atomic activation and migration; do not infer that
capability from these records.

## Acceptance tests

`tests/test_activation_timing.py`: inclusive future boundary on unchanged logs,
clock injection, supersession/rollback, offsets, invalid registry data and a
file replacement between reading and selection.

`tests/test_configuration_activation.py`: console/library provenance parity,
changed-profile identity, no fabricated local approval, pre-append validation,
legacy 0.6 acceptance, scheduled CLI input, matching/mismatching bank replacement,
corrupt/missing recovery and immutable loaded arrays. T05 tests retain coverage
of consumed config bytes and stale profile/quality/calibration caches.
