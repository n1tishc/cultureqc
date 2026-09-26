"""
culture/spc.py on synthetic residual streams: in-control false-alarm rate,
step-shift detection delay, sides, restart after a signal, skipped points.
"""

from __future__ import annotations

import numpy as np

from culture.spc import Monitor, Params, run_monitor, run_monitors, standard_monitors

P = Params(lam=0.2, L=2.86, k=0.5, h=4.0)


def test_in_control_false_alarm_rate_is_low():
    z = list(np.random.default_rng(0).standard_normal(20_000))
    for kind in ("ewma", "cusum"):
        rate = np.mean(run_monitor(z, Monitor("r", kind, "upper", "X"), P))
        assert 0.0005 < rate < 0.02, (kind, rate)


def test_step_shift_is_detected_quickly_on_the_right_side():
    rng = np.random.default_rng(1)
    delays = {"ewma": [], "cusum": []}
    for _ in range(200):
        z = list(rng.standard_normal(20)) + list(rng.standard_normal(30) - 2.0)  # shift down by 2 SD
        for kind in delays:
            lower = run_monitor(z, Monitor("r", kind, "lower", "X"), P)
            first = next((i - 19 for i in range(20, 50) if lower[i]), None)
            delays[kind].append(first if first is not None else 99)
    for kind, d in delays.items():
        assert np.median(d) <= 6, (kind, np.median(d))
    upper = run_monitor([-3.0] * 30, Monitor("r", "cusum", "upper", "X"), P)
    assert not any(upper)


def test_monitor_restarts_after_a_signal_and_skips_missing_points():
    fired = run_monitor([3.0] * 6, Monitor("r", "cusum", "upper", "X"), Params(k=0.5, h=4.0))
    assert fired == [False, True, False, True, False, True]  # 2.5, 5.0 fires, restart from 0
    with_gaps = run_monitor([3.0, None, float("nan"), 3.0], Monitor("r", "cusum", "upper", "X"), Params(k=0.5, h=4.0))
    assert with_gaps == [False, False, False, True]


def test_run_monitors_labels_signals_with_reason_residual_and_kind():
    mons = standard_monitors(["detachment"])
    assert {m.reason for m in mons} == {"GROWTH_BELOW_EXPECTED", "ANOMALY_DRIFT", "FAILURE_CLASS_DRIFT"}
    res = [{"growth": -6.0, "anomaly": 0.0, "class_detachment": None}]
    flags = run_monitors(res, mons, P)
    assert flags == [["GROWTH_BELOW_EXPECTED:growth:ewma", "GROWTH_BELOW_EXPECTED:growth:cusum"]]


def test_eval_counting_rules():
    import importlib.util
    import os

    import pandas as pd
    spec = importlib.util.spec_from_file_location(
        "eval_spc", os.path.join(os.path.dirname(__file__), "..", "scripts", "eval_spc.py"))
    es = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(es)

    def stream(sid, ftype, onset, signals, gate):
        return pd.DataFrame({"stream_id": sid, "fault_type": ftype, "onset_hours": onset, "cadence_h": 6.0, "n_fov": 1,
                             "visit_idx": range(len(signals)), "hours": [6.0 * i for i in range(len(signals))],
                             "signals": signals, "gate_pass": gate})
    base = stream("b", "none", float("nan"), [[], ["X"], [], []], [True, True, False, True])
    fa = es.false_alarms(base)
    assert fa["signals"] == 1 and fa["visits"] == 4 and fa["per_100"] == 25.0 and fa["trend_eligible"] == 3

    # onset at 10 h: visits at 12 and 18 h are post-onset; the 6 h signal is a pre-onset false alarm
    f = stream("f", "growth_stall", 10.0, [[], ["X"], [], ["Y"]], [True, True, False, True])
    d = es.detection(f, "growth_stall").iloc[0]
    assert d.pre_onset_signals == 1 and d.spc_delay == 2 and d.gate_delay == 1 and d.any_delay == 1
    assert d.post_visits == 2 and d.post_eligible == 1 and d.first_codes == "Y"
