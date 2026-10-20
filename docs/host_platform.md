# cultureQC inside a host platform: what goes in, what comes out

cultureQC is built as one component of an automated culture platform, the
system that schedules visits, moves the vessels, images them, keeps the
audit trail and signs records. cultureQC reads an image and returns a
reading, an action and a hash-chained record. It is not integrated with any
platform, and none of what follows has been run inside one. This page
describes the boundary it is designed for, and which side owns each control.

For a bounded first evaluation, use the proposed
[one-setup partner pilot protocol](specs/partner-pilot.md) and its
[approval worksheet](specs/partner-pilot-approvals.md). The first phase is offline,
confluency/audit-focused and non-actuating; setup, sample plan, rights and acceptance
require partner signoff. The proposal does not activate a profile or authorize
deployment.

See the [release-state and evaluation boundary](specs/release-state.md) for the
local source/runtime identities, stored versus live surfaces, component terms
and unresolved commercialization gate.

## Per visit

For each image, the host passes:

| Input | Why |
|---|---|
| The image file | Read once and hashed into the record (`image_hash`) |
| `flask_id` (vessel or labware ID), `cell_line`, `protocol_stage` | Keys the record to the host's own objects |
| `lineage`: passage number, parent vessel | Kept with the reading, so the record of a decision carries the vessel's history |
| `imager_id`, `fov` (field index and position) | Which instrument and where in the vessel |
| `profile_id` | Which imaging setup took the image, so the matching calibration profile reads it (below) |
| `setup_id` | Host-controlled, versioned capture configuration identity; separately matched to approved decision scope, never inferred from the selected profile |
| `environment` | A snapshot the host already logs (e.g. temperature, CO₂), stored as given |
| Target confluency, hours since passage and since feed | The rules' inputs (`culture/rules.py`) |
| `captured_at` | Host capture timestamp with timezone; omitted means explicitly unknown, never replaced with analysis time |

and gets back one **reading** record (`culture/schema.json`) with:

- `confluency_pct` and `confluency_interval`, the reading and its 90% error
  band for that imaging setup;
- `recommended_action`: `passage`, `feed`, `continue`, `human_review` or
  `reimage`, with a factual `action_reason`;
- `decision`: stable reason code, check requirements/results, passage/feed
  timing and warnings. Under `rules_v0.7`, all actions have `mode: advisory`
  and `host_actionable: false`; the host must not treat them as commands;
- `passage_eligibility`: whether the actual setup, cell line, loaded model hash,
  reading and target match an approved decision scope, plus the reason;
- `recovery_request`, `{"action": "reimage", "reasons": [...]}` when the
  image fails the quality gate, for the scheduler to act on;
- the provenance: image, probability map, configs, profile and model weights
  by SHA-256, and the rules version.

New records use **schema 0.8**. `decision_inputs` retains immutable effective
rule inputs; `replay_decision(record, record["decided_by"])` reproduces the
decision without models or mutable configuration. `config_snapshot` holds
actually consumed YAML text/path/hash, including anomaly overrides; configuration
hash keys are now effective source paths, not a post-run inventory of filenames.
Approvals remain identified by `model_check.approvals_head`. Analysis start/end
timestamps and finalization time are separate from nullable host capture time.
See [decision replay and migration](specs/decision-replay.md) before updating a
host consumer. This does not make outputs host-actionable.

`configuration_activation` explicitly states `host_managed`, with
`local_enforcement: false`, no authenticated host approval reference, and a
configuration identity derived from the consumed snapshots and effective policy.
The host must approve and freeze a complete release before inference; recording
a configuration change does not enforce that approval locally. Only the shipped
and optional fine-tuned segmentation models have local effective-time approval
checks. See the [activation and migration contract](specs/configuration-activation.md).

`preprocessing` records the controlled decoding policy, original-byte hash,
source format/mode/dimensions, grayscale transform, decoder version and decoded
pixel hash. Live inputs must be single-frame uint8 grayscale/RGB with default
orientation and no transparency. High-bit-depth inputs, including 12-bit data
stored in uint16, are refused rather than implicitly darkened or auto-scaled.
Use a separately validated fixed setup-specific export for unsupported inputs;
this release supplies no approved high-bit-depth mapping. See the
[ingestion contract](specs/controlled-image-ingestion.md) for limits and migration.

```python
from culture.pipeline import analyze

rec = analyze(
    image_path, flask_id="A12", cell_line="MSC", profile_id="msc_phase",
    lineage={"passage_number": 7, "parent_flask_id": "A07"}, imager_id="imager-1",
    fov={"index": 3, "x_mm": None, "y_mm": None}, hours_since_passage=hours,
    log_path="records.jsonl",
)
rec["recommended_action"], rec["confluency_interval"], rec["recovery_request"]
```

## Exceptions go to a person; the person's decision is its own record

These remain research/advisory outputs, not permission to operate lab equipment.
`reimage` is for the
scheduler. `human_review` is for an operator, with the reason on the record:
the reading's error band includes the target, the anomaly check flagged the
image, or the setup lacks calibration or approved passage eligibility.

The operator's decision is written with `culture.records.review_event` as a
**review** record that points to the reading's `record_hash`. The reading is
never edited. The review carries the decision (`accept` or `override`), the
final action, the reason (required for an override), the reviewer, the meaning
of the signature and the time. Identity, authentication and the electronic
signature are the host's; the review carries `host_signature_ref`, a pointer
to the host's signature record.

## A new microscope or cell line: calibrate, then change control

The cutoff that turns Cellpose-SAM's probability map into a reading depends on
the imaging setup (`results/confluency_profiles.md`). A new setup starts as
`uncalibrated`: its readings carry no error band, and the rules never passage
on them alone. To calibrate it:

1. Label cell versus background on a few dozen images from that setup.
   `scripts/label_page.html` is the brush page used for the C2C12 frames.
2. Fit the profile with `scripts/confluency_profiles.py`: the cutoff on half
   of the images, and the error band measured on images left out of the fit.
   Its learning curve shows how the error falls with the number of labelled
   images.
3. Test it once on the other half against criteria written down beforehand
   (A1–A5 in `results/confluency_profiles.md`).
4. Add it to `configs/confluency_profiles.yaml` under the host's change
   control, and write a **change** record (`culture.records.change_event`):
   the profile it replaces and the new one by SHA-256, the reason, the
   results file by SHA-256, and the approver.

From then on, every reading from that setup names the profile and its hash,
so the host can trace which calibration produced a number and link it to its
authenticated approval. cultureQC records this configuration but does not check
profile activation against a local approval registry.

## Measurement calibration is not passage validation

`rules_v0.6` introduces a conservative product-policy gate. Existing `validated`
profile status describes measurement calibration only: MSC and EVICAN passed
their measurable criteria but have no measurable A2/A3/A4 decision-range evidence.
Their cutoffs, bands and historical results are unchanged; neither is authorized
for automatic passage. All shipped profiles have unsupported action eligibility.

A future eligible profile needs all A1–A5 passes, an approval reference and a
`validated_scope` binding a versioned `setup_id`, cell line, model SHA-256,
reading range and target range. The host must bind that setup ID to its microscope,
objective, modality, pixel scale and capture/preprocessing configuration under
change control, and change the ID when any relevant setting changes. Selecting
`profile_id` is not evidence that this setup matches. Missing or mismatched context
leaves the measurement available but blocks a passage recommendation. Unknown
explicit profile IDs and malformed profiles raise `ValueError` rather than falling back.

The approval reference is host-managed configuration, not authentication or an
electronic signature; this gate does not replace the host's approval controls.
See `docs/specs/passage-eligibility.md` for migration and remaining policy gaps.

## Who owns what

### Missing checks, timing and recovery

Image quality is required for passage candidates. Anomaly is exploratory and
optional by default; demoted QC is explicitly not applicable. A required check
that is unavailable cannot silently pass. Callers can declare anomaly/QC
requirements with `CheckPolicy`; doing so is not detector validation or approval.
Unknown passage time never satisfies the passage interval; unknown feed time
does not mean feeding is unnecessary. Live console timing now defaults to null,
not invented 48h/12h history. Numeric/flag validation raises `ValueError` for
malformed inputs before a normal decision is emitted.

The host owns bounded timeouts/retries, reimage scheduling, stale-result rejection
and escalation. An exception/timeout is not a negative check or an implicit
continue. No infinite recovery loop or scientific threshold is introduced.
See [the rules_v0.7 contract](specs/missing-checks-and-timing.md) for precedence,
stable fields and migration. T05 supplies immutable-input replay as specified above.

| Control | cultureQC | Host platform |
|---|---|---|
| The reading, its error band, the action and its reason | Yes | |
| Hash chain; record types for readings, reviews and changes | Locked local POSIX append with file/directory sync | Durable storage, retention and idempotent delivery |
| Checkpoint (record count and head hash) | Writes it (`python -m culture.records checkpoint`) | Stores it outside the log: in its own audit trail or WORM storage |
| Identity, access control, electronic signatures | | Yes |
| Scheduling, re-imaging, vessel handling | Asks for re-imaging | Yes |
| Change control and approval of profiles, rules and models | Records the change | Approves it |
| Validation of the whole system (IQ/OQ/PQ) | Provides the evidence for its part | Yes |

Audit appends serialize verification, finalization and writing across cooperating
threads/processes on one local POSIX file. Corrupt or unterminated tails are
refused without repair. Success follows file and parent-directory `fsync`;
an exception after writing has an uncertain outcome, so the host must reconcile
a stable event ID before retrying. This is not exactly-once delivery, shared
network storage support, or durable retention on `/tmp`. Stop workers before
rotating/replacing a log and retain external checkpoints. See the
[concurrent audit contract](specs/concurrent-audit-append.md) for storage and
recovery responsibilities.

How each clause of 21 CFR Part 11, the FDA–EMA AI principles and the draft
Annex 22 maps onto this split is in `docs/audit_mapping.md`.
