# Evidence-informed pilot thresholds: proposed, not approved

Researched 2026-10-17. Scope: non-actuating cultureQC research pilot, not sterility release, diagnosis or autonomous passaging. No model, configuration, protocol approval or historical result is changed by this document.

## Conclusion

The primary sources reviewed support frequent, spatially representative imaging and an explicit false-alarm/detection-delay tradeoff. They do **not** establish a universal acceptable contamination sensitivity, growth-stall cutoff or alert delay for cultureQC's target setup. The values below are engineering proposals for an owner-reviewed pilot, not published biological standards or measured product performance.

Recommended starting point: **2-hour imaging; 10× phase contrast with 4–5 repeatable fields for growth; preferred combined false-review rate ≤0.5 per 100 healthy culture-visits, ceiling 1; contamination visual-warning target within 4 hours of independently visible onset; growth-slowdown target within 24 hours of independently defined onset.** Both detector targets remain unproven. A 5% score flag rate can be explored silently, not treated as an acceptable operator-alert rate.

## What the primary sources actually support

| Source | Supported finding | Boundary |
|---|---|---|
| [Sartorius cell-culture QC application note, Figure 4](https://www.sartorius.com/resource/blob/63378/449a19d7aeab75fd483719dc769fbdc6/8000-0023-c00-cell-culture-quality-control-application-note-data.pdf) | Growth/confluency imaging every 2 hours over four days in the illustrated experiment | Vendor study, not proof of contamination or stall detection latency |
| [Sartorius cell-culture QC](https://www.sartorius.com/en/applications/life-science-research/live-cell-assays/cell-culture-qc) | 4×/10×/20× options and multiple-area or whole-well imaging address detail versus coverage | No guarantee that a particular objective resolves the target contaminant |
| [Gidda et al., Bio-protocol, procedure B.2](https://bio-protocol.org/en/bpdetail?id=5210&pos=b&type=0) | A worked assay uses 4–5 fields at 10×, with 2- or 4-hour acquisition | Fluorescent live/dead assay with phase confluency; transferable acquisition example, not label-free stall validation |
| [Nikon resolution calculator](https://www.microscope.healthcare.nikon.com/microtools/resolution-calculator/) | Numerical aperture and specimen-plane pixel sampling matter to resolution | Magnification alone cannot specify a bacteria-detection setup |
| [Thermo Fisher contamination guide](https://www.thermofisher.com/gp/en/home/references/gibco-cell-culture-basics/biological-contamination.html) | Low-power views can show tiny granules; higher power resolves bacterial forms; its illustrated E. coli are about 2 µm long and 0.5 µm wide | Visible contamination is not the same endpoint as infection onset or all-contaminant exclusion |
| [ATCC mycoplasma guidance](https://www.atcc.org/the-science/authentication/mycoplasma-contamination) | Routine testing with appropriate methods, including PCR, is needed | An unflagged routine image cannot establish mycoplasma clearance |
| [NIST control-chart guidance](https://www.itl.nist.gov/div898/handbook/pmc/section3/pmc32.htm) and [ARL explanation](https://www.itl.nist.gov/div898/handbook/pmc/section3/pmc3131.htm) | Sensitivity trades against false alarms; textbook two-sided three-sigma Shewhart limits give about 0.27% false signals under model assumptions; estimated parameters can change behavior | Not a cell-culture regulation and not a transferable guarantee for correlated images or multiple monitors |

Additional acquisition and cell-specific confluency sources are captured in the [growth source notes](2026-10-17-growth-threshold-source-notes.md).

## Proposed acquisition and alert policy

All numbers in this section are proposals unless explicitly identified as source observations.

| Item | Starting proposal | Evaluation requirement |
|---|---|---|
| Acquisition | Every 2 hours; evaluate 4- and 6-hour alternatives by downsampling the same development series | Record exposure/environment effects and compute/storage cost; freeze chosen cadence before final evaluation |
| Growth/confluency coverage | 10× phase contrast, 4–5 repeatable spatially distributed FOVs; whole-well/larger-area acquisition where practical | Record actual area, numerical aperture and µm/px; measure FOV variability and registration quality. More frames alone do not remove sampling noise |
| Contamination coverage | Full available image or predeclared multi-tile coverage, not centre tile alone; compare higher-resolution acquisition if organisms are unresolved | Inspect target-scale positive examples with an independent reference before assuming a score cutoff can work. Do not assign a fictitious pixel scale or equate 20× with adequate resolution |
| Silent candidate flags | Explore operating points at 0.5%, 1%, 2% and 5% tuning false-positive rates | Log only in shadow mode; candidate selection uses development/tuning data, never final-test feedback |
| User-facing review prompts | Preferred ≤0.5 false-positive visits per 100 healthy culture-visits; maximum proposed pilot ceiling 1 | Budget applies to the combined detector alert, not separately to each tile or monitor. Report each detector and combined output |
| Persistence | Compare one-visit versus two-consecutive-visit prompts in tuning, with duplicate-notification handling fixed in advance | Correlated visits mean two confirmations do not simply square the false-positive rate. Measure added delay; do not postpone an independently observed problem just to satisfy persistence |
| Contamination visual warning | ≥90% of independent optically visible, reference-confirmed episodes warned within 4 hours of independently adjudicated visible onset | This is a proposed scoped visual-warning endpoint, not detection within 4 hours of infection. Also report sensitivity and latency across **all** reference-confirmed episodes, including invisible ones |
| Growth slowdown | Candidate definition: growth ≤50% of a matched healthy reference over a sustained 12-hour interval; ≥90% of qualifying independent episodes warned within 24 hours of onset | Definition and onset must be independently established, not assigned using the detector being tested. Final targets require adequate signal on the actual cell line |

The growth proposal targets a substantial sustained slowdown, not every deviation. The existing 40%-speed simulation remains a separate historical benchmark. Use a reference fixed before the fault, rather than continuously adapting it to the stalled culture. Record warm-up, lag phase, expected saturation, planned differentiation/treatment and missing visits explicitly; these are not automatically pathological stalls. Include unavailable-monitoring time and missed episodes in coverage reporting rather than deleting them from the denominator.

Acquisition every 2 hours does **not** mean estimating reliable growth from two images 2 hours apart. Use longer-horizon data to accumulate signal. Slower-growing or unusually variable cultures may need a different horizon, agreed before testing; there is no evidence here that 24 hours is universally adequate.

### Define the metric before choosing the cutoff

For the proposed visit-level false-positive rate, a visit is one culture/vessel acquisition time after predeclared spatial aggregation. The numerator counts healthy scheduled visits for which the combined detector is in a false-positive state; the denominator is all reference-healthy scheduled visits. Report the same rate among analyzable visits plus the missing/rejected-visit fraction, so suppressing analysis cannot improve the apparent budget unnoticed.

Separately report new false-alert episodes, delivered notifications, acknowledgement time and review minutes. A persistent false-positive state is not many independent contaminations; deduplication must not hide its duration. Episode start/end/reset rules belong in the frozen analysis plan. Image-quality reimage prompts are a separate endpoint, but must also appear in total operator workload.

For detection-within-deadline, the denominator is every independent qualifying episode, including missed cases. Do not report median delay among only detected episodes as if it establishes the deadline target. Describe visibility adjudication, blinded references and onset uncertainty before scoring. Separately disclose episodes never visually detectable; do not remove them from an overall contamination claim.

## Why a casual 5% alert allowance is expensive

Illustrative calculation, **not observed workload**: 20 healthy vessels imaged every 2 hours produce 1,680 vessel-visits per week.

| False-positive visit rate | Expected false-positive visits/week |
|---|---:|
| 0.5% | 8.4 |
| 1% | 16.8 |
| 5% | 84 |

Calculation: vessels × 12 visits/day × 7 days × rate. Linearity of expectation does not require independence. Episode probabilities require a model of dependence and event duration. Counts are not necessarily distinct notifications after deduplication. Actual acceptability depends on review time, number of vessels and consequences of missed events. Even the proposed 0.5% budget may need tightening at larger fleet sizes.

## Why the current failures are not just overly strict thresholds

- [Realistic simulated contamination](../../results/contamination_scale.md): AUROC 0.48 and 1/49 held-out contaminated images flagged versus 2/49 matched clean controls. A lower cutoff is not an evidence-based remedy for that ranking. Improve visible signal, spatial coverage and feature suitability, then measure operating curves.
- [Growth sampling study](../../results/growth_signal_summary.md): growth increment versus FOV-noise ratios of 0.35–1.12 across the tested conditions. Two-hour acquisition may enable longer time-series analysis, but has not been shown to solve this measurement problem.
- [Historical SPC sweep](../../results/spc_summary.md): relaxing the multiplier from 1.8 to 1.5 changes tuning false alarms from 0.89 to 3.12/100 visits and detected fault runs from 2/16 to 4/16. These are combined historical monitors/fault types, not current growth-stall performance. Held-out stalls remain 0/2. Do not deploy multiplier 1.5 on the strength of that table.
- Preserve current passage targets and review boundaries until cell-specific policy is approved. Better confluency MAE does not validate automated decisions or justify narrowing the review region.

## Evidence needed before calling the targets acceptable performance

Separate an exploratory point estimate from a validated performance claim. Predeclare one-sided confidence bounds, cluster handling and minimum independent sample counts. A proposed confirmation gate is an upper 95% bound at or below the chosen false-positive ceiling and a lower 95% bound at or above the chosen detection target. Failure to establish those bounds means insufficient evidence, not automatic relaxation.

Illustrative exact-binomial calculations: zero false positives in 299 independent trials gives a one-sided 95% upper bound below 1%; 29/29 independent detections gives a one-sided 95% lower bound above 90%. These derive from `1 - 0.05^(1/n)` and `0.05^(1/n)`, respectively, using [NIST's exact-binomial framework](https://www.itl.nist.gov/div898/software/dataplot/refman2/auxillar/exacbino.htm). **They are not sample-size instructions for correlated image sequences.** Repeated visits, shared cultures and acquisition sessions require an appropriate clustered design; a small number of cultures with many frames does not supply those independent trials.

## Decision and implementation handoff

1. Treat the table as **proposed pilot v0**, not an approved E0 protocol. Leave `protocol.draft.json` unresolved.
2. Confirm available microscope, objective/NA, true pixel scale, vessel/cell line, lab workflow and independent reference labels. Research cannot discover the owner's actual hardware or acceptable interruption cost.
3. Agree on the alert budget and deadline endpoint; predeclare subgroup coverage, controls, sample-size justification and statistical bounds. Different endpoints need separate E1/E2/E3 packets.
4. Build an offline operating-curve/replay evaluator against development data; compare the candidate budgets and persistence policies without activating them.
5. Freeze selected artifacts and analysis before untouched evaluation. Keep final-test custody, runtime correctness and activation approval separate, as in the [E0–E4 implementation flow](../specs/detection-experiments/README.md).

VP framing: **“We are designing for low-noise, timely review prompts—not more red flags. We will measure missed events, review burden and detection delay on the target setup.”** The numerical targets are evaluation goals, not capabilities to place on the website as achieved results.
