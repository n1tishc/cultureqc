# A7: instrument-drift monitor (minimal)

Generated 2026-09-26T18:19:55Z by `scripts/eval_drift.py`. C2C12 images: Ker et al., *Sci Data* 5:180237 (2018), CC BY 4.0; visits, lamp dimming and single-flask faults are simulated (replay).

**Method** (`culture/drift.py`): flasks aligned on hours since start. Per visit, exposure = log exposure relative to the flask's own first 24 h, minus the expected change at that age, over the expected SD (reference from tuning base-sequence frames), and A4's anomaly z. Every visit counts, gate failures included. Per window (width = cadence), the median over active flasks (≥ 5) of each, standardised by the mean/SD of the tuning normal fleet's population series; EWMA (λ = 0.2) on each (exposure two-sided, anomaly upper). INSTRUMENT_DRIFT is active in every window where either EWMA is beyond its limit; per-flask SPC flags (A6) in active windows are kept but marked suppressed.

Exposure reference (expected log change vs age; 6 h bins, flat beyond the last bin with ≥ 5 tuning flasks): 27 h +0.002 (SD 0.025), 33 h +0.006 (SD 0.025), 39 h +0.013 (SD 0.025), 45 h +0.019 (SD 0.025), 51 h +0.026 (SD 0.025), 57 h +0.035 (SD 0.025), 63 h +0.041 (SD 0.034), 69 h +0.050 (SD 0.042), 75 h +0.061 (SD 0.050), 81 h +0.070 (SD 0.058), 87 h +0.084 (SD 0.063).

Population standardisation (tuning normal fleet, n_fov = 1, both cadences): exposure mean +0.033, SD 0.034 (14 windows); anomaly mean -0.225, SD 0.415 (14 windows).

## Limit selection (tuning normal fleets only)

smallest c on [1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0] (L = 2.86·c) with no INSTRUMENT_DRIFT window on the tuning normal fleets (all cadence × FOV cells). Little power: one population series per cadence cell, so zero tuning alarms at the smallest c says little about held-out behaviour.

| c | L | tuning normal: drift episodes | active windows |
|---|---|---|---|
| 1 ← chosen | 2.86 | 0 | 0 |
| 1.25 | 3.57 | 0 | 0 |
| 1.5 | 4.29 | 0 | 0 |
| 1.75 | 5.00 | 0 | 0 |
| 2 | 5.72 | 0 | 0 |
| 2.5 | 7.15 | 0 | 0 |
| 3 | 8.58 | 0 | 0 |

## V7 on the held-out fleet (L = 2.86)

Pass (spec): dimming → `INSTRUMENT_DRIFT`, not per-flask flags; single-flask faults still flagged. Counting rules are in the script docstring, fixed before the held-out run; this is that run.

### Normal and dimming fleets

| cadence | FOVs | normal: drift episodes (windows) | normal: first drift window ends | normal: flags suppressed | dimming: drift delay after onset | post-onset SPC flags: anomaly drift (unsuppressed / total) | all codes (unsuppressed / total) | post-onset REIMAGE visits (flasks) |
|---|---|---|---|---|---|---|---|---|
| 6 h | 1 | 2 (8) | 42 h | 6 | 2 h | 0 / 1 | 0 / 2 | 54 (10/14) |
| 6 h | 3 | 2 (8) | 42 h | 6 | 2 h | 0 / 1 | 0 / 2 | 54 (10/14) |
| 12 h | 1 | 1 (4) | 48 h | 2 | 8 h | 0 / 1 | 0 / 1 | 27 (10/14) |
| 12 h | 3 | 1 (4) | 48 h | 2 | 8 h | 0 / 1 | 0 / 1 | 27 (10/14) |

### Single-flask fault fleets (13 normal flasks + 1 fault twin)

| fault stream | cadence | FOVs | drift windows | fault flask post-onset: SPC flags (suppressed) | REIMAGE visits | first flag after onset (visits) |
|---|---|---|---|---|---|---|
| growth_stall: 090303_exp1_F0014__fault_stall | 6 h | 1 | 8 | 0 (0) | 0 | — |
| growth_stall: 090303_exp1_F0014__fault_stall | 6 h | 3 | 8 | 0 (0) | 0 | — |
| growth_stall: 090303_exp1_F0014__fault_stall | 12 h | 1 | 4 | 0 (0) | 0 | — |
| growth_stall: 090303_exp1_F0014__fault_stall | 12 h | 3 | 4 | 0 (0) | 0 | — |
| contamination_onset: 090318_exp1_F0005__fault_contam | 6 h | 1 | 8 | 0 (0) | 7 | 2 |
| contamination_onset: 090318_exp1_F0005__fault_contam | 6 h | 3 | 8 | 0 (0) | 7 | 2 |
| contamination_onset: 090318_exp1_F0005__fault_contam | 12 h | 1 | 4 | 0 (0) | 3 | 2 |
| contamination_onset: 090318_exp1_F0005__fault_contam | 12 h | 3 | 4 | 0 (0) | 3 | 2 |
| growth_stall: 090318_exp1_F0007__fault_stall | 6 h | 1 | 8 | 0 (0) | 0 | — |
| growth_stall: 090318_exp1_F0007__fault_stall | 6 h | 3 | 8 | 0 (0) | 0 | — |
| growth_stall: 090318_exp1_F0007__fault_stall | 12 h | 1 | 4 | 0 (0) | 0 | — |
| growth_stall: 090318_exp1_F0007__fault_stall | 12 h | 3 | 4 | 0 (0) | 0 | — |
| contamination_onset: 090325_exp1_F0013__fault_contam | 6 h | 1 | 8 | 0 (0) | 8 | 1 |
| contamination_onset: 090325_exp1_F0013__fault_contam | 6 h | 3 | 8 | 0 (0) | 8 | 1 |
| contamination_onset: 090325_exp1_F0013__fault_contam | 12 h | 1 | 4 | 0 (0) | 4 | 1 |
| contamination_onset: 090325_exp1_F0013__fault_contam | 12 h | 3 | 4 | 0 (0) | 4 | 1 |

### Verdict

- **V7 (a) dimming: pass by the rule, but not evidence.** INSTRUMENT_DRIFT was raised after onset in every cell (6 h/1 FOV 2 h, 6 h/3 FOV 2 h, 12 h/1 FOV 8 h, 12 h/3 FOV 8 h) and 0 post-onset anomaly-drift flags were left unsuppressed (0 of any SPC code). The held-out **normal** fleet was in drift from the same windows (first drift window ends 6 h/1 FOV 42 h, 6 h/3 FOV 42 h, 12 h/1 FOV 48 h, 12 h/3 FOV 48 h), so the monitor did not tell dimming from normal. The suppression is from the same false drift.
- **V7 (b) single-flask: fail.** By clause: no drift window fail (A7's own failure: every single-flask fleet inherits the normal fleet's false drift); nothing on the fault flask suppressed pass; fault flask flagged after onset: contamination_onset 8/8 streams × cells; growth_stall 0/8 streams × cells (inherited from A6: SPC catches neither fault, REIMAGE catches contamination, nothing flags the stall, so this clause fails whatever the drift monitor does).
- Normal fleet false alarms: 6 drift episodes across cells; 16 real per-flask SPC flags on normal flasks were hidden by them.

**REIMAGE is not suppressed and not in the culture-flag count.** Under dimming, most flasks get REIMAGE after onset (column above): one per-flask image action each, which is what V7 wants to avoid. Rolling them into one instrument action while INSTRUMENT_DRIFT is active is a B5/B6 decision-logic question (§11.1 currently ranks REIMAGE first).

### Why the normal fleet drifts

The tuning population SD (0.034, exposure) is the window-to-window SD of one fleet's median. Because the reference is itself the median over the tuning flasks, that median sits near zero by construction, and its SD says nothing about how far another fleet's median can sit. The held-out normal median sits at about −0.2 per-flask z, far beyond that SD, so the EWMA drifts out and stays out. This was checked after the held-out run: scoring each tuning flask against a reference fitted without it gives SD 0.032, so in-sample fitting is not the cause.

## Post-hoc diagnostic (not a verdict; chosen after seeing held-out results)

Candidate B5 design change: standardise each window's median by the standard error of a median of n independent flasks, 1.2533 · s / √n, where s is the between-flask SD within a window on the tuning normal fleet (exposure s = 0.942, anomaly s = 0.900). Same λ and L (2.86, not reselected), both inputs. It assumes flasks are independent; tuning flasks cluster by experiment (per-flask mean exposure z up to +1.7 in 090325), so the effective n is below the count and this SE is optimistic.

| cadence | FOVs | normal: drift episodes (windows; by input) | dimming: drift delay after onset | dimming: pre-onset drift windows | single-flask fleets with a drift window |
|---|---|---|---|---|---|
| 6 h | 1 | 0 (0; exposure 0, anomaly 0) | 2 h | 0 | 0/4 |
| 6 h | 3 | 0 (0; exposure 0, anomaly 0) | 2 h | 0 | 0/4 |
| 12 h | 1 | 0 (0; exposure 0, anomaly 0) | 8 h | 0 | 0/4 |
| 12 h | 3 | 0 (0; exposure 0, anomaly 0) | 8 h | 0 | 0/4 |

## Notes

- The easiest case for a population monitor: every flask dims at the same age, with the same ramp, and flasks are age-aligned. Staggered flask ages and gradual real drift are untested.
- Every stream uses replay seed 0, so all flasks share visit times; at 6 h one window (42–48 h) has no visits, which splits one continuous drift into two episodes.
- Exposure and anomaly are per frame, so the 1- and 3-FOV cells share the population series; they differ only in the per-flask growth flags.
- A drift that starts inside a flask's first 24 h shifts its own baseline and is invisible for that flask.
- Fleet view: `results/drift_fleet.png` (held-out, 6 h, 1 FOV, the verdict run).
