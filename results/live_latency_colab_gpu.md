# Live latency and parity: Tesla T4

Generated 2026-09-29T21:52:32Z by `demo/selfcheck.py` on **Tesla T4** (cuda: True), Linux x86_64, torch 2.11.0+cu128.
Per image, models already loaded (one untimed warm-up pass first). Live values vs the stored precomputed example (`demo/examples/examples.json`). Compare with the CPU figure in `results/live_latency.md` (V9).

| example | size | Cellpose-SAM (s) | anomaly (s) | classifier (s) | total (s) | confluency live vs stored (%) | confidence live vs stored | anomaly score live vs stored | anomaly flag | action | map points across the cutoff (%) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| c2c12_normal_0_20 | 1392×1040 | 11.39 | 0.051 | 0.019 | 11.46 | 16.82 vs 16.82 | 0.775 vs 0.775 | 0.231322 vs 0.231322 | same | same | 0.032 |
| c2c12_normal_20_40 | 1392×1040 | 12.02 | 0.033 | 0.014 | 12.06 | 39.40 vs 39.41 | 0.512 vs 0.512 | 0.22051 vs 0.22051 | same | same | 0.060 |
| c2c12_normal_40_100 | 1392×1040 | 12.48 | 0.023 | 0.014 | 12.51 | 51.44 vs 51.42 | 0.014 vs 0.013 | 0.263359 vs 0.263359 | same | same | 0.153 |
| c2c12_contamination_1 | 1392×1040 | 12.72 | 0.021 | 0.014 | 12.76 | 86.65 vs 86.64 | 0.658 vs 0.658 | 0.623282 vs 0.623284 | same | same | 0.078 |
| c2c12_contamination_real_size | 1392×1040 | 11.78 | 0.069 | 0.019 | 11.87 | 12.17 vs 12.18 | 0.709 vs 0.709 | 0.328035 vs 0.328035 | same | same | 0.041 |
| evican_pc3 | 506×412 | 2.98 | 0.048 | 0.014 | 3.04 | 5.13 vs 5.13 | 0.969 vs 0.969 | 0.347918 vs 0.347918 | same | same | 0.000 |
| evican_ht29 | 444×416 | 3.00 | 0.032 | 0.013 | 3.05 | 29.30 vs 29.35 | 0.263 vs 0.266 | 0.264345 vs 0.264345 | same | same | 0.113 |

Median total per 1392×1040 C2C12 frame: **12.06 s** (n = 5). Anomaly flag and action the same as stored: 7 of 7 examples.
