# A6: SPC on residuals (minimal)

Generated 2026-09-26T17:59:40Z by `scripts/eval_spc.py`. C2C12 images: Ker et al., *Sci Data* 5:180237 (2018), CC BY 4.0; visits are simulated from them (replay) and the faults are simulated.

**Residuals** (per trend-eligible visit, i.e. passing the quality gate): growth = one-step-ahead (observed − expected) / predictive SD (needs 5 earlier visits); anomaly = A4's per-bin z; failure class = calibrated probability of each of contamination_suspected, detachment, image_quality. Each is standardised by its mean/SD on the tuning normal streams:

| residual | tuning mean | tuning SD | visits | median lag-1 autocorrelation |
|---|---|---|---|---|
| growth (growth_z) | +0.686 | 1.786 | 220 | -0.177 |
| anomaly (anomaly_z) | -0.069 | 0.986 | 420 | 0.013 |
| class_contamination_suspected (p_contamination_suspected) | +0.182 | 0.258 | 420 | 0.107 |
| class_detachment (p_detachment) | +0.121 | 0.211 | 420 | 0.089 |
| class_image_quality (p_image_quality) | +0.606 | 0.362 | 420 | 0.34 |

EWMA and CUSUM limits assume independent points; positive autocorrelation raises the false-alarm rate above the nominal one.

**Monitors:** EWMA + one-sided tabular CUSUM on each residual (growth: lower side, GROWTH_BELOW_EXPECTED; anomaly: upper, ANOMALY_DRIFT; each class: upper, FAILURE_CLASS_DRIFT); 10 monitors, restarted after each signal.

## Tuning (tuning fleet only)

λ = 0.2 and k = 0.5 fixed; L = 2.86·c, h = 4.0·c. smallest c on [1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.8, 2.0, 2.25, 2.5, 3.0] (L = 2.86·c, h = 4.0·c; λ, k fixed) with combined false alarms ≤ 1.0 per 100 flask-visits on the tuning normal base streams (all cadence × FOV cells pooled); fault detection not used.

| c | L | h | false alarms / 100 visits (tuning normal) | tuning fault runs detected (not used to choose) |
|---|---|---|---|---|
| 1 | 2.86 | 4.00 | 9.38 | 10/16 |
| 1.1 | 3.15 | 4.40 | 6.25 | 8/16 |
| 1.2 | 3.43 | 4.80 | 4.46 | 8/16 |
| 1.3 | 3.72 | 5.20 | 4.02 | 6/16 |
| 1.4 | 4.00 | 5.60 | 3.57 | 4/16 |
| 1.5 | 4.29 | 6.00 | 3.12 | 4/16 |
| 1.6 | 4.58 | 6.40 | 2.23 | 2/16 |
| 1.8 ← chosen | 5.15 | 7.20 | 0.89 | 2/16 |
| 2 | 5.72 | 8.00 | 0.45 | 2/16 |
| 2.25 | 6.43 | 9.00 | 0.45 | 0/16 |
| 2.5 | 7.15 | 10.00 | 0.00 | 0/16 |
| 3 | 8.58 | 12.00 | 0.00 | 0/16 |

## V6 on the held-out fleet (L = 5.15, h = 7.20)

Pass (spec): ≤ 1 false alarm per 100 flask-visits; detection ≥ 90% and median delay ≤ 3 visits for contamination and growth stall. Held-out has 2 streams per fault type, so detection is 0/2, 1/2 or 2/2 per cell; 90% means 2/2. Delay counts the first visit after onset as 1.

| cadence | FOVs | false alarms / 100 visits | per 100 trend-eligible | REIMAGE on normal visits | contamination: SPC detected | median delay | growth stall: SPC detected | median delay |
|---|---|---|---|---|---|---|---|---|
| 6 h | 1 | 3.85 (8/208) | 4.42 | 13.0% | 0/2 | — | 0/2 | — |
| 6 h | 3 | 3.85 (8/208) | 4.42 | 13.0% | 0/2 | — | 0/2 | — |
| 12 h | 1 | 3.57 (4/112) | 4.04 | 11.6% | 0/2 | — | 0/2 | — |
| 12 h | 3 | 3.57 (4/112) | 4.04 | 11.6% | 0/2 | — | 0/2 | — |

All cells pooled: 3.75 false alarms per 100 visits (24/640, 14 streams × cells). **V6: false alarms fail; detection fail; delay fail** (n = 2 streams per fault type).

### Per fault stream (held-out)

SPC, the quality gate (REIMAGE) and the first flag of either kind, in visits after onset. *post-onset eligible*: visits after onset that pass the gate (the only ones SPC sees).

| fault | stream | cadence | FOVs | post-onset visits | post-onset eligible | SPC delay | first SPC codes | REIMAGE delay | first flag of any kind | pre-onset SPC signals |
|---|---|---|---|---|---|---|---|---|---|---|
| contamination_onset | 090318_exp1_F0005_Data__fault_contam | 6 h | 1 | 8 | 1 | — | — | 2 | 2 | 0 |
| contamination_onset | 090318_exp1_F0005_Data__fault_contam | 6 h | 3 | 8 | 1 | — | — | 2 | 2 | 0 |
| contamination_onset | 090318_exp1_F0005_Data__fault_contam | 12 h | 1 | 4 | 1 | — | — | 2 | 2 | 0 |
| contamination_onset | 090318_exp1_F0005_Data__fault_contam | 12 h | 3 | 4 | 1 | — | — | 2 | 2 | 0 |
| contamination_onset | 090325_exp1_F0013_Data__fault_contam | 6 h | 1 | 8 | 0 | no SPC data | — | 1 | 1 | 0 |
| contamination_onset | 090325_exp1_F0013_Data__fault_contam | 6 h | 3 | 8 | 0 | no SPC data | — | 1 | 1 | 0 |
| contamination_onset | 090325_exp1_F0013_Data__fault_contam | 12 h | 1 | 4 | 0 | no SPC data | — | 1 | 1 | 0 |
| contamination_onset | 090325_exp1_F0013_Data__fault_contam | 12 h | 3 | 4 | 0 | no SPC data | — | 1 | 1 | 0 |
| growth_stall | 090303_exp1_F0014_Data__fault_stall | 6 h | 1 | 8 | 8 | — | — | — | — | 0 |
| growth_stall | 090303_exp1_F0014_Data__fault_stall | 6 h | 3 | 8 | 8 | — | — | — | — | 0 |
| growth_stall | 090303_exp1_F0014_Data__fault_stall | 12 h | 1 | 5 | 5 | — | — | — | — | 0 |
| growth_stall | 090303_exp1_F0014_Data__fault_stall | 12 h | 3 | 5 | 5 | — | — | — | — | 0 |
| growth_stall | 090318_exp1_F0007_Data__fault_stall | 6 h | 1 | 9 | 9 | — | — | — | — | 0 |
| growth_stall | 090318_exp1_F0007_Data__fault_stall | 6 h | 3 | 9 | 9 | — | — | — | — | 0 |
| growth_stall | 090318_exp1_F0007_Data__fault_stall | 12 h | 1 | 5 | 5 | — | — | — | — | 0 |
| growth_stall | 090318_exp1_F0007_Data__fault_stall | 12 h | 3 | 5 | 5 | — | — | — | — | 0 |

### False alarms by monitor (held-out normal streams, all cells)

| monitor | signals |
|---|---|
| ANOMALY_DRIFT:anomaly:cusum | 12 |
| ANOMALY_DRIFT:anomaly:ewma | 12 |
| FAILURE_CLASS_DRIFT:class_detachment:ewma | 4 |
| FAILURE_CLASS_DRIFT:class_detachment:cusum | 4 |
| FAILURE_CLASS_DRIFT:class_image_quality:cusum | 2 |
| FAILURE_CLASS_DRIFT:class_contamination_suspected:cusum | 2 |

Signals per held-out normal sequence (all cells): 090303_exp1_F0003 0, 090303_exp1_F0014 0, 090318_exp1_F0001 2, 090318_exp1_F0003 0, 090318_exp1_F0005 0, 090318_exp1_F0007 0, 090318_exp1_F0011 0, 090318_exp1_F0013 4, 090318_exp1_F0016 16, 090325_exp1_F0003 0, 090325_exp1_F0007 0, 090325_exp1_F0011 2, 090325_exp1_F0013 0, 090325_exp1_F0018 0.

### Lamp dimming (context for A7; V7 wants no per-flask flags)

Held-out dimming streams × cells: 56; with a per-flask SPC signal after onset: 6; with a REIMAGE after onset: 40.

### Spec addition, not in V6: growth above expected

Contamination sprites raise the Cellpose confluency reading (A4: median +59 pp), so an upper-side growth monitor (GROWTH_ABOVE_EXPECTED) was run separately with the same limits: 0 signals on held-out normal visits (0.00 per 100); contamination streams × cells detected: 0/8.

## Notes

- Anomaly and class residuals are per frame, so the 1-FOV and 3-FOV cells differ only in the growth residual; they are not independent evidence.
- At 12 h, fault streams have 3–4 visits up to onset (`results/replay_fleet_summary.md`), so the growth residual cannot score the first visits after onset.
- Charts: `results/spc_examples.png` (held-out, 6 h, 1 FOV); trade-off: `results/spc_tradeoff.png`.
