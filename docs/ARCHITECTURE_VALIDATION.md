# Phase A — Architecture validation

**Branch:** `slice-1b-compute-cache` (nothing merged to `main`). **Date:** 2026-09-26. **Spec:** `cultureQC_upgrade_spec.md` §2A.

Data: C2C12 time-lapse, Ker et al., *Sci Data* 5:180237 (2018), OSF `ysaq2`, **CC BY 4.0**. EVICAN (CC BY 4.0) for V1. Visits, FOV repositioning and all faults are **simulated** from recorded frames (replay); fault-detection numbers below are on **simulated faults**.

Every number here is copied from a results file named next to it; nothing is re-derived in this document. Thresholds are the spec's provisional ones; nothing was tuned on the held-out fleet except where a section says so explicitly.

## Summary

| ID | Question | Measured (held-out) | Verdict | Spec's design change if it fails → does it address the cause? |
|---|---|---|---|---|
| V1 | Confluency good enough on real images? | EVICAN MAE **8.35 pp** (n = 33); reads low (mean signed −8.32 pp). 60–90% band: **1 image, read 0% vs 65% truth** | **Pass** overall; band **not measurable** | — (stop rule is > 10 pp) |
| V2 | Growth between visits beats FOV noise? | Median increment ÷ σ_fov at 30–70%: **0.35 (6 h), 0.65 (12 h)** at 1 FOV; 0.61 / 1.12 at 3 FOVs | **Fail**, every cell incl. 3 FOVs | "Growth-deviation flags only at the longer cadence" → **no**: 12 h / 3 FOVs is 1.12, still < 2. Only a larger FOV (context: 0.5-frac, never replayed) reaches 2 |
| V3 | Passage prediction useful and honest? | 50% target, target − 10 cut: median abs error 2.1–9.0 h across cells; coverage 3/3 to 4/5 | **No verdict** (5 sequences cross 50%; 0 cross 60–80%) | — |
| V4 | Density conditioning removes growth confound? | Spearman ρ binned **−0.16** vs global −0.09 | **Fail** | "Drop anomaly *trend* monitoring; keep per-visit flag" → **yes**, and V6 supports it (anomaly/class monitors gave all held-out false alarms) |
| V5 | Per-visit anomaly score separates faults? | (b) C2C12 contamination AUROC **1.00** at ≥ 150 sprites; (a) synthetic, stand-in CLS scorer: 1.00 / 0.82 / 0.78 | (b) **Pass on n = 2**; (a) **fail for the stand-in**, patch scorer not measured | Weak classes listed as limitations; classifier primary for them |
| V6 | SPC catches faults without alarm fatigue? | **3.75** false alarms / 100 visits; contamination **0/2**, growth stall **0/2** detected by SPC | **Fail** on all three | Raise L / require agreement / lower λ → **no**: the causes are structural (see V6) |
| V7 | Tells instrument from culture? | Dimming raised INSTRUMENT_DRIFT 2 h / 8 h after onset — **but the normal fleet drifted too**; single-flask fleets all inherit it | (a) **pass by rule, not evidence**; (b) **fail** | "Informational only + README limitation" → matches B5's place in the cut order |
| V8 | Trended probabilities calibrated? | ECE on val after T = **0.0057** (in-sample); test 0.0139 | **Pass**, synthetic tiles only; the classifier is off-domain on C2C12 | — |
| V9 | Live path fits the Space? | **689 s per FOV** at C2C12 frame size (Cellpose-SAM ≈ all of it), 2-thread Mac approximation | **Fail** (138× the 5 s budget) | ViT-S / fewer crops / smaller input → **no** (smallest input tried: 14×). Precompute demo examples, or a GPU Space / lighter live confluency model |
| V10 | Media conditions distinguishable? | Conditions not resolved; per experiment, area doubling time 17.7 / 12.4 / 15.4 h (medians) | Informational | — |

**What matters most for Phase B.** Three findings change the design, not just the parameters:

1. **Growth deviations are below the noise floor at the replayed FOV size (V2).** One visit's growth step is about a third (6 h) to two-thirds (12 h) of one 0.25-frac FOV's σ_fov. This is why the growth residual cannot see a stall (V6), and no SPC tuning fixes it. Detecting a stall needs more or larger FOVs, and accumulation over many visits.
2. **The QC classifier does not transfer to real C2C12 frames.** It calls 5.0% of held-out normal frames "normal" and 67.1% "image_quality" (`results/classifier_c2c12.md`); it does call 91.8% of contaminated frames "contamination". Every class-probability residual and the calibration result (V8) sit on top of this.
3. **The live path is ~140× over budget (V9)**, entirely from Cellpose-SAM, so the demo strategy is a decision, not an optimisation.

## Setup

- **Fleet (A2)**, `results/replay_fleet_summary.md`: 24 C2C12 base sequences (~85 h, hourly frames, 3 experiments: 090303, 090318, 090325) and 32 simulated fault sequences (24 lamp dimming, 4 contamination onset, 4 growth stall). Split by sequence, **stratified by fault type**, seed 0: **10 tuning / 14 held-out**, 2 contamination + 2 stall on each side (`results/replay_fleet_split.csv`). Held-out per experiment: 2 / 7 / 5.
- **Replay:** mean cadence 6 h and 12 h (jitter ±25%), 1 and 3 FOVs per visit, each FOV a 0.25-frac crop (348 × 260 of a 1392 × 1040 frame), seed 0 for every stream. 24 h cadence: 5 visits per stream, **not testable** on the C2C12 span.
- **Rules followed:** thresholds and limits chosen on tuning only; reported on held-out only; counting rules written into each script's docstring before its held-out run; every outcome counted. Exceptions are flagged where they occur (A7's post-hoc diagnostic).
- **Deviation from the spec:** §2.2 says all numbers come from one `scripts/validate_architecture.py`. That script does not exist; each check has its own script, run on the cache on the Mac (CPU). To reproduce:

| Check | Script | Output | Runtime (Mac, approx.) |
|---|---|---|---|
| A2 fleet + split | `scripts/replay_fleet.py` | `results/replay_fleet_*` | ~10 s |
| V1 | `scripts/eval_confluency_real.py` | `results/confluency_real_summary.md` | hours (Slice 1) |
| V2, V10 | `scripts/eval_growth_signal.py` | `results/growth_signal_summary.md` | < 1 min |
| V3 | `scripts/backtest_growth.py`, `scripts/plot_growth_backtest.py` | `results/growth_backtest.{md,csv}`, `results/growth_backtest_v3.png` | not recorded |
| V4, V5 | `scripts/eval_anomaly.py` | `results/anomaly_summary.md` | ~22 min |
| V6 | `scripts/eval_spc.py` | `results/spc_summary.md` | ~2 min (residuals cached) |
| V7 | `scripts/eval_drift.py` | `results/drift_summary.md` | ~1 min |
| V8 | `scripts/calibrate_classifier.py` | `results/calibration_summary.md` | < 1 min |
| V9 | `scripts/benchmark_live_path.py` | `results/live_latency.md` | ~52 min |
| Context | `scripts/eval_classifier_c2c12.py`, `scripts/calibrate_quality_gate.py` | `results/classifier_c2c12.md`, `results/quality_gate_c2c12.md` | < 1 min |

Tests: `pytest tests` → 112 passed, 1 xfailed.

**Quality gate on C2C12** (`results/quality_gate_c2c12.md`): thresholds from the tuning frames (percentiles 1/99). Held-out normal frames fail 12.1% (tuning 4.2%); contamination frames 92%; dimmed frames 51%. Gate-failed visits get REIMAGE and leave the trend views, which shapes V6 and V7.

---

## V1 — Confluency on real images

- **Setup:** Cellpose-SAM (`cpsam_v2`, probmap) on 33 EVICAN `eval2019` images (held-out split of the dataset; not in Cellpose-SAM's training corpus).
- **Number:** MAE **8.35 pp**, median AE 5.49 pp, mean signed error **−8.32 pp** (reads low). Baselines: global threshold 11.20 pp; simplified local-contrast 23.42 pp.
- **Verdict: pass** (≤ 10 pp; 5–10 pp = proceed with error analysis). **60–90% band: not measurable**: EVICAN `eval2019` has one image there (`15_Caco-2.jpg`, 65.11%), read as **0.00%** (severely underexposed image).
- **Consequence:** all C2C12 "truth" in V2/V3 is Cellpose-SAM's own full-frame reading, so "50%" means 50% as Cellpose-SAM reads it, likely ~8 pp below true coverage. The band where passage decisions happen is still unvalidated.
- `results/confluency_real_summary.md`, `results/confluency_real_scatter.png`.

## V2 — Growth between visits vs FOV noise

- **Setup:** held-out normal streams. Increment = full-frame confluency at the next visit minus this visit, for visits at 30–70% (held-out sequences peak at 56%, so 30–56%; 9 of 14 streams contribute). σ_fov = 2.828 + 0.2072 × confluency (C2C12, 0.25-frac crops, `configs/noise.yaml`), ÷ √n_fov.
- **Number (median ratio):**

| cadence | 1 FOV | 3 FOVs | pairs (1 FOV) |
|---|---|---|---|
| 6 h | **0.35** | 0.61 | 37 |
| 12 h | **0.65** | 1.12 | 12 |

  Measured visit-level error (visit mean − full frame) agrees with the model: SD 13.21 pp at 1 FOV (model 11.41), 7.51 pp at 3 FOVs (model 6.59). Context: with the 0.5-frac noise fit, the same increments give 0.85 / 1.46 (6 h) and 1.56 / **2.71** (12 h) — not replayed at that size.
- **Verdict: fail** at 1 FOV and at 3 FOVs, both cadences.
- **Spec's change:** "fails at 3 FOVs → growth-deviation flags only at the longer cadence." That does not reach 2 here either (12 h / 3 FOVs = 1.12). What moves the ratio is **FOV size** (and count): a question for Celltrio, not a setting we can choose.
- `results/growth_signal_summary.md`, `results/growth_signal_v2.png`.

## V3 — Passage prediction

- **Setup (A1):** fit on visits until the observed series first reaches target − 20 / target − 10; truth = first crossing in the hourly full-frame series. Targets crossed by held-out sequences: 50% by 5 of 14; 60–80% by none. 30% and 40% added (12 and 8 sequences), labelled not-in-spec, never counted toward V3.
- **Number (50%, target − 10 cut, median abs error / 90% interval covers truth):**

| cadence | 1 crop | 3 crops | full frame (ceiling) |
|---|---|---|---|
| 6 h | 4.9 h, 3/4 | 9.0 h, 4/5 | 2.4 h, 3/5 |
| 12 h | 2.1 h, 3/3 | 5.8 h, 3/4 | 1.9 h, 3/4 |

- **Verdict: no verdict.** At n ≤ 5, coverage moves in steps of 20 pp; the error numbers are inside 12 h but on 3–5 sequences. The bootstrap still misses model-selection uncertainty (known; V3's fix).
- `results/growth_backtest.md`, `results/growth_backtest_v3.png`.

## V4 — Density conditioning

- **Setup (A4):** DINOv2-small patch kNN on the 256 px centre tile (AnomalyDINO-style scoring, PatchCore coreset), banks per full-frame confluency bin from tuning normal frames; bins merged to 0–20 / 20–40 / 40–100 (too few tuning sequences above 40%). Global bank for comparison.
- **Number:** Spearman ρ(score, confluency) on 1228 held-out normal frames: **binned z −0.16, global −0.09**. Shape diagnostic (mean z by band): binned flattens the ≥ 50% rise (+0.37 vs global +1.19) but not the low end (0–10%: +0.55 binned vs +0.58 global). Held-out flag rate at the 5% threshold: **10.0%** (one sequence, 090318 F0016, at 69%).
- **Verdict: fail** as the spec writes it.
- **Spec's change:** drop anomaly *trend* monitoring; keep the per-visit OOD flag. **Supported by V6:** all 24 held-out SPC false alarms came from anomaly and class monitors, 16 of them on 090318 F0016. Calibration transfer across experiments (090318 has 1 tuning sequence) is the other half of the problem.
- `results/anomaly_summary.md`, `results/anomaly_v4.png`.

## V5 — Per-visit anomaly separation

- **(b) C2C12 contamination:** AUROC **1.00** (binned z) at ≥ 150 sprites per tile area, 0.99 below; 100% flagged. **Pass on n = 2** held-out contamination sequences. Caveat: the sprites raise Cellpose confluency by a median **+59 pp**, and 88% of contaminated frames land in a different bin from their base frame. Lamp dimming does not move the score (AUROC 0.41–0.49).
- **(a) Synthetic tiles:** only CLS embeddings exist on the Mac for synthetic tiles, so a **stand-in CLS-kNN scorer** was used: contamination 1.00, detachment **0.82**, image_quality **0.78**. **Fail for the stand-in**; the patch scorer on synthetic tiles is **not measured**.
- **Spec's change:** list weak classes as limitations; the classifier stays primary for them (subject to its transfer problem, below).
- `results/anomaly_summary.md`, `results/anomaly_v5.png`.

## V6 — SPC on residuals

- **Setup (A6):** EWMA + one-sided tabular CUSUM on growth (one-step-ahead z, lower side), anomaly z and three class probabilities (upper), each standardised on tuning normals. λ = 0.2, k = 0.5; one multiplier c on L and h, chosen as the smallest with ≤ 1 false alarm / 100 tuning visits: **c = 1.8 (L 5.15, h 7.2)** (the spec's L = 2.86 gave 9.4 / 100 on tuning).
- **Number (held-out):** **3.75 false alarms / 100 visits** (24/640; 16 on 090318 F0016). Contamination **0/2** and growth stall **0/2** detected by SPC in every cell. REIMAGE flags contamination 1–2 visits after onset (it removes those visits from SPC). Growth z on tuning normals: mean +0.69, SD 1.79.
- **Verdict: fail** (false alarms, detection, delay).
- **Why, and whether the spec's levers help:** the spec's levers (raise L, require EWMA + CUSUM agreement, lower λ) do not reach the causes:
  1. **Stall:** the per-visit refit absorbs the plateau, and (V2) one visit's growth step is below one FOV's noise. A frozen or population growth reference only helps together with a CUSUM that accumulates over many visits, or more/larger FOVs. This is a bigger change than a residual swap.
  2. **Contamination:** the quality gate removes post-onset visits, so SPC sees 0–1 of them. It is caught, by REIMAGE (8/8 in A7's per-flask table) and by the classifier (91.8% of contaminated frames), just not by SPC. Fix in decision logic: repeated gate failure / immediate classifier call as a first-class contamination flag.
  3. **False alarms:** anomaly and class monitors on one poorly covered experiment (see V4); the class residual trends an off-domain classifier.
- `results/spc_summary.md`, `results/spc_examples.png`, `results/spc_tradeoff.png`.

## V7 — Instrument vs culture

- **Setup (A7):** flasks aligned on hours since start. Population inputs per visit: log exposure relative to the flask's own first 24 h minus an age-dependent expected change (tuning frames), and A4 anomaly z; every visit counted, gate failures included. Per window (= cadence), fleet median, standardised by the tuning fleet's population series; EWMA (λ 0.2, L 2.86); INSTRUMENT_DRIFT while beyond the limit; per-flask SPC flags in drift windows marked suppressed.
- **Number (the pre-registered held-out run):** dimming → INSTRUMENT_DRIFT **2 h (6 h cadence) / 8 h (12 h)** after onset, 0 unsuppressed post-onset culture flags. But the **held-out normal fleet drifts from the same windows** (first drift window ends 42 h / 48 h): 6 drift episodes across cells, 16 real per-flask flags hidden. Every single-flask fleet inherits it. Stall flasks have no flag at all (from A6); contamination flasks are flagged by REIMAGE (8/8). Dimming still gives REIMAGE on 10 of 14 flasks.
- **Verdict:** (a) dimming **pass by the rule, not evidence**; (b) single-flask **fail**.
- **Cause:** the tuning population SD (0.034 in per-flask z) is one fleet's window-to-window SD, which misses fleet-to-fleet offset. Held-out normals sit ≈ −0.2 z below the tuning reference. (Leave-one-flask-out references gave 0.032: in-sample fitting is not the cause.)
- **Post-hoc diagnostic (chosen after seeing held-out; not a verdict):** standardising by the standard error of a median of n flasks (1.2533 · s / √n) gives 0 normal drift episodes, 0/16 single-flask fleets in drift, dimming still at 2 h / 8 h. Assumes independent flasks; they cluster by experiment, so it is optimistic.
- **Spec's change:** informational only + README limitation. B5 is already in the cut order; if kept, it starts from the diagnostic above.
- Easiest possible case: synchronous onset, identical ramp, age-aligned flasks.
- `results/drift_summary.md`, `results/drift_fleet.png`.

## V8 — Calibration

- **Setup (A5):** temperature scaling on cached val logits of the synthetic tile set; T = 1.5536.
- **Number:** ECE val **0.0057** after (0.0102 before; in-sample), test **0.0139** after.
- **Verdict: pass**, on synthetic tiles only. On real C2C12 frames the classifier's calls are mostly wrong for normal flasks (5.0% "normal"), so "calibrated" does not carry over. Whether to keep class-residual SPC (V8's fail branch: trend only anomaly + growth) is a review decision.
- `results/calibration_summary.md`, `results/classifier_c2c12.md`.

## V9 — Latency

- **Setup (A8):** live per-FOV path, models resident, on an Apple M2 Pro with torch/OpenCV at **2 threads** to mimic the Space (HF CPU Basic, 2 vCPU). An approximation, most likely a lower bound. Input: a real LIVECell phase-contrast fixture tiled to C2C12 frame size (C2C12 frames are not on the Mac; Cellpose time tracks pixel count).
- **Number (per FOV, median of 2):** Cellpose-SAM **689 s** (1392 × 1040), 230 s (704 × 520), 71 s (348 × 260). Classifier 0.67 s with Grad-CAM (0.17 s without); DINOv2-small 0.03 s; patch kNN 0.003 s; gate < 0.01 s. Everything but Cellpose ≈ 0.7 s.
- **Verdict: fail** — 138× / 46× / 14× the 5 s budget at 1 FOV; 3 FOVs triple it.
- **Spec's change:** ViT-S / fewer crops / smaller input do not close it. Remaining: precompute demo examples and say so (spec), or a GPU Space / lighter live confluency model (V1 must be rechecked on any replacement).
- `results/live_latency.md`.

## V10 — Growth per experiment (informational)

Conditions are "unknown" in this C2C12 import, so per experiment (held-out sequences, `fit_growth` on the hourly full-frame series). Confluency-area doubling time, early phase — a rate of confluency, not cell doubling time:

| experiment | sequences | median (range), h |
|---|---|---|
| 090303 | 2 | 17.7 (17.5–17.9) |
| 090318 | 7 | 12.4 (10.7–21.5) |
| 090325 | 5 | 15.4 (9.5–21.5) |

`results/growth_signal_summary.md`.

---

## What this does and doesn't prove

**Does:** the temporal logic was run end to end on **real C2C12 phase-contrast sequences** with simulated visits, repositioning and faults, under a tuning/held-out split and pre-written counting rules. It shows where the architecture breaks: per-visit growth signal vs FOV noise, gate/SPC interaction for contamination, anomaly calibration transfer across experiments, population drift standardisation, classifier domain transfer, and live latency.

**Doesn't:**
- Not RoboCell or Celltrio images. One cell line (C2C12), one microscope, ~85 h span, 3 experiments.
- Cadence (6 h, 12 h), FOVs per visit (1, 3) and FOV size (0.25-frac crop) are **assumptions** to confirm with Celltrio. V2 depends on them directly.
- Faults are simulated: sprite contamination, re-timed frames for stalls, synchronous lamp dimming. Real faults are messier and slower.
- Held-out n is small: 14 normal sequences, **2 per fault type**. Frames within a sequence are not independent. A pass on n = 2 (V5b) is weak; a fail on n = 2 is informative only when the mechanism is clear (V6, V7).
- Confluency "truth" is Cellpose-SAM's own reading, which V1 found ~8 pp low and unvalidated in the 60–90% band.
- V9 is a Mac approximation of the Space, not a measurement on it.

---

## Next steps (proposals for the Phase A review)

### Decisions for you

1. **Demo strategy (V9).** (a) Precomputed replay examples in the Space, labelled as such (fits the freeze; the spec's own fallback). (b) A GPU Space. (c) A lighter live confluency model (needs V1 rerun). Recommendation: (a) for Oct 4; (b)/(c) after.
2. **Anomaly trend monitoring (V4).** Recommendation: follow the spec — drop the anomaly *trend*, keep the per-visit OOD flag. V6's false alarms all came from anomaly/class monitors.
3. **Class-residual SPC (V8 spirit).** The classifier calls 5% of normal C2C12 frames normal. Recommendation: stop trending class probabilities until B3 has addressed domain shift.
4. **Growth-stall detection (V2/V6).** Either present it as a stated limitation at the replayed FOV size, or invest in a frozen/population reference + long-horizon CUSUM and ask Celltrio about FOV size first. Recommendation: limitation for the demo; the Celltrio question now.
5. **B5 instrument drift (V7).** Keep as informational (spec's fail branch), or build on the post-hoc SE-of-median scaling. Recommendation: informational + README limitation; B5 stays early in the cut order.
6. **REIMAGE roll-up.** While INSTRUMENT_DRIFT is active, should N per-flask REIMAGEs become one instrument action? (Decision-logic question for B6; §11.1 ranks REIMAGE first today.)
7. **B3 retrain (GPU).** The domain-shift test is effectively already failed on C2C12; the conditional retrain would need a GPU run (the spec allows it only if triggered). Needs your go-ahead.

### Phase B, in the spec's priority order, with the design changes placed

| Slice | Priority | Design change from Phase A |
|---|---|---|
| B1 timeline on real C2C12 replays | Must | Normal + fault scenarios; show REIMAGE and contamination flags as they fire; label "Replay of recorded time-lapse (simulated visits)"; C2C12 credit |
| B2 anomaly in the app | Must | Per-visit OOD flag + heatmap; no trend (if decision 2); site-calibration mode, since calibration does not transfer across experiments (090318) |
| B3 calibration + domain shift | Must (calibration) | Document classifier behaviour on real frames; conditional retrain if decision 7 |
| B4 SPC in the app | Must | Contamination as a first-class flag (repeated gate failure / immediate classifier call); growth residual only with the stated V2 limitation, or the redesign in decision 4; detectability matrix states what is and isn't detectable at the assumed FOV setup; mycoplasma wording + forbidden-phrase test |
| B5 instrument drift | Should (cut early) | Informational, or SE-of-median scaling + REIMAGE roll-up |
| B6 decision engine | Should | REIMAGE / INSTRUMENT_DRIFT precedence per decision 6 |
| B8 docs + demo | Must | This report as a README section; results table with provenance; limitations above; demo per decision 1 |

Cut order stays S → B7 → B5 → B3 shift/retrain → B6. Code freeze **Sun Oct 4**.

### Questions for Celltrio

- Imaging **cadence** per flask, and whether flasks on one instrument are imaged in one round (A7 assumes age-aligned rounds).
- **FOVs per visit and FOV size** relative to the flask (V2's ratio depends on both).
- Image format, bit depth and resolution; can they share a few real RoboCell sequences for validation (would replace C2C12 as the primary test set)?

### Housekeeping

- README: C2C12 credit (Ker et al. 2018, CC BY 4.0) — required once C2C12 appears in the product.
- Drive sidecars still carry the old fault-onset labels (fixed locally in `3d0c140`); refresh before any Colab rerun.
- Nothing is merged to `main` until you say so.
