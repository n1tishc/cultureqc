# B0: scale-matched QC classifier test

Generated 2026-09-27T00:26:45Z by `scripts/classifier_scale_test.py` (cuda (Tesla T4), 2.0 min). Spec: `cultureQC_upgrade_specv3.md` §2B.1. Images: C2C12, Ker et al., *Sci Data* 5:180237 (2018), CC BY 4.0 (**real**); contamination and lamp dimming are **simulated faults**. Classifier `qc_effnetb0_v1`, trained on synthetic tiles only.

## Scale

- C2C12: 1.3 µm/px (Ker et al. 2018, Methods). LIVECell training tiles: 1.243 µm/px (Edlund et al. 2021, Methods: 704 × 520 px = 0.875 × 0.645 mm²).
- f = 1.046. Selectable f × {0.75, 1, 1.25}; context only f × {0.5, 2}.

## Frames

| split | group | frames | sequences |
|---|---|---|---|
| heldout | contamination_onset | 49 | 2 |
| heldout | lamp_dimming | 327 | 14 |
| heldout | normal | 1228 | 14 |
| tuning | contamination_onset | 48 | 2 |
| tuning | lamp_dimming | 225 | 10 |
| tuning | normal | 860 | 10 |

## Tuning (choice made here)

| variant | factor | normal → normal | contamination recall | normal → contamination | dimmed → contamination | criteria met |
|---|---|---|---|---|---|---|
| unscaled | — | 8.6% | 97.9% | 16.0% | 29.3% | context |
| f x 0.75 | 0.784 | 10.1% | 54.2% | 6.3% | 14.7% | 0/3 |
| f x 1 | 1.046 | 4.0% | 100.0% | 10.0% | 24.9% | 1/3 |
| f x 1.25 | 1.307 | 0.8% | 100.0% | 13.7% | 29.8% | 1/3 |
| f x 0.5 | 0.523 | 22.0% | 6.2% | 6.4% | 12.9% | context |
| f x 2 | 2.092 | 0.0% | 93.8% | 18.3% | 45.3% | context |

Chosen on tuning: **multiplier 1 (factor 1.046)**.

## Held-out (reported once)

| variant | normal → normal (≥ 80%) | contamination recall (≥ 85%) | normal → contamination (≤ 5%) | dimmed → contamination |
|---|---|---|---|---|
| unscaled | 5.0% | 91.8% | 15.9% | 29.4% |
| chosen | 2.9% | 93.9% | 7.8% | 20.8% |

**B0 verdict: FAIL: go to B3 retrain (`nb/05`).** normal called normal not met; contamination recall met; normal called contamination not met.

## Checks

- Parity, unscaled vs cache `qc_effnetb0_v1` logits: 2737 of 2737 frames matched by sha; max |Δlogit| 5.39e-02.
- Unscaled held-out numbers should match `results/classifier_c2c12.md` (same frames, same model).
- Frames within a sequence are not independent; held-out contamination is 2 sequences.
- `classifier_scale_examples.png`: 5 normal + 5 contaminated held-out frames (seed 0), unscaled vs chosen.
