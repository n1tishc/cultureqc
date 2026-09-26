import math

import numpy as np
import pandas as pd

from culture.drift import (episodes, ewma_state, fit_reference, population_series, relative_log,
                           suppressed)


def _fleet(n_flasks=10, n_visits=15, cadence=6.0, shift_from=None, shift=0.0, only_flask=None, seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    for f in range(n_flasks):
        for i in range(n_visits):
            h = i * cadence + 1.0
            x = float(rng.normal(0, 0.1))
            if shift_from is not None and h >= shift_from and (only_flask is None or f == only_flask):
                x += shift
            rows.append({"flask": f"F{f}", "hours": h, "x": x})
    return pd.DataFrame(rows)


def _active(fleet, cadence=6.0):
    pop = population_series(fleet, "x", cadence, start_h=0.0, min_flasks=5)
    z = [None if pd.isna(m) else m / 0.1 for m in pop["median"]]
    _, hit = ewma_state(z, lam=0.2, L=2.86, side="two")
    return pop, hit


def test_common_shift_fires_only_after_it_starts():
    pop, hit = _active(_fleet(shift_from=48.0, shift=-1.0))
    assert not any(h for h, s in zip(hit, pop.start) if s < 48.0)
    assert any(h for h, s in zip(hit, pop.start) if s >= 48.0)


def test_single_outlier_flask_does_not_move_the_median():
    _, hit = _active(_fleet(shift_from=48.0, shift=-5.0, only_flask=3))
    assert not any(hit)


def test_windows_with_too_few_flasks_are_skipped():
    fleet = _fleet(n_flasks=10)
    fleet = fleet[~((fleet.hours >= 30.0) & (fleet.hours < 36.0) & (fleet.flask.isin([f"F{i}" for i in range(7)])))]
    pop = population_series(fleet, "x", 6.0, start_h=0.0, min_flasks=5)
    w5 = pop[pop.window == 5].iloc[0]
    assert w5.n_flasks == 3 and math.isnan(w5["median"])
    stats, hit = ewma_state([None if pd.isna(m) else m for m in pop["median"]], 0.2, 2.86, "two")
    assert stats[5] is None and hit[5] is False


def test_population_uses_latest_visit_per_flask_and_skips_baseline_windows():
    fleet = pd.DataFrame({"flask": ["A", "A", "B", "C"], "hours": [25.0, 29.0, 26.0, 27.0], "x": [9.0, 1.0, 2.0, 3.0]})
    pop = population_series(fleet, "x", 6.0, start_h=24.0, min_flasks=3)
    assert list(pop.window) == [4]
    assert pop["median"].iloc[0] == 2.0  # A's latest visit (1.0), B 2.0, C 3.0


def test_ewma_state_has_no_restart():
    _, hit = ewma_state([5.0] * 6, lam=0.2, L=2.86, side="upper")
    assert all(hit)  # stays active while the shift persists
    _, hit = ewma_state([-5.0] * 3, lam=0.2, L=2.86, side="upper")
    assert not any(hit)


def test_episodes_and_suppression():
    assert episodes([False, True, True, False, True]) == 2
    assert episodes([]) == 0
    s = suppressed(pd.Series([5.9, 6.0, 13.0, 20.0]), 6.0, {1, 3})
    assert list(s) == [False, True, False, True]


def test_relative_log_and_reference():
    hours = pd.Series([0.0, 12.0, 30.0, 0.0, 12.0, 30.0])
    flask = pd.Series(["A", "A", "A", "B", "B", "B"])
    vals = pd.Series([100.0, 100.0, 110.0, 50.0, 50.0, 55.0])
    rel = relative_log(vals, hours, flask, baseline_hours=24.0)
    assert np.allclose(rel, [0, 0, math.log(1.1)] * 2)

    h = pd.Series(np.tile(np.arange(24.0, 48.0), 6))
    f = pd.Series(np.repeat([f"F{i}" for i in range(6)], 24))
    r = pd.Series(0.01 * (h - 24.0) + np.random.default_rng(0).normal(0, 0.001, len(h)))
    ref = fit_reference(r, h, f, baseline_hours=24.0, bin_hours=6.0, min_flasks=5)
    assert ref.hours == [27.0, 33.0, 39.0, 45.0]
    e, sd = ref.at(np.array([27.0, 100.0]))
    assert abs(e[0] - 0.025) < 0.002  # median of hours 24..29
    assert abs(e[1] - ref.expected[-1]) < 1e-12  # flat beyond the last knot
    sds = sorted(ref.sd)
    assert sds[0] == sds[1]  # the two bins below the median SD are raised to it
