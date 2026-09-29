# Contamination at a realistic bacterial size

Generated 2026-09-29T00:52:40Z by `scripts/contamination_scale.py` on the Mac (Apple MPS), with the live path's models: Cellpose-SAM (cpsam_v2), the quality gate (C2C12 thresholds), and DINOv2-small with the frozen anomaly calibration in `configs/anomaly.yaml`. C2C12 images: Ker et al., *Sci Data* 5:180237 (2018), CC BY 4.0. Bacteria: DeepBacs (Zenodo 5550935), 79 nm/px.

## Why

The original contamination fault set pastes DeepBacs bacteria pixel for pixel into 1.3 µm/px C2C12 frames, so they are 16.5× too long (docs/ARCHITECTURE_VALIDATION.md, V5 correction). Here the same frames are rebuilt with the bacteria shrunk by 0.079 / 1.3 = 0.0608, area-averaged, so a bacterium narrower than a pixel darkens part of one pixel. The median bacterium in the sprite library is 59 px long at 79 nm/px (longest side of the minimum-area rectangle around its mask; the 55 px in docs/STATUS.md B0 is a bounding-box measure) ({length * 0.079:.1f} µm): {length:.0f} px (77 µm) as originally pasted, 3.6 px as pasted here. Bacteria are placed on background pixels only, and one narrower than a pixel darkens it by a few grey levels, so fewer are visible in the plot than were placed.

## Design

Fixed before any realistic-size output was seen:

- Same 4 sequences, onset, frames, seed and density ramp as the original (20 → 400 bacteria per 256 px tile area over 24 h after onset); only the bacterium size changes.
- Frozen anomaly thresholds, confidence floor (0.30) and rules; nothing is tuned on these frames, and the density is not extended past the original 400.
- Two realistic variants: with the simulator's turbidity haze, as the original, and without it. The haze strength follows the bacterium count, not the size, so on its own it could make a flag look like detection. Both variants place the same bacteria in the same spots.
- Held-out frames are scored against the full tuning banks (the live path's), tuning frames against banks rebuilt without their own sequence, as in `scripts/eval_anomaly.py`.

Changed after the first variant's output was seen, and why:

- The score step first ran the quality gate with the default thresholds; the C2C12 thresholds are the ones every other C2C12 result uses, so the gate is recomputed from the PNGs with them (no model).
- A control was added: the same 97 frames with no fault, scored here. The first comparison was against the cache's values from the Colab GPU, which mixes the bacteria's effect with the platform's; contaminated-vs-clean below is measured on this Mac only.

## Controls

- Base frames re-downloaded from OSF and converted with the stored normalization: 97/97 byte-identical to the frames in the compute cache.
- The builder at scale 1 with haze rebuilds the original fault frames: 1/97 byte-identical (the manifest's sha256). The two frames kept as demo examples show why the rest are not: c2c12_contamination_1, 5 of 1,447,680 pixels differ, by at most 1 grey level; c2c12_contamination_2, 10 of 1,447,680 pixels differ, by at most 1 grey level. The same bacteria land in the same places; the last-bit differences come from floating-point rounding on this Mac (ARM) against Colab (x86).
- This Mac vs the cache (Colab GPU), clean frames: confluency differs by a median 0.01 pp (max 0.05), anomaly score by a median 0.0001 (max 0.0003), the flag agrees on 97/97. Original fault frames: 0.01 pp (max 0.19), 0.0001 (max 0.0003), 97/97.

## Results

All 97 frames (4 sequences, both splits) unless marked held-out (49 frames, 2 sequences). Frames within a sequence are not independent. Shifts are paired: the same frame with the fault minus without it, both scored here. AUROC, as V5(b): held-out frames of the column vs the 1228 held-out normal frames in the cache (binned z; the cache's side was scored on the Colab GPU).

| | no fault (control) | original: 16.5× too large, haze | realistic size, haze | realistic size, no haze |
|---|---|---|---|---|
| bacteria placed / asked for | — | 591,987 / 643,876 | 639,337 / 643,876 | 639,337 / 643,876 |
| held-out AUROC, all frames | 0.47 | 1.00 | 0.48 | 0.48 |
| held-out AUROC, ≥ 150 per tile | 0.44 | 1.00 | 0.50 | 0.51 |
| anomaly flag, all frames | 4 of 97 (4%) | 97 of 97 (100%) | 1 of 97 (1%) | 1 of 97 (1%) |
| anomaly flag, held-out | 2 of 49 | 49 of 49 | 1 of 49 | 1 of 49 |
| anomaly flag, 0–100 per tile | 2 of 12 | 12 of 12 | 0 of 12 | 0 of 12 |
| anomaly flag, 100–200 per tile | 0 of 12 | 12 of 12 | 0 of 12 | 0 of 12 |
| anomaly flag, 200–300 per tile | 1 of 12 | 12 of 12 | 0 of 12 | 0 of 12 |
| anomaly flag, 300–400 per tile | 1 of 61 | 61 of 61 | 1 of 61 | 1 of 61 |
| confluency, median (range) | 22.9% (9.8–50.8) | 88.3% (26.7–91.2) | 18.7% (9.0–37.7) | 18.7% (9.0–38.0) |
| confluency shift vs the clean frame, median (IQR) | — | +58.9 pp (+49.1 to +66.1) | -4.3 pp (-8.6 to -2.4) | -4.2 pp (-8.2 to -2.5) |
| quality gate fails (REIMAGE) | 18 of 97 | 91 of 97 | 12 of 97 | 16 of 97 |
| confidence below the floor (0.3) | 10 of 97 | 13 of 97 | 5 of 97 | 5 of 97 |
| target 80%: reach it (confidence ≥ floor) | none (highest 42.7%) | 64 | none (highest 32.3%) | none (highest 32.6%) |
| target 80%: of those, held by the flag | — | 64 | — | — |
| target 50%: reach it (confidence ≥ floor) | none (highest 42.7%) | 76 | none (highest 32.3%) | none (highest 32.6%) |
| target 50%: of those, held by the flag | — | 76 | — | — |

Reference, from `results/anomaly_summary.md`: held-out normal frames are flagged at 14.7% in the 0–20% bin, 3.8% in 20–40% and 0.6% in 40–100% (thresholds set for 5% on tuning normals).

Plot: `results/contamination_scale_examples.png` (copied to `demo/figures/contamination_scale.png` for the console's Detectability tab), the anomaly check's 256 px centre tile of c2c12_090318_exp1_F0005_Data__fault_contam, frame 1057.

## Per-frame scores

`results/contamination_scale.csv`: one row per frame and variant.
