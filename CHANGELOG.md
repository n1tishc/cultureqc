# Changelog

Changes that affect what a record says, what the rules decide, or what a
viewer is told. Commit hashes are on branch `slice-1b-compute-cache`.

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
