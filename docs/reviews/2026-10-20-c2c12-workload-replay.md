# T02 second slice — C2C12 workload-only replay

Implemented locally, without new inference, training, threshold changes, commits,
pushes or deployment. T02 remains **partial**: these cached replays do not deliver
independent biological decision evidence or an end-to-end model comparison.
The EVICAN bundle, historical results, runtime policies and website are unchanged.

## Deliverables

- `scripts/compare_c2c12_workload.py`: freeze/validate/replay common cached inputs.
- `results/policy_comparison_c2c12/`: 1,228 frozen frame inputs, archived exact v2
  rules, split/quality/anomaly snapshots, manifest and reproducible reports.
- `tests/test_c2c12_workload.py`: isolated cache-free replay, integrity refusal,
  cohort/lineage semantics, quality/anomaly consistency, timing, group denominators
  and unmeasured-accuracy safeguards.
- [Updated protocol and remaining evidence requirements](../specs/matched-policy-comparison.md).

The evidence agent audited original cohort/bank/split provenance and independently
reviewed the implementation. It found no blocking join or metric issue. Manifest
checksums are explicitly not an externally protected authenticity anchor.

## What it shows

These are **rule outputs**, not measured minutes of human work. “Normal” means
unmodified source frames, not a biological health adjudication. Current continue
outputs still require host review/authorization; they are not automated clearance.

At the historical 80% target, with assumed 48-hour passage / 12-hour feed timing:

| Cohort | Original v2 policy | Classifier-neutralized v2 | Current configured policy |
|---|---|---|---|
| All 1,228 frames | 977 review, 251 continue | 70 review, 1,158 continue | 149 reimage, 1,079 continue |
| Dense **reading** ≥40%, n=160 | 130 review, 30 continue | 70 review, 90 continue | 25 reimage, 135 continue |

No cached reading reaches 80%; maximum is 56.98%. **Zero explicit current review
does not prove successful passage or elimination of review work.** Current reimage
burden is 12.1% overall and 15.6% in the dense-reading subset. No independent mask
truth is available to score accuracy or passage safety.

At the diagnostic 50% target, current policy gives **42 review + 149 reimage** on
all frames; the dense-reading subset has **42 review + 25 reimage out of 160**.
The target is illustrative, not a proposed culture threshold. Unknown timing
preserves a distinct reason from assumed elapsed timing even where actions match.

The 123 anomaly flags are neither 123 human-review requests nor confirmed
contamination events. The historical centre-tile scorer is not the new experimental
whole-frame coverage method. Growth stalls and simulated faults are not scored here.

## Why grouping matters

There are **14 sequence groups across 3 experiment groups**, all three also present
in tuning. These are not 1,228 independent cultures, and the 4,912 image/context
rows are not additional samples. Both group levels and their equal-group averages
are retained alongside frame-weighted pooled rates.

At 80%, current reimage counts by experiment are 29/170, 110/623 and 10/435
(about 17.1%, 17.7% and 2.3%). The pooled result hides this variation. Dense-reading
frames occur in only 8 of 14 sequences; empty groups have null rates, not perfect
performance. No population interval or ROI is inferred.

## Reproducibility and verification

```sh
.venv/bin/python scripts/compare_c2c12_workload.py --out /tmp/cultureqc-c2c12-replay
```

Use a new output directory. Replay needs no cache, weights, raw images, root
configs, Git executable/history or network. The suite copies only source files and
the frozen bundle into a minimal temporary tree to verify this.

- Initial combined C2C12/EVICAN replay suite: **45 passed**.
- Final combined replay/rules/eligibility/claims/README-provenance suite:
  **238 passed** (includes the 45 above, not additional to them):
  `.venv/bin/python -m pytest tests/test_c2c12_workload.py tests/test_policy_comparison.py tests/test_rules_band.py tests/test_rules_missing_checks.py tests/test_passage_eligibility.py tests/test_claims.py tests/test_readme_provenance.py -q -p no:rerunfailures`.
- Full paired outputs and reports reproduce exactly; original bundle bytes are
  unchanged after replay.
- All frozen sources/artifacts are checked before baseline execution. Changed
  observations, groups, truth labels, quality outputs and anomaly flags are rejected.
- Configured bank array hash matches the loaded bank arrays. The NPZ file hash is
  separately recorded; it is not mistakenly compared with the array-content hash.
- Exact historical weight provenance and per-row score-to-bank binding remain
  unavailable. The checks do not manufacture that missing provenance.
- `deploy/sync_space.py --check` and `git diff --check` passed.

No frontend code changed, so this does not claim a new website visual/build or
human accessibility pass.

## Next work

Further scientific claims require the approved target-setup cohort, independent
annotations, actual operational timing/checks and weight provenance described in
the partner-pilot packet. No additional model run or threshold relaxation follows
automatically from this report.

The next independently actionable local acceptance step is the pending T12
desktop/mobile visual and pointer check, then the VP walkthrough once its gates
are met. Human screen-reader and actual 200% zoom verification remain pending by
request; no public release is authorized.
