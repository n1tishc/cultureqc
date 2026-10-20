# T06: bind records to the loaded segmentation model

Implemented locally, 2026-10-17–18. Not pushed or deployed. This is a runtime
provenance fix, not a new confluency model or an accuracy improvement.

## Failure and correction

The deterministic reproduction loaded approved weights A, replaced the source
with approved B and requested another reading. Previously, the cached model
still produced A's output while its successful approval check identified B.
Separate record-builder regressions also showed that a file inventory taken
after inference could overwrite the correct per-inference identity.

`culture/seg.py` now verifies the source, copies it into a private read-only
temporary snapshot, verifies that snapshot and loads Cellpose from that path.
The model retains the snapshot owner and its verified digest. Every reading
compares the current approved source with that loaded identity before inference.
An approved replacement refuses the first affected reading and clears the
singleton; retry loads the approved replacement. An unapproved or missing source
refuses. A source replacement during inference does not relabel the output.

`culture/pipeline.py` and `demo/analysis.py` use the particular inference's
`model_check.sha256` for the record's segmentation hash, not a newly discovered
cache file. The console records null when that identity is absent. Other model
hashes retain their existing inventory semantics.

`culture/weights.py` invalidates hash memoization on real path, device, inode,
size and nanosecond modification/change times, including same-size replacements
that preserve modification time.

## Verification and operational contract

Fixture tests cover approved/unapproved replacement, approved rollback, missing
source, unavailable/broken/unrelated approvals, failed load cleanup, device
selection, replacement during copy/load/inference and record-builder consistency.
Two unfinished tests initially represented a valid log without this model using
an empty log. Empty logs correctly report unavailable approvals; those fixtures
now contain a valid unrelated model approval. No production approval semantics
were weakened to make the tests pass.

See [combined verification](2026-10-18-detection-signal-implementation.md).
Cellpose construction and evaluation are stand-ins in those regression tests.
The subsequent [real-Cellpose local CPU check](2026-10-18-cellpose-release-validation.md)
passes with identical probability maps and records startup/resource observations.
Target-host provisioning and capacity verification remain deployment gates;
local parity is not production qualification.

- Provision the approved `cpsam_v2` file before the first shipped-model call;
  loading no longer implicitly downloads a missing shipped artifact.
- Allow temporary disk space for an additional weights copy (about 1.2 GB per
  live model instance), plus copy/hash startup cost. Keep the snapshot until the
  instance is released; cleanup also runs on construction failure.
- Read-only permissions and a private directory prevent ordinary source-file
  replacement from altering loaded bytes. They are not protection against a
  privileged or same-user adversary changing process memory/private files.
- Approval is checked before inference; this is not transactionally locked
  activation/revocation across concurrent administrative writes. T07 and approval
  log consistency remain separate work. Approver authentication is host-owned.
- Fine-tuned loading, DINO/QC lifecycle identity, multi-writer record persistence
  and the remaining T03–T05/T07–T09 contracts are not closed by this patch.
