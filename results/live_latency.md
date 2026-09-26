# A8: live per-visit latency

Generated 2026-09-26T19:03:40Z by `scripts/benchmark_live_path.py`; per-run data in `results/live_latency.csv`.

**Hardware (approximation):** Apple M2 Pro Mac, torch 2.14.0, torch and OpenCV limited to **2 threads** to mimic the product Space (HF CPU Basic, 2 vCPU; `deploy/README.md`). Apple Silicon cores are faster than a shared cloud vCPU, so treat these as a lower bound for the Space. Median of 2 runs per input after a warm-up; models resident.

**Input:** no C2C12 frames are on the Mac, so a real phase-contrast LIVECell fixture (`test-data/A172_Phase_C7_1_00d00h00m_1.tif`) is tiled 2 × 2 and cropped to the C2C12 frame size. Cellpose time tracks pixel count, not content (`results/baseline_latency.md`).

One-time model load (excluded): Cellpose-SAM 2.9 s, classifier 0.6 s, DINOv2-small 4.4 s, kNN banks 0.0 s.

## Per FOV (seconds, median)

| input | quality gate | Cellpose-SAM | classifier (+ Grad-CAM) | DINOv2-small qctile | patch kNN | total per FOV |
|---|---|---|---|---|---|---|
| 1392x1040 (C2C12 frame size) | 0.00768 | 689 | 0.674 | 0.026 | 0.00304 | 689.7 |
| 704x520 (fixture native) | 0.00209 | 230 | 0.662 | 0.0258 | 0.00263 | 230.9 |
| 348x260 (replay 0.25 FOV crop) | 0.000449 | 71 | 0.667 | 0.0258 | 0.00265 | 71.7 |

Classifier without Grad-CAM: 1392x1040 0.17 s, 704x520 0.17 s, 348x260 0.16 s.

## V9: per visit (budget 5 s)

A visit is n_fov independent FOV images, each through the whole path.

| input | 1 FOV | 3 FOVs | Cellpose share | V9 (1 FOV) |
|---|---|---|---|---|
| 1392x1040 (C2C12 frame size) | 689.7 s | 2069.0 s | 100% | fail (138× budget) |
| 704x520 (fixture native) | 230.9 s | 692.8 s | 100% | fail (46× budget) |
| 348x260 (replay 0.25 FOV crop) | 71.7 s | 215.1 s | 99% | fail (14× budget) |

Everything except Cellpose-SAM, per FOV: 1392x1040 0.71 s, 704x520 0.69 s, 348x260 0.70 s.

Growth fit per visit (not in the spec's list; `results/growth_runtime.txt`, default threads): 0.32 s median for a 20-visit segment.

## Consequence (spec fail branch)

Cellpose-SAM is essentially the whole cost; everything else fits the budget many times over. The spec's listed levers do not close the gap on this path: the backbone is already ViT-S, fewer crops only divides by n_fov, and even the smallest input tried is well over budget. What remains in the spec is "precompute demo examples and say so"; beyond it, a GPU Space or a lighter confluency model for the live path (a Phase B decision, with V1 rechecked on whatever replaces Cellpose-SAM). For reference, Slice 0 measured the same 704 × 520 fixture at 140 s with default threads (`results/baseline_latency.md`).
