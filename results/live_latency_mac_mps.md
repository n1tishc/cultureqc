# Live latency and parity: Apple MPS for Cellpose-SAM; DINOv2 and the classifier on CPU (6 threads)

Generated 2026-10-04T17:50:47Z by `demo/selfcheck.py` on **Apple MPS for Cellpose-SAM; DINOv2 and the classifier on CPU (6 threads)** (cuda: False), Darwin arm64, torch 2.14.0.
Per image, models already loaded (one untimed warm-up pass first). Live values vs the stored precomputed example (`demo/examples/examples.json`). Compare with the CPU figure in `results/live_latency.md` (V9).

| example | size | Cellpose-SAM (s) | anomaly (s) | classifier (s) | total (s) | confluency live vs stored (%) | confidence live vs stored | anomaly score live vs stored | anomaly flag | action | map points across the cutoff (%) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| c2c12_normal_0_20 | 1392×1040 | 15.78 | 0.028 | 0.217 | 16.03 | 16.82 vs 16.82 | 0.775 vs 0.775 | 0.231322 vs 0.231322 | same | same | 0.000 |
| c2c12_normal_20_40 | 1392×1040 | 16.23 | 0.027 | 0.217 | 16.48 | 39.41 vs 39.41 | 0.512 vs 0.512 | 0.22051 vs 0.22051 | same | same | 0.000 |
| c2c12_normal_40_100 | 1392×1040 | 16.50 | 0.027 | 0.218 | 16.75 | 51.43 vs 51.43 | 0.015 vs 0.015 | 0.263359 vs 0.263359 | same | same | 0.000 |
| c2c12_contamination_1 | 1392×1040 | 16.43 | 0.035 | 0.264 | 16.73 | 86.64 vs 86.64 | 0.657 vs 0.657 | 0.623284 vs 0.623284 | same | same | 0.000 |
| c2c12_contamination_real_size | 1392×1040 | 15.55 | 0.034 | 0.188 | 15.78 | 12.18 vs 12.18 | 0.709 vs 0.709 | 0.328035 vs 0.328035 | same | same | 0.000 |
| evican_pc3 | 506×412 | 4.02 | 0.030 | 0.206 | 4.25 | 6.60 vs 6.60 | 0.965 vs 0.965 | 0.347918 vs 0.347918 | same | same | 0.000 |
| evican_ht29 | 444×416 | 4.03 | 0.029 | 0.206 | 4.26 | 52.91 vs 52.91 | 0.828 vs 0.828 | 0.264345 vs 0.264345 | same | same | 0.000 |

Median total per 1392×1040 C2C12 frame: **16.48 s** (n = 5). Anomaly flag and action the same as stored: 7 of 7 examples.
