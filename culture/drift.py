"""
cultureqc.drift — minimal instrument-drift monitor (A7; cultureQC_upgrade_spec.md
§2A.8, §10).

If many flasks on one instrument move together, the cause is the instrument,
not the cultures. Flasks are aligned on hours since their own start (the
relative clock the simulated lamp dimming is defined on).

Per flask and visit, two population inputs:
  - exposure: log(exposure_mean) minus the flask's own median over its first
    `baseline_hours` (flasks differ in brightness far more than drift moves
    them), minus the expected change at that age, divided by the expected SD
    at that age (both from a reference fitted on tuning normal frames,
    fit_reference()). Normal growth raises exposure slowly, hence the
    age-dependent expected value.
  - anomaly: A4's per-bin anomaly z.
Every visit counts, including quality-gate failures: a dimmed frame fails the
gate, and that is exactly the frame the instrument monitor must see.

Population statistic per window (width = the visit cadence, [k·w, (k+1)·w)):
the median over active flasks (those with a visit in the window; a flask's
latest visit in it) of each input, from the first window starting at or after
`baseline_hours`. Each population series is standardised by its mean/SD on
the tuning normal fleet and trended with an EWMA (λ, time-varying limit
± L·sqrt(λ/(2−λ)·(1−(1−λ)^{2t}))).

Drift state, not episodes-with-restart: INSTRUMENT_DRIFT is active in every
window where some population EWMA is beyond its limit (an instrument fault
persists until fixed, and suppression must cover all of it). An episode is a
run of active windows.

Suppression: a per-flask flag at a visit in an active window is kept but
marked suppressed. The window's state is known when the window closes, so a
flag waits for its imaging round (window) to finish.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

from culture.spc import ewma_limit


@dataclass(frozen=True)
class Reference:
    """Expected per-flask log-exposure change and its SD vs hours since start
    (linear interpolation between knots, flat beyond the ends)."""
    hours: list[float]
    expected: list[float]
    sd: list[float]

    def at(self, h):
        return (np.interp(h, self.hours, self.expected), np.interp(h, self.hours, self.sd))


def relative_log(values: pd.Series, hours: pd.Series, flask: pd.Series, baseline_hours: float) -> pd.Series:
    """log(values) minus each flask's median log value over hours < baseline_hours."""
    lx = np.log(values.astype(float))
    base = lx[hours < baseline_hours].groupby(flask[hours < baseline_hours]).median()
    return lx - flask.map(base)


def fit_reference(rel: pd.Series, hours: pd.Series, flask: pd.Series, baseline_hours: float,
                  bin_hours: float, min_flasks: int) -> Reference:
    """Per bin of `bin_hours` from `baseline_hours` on: expected = median over
    flasks of each flask's median `rel` in the bin; SD = SD of `rel` minus
    expected over the bin's frames. Bins with fewer than `min_flasks` flasks
    are dropped (the reference is then flat beyond the last kept bin). SDs
    are floored at the median of the kept bins' SDs, so a quiet stretch does
    not turn tiny wobbles into large z."""
    df = pd.DataFrame({"rel": rel.to_numpy(), "h": hours.to_numpy(), "f": flask.to_numpy()})
    df = df[df.h >= baseline_hours]
    df["bin"] = np.floor((df.h - baseline_hours) / bin_hours).astype(int)
    knots, exp, sds = [], [], []
    for b, g in df.groupby("bin"):
        per_flask = g.groupby("f").rel.median()
        if len(per_flask) < min_flasks:
            continue
        e = float(per_flask.median())
        knots.append(baseline_hours + (b + 0.5) * bin_hours)
        exp.append(e)
        sds.append(float((g.rel - e).std(ddof=1)))
    if not knots:
        raise ValueError("no bin has enough flasks for a reference")
    floor = float(np.median(sds))
    return Reference(knots, exp, [max(s, floor) for s in sds])


def population_series(visits: pd.DataFrame, value: str, window_h: float, start_h: float,
                      min_flasks: int) -> pd.DataFrame:
    """Median of `value` over active flasks per window. `visits` needs columns
    flask, hours, `value`. Windows start at multiples of window_h; only those
    starting at or after start_h are returned (baseline windows are skipped).
    Returns columns window, start, end, n_flasks, median (NaN if too few)."""
    v = visits.dropna(subset=[value]).copy()
    v["window"] = np.floor(v.hours / window_h).astype(int)
    last = v.sort_values("hours").groupby(["window", "flask"]).tail(1)
    first_w = int(math.ceil(start_h / window_h - 1e-9))
    last_w = int(np.floor(visits.hours.max() / window_h))
    rows = []
    for w in range(first_w, last_w + 1):
        g = last[last.window == w]
        rows.append({"window": w, "start": w * window_h, "end": (w + 1) * window_h, "n_flasks": len(g),
                     "median": float(g[value].median()) if len(g) >= min_flasks else np.nan})
    return pd.DataFrame(rows)


def ewma_state(z: list[float | None], lam: float, L: float, side: str) -> tuple[list[float | None], list[bool]]:
    """EWMA without restart; per point the statistic (None where z is None)
    and whether it is beyond the limit on `side` ("upper", "lower", "two")."""
    stats, out, e, t = [], [], 0.0, 0
    for x in z:
        if x is None or (isinstance(x, float) and math.isnan(x)):
            stats.append(None)
            out.append(False)
            continue
        t += 1
        e = lam * x + (1.0 - lam) * e
        lim = ewma_limit(lam, L, t)
        hit = {"upper": e > lim, "lower": e < -lim, "two": abs(e) > lim}[side]
        stats.append(e)
        out.append(bool(hit))
    return stats, out


def episodes(active: list[bool]) -> int:
    """Number of runs of True."""
    return sum(1 for i, a in enumerate(active) if a and (i == 0 or not active[i - 1]))


def suppressed(visit_hours: pd.Series, window_h: float, active_windows: set[int]) -> pd.Series:
    """True where a visit falls in a window with INSTRUMENT_DRIFT active."""
    return np.floor(visit_hours / window_h).astype(int).isin(active_windows)
