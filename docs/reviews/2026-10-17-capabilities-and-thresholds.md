# What improved, what works, and what thresholds cannot fix

Reviewed 2026-10-17 against current repository code and committed studies. Independent read-only reviews covered confluency/audit history and contamination/growth detection. No model runs, threshold changes, replacement scientific results, commit or push are authorized by this review.

## Executive conclusion

There is a substantial confluency measurement improvement and a richer audit foundation. There is **not** demonstrated reliable bacterial-contamination or growth-stall detection at the tested imaging setup. If those detectors are mandatory acceptance requirements, the product is not yet complete against them. A better website cannot close that gap.

The VP story should lead with **lab-adapted confluency and inspectable records**, then distinguish shipped behavior, experimental improvements and unfinished detectors. Neither “everything failed” nor “v4 is better at everything” describes the evidence.

## 1. The strongest measured upgrade: confluency

Mean absolute error against expert masks, percentage points:

| mCellSeg evaluation | Default cutoff, no calibration | Setup calibration | Fine-tuned + calibrated |
|---|---:|---:|---:|
| Sealed test, 90 images | 26.49 | 7.80 | **2.65** |
| Swapped test, 79 images | 24.81 | 7.40 | **1.71** |
| Combined secondary analysis, 169 images | 25.71 | 7.61 | **2.22** |

Sources: [sealed study](../../results/confluency_mcellseg.md), [swapped and pooled study](../../results/confluency_mcellseg_swap.md).

- The pooled reduction versus calibration alone is approximately **71%**, calculated from the stored unrounded means. Readings within 5 pp improve from **73/169 to 153/169**. In the 60–90% range, mean error falls from **8.82 to 4.22 pp**.
- This is four setups, one lab, two cell lines; not a multi-instrument deployment study. Each test image was read by a model not trained on it, but the two halves are not independent studies. The pooled result is secondary.
- The sealed dense-range improvement meets its predeclared comparison: +4.45 pp, 95% interval +0.83 to +7.94. Swapped improvement is +4.84 pp, interval −0.80 to +12.29; that comparison **does not meet the replication criterion**.
- Pooled fine-tuned action agreement is **15/17**, below 95%. Two early passage calls occur at expert readings of 77.9% and 79.3% against an 80% target. Only ten images reach 80% across both halves. Better measurement is not validated automated passage.
- Fine-tuning is experimental and does not drive shipped recommendations. The console's four selected examples use retrained illustration weights; the original scored weights were not retained. See [figure provenance](../../results/confluency_finetune_figure.md).

Separately, the shipped setup-calibration capability reduces MSC error **8.19 → 3.43 pp** on 320 images with leave-one-population-out evaluation. Only four images are at 60–90%, so passage-range criteria could not be established there. [Calibration study](../../results/confluency_profiles.md).

### Do not label those columns “v2” and “v4”

The default-cutoff arm resembles v2's approach, but these are matched measurement methods, not executions of the two product releases. V2's historical 2.34 pp headline was synthetic, and its per-tile reconstruction artifacts are unavailable. It cannot be numerically compared with the real-image 2.22 pp result. [Historical headline audit](../../results/v02_headline.md).

## 2. Major changes versus v2, translated for the VP

| Area | Actual advance | VP significance / boundary |
|---|---|---|
| Confluency | Setup-specific cutoff calibration and estimated error bands; strong experimental fine-tuning results | A path to measurements adapted to the instrument rather than a single default cutoff. Fine-tuning is not yet the decision model. |
| Decisions | Image-quality rejection, uncertainty-aware passage review, uncalibrated-at-target review, anomaly hold for otherwise eligible passage | More explicit reasons to ask a person or re-image; not proof that autonomous action is correct. |
| Audit events | Separate linked review events and structured change records with before/after hashes and evidence fields | Better investigation and change-control foundation. The displayed chain has seven readings and two changes, **no review event**. |
| Audit verification | Browser inspection/tampering demonstration and external-checkpoint verification of chain rewrites/deleted tails | Integrity can be inspected; independently trusted checkpoints and host identity remain required. V2 already had SHA-256 chaining—it is not new by itself. |
| Provenance | Richer quality, calibration, acquisition/configuration and model-check fields | More context to investigate a reading. Missing effective decision inputs and runtime identity gaps still prevent a complete reproducibility claim. |
| Detection approach | Synthetic classifier demoted; real-image anomaly banks, image-quality gate and replay evaluation added | More honest and better scoped than synthetic-only accuracy. Does **not** establish improved biological-contamination or stall sensitivity. |

Sources: [pipeline](../../culture/pipeline.py), [rules](../../culture/rules.py), [records](../../culture/records.py), [model loading](../../culture/seg.py), [classifier configuration](../../configs/qc.yaml). Historical comparison inspected commit `e2274dd`.

Existing runtime backlog remains: cached loaded-model versus file identity, multi-writer chain appends, complete decision inputs, activation/approval semantics and image decoding. See [T03–T09](2026-10-15-v4-vs-v2-agent-backlog.md). Hashes do not establish biological validity, signed identity or regulatory compliance.

## 3. Contamination: a genuine detection gap

- The successful stress test pasted bacteria **16.5× too large**: 49/49 held-out contaminated frames flagged, AUROC 1.00, only two held-out sequences.
- At realistic simulated size: **1/49 held-out frames flagged**, versus **2/49 clean control frames**; AUROC **0.48**. Across both splits, 1/97 contaminated versus 4/97 clean frames were flagged. Removing simulated haze did not fix it.
- These are simulations on real C2C12 backgrounds, not natural contaminated cultures. Heavier contamination beyond the tested range was not evaluated.
- The anomaly detector examines a **256 px centre tile, roughly 4.5% of the image**. At the tested 1.3 µm/px scale, the median simulated bacterium is only about 3.6 px long; the old exaggerated sprite was 59 px. Coverage, optical resolution and feature suitability are plausible improvement targets—not established fixes.
- The v2 classifier's synthetic headline does not transfer: only **5% of 1,228 healthy real C2C12 frames** were called normal. It is demoted from current product decisions.

Sources: [realistic-size experiment](../../results/contamination_scale.md), [anomaly study](../../results/anomaly_summary.md), [classifier transfer](../../results/classifier_c2c12.md).

**Threshold interpretation:** the current score is higher for more unusual images; lowering its cutoff raises sensitivity and false alarms. Its thresholds target 5% tuning false positives but produce **10% held-out normal flags**. Near-chance ranking on realistic bacteria supplies no evidence of a useful cutoff that separates bacteria from clean images. No saved recall-versus-false-positive threshold sweep was found in the inspected anomaly results. Do not claim a threshold-only fix.

A gate-triggered **REIMAGE is not a contamination diagnosis**. Current rules can hold an uncalibrated high-confluency image for review, but that is a decision safeguard, not successful contamination detection. Historical architecture prose about rules_v0.3 is not current rules_v0.5 behavior.

## 4. Growth stalls: noise, adaptation and threshold tradeoffs

- **0/2 held-out simulated stalls detected** at all tested 6h/12h and 1/3-FOV combinations. The simulation slows progression to 40% speed; a single frame has no new visual contamination cue.
- Per-visit growth versus field-sampling noise is only **0.35–1.12×**, against a proposed 2× signal criterion.
- The repeatedly refitted growth curve can absorb the slowdown; the growth residual also needs five earlier visits. Making an alert easier to trigger does not remove these limitations.

The existing SPC tuning sweep does show a sensitivity/noise tradeoff:

| Limit multiplier | False alarms per 100 tuning visits | Tuning fault runs detected |
|---|---:|---:|
| 1.0 | 9.38 | 10/16 |
| 1.5 | 3.12 | 4/16 |
| 1.8, selected | 0.89 | 2/16 |
| 2.25 | 0.45 | 0/16 |

**Important:** this is the historical combined-monitor sweep across fault types, not a stall-only improvement. Sixteen runs repeat four tuning fault sequences across visit settings; they are not sixteen independent faults. Anomaly/class trend monitors were subsequently dropped. The chosen multiplier still gave **3.75 false alarms/100 held-out visits** and no held-out contamination/stall detection. Do not turn 10/16 into a current stall-recall claim.

Sources: [SPC results and sweep](../../results/spc_summary.md), [growth/noise study](../../results/growth_signal_summary.md), [architecture mechanisms](../ARCHITECTURE_VALIDATION.md).

## 5. Three different “thresholds”—do not mix them

1. **Detector operating threshold:** lower anomaly/SPC limits can yield more alerts and more false alarms. Choose using tuning data and an explicit operational cost budget.
2. **Measurement/action boundary:** the 80% passage target and uncertainty band determine action. The sealed fine-tuned study's two early calls came with a band that was too narrow on that setup; relaxing review may worsen those errors. A biologically acceptable tolerance needs a protocol agreed before testing, not a retrospective pass.
3. **Acceptance criterion:** changing “90% detection” or “95% agreement” after seeing results changes the goalpost, not the detector. Even a more permissive sensible criterion does not make 0/2 detected stalls an effective detector.

## 6. Implementable next experiments, not threshold deployment

| Packet | Depends on | Work | Required output |
|---|---|---|---|
| E0: freeze protocol | Owner's instrument/use case | Specify objective, pixel scale, FOV coverage, cadence, acceptable false alerts, detection delay and confirmed labels; split by culture/sequence/session | Versioned protocol and untouched final-test manifest |
| E1: contamination operating curves | E0 + labelled target-setup data | Compare current centre tile with multi-tile/native-resolution coverage; fit candidate score cutoffs on tuning data only | Sensitivity/FPR curves, per-sequence confidence intervals, missed-example gallery; no success claim without signal separation |
| E2: stall signal redesign | E0 + longitudinal data | Compare registered/larger FOVs, frozen healthy-reference forecasts and longer-horizon accumulation; sweep growth-only limits | False alerts/100 visits, detected sequences and delay, including gate-rejected visits as a separate event stream |
| E3: confluency/action confirmation | E0 + new dense-range masks | Reproduce/retain exact model artifacts, verify dense-range bias and interval coverage, tune on development data then freeze | Held-out measurement and action results across enough independent ≥80% cultures; retained weights and run manifest |
| E4: evaluate and approve | Relevant E1/E2/E3 + runtime backlog | Score untouched tests once; reject regressions; explicitly decide experimental versus active capabilities | New source reports, approved configuration records and rollback plan—only then consider activation |

E1, E2 and E3 can run independently after E0. Larger-FOV growth signal estimates in existing results are extrapolations, not completed detector validation. No particular replacement cutoff is justified yet. Current threshold/configuration files are unchanged.

**Implementation follow-up:** [E0–E4 packets and readiness tooling](../specs/detection-experiments/README.md) now provide draft protocol/manifest files and a read-only preflight checker. E0 preparation is implemented, but owner inputs, independent data allocation and approval remain pending; no frozen protocol or new detector result is claimed.

## Website changes in this pass

- Fine-tuning gains lead Evidence, followed by calibration and inspectable audit records; no version-versus-version hero.
- Removed the public architecture V1–V10 catalogue and pass/fail tally. These are experiment IDs, not ten product versions. Source reports remain unchanged and linked under supporting evidence.
- Full confluency criteria and detection matrix use expandable details. Realistic contamination and stall limitations remain visible in a concise “Further improvements” summary; failed results were not changed into successes.
- Legacy `/validation#checks` still reaches detection scope. Fine-tuning's failed action criterion, non-replication and non-decision role remain adjacent to the headline.
- Human screen-reader/200% zoom checks remain pending. Nothing pushed; user approval remains required.

### Verification

- `node --test site/tests/*.test.js`: 11 passed; `npm --prefix site run build`: passed.
- `node --check site/tests/evidence.browser.js` and `git diff --check`: passed.
- New saved `site/tests/evidence.browser.js`: headline values/scope, removed catalogue, visible detection gaps, keyboard-operated disclosures, retained failed criteria, legacy anchor, desktop/mobile document width and linked nine-record verification passed.
- Existing `site/tests/technical-controls.browser.js`: all replay and fine-tuning setup controls passed after the page reordering.
- Independent source review prompted three corrections: explicit headline action/non-replication limits, “simulated” contamination wording, and removal of a stale “above” reference. A separate factual review found no substantive error in the detection/threshold experiment plan.
- One desktop/mobile capture batch was inspected: [Evidence desktop](assets/2026-10-17-evidence/desktop.png), [Evidence mobile](assets/2026-10-17-evidence/mobile.png), [detection desktop](assets/2026-10-17-evidence/detection-desktop.png), [detection mobile](assets/2026-10-17-evidence/detection-mobile.png). No document-width overflow at 1280 or 390 px. This is scoped visual review, not human AT/zoom acceptance.
- Protected scientific/backend/configuration paths match HEAD; the existing `site/src/data.json` edits remain untouched.
