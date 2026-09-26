# V2 and V10: growth signal vs FOV noise

Generated 2026-09-26T19:30:42Z by `scripts/eval_growth_signal.py`. C2C12 images: Ker et al., *Sci Data* 5:180237 (2018), CC BY 4.0; visits are simulated from them (replay). Held-out normal streams only.

## V2: increment ÷ σ_fov

Increment = full-frame Cellpose-SAM confluency at the next visit minus this visit, for visits at 30–70% (full frame). σ_fov = 2.828 + 0.2072 × confluency (`configs/noise.yaml` entries.c2c12, crop_frac 0.25, the replay FOV size) / √n_fov. Pass (spec): median ratio ≥ 2 at 1 FOV.

Held-out C2C12 sequences peak at 56% here, so the band is effectively 30–56%: 9 of 14 held-out streams contribute.

| cadence | FOVs | pairs in band (streams) | median increment (pp) | median σ_fov/√n (pp) | median ratio | IQR of ratio | V2 |
|---|---|---|---|---|---|---|---|
| 6 h | 1 | 37 (9) | 3.86 | 11.09 | **0.35** | 0.15–0.52 | fail |
| 6 h | 3 | 37 (9) | 3.86 | 6.40 | **0.61** | 0.27–0.90 | fail (context) |
| 12 h | 1 | 12 (8) | 7.39 | 10.77 | **0.65** | 0.38–1.24 | fail |
| 12 h | 3 | 12 (8) | 7.39 | 6.22 | **1.12** | 0.66–2.15 | fail (context) |

**Measured visit-level error** (replayed visit mean minus the same frame's full-frame value; visits at 30–70%), against the σ_fov model:

| FOVs | visits | mean error (pp) | SD (pp) | model σ_fov/√n at the median confluency (pp) | median increment ÷ measured SD, 6 h | 12 h |
|---|---|---|---|---|---|---|
| 1 | 69 | -0.04 | 13.21 | 11.41 | 0.29 | 0.56 |
| 3 | 69 | -0.77 | 7.51 | 6.59 | 0.51 | 0.98 |

The same frames are replayed at 1 and 3 FOVs and in both cadences, so the rows are not independent.
A difference of two noisy readings has √2 × the noise of one; the spec's ratio leaves that out, so the signal-to-noise of one increment is the ratio ÷ 1.41.

**V2 at 1 FOV: fail** (6 h 0.35, 12 h 0.65). At 3 FOVs: fail (6 h 0.61, 12 h 1.12).

FOV size matters as much as FOV count. The replay FOV is a 0.25-frac crop (348 × 260 of a 1392 × 1040 frame, an A2 choice). With the 0.5-frac σ_fov fit from the same noise config (σ = 1.325 + 0.0819 × confluency), same increments: median ratio 6 h/1 FOV 0.85, 6 h/3 FOV 1.46, 12 h/1 FOV 1.56, 12 h/3 FOV 2.71 (context; not replayed at that size).

All confluencies, for context (not the spec's band): median ratio 6 h/1 FOV 0.40, 6 h/3 FOV 0.69, 12 h/1 FOV 0.84, 12 h/3 FOV 1.46.

Plot: `results/growth_signal_v2.png`; every pair: `results/growth_signal_v2_pairs.csv`.

## V10 (informational): growth per experiment

`culture.growth.fit_growth` on each held-out sequence's hourly full-frame series (condition metadata is "unknown" in this C2C12 import, so grouped by experiment). Confluency-area doubling time, early phase — a rate of confluency, not cell doubling time.

| experiment | sequences | fits OK | chosen model (logistic/gompertz) | area doubling time, median (range), h | start → end confluency, median (%) |
|---|---|---|---|---|---|
| 090303 | 2 | 2 | 2/0 | 17.7 (17.5–17.9) | 1.2 → 43.4 |
| 090318 | 7 | 7 | 5/2 | 12.4 (10.7–21.5) | 2.6 → 47.1 |
| 090325 | 5 | 5 | 3/2 | 15.4 (9.5–21.5) | 2.4 → 43.1 |

Per sequence: `results/growth_signal_v10.csv`.
