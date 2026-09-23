"""
cultureqc.growth — per-segment growth curve fit + time-to-target prediction
(cultureQC_upgrade.md §6.1).

Fits a segment's trend-eligible visits (real timestamps, converted to hours
since the segment's first visit) with two candidate curves — logistic and
Gompertz — weighted by `1 / (confluency_sd^2 + sigma_fov^2)`, where
`sigma_fov` is the *measured* FOV-repositioning noise floor from
`configs/noise.yaml` (scripts/fov_noise.py, fit on real cached repositioning
crops) at that visit's confluency level and crop_frac — not re-measured or
guessed a second time here, same "exactly one implementation of what X
means" convention `culture/quality.py` uses for blur/exposure/uniformity.

AIC (weighted-least-squares form, `n*ln(WRSS/n) + 2k`) picks between the two
fits; both are reported, never just the winner.

**Time to target** confluency (T*, default 80%) is closed-form per model. If
the fitted carrying capacity K never reaches the target, status is
`NOT_REACHED` — a real, distinct outcome, never a fabricated crossing time.

**Uncertainty on T*** and the plotted band both come from one shared
residual bootstrap (>= 500 resamples, seeded via `seed`): resample fit
residuals with replacement, refit the chosen model to each resampled series,
and use the resulting parameter sets both for percentiles of T* (a 90%
interval) and for percentiles of the fitted *curve itself* over a time grid
— not two separate, possibly-inconsistent uncertainty computations.

Call that curve band a **fit uncertainty band**, not a "prediction band":
it's the 90% spread of the fitted mean curve across resampled refits, which
is narrower than a true prediction band for a *future single observation*
would be (a real prediction band would also add each point's own
`sigma_fov`-scale observation noise on top, which this does not). §6.1 says
"prediction band"; this module (and the UI, and the README) intentionally
say the more precise thing instead so the plotted band isn't read as wider
than it is.

**"Area doubling time"** (`ln2 / r`, early phase — never "cell doubling
time": this is FOV-area growth, not a mitotic count) is reported
model-agnostically as `ln2 / mu`, where `mu` is the model's own specific
growth rate `(dC/dt)/C` evaluated at the earliest visit's time. For the
logistic this reduces to `r * (1 - C/K)`, close to the `r` parameter itself
early in the curve; there's no single `r` for Gompertz, so this is the
honest generalization of "early phase doubling time" for either model.

**Known limit — the T* interval does not cover model-selection uncertainty.**
AIC picks logistic vs Gompertz once, on the real (unresampled) fit; every
bootstrap resample is then refit to *that same chosen model* — a resample is
never allowed to prefer the other model. This is the standard, much simpler
"bootstrap conditional on the selected model" approach, not full model-
averaging, and it understates the true interval width specifically when the
two models' AIC are close (i.e. the selection itself was uncertain) — see
scripts/backtest_growth.py's synthetic backtest, where sparse/noisy prefixes
with near-tied AIC show the 90% interval covering the true crossing well
below 90% of the time. Treat T*'s interval as "uncertainty given the chosen
model," not "uncertainty including whether logistic or Gompertz is right."

Callers must pass an already trend-filtered window of visits — e.g.
`History.require_single_window(segment_id)` or one window from
`History.trend_windows(segment_id)` — `growth.py` does not re-filter
quality-failing visits or re-split on `model_versions` changes; that
enforcement point stays in `culture/history.py` (see its own docstring), not
duplicated here.

Usage:
    from culture.growth import fit_growth
    result = fit_growth(visits, target_pct=80.0, seed=0)
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
import yaml
from scipy.optimize import curve_fit

_DEFAULT_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "configs", "growth.yaml"
)
_NOISE_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "configs", "noise.yaml"
)

_CROP_FRAC_RE = re.compile(r"crop_f([0-9.]+)_")


def _load_yaml(path: str) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def _logistic(t: np.ndarray, K: float, r: float, t0: float) -> np.ndarray:
    return K / (1.0 + np.exp(-r * (t - t0)))


def _gompertz(t: np.ndarray, K: float, b: float, c: float) -> np.ndarray:
    return K * np.exp(-b * np.exp(-c * t))


MODEL_FNS = {"logistic": _logistic, "gompertz": _gompertz}
PARAM_NAMES = {"logistic": ("K", "r", "t0"), "gompertz": ("K", "b", "c")}


def growth_config_hash(config_path: str = _DEFAULT_CONFIG_PATH) -> str:
    """SHA-256 of configs/growth.yaml's raw bytes — for visit/decision
    records' config_hashes field, same convention as quality.config_hash()."""
    from culture.records import hash_file
    return hash_file(config_path)


# -- weighting -----------------------------------------------------------

def _sigma_fov_for_visit(visit: dict, noise_cfg: dict, fallback_frac: float) -> float:
    """configs/noise.yaml's measured `sigma_fov(confluency_pct) = intercept +
    slope*pct`, per crop_frac (scripts/fov_noise.py, real cached
    repositioning crops) — not re-measured or guessed here. Parses the
    visit's own `crop_specs` for the frac(s) actually sampled and averages
    sigma_fov across the distinct fracs found. Falls back to
    `fallback_frac` (configs/growth.yaml) for a visit with no parseable crop
    spec (e.g. a single "full"-frame fallback reading — see
    culture/replay.py:_sample_crops_for_frame — which has no measured
    crop-repositioning-noise entry at all; the fallback frac is the closest
    available proxy, not a measurement of the full-frame case)."""
    fracs = set()
    for spec in visit.get("crop_specs") or []:
        m = _CROP_FRAC_RE.search(spec)
        if m:
            fracs.add(m.group(1))
    if not fracs:
        fracs = {str(fallback_frac)}

    available = {float(k): v for k, v in noise_cfg["crop_fracs"].items()}
    pct = visit["confluency_mean"]
    sigmas = []
    for frac in fracs:
        entry = noise_cfg["crop_fracs"].get(frac)
        if entry is None:
            nearest = min(available, key=lambda k: abs(k - float(frac)))
            entry = available[nearest]
        sigma = entry["intercept"] + entry["slope"] * pct
        sigmas.append(max(sigma, 0.0))
    return float(np.mean(sigmas))


def _weights(visits: list[dict], noise_cfg: dict, fallback_frac: float) -> np.ndarray:
    """§6.1: `1 / (confluency_sd^2 + sigma_fov^2)`. A small floor keeps a
    visit with zero measured SD and zero sigma_fov (degenerate synthetic
    fixtures) from producing an infinite weight."""
    w = []
    for v in visits:
        sd = v.get("confluency_sd") or 0.0
        sigma_fov = _sigma_fov_for_visit(v, noise_cfg, fallback_frac)
        var = sd**2 + sigma_fov**2
        w.append(1.0 / max(var, 1e-6))
    return np.array(w, dtype=np.float64)


def _hours_since_start(visits: list[dict]) -> tuple[np.ndarray, pd.Timestamp]:
    times = pd.to_datetime(pd.Series([v["timestamp"] for v in visits]), format="ISO8601")
    t0 = times.min()
    hours = ((times - t0).dt.total_seconds() / 3600.0).to_numpy()
    return hours, t0


# -- fitting ---------------------------------------------------------------

def _bounds_for(model_name: str, bounds_cfg: dict, t: np.ndarray) -> tuple[list[float], list[float]]:
    span = max(float(t.max() - t.min()), 1.0)
    if model_name == "logistic":
        b = bounds_cfg["logistic"]
        return (
            [1.0, b["r_min"], float(t.min()) - 2 * span],
            [100.0, b["r_max"], float(t.max()) + 2 * span],
        )
    b = bounds_cfg["gompertz"]
    return ([1.0, b["b_min"], b["c_min"]], [100.0, b["b_max"], b["c_max"]])


def _aic(y: np.ndarray, y_pred: np.ndarray, weights: np.ndarray, k_params: int) -> float:
    """Weighted-least-squares AIC: `n*ln(WRSS/n) + 2k`. The additive
    constant this drops is identical for both candidate models (same data,
    same weights), so it cancels in the logistic-vs-Gompertz comparison;
    reported anyway per §6.1 ("choose by AIC; report both")."""
    resid = y - y_pred
    wrss = max(float(np.sum(weights * resid**2)), 1e-12)
    n = len(y)
    return n * np.log(wrss / n) + 2 * k_params


def _initial_guess(model_name: str, t: np.ndarray, y: np.ndarray, bounds_cfg: dict) -> list[float]:
    K0 = float(np.clip(np.max(y) * 1.15, 5.0, 100.0))
    if model_name == "logistic":
        return [K0, 0.05, float(np.median(t))]
    y0 = max(float(y[0]), 0.5)
    b_lo, b_hi = bounds_cfg["gompertz"]["b_min"], bounds_cfg["gompertz"]["b_max"]
    b0 = float(np.clip(-np.log(y0 / K0), b_lo, b_hi))
    return [K0, b0, 0.05]


def _fit_one(model_name: str, t: np.ndarray, y: np.ndarray, weights: np.ndarray, bounds_cfg: dict) -> dict | None:
    fn = MODEL_FNS[model_name]
    p0 = _initial_guess(model_name, t, y, bounds_cfg)
    bounds = _bounds_for(model_name, bounds_cfg, t)
    sigma = 1.0 / np.sqrt(weights)

    try:
        params, _cov = curve_fit(fn, t, y, p0=p0, sigma=sigma, absolute_sigma=True, bounds=bounds, maxfev=20000)
    except RuntimeError:
        return None

    y_pred = fn(t, *params)
    aic = _aic(y, y_pred, weights, k_params=3)
    return {"params": dict(zip(PARAM_NAMES[model_name], (float(p) for p in params))), "aic": aic}


def _bootstrap_refit(model_name: str, params: dict, t: np.ndarray, y: np.ndarray, weights: np.ndarray,
                      bounds_cfg: dict, n_boot: int, rng: np.random.Generator) -> list[dict]:
    """Residual bootstrap (§6.1: '>= 500'): resample *standardized*
    residuals (raw residual / per-point sigma) with replacement, then
    rescale each resampled draw back by the target point's own sigma before
    adding it back to the fitted curve. This is the standard weighted/
    heteroscedastic residual bootstrap for WLS — plain (unstandardized)
    residual resampling would pool residuals across very different noise
    scales (sigma_fov varies a lot with confluency, per configs/noise.yaml)
    and could inject a high-noise-point's residual onto a low-noise point or
    vice versa, systematically under/overstating the interval. Standardizing
    first, rescaling after, keeps each reconstructed point's injected noise
    at its own measurement scale while still drawing the noise *shape* from
    the pooled residuals. A failed resample refit (curve_fit hits maxfev or
    bounds) is simply dropped, not substituted with anything — the caller
    checks how many succeeded."""
    fn = MODEL_FNS[model_name]
    p0 = [params[k] for k in PARAM_NAMES[model_name]]
    bounds = _bounds_for(model_name, bounds_cfg, t)
    sigma = 1.0 / np.sqrt(weights)
    y_pred = fn(t, *p0)
    standardized_resid = (y - y_pred) / sigma

    boot_params = []
    for _ in range(n_boot):
        resampled = rng.choice(standardized_resid, size=len(standardized_resid), replace=True)
        y_boot = np.clip(y_pred + resampled * sigma, 0.0, 100.0)
        try:
            p_boot, _cov = curve_fit(fn, t, y_boot, p0=p0, sigma=sigma, absolute_sigma=True, bounds=bounds, maxfev=5000)
        except RuntimeError:
            continue
        boot_params.append(dict(zip(PARAM_NAMES[model_name], (float(x) for x in p_boot))))
    return boot_params


# -- time to target / doubling time -----------------------------------------

def _time_to_target(model_name: str, params: dict, target: float) -> float | None:
    """Closed-form T*. Returns None (NOT_REACHED) if the fitted carrying
    capacity K never reaches `target` — never a fabricated crossing time."""
    K = params["K"]
    if target >= K:
        return None
    if model_name == "logistic":
        r, t0 = params["r"], params["t0"]
        return float(t0 - np.log(K / target - 1.0) / r)
    b, c = params["b"], params["c"]
    inner = -np.log(target / K) / b
    if inner <= 0:
        return None
    return float(-np.log(inner) / c)


def _specific_growth_rate(model_name: str, params: dict, t_ref: float) -> float:
    """`mu(t) = (dC/dt)/C`, evaluated at t_ref. Logistic: `r*(1 - C/K)`.
    Gompertz: `b*c*exp(-c*t)` (no division needed — this form is already
    `(dC/dt)/C` for the Gompertz curve)."""
    if model_name == "logistic":
        K, r, t0 = params["K"], params["r"], params["t0"]
        C = float(_logistic(np.array([t_ref]), K, r, t0)[0])
        return r * (1.0 - C / K)
    b, c = params["b"], params["c"]
    return b * c * np.exp(-c * t_ref)


def _area_doubling_time(model_name: str, params: dict, t_ref: float) -> float | None:
    """`ln2 / mu`, early phase. None if the early-phase specific growth rate
    is non-positive (e.g. fit already past inflection at the first visit) —
    "doubling time" isn't meaningful there, so this returns None rather than
    a negative or infinite number.

    This is a RATE, independent of the fitted carrying capacity K — a
    segment can have a fast early doubling time and still be NOT_REACHED
    (rises steeply to a low ceiling), while a segment with a much slower
    doubling time can still reach a high target eventually (rises slowly
    throughout, to a higher ceiling). Rate and ceiling are different axes;
    don't read a short doubling time as "this segment is doing well" without
    also checking t_star_status/K. See scripts/growth_examples.py's "poor"
    vs "plateau" pair for a concrete instance of this."""
    mu = _specific_growth_rate(model_name, params, t_ref)
    if mu <= 0:
        return None
    return float(np.log(2.0) / mu)


def _t_star_interval(model_name: str, boot_params: list[dict], target: float) -> tuple[tuple[float, float] | None, int]:
    t_stars = [
        ts for ts in (_time_to_target(model_name, p, target) for p in boot_params)
        if ts is not None and np.isfinite(ts)
    ]
    if len(t_stars) < max(10, 0.5 * len(boot_params)):
        return None, len(t_stars)
    lo, hi = np.percentile(t_stars, [5, 95])
    return (float(lo), float(hi)), len(t_stars)


def _fit_band(model_name: str, boot_params: list[dict], t_grid: np.ndarray) -> tuple[list[float] | None, list[float] | None]:
    """90% spread of the fitted *mean curve* across bootstrap refits — a fit
    uncertainty band, not a prediction band for a future single observation
    (see module docstring's 'Call that curve band...' note)."""
    if not boot_params:
        return None, None
    fn = MODEL_FNS[model_name]
    curves = np.array([fn(t_grid, *[p[k] for k in PARAM_NAMES[model_name]]) for p in boot_params])
    lo = np.percentile(curves, 5, axis=0)
    hi = np.percentile(curves, 95, axis=0)
    return lo.tolist(), hi.tolist()


# -- result -----------------------------------------------------------------

@dataclass
class GrowthResult:
    segment_id: str | None
    status: str  # "OK" | "INSUFFICIENT_DATA" | "FIT_FAILED"
    n_visits: int
    span_hours: float
    target_pct: float
    seed: int = 0
    chosen_model: str | None = None
    fits: dict = field(default_factory=dict)  # {"logistic": {"params": {...}, "aic": float}, "gompertz": {...}}
    t_star_hours: float | None = None
    t_star_status: str | None = None  # "REACHED" | "NOT_REACHED" | None (only when status != "OK")
    t_star_interval_hours: tuple[float, float] | None = None
    n_bootstrap_success: int | None = None
    area_doubling_time_hours: float | None = None
    t0_timestamp: str | None = None  # ISO timestamp the t=0 hour axis is relative to
    t_grid_hours: list | None = None
    y_grid: dict | None = None  # {"mean": [...], "lo": [...]|None, "hi": [...]|None} -- lo/hi is a 90% FIT uncertainty band, not a prediction band (see module docstring)


def fit_growth(
    visits: list[dict],
    target_pct: float | None = None,
    seed: int = 0,
    config_path: str = _DEFAULT_CONFIG_PATH,
    noise_config_path: str = _NOISE_CONFIG_PATH,
    n_boot: int | None = None,
) -> GrowthResult:
    """Fit a segment's trend-eligible visits (see module docstring for what
    `visits` must already have had done to it) and predict time to target
    confluency. Deterministic given `seed` — the bootstrap is the only
    randomness source (curve_fit itself is deterministic given p0/bounds)."""
    cfg = _load_yaml(config_path)
    noise_cfg = _load_yaml(noise_config_path)
    target_pct = cfg["target"]["default_pct"] if target_pct is None else target_pct
    n_boot = cfg["bootstrap"]["n_resamples"] if n_boot is None else n_boot
    fallback_frac = cfg["fallback_crop_frac"]

    n = len(visits)
    segment_id = visits[0]["segment_id"] if visits else None
    if n == 0:
        return GrowthResult(segment_id=segment_id, status="INSUFFICIENT_DATA", n_visits=0, span_hours=0.0, target_pct=target_pct, seed=seed)

    visits_sorted = sorted(visits, key=lambda v: v["timestamp"])
    t, t0_ts = _hours_since_start(visits_sorted)
    span = float(t.max() - t.min())

    md = cfg["minimum_data"]
    if n < md["min_visits"] or span < md["min_hours"]:
        return GrowthResult(segment_id=segment_id, status="INSUFFICIENT_DATA", n_visits=n, span_hours=span, target_pct=target_pct, seed=seed)

    y = np.array([v["confluency_mean"] for v in visits_sorted], dtype=np.float64)
    weights = _weights(visits_sorted, noise_cfg, fallback_frac)

    fits = {}
    for model_name in ("logistic", "gompertz"):
        fit = _fit_one(model_name, t, y, weights, cfg["bounds"])
        if fit is not None:
            fits[model_name] = fit

    if not fits:
        return GrowthResult(segment_id=segment_id, status="FIT_FAILED", n_visits=n, span_hours=span, target_pct=target_pct, seed=seed)

    chosen_model = min(fits, key=lambda m: fits[m]["aic"])
    params = fits[chosen_model]["params"]

    rng = np.random.default_rng(seed)
    boot_params = _bootstrap_refit(chosen_model, params, t, y, weights, cfg["bounds"], n_boot, rng)

    t_star = _time_to_target(chosen_model, params, target_pct)
    t_star_status = "REACHED" if t_star is not None else "NOT_REACHED"
    interval = None
    if t_star is not None:
        interval, _n_interval = _t_star_interval(chosen_model, boot_params, target_pct)

    doubling = _area_doubling_time(chosen_model, params, float(t.min()))

    grid_end = max(float(t.max()), (t_star or float(t.max())) * 1.05, float(t.max()) + 1.0)
    t_grid = np.linspace(float(t.min()), grid_end, 60)
    fn = MODEL_FNS[chosen_model]
    y_mean = fn(t_grid, *[params[k] for k in PARAM_NAMES[chosen_model]]).tolist()
    y_lo, y_hi = _fit_band(chosen_model, boot_params, t_grid)

    return GrowthResult(
        segment_id=segment_id,
        status="OK",
        n_visits=n,
        span_hours=span,
        target_pct=target_pct,
        seed=seed,
        chosen_model=chosen_model,
        fits={m: {"params": f["params"], "aic": f["aic"]} for m, f in fits.items()},
        t_star_hours=t_star,
        t_star_status=t_star_status,
        t_star_interval_hours=interval,
        n_bootstrap_success=len(boot_params),
        area_doubling_time_hours=doubling,
        t0_timestamp=t0_ts.isoformat(),
        t_grid_hours=t_grid.tolist(),
        y_grid={"mean": y_mean, "lo": y_lo, "hi": y_hi},
    )
