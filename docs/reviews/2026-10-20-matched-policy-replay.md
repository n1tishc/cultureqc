# T02 first slice — Frozen EVICAN policy replay

Implemented locally. T02 is **partial**, not a completed end-to-end benchmark.
No inference, retraining, threshold adjustment, commit, push or deployment.
The standalone website and historical demo records are unchanged.

## Deliverables

- `scripts/compare_decision_policies.py`: freeze, validate and replay common inputs.
- `results/policy_comparison_evican/`: original v2 rule source, 33 paired image
  inputs, frozen provenance manifest and reproducible JSON/Markdown outputs.
- `tests/test_policy_comparison.py`: cache-free replay, integrity/source drift,
  boundary/precedence, unknown timing/checks, denominators and no-overwrite tests.
- [Protocol and next implementation packet](../specs/matched-policy-comparison.md).

## What the replay actually shows

The original v2 rule implementation and current `rules_v0.7` run on the same cached
image identities, under explicit common timing/target scenarios. Separate variants
neutralize the classifier, change decision policy, and then apply the configured
reading/band. There are **33 images**, not 132 independent samples: 132 is the number
of image/target/timing combinations.

With the assumed 48-hour passage / 12-hour feed timing:

| Scenario | Original v2 policy | Current configured policy | Interpretation |
|---|---|---|---|
| 80% target, all 33 | 32 review, 1 continue | 2 review, 31 continue | Less explicit review in this cache, but **zero GT-ready cases**; not evidence of successful passage or saved work |
| 80% target, dense GT ≥40%, n=3 | 3 review | 2 review, 1 continue | Report dense burden beside the all-image rate |
| 50% diagnostic target, all 33 | 32 review, 1 continue | 11 review, 22 continue | All three GT-ready images go to review; no current passage recommendation |
| 50% diagnostic target, current without calibration | — | 1 review, 32 continue; 2 GT-ready called continue | Demonstrates why lower review alone is not a success criterion |

At cutoff 0 versus configured −3.5, the same cached segmentation maps give MAE
**8.36 → 3.78 pp** on these reused 33 images. This is **calibration**, not an improved
or fine-tuned model, and the selection was not fully blind. The script performs no
new optimization. The configured band remains 29.4 pp with unsupported action scope.

Every current output remains advisory. Quality and anomaly checks are unavailable,
not passing. Timing is either explicitly unknown or a labelled assumption.
The mask supplies confluency truth, not an adjudication of feeding, health, timing,
safe passage or automation. No biological independent-unit count or population
uncertainty interval can be justified from these files.

## Verification

- Freeze succeeded from the local caches with unique image/logit joins and exact
  correspondence to the original 33-image truth table.
- Dedicated suite: **20 passed**. Final combined replay/rules/eligibility/claims/
  README-provenance run: **213 passed** (includes those 20, not additional to them):
  `.venv/bin/python -m pytest tests/test_policy_comparison.py tests/test_rules_band.py tests/test_rules_missing_checks.py tests/test_passage_eligibility.py tests/test_claims.py tests/test_readme_provenance.py -q -p no:rerunfailures`.
- Replay artifacts are deterministic and frozen source/input modifications are
  rejected. Existing output directories and historical bundles cannot be overwritten.
- A minimal-copy subprocess test exercises replay without the cache, models, Git
  executable/history, config tree or raw images.
- Independent read-only review found no remaining blocker in this bounded replay.
  It corrected an initial reviewer mix-up between the unrounded fitted band in
  historical results and the actually configured 29.4 pp band.
- `git diff --check` and `deploy/sync_space.py --check` passed. No frontend code
  changed; this task does not claim a new visual, screen-reader or site-build pass.

## What remains

The next code task is the **C2C12 workload-only companion** described in the spec:
preserve sequence/experiment grouping and split/bank provenance; no model-proxy
truth or frame-independent confidence intervals. Independent dense/target-setup
labels, authenticated weights and operational checks are still needed for stronger
claims. Missing historical synthetic headline artifacts are not reconstructed.

This evidence stays internal; it does not turn the homepage into a v2/v4 scoreboard.
Human accessibility checks remain pending by request; T12 fresh visual/pointer
acceptance, V3 rehearsal and external evaluation/release gates remain pending.
