# FOV noise floor — Slice 1b (`cultureQC_upgrade.md` §4.3)

**Source:** cached crop confluency in `cache`, no GPU/recompute. 246 real images (autoqc_bench_test, evican_eval2019), excluding synthetic tiles.

**Method:** for each image and each configured `crop_frac`, K deterministic random sub-crops simulate K repositions of the same FOV. Mean confluency across those crops is the density regime; SD across them is the noise floor at that density — the swing the temporal layer must exceed before flagging a real change, not measurement noise.

| crop_frac | n points (images) | mean SD (pp) | max SD (pp) | linear fit R² |
|---:|---:|---:|---:|---:|
| 0.25 | 246 | 6.115 | 51.278 | 0.729 |
| 0.5 | 246 | 2.908 | 31.277 | 0.527 |

**Fit:** `sigma_fov(confluency_pct) = intercept + slope * confluency_pct`, per `crop_frac` — a plain linear fit, not a joint 2D surface over (confluency, crop_frac). The cache only has two discrete crop_frac values by default (0.25, 0.5), not a continuous range, so a 2-parameter-per-frac linear model is the honest amount of structure this data supports — a fancier joint model would be extrapolating past what's actually here. Saved to `configs/noise.yaml` for Slices 2-5 to import directly.

See `results/fov_noise_plot.png` for the scatter + fit lines, `results/fov_noise.csv` for every (image, crop_frac) point.
