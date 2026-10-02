# Changelog

Changes that affect what a record says, what the rules decide, or what a
viewer is told. Commit hashes are on branch `slice-1b-compute-cache` unless a section names another.

## Confluency calibration profiles (from 2026-10-02, branch `confluency-calibration`)

The confluency reading is now calibrated per imaging setup and carries a
measured error band; reviews and changes are their own records. Method and
acceptance criteria were committed before scoring (`1ef52cb`, `2baa18f`):
`results/confluency_profiles.md`.

### Rules `rules_v0.5`

- **Passage reads the error band.** A reading whose band clears the target
  passages; a band that includes the target goes to a person; a setup with no
  calibration profile never passages on its reading alone.
- **Boundary ambiguity no longer decides.** It tracks density, not the
  reading's error (`results/confidence_vs_error.md`); it stays in the record.
- **`reimage`** is a new action: the image failed the quality gate calibrated
  for its setup.
- An anomaly flag still holds a passage (unchanged since `rules_v0.3`); its
  density bin is still picked by the reading at Cellpose's default cutoff,
  which its banks were calibrated on.

### Records: schema `0.4`

- Three record types in one chain: `reading`, `review` and `change`.
  `reviewed_by` and `review_outcome` are gone from the reading: a review is a
  new record linked to the reading's hash, so the reading is never edited.
- A reading names its confluency profile (id, SHA-256, status, cutoff, band)
  and carries `confluency_interval`, the quality gate's result, a
  machine-readable `recovery_request`, the host platform's keys (`lineage`,
  `imager_id`, `fov`, `environment`), and `model_weights_hash`, now filled.
- `config_hashes` adds `confluency_profiles.yaml` and `quality.yaml`.

### Docs

- `docs/host_platform.md`: what a host platform supplies and receives per
  visit, how exceptions, reviews and profile changes flow, and who owns which
  control.
- `docs/audit_mapping.md`: the record fields and the Part 11 rows for schema
  0.4.

## Pre-freeze fixes (from 2026-09-30)

Fixes from a self-review and an outside review: wrong or under-disclosed
things corrected, no new capability. `docs/STATUS.md` has the item-by-item log.

### Rules `rules_v0.4`: label only

- **`hold` is renamed `continue`.** "Hold" read as "put this flask on hold";
  the action means keep culturing, no action now. **Every decision is
  identical to `rules_v0.3`**: the seven stored examples were re-derived from
  their stored model outputs, with no model run, and give the same action
  (four `hold` → `continue`, three `human_review` unchanged).
- Rule 2's reason now names the score it uses: "Boundary ambiguity 0.99 is
  above 0.70 (record confidence 0.01 below floor 0.30): …".
- "Passage held" (an anomaly flag turning `passage` into `human_review`) is
  unchanged in meaning and wording.

### Records: schema `0.3`

- `culture/schema.json` now matches what the pipeline writes:
  `confluency_method` values (`probmap`, `instance`, `threshold`), the
  `record_hash` property, and `continue`. `schema_version` moves from `0.2`
  (never bumped when v0.3 added the `anomaly_*`, `config_hashes` and
  `confluency_map_hash` fields) to `0.3`. The stored records are validated
  against it in `tests/test_demo_examples.py`, and the smoke test's schema
  check is no longer an expected failure.
- **Hashes changed.** The seven stored example records were re-chained with
  `decided_by: rules_v0.4`, the new reason text and `schema_version: 0.3`, so
  every `record_hash` and `prev_record_hash` differs from the v0.3 records.
  `record_id`, timestamps and every model output are unchanged.
- The field `confidence` keeps its name; see the next section.

### The confluency score is shown as "boundary ambiguity"

- A pre-registered check (`results/confidence_vs_error.md`; rule committed in
  `3a15fda` before the result in `1d64ee5`) found the score does not predict
  the reading's error (Spearman ρ −0.36, 95% CI −0.69 to +0.02; risk–coverage
  no better than random, p = 0.303) and tracks density instead. Viewers now
  see 1 − `confidence` as **boundary ambiguity**, a density-sensitive review
  trigger; the review threshold is unchanged (`f5532f5`).

### What a viewer is shown (`8` in `docs/STATUS.md`)

- The demoted QC classifier is off the site's example cards. It is still in
  every record (`qc_used_in_decision: false`); the console keeps it collapsed
  under "Demoted — known wrong on real frames (5.0% of normal frames called
  normal); not used for the action".
- The contamination replay's passage forecast is exported as
  `status: "suppressed_fault"` with the reason "driven by pasted bacteria
  raising measured confluency, not by growth"; the site and console show the
  reason instead of a crossing time. The fit is kept in the replay JSON; the
  growth model is unchanged.
- The Timeline says why its passage target is 50% (the recordings never pass
  57.0%) while the Analyze examples use 80%.
- Site sections reordered: Reading, Confluency, Records, Integration, Timeline,
  Limits, Validation, Since v0.2.

### Audit chain

- `verify_chain` returns a structured result; a missing or empty log is no
  longer reported as intact. `checkpoint()` records the count and head hash,
  and verifying against it catches the two changes a bare chain misses: a
  full rewrite and a deleted tail (`8542add`). Docs no longer say an edit
  "breaks every link after it".
- The site's Records section has two more switches, rewrite record 3 and every
  later hash, and delete the last two records: the chain alone passes both,
  and the checkpoint shipped with the page (made from the stored records at
  build time) catches both.

### Repository

- The earlier working specs (`cultureQC_upgrade.md`, `cultureQC_upgrade_spec.md`)
  are no longer tracked; they stay readable in history at `4a82657`. History
  was not rewritten (`1e6b77e`).
- CI runs on this branch, including the Python tests that need no model
  weights or cache (`1e6b77e`).
- `configs/detectability.yaml`: one wording change in `tested_setup`, no
  numbers. Its SHA-256 changes. The five replays are re-exported, and that
  hash is the only line that differs; the stored examples keep the hash that
  was in force when they were made.
- The claims checker's integration and audit-trail rules are generic: any
  "integrates with …" unless negated, and any statement that another system
  lacks audit trails.
- README: a "How it was built" section; the dated decisions it lists are in
  `docs/STATUS.md`.
