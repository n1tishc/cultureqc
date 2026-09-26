# FOV noise floor — Slice 1b (`cultureQC_upgrade.md` §4.3)

**Source:** cached crop confluency in `cache`, no GPU/recompute. 2088 real images (c2c12), excluding synthetic tiles. They come from 24 time-lapse sequences, so frames of one sequence are not independent samples.

**Method:** for each image and each configured `crop_frac`, K deterministic random sub-crops simulate K repositions of the same FOV. Mean confluency across those crops is the density regime; SD across them is the noise floor at that density — the swing the temporal layer must exceed before flagging a real change, not measurement noise.

| crop_frac | n points (images) | mean SD (pp) | max SD (pp) | linear fit R² |
|---:|---:|---:|---:|---:|
| 0.25 | 2088 | 6.593 | 28.736 | 0.392 |
| 0.5 | 2088 | 2.891 | 16.638 | 0.275 |

**Fit:** `sigma_fov(confluency_pct) = intercept + slope * confluency_pct`, per `crop_frac` — a plain linear fit, not a joint 2D surface over (confluency, crop_frac). The cache only has two discrete crop_frac values by default (0.25, 0.5), not a continuous range, so a 2-parameter-per-frac linear model is the honest amount of structure this data supports — a fancier joint model would be extrapolating past what's actually here. Saved to `configs/noise.yaml` under `entries.c2c12`; the top-level fit that culture/growth.py reads is unchanged.

See `results/fov_noise_c2c12_plot.png` for the scatter + fit lines, `results/fov_noise_c2c12.csv` for every (image, crop_frac) point.
