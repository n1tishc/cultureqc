# Live latency and parity: Apple MPS for Cellpose-SAM; DINOv2 and the classifier on CPU (6 threads)

Generated 2026-09-29T01:10:58Z by `demo/selfcheck.py` on **Apple MPS for Cellpose-SAM; DINOv2 and the classifier on CPU (6 threads)** (cuda: False), Darwin arm64, torch 2.14.0.
Per image, models already loaded (one untimed warm-up pass first). Live values vs the stored precomputed example (`demo/examples/examples.json`). Compare with the CPU figure in `results/live_latency.md` (V9).

| example | size | Cellpose-SAM (s) | anomaly (s) | classifier (s) | total (s) | confluency live vs stored (%) | confidence live vs stored | anomaly score live vs stored | anomaly flag | action | map points across the cutoff (%) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| c2c12_normal_0_20 | 1392×1040 | 16.06 | 0.058 | 0.222 | 16.34 | 16.82 vs 16.82 | 0.775 vs 0.775 | 0.231322 vs 0.231322 | same | same | 0.029 |
| c2c12_normal_20_40 | 1392×1040 | 16.17 | 0.034 | 0.226 | 16.43 | 39.41 vs 39.41 | 0.512 vs 0.512 | 0.22051 vs 0.22051 | same | same | 0.051 |
| c2c12_normal_40_100 | 1392×1040 | 17.41 | 0.161 | 0.221 | 17.80 | 51.43 vs 51.42 | 0.015 vs 0.013 | 0.263359 vs 0.263359 | same | same | 0.151 |
| c2c12_contamination_1 | 1392×1040 | 16.70 | 0.204 | 0.208 | 17.12 | 86.64 vs 86.64 | 0.657 vs 0.658 | 0.623284 vs 0.623284 | same | same | 0.065 |
| c2c12_contamination_real_size | 1392×1040 | 15.87 | 0.043 | 0.203 | 16.11 | 12.18 vs 12.18 | 0.709 vs 0.709 | 0.328035 vs 0.328035 | same | same | 0.000 |
| evican_pc3 | 506×412 | 4.16 | 0.031 | 0.199 | 4.39 | 5.13 vs 5.13 | 0.969 vs 0.969 | 0.347918 vs 0.347918 | same | same | 0.000 |
| evican_ht29 | 444×416 | 4.13 | 0.032 | 0.210 | 4.37 | 29.30 vs 29.35 | 0.265 vs 0.266 | 0.264345 vs 0.264345 | same | same | 0.078 |

Median total per 1392×1040 C2C12 frame: **16.43 s** (n = 5). Anomaly flag and action the same as stored: 7 of 7 examples.
