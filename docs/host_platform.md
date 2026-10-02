# cultureQC inside a host platform: what goes in, what comes out

cultureQC is built as one component of an automated culture platform, the
system that schedules visits, moves the vessels, images them, keeps the
audit trail and signs records. cultureQC reads an image and returns a
reading, an action and a hash-chained record. It is not integrated with any
platform, and none of what follows has been run inside one. This page
describes the boundary it is designed for, and which side owns each control.

## Per visit

For each image, the host passes:

| Input | Why |
|---|---|
| The image file | Read once and hashed into the record (`image_hash`) |
| `flask_id` (vessel or labware ID), `cell_line`, `protocol_stage` | Keys the record to the host's own objects |
| `lineage`: passage number, parent vessel | Kept with the reading, so the record of a decision carries the vessel's history |
| `imager_id`, `fov` (field index and position) | Which instrument and where in the vessel |
| `profile_id` | Which imaging setup took the image, so the matching calibration profile reads it (below) |
| `environment` | A snapshot the host already logs (e.g. temperature, CO₂), stored as given |
| Target confluency, hours since passage and since feed | The rules' inputs (`culture/rules.py`) |

and gets back one **reading** record (`culture/schema.json`) with:

- `confluency_pct` and `confluency_interval`, the reading and its 90% error
  band for that imaging setup;
- `recommended_action`: `passage`, `feed`, `continue`, `human_review` or
  `reimage`, with a one-sentence `action_reason`;
- `recovery_request`, `{"action": "reimage", "reasons": [...]}` when the
  image fails the quality gate, for the scheduler to act on;
- the provenance: image, probability map, configs, profile and model weights
  by SHA-256, and the rules version.

```python
from culture.pipeline import analyze

rec = analyze(
    image_path, flask_id="A12", cell_line="C2C12", profile_id="c2c12_ker2018",
    lineage={"passage_number": 7, "parent_flask_id": "A07"}, imager_id="imager-1",
    fov={"index": 3, "x_mm": None, "y_mm": None}, hours_since_passage=hours,
    log_path="records.jsonl",
)
rec["recommended_action"], rec["confluency_interval"], rec["recovery_request"]
```

## Exceptions go to a person; the person's decision is its own record

Only `human_review` and `reimage` need anyone. `reimage` is for the
scheduler. `human_review` is for an operator, with the reason on the record:
the reading's error band includes the target, the anomaly check flagged the
image, or the setup has no calibration profile.

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
so which calibration produced a number can be traced back to the change that
approved it.

## Who owns what

| Control | cultureQC | Host platform |
|---|---|---|
| The reading, its error band, the action and its reason | Yes | |
| Hash chain; record types for readings, reviews and changes | Yes | |
| Checkpoint (record count and head hash) | Writes it (`python -m culture.records checkpoint`) | Stores it outside the log: in its own audit trail or WORM storage |
| Identity, access control, electronic signatures | | Yes |
| Scheduling, re-imaging, vessel handling | Asks for re-imaging | Yes |
| Change control and approval of profiles, rules and models | Records the change | Approves it |
| Validation of the whole system (IQ/OQ/PQ) | Provides the evidence for its part | Yes |

How each clause of 21 CFR Part 11, the FDA–EMA AI principles and the draft
Annex 22 maps onto this split is in `docs/audit_mapping.md`.
