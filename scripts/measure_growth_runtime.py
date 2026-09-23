#!/usr/bin/env python3
"""
CPU runtime for culture.growth.fit_growth() on a ~20-visit segment
(cultureQC_upgrade.md §6.4 acceptance: "CPU runtime for a ~20-visit segment
recorded"). Synthetic visits (a noisy logistic series) -- this measures the
fitting code's wall time, not anything about real growth data.

Usage:
    python scripts/measure_growth_runtime.py
Outputs:
    results/growth_runtime.txt
"""

from __future__ import annotations

import os
import sys
import time
from datetime import datetime, timedelta, timezone

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from culture.growth import fit_growth

RESULTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
N_VISITS = 20
N_RUNS = 5


def _make_visit(t_hours: float, confluency: float, sd: float = 1.0, crop_frac: str = "0.25") -> dict:
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    ts = (base + timedelta(hours=t_hours)).isoformat()
    return {
        "segment_id": "S1", "timestamp": ts, "confluency_mean": confluency, "confluency_sd": sd,
        "crop_specs": [f"crop_f{crop_frac}_s1_k{i}" for i in range(3)],
    }


def main():
    rng = np.random.default_rng(0)
    hours = np.linspace(0, 190, N_VISITS)
    K, r, t0 = 90.0, 0.045, 90.0
    y = K / (1.0 + np.exp(-r * (hours - t0))) + rng.normal(0, 2.0, len(hours))
    visits = [_make_visit(h, c) for h, c in zip(hours, y)]

    fit_growth(visits, target_pct=80.0, seed=0, n_boot=500)  # warmup

    times = []
    for _ in range(N_RUNS):
        t_start = time.perf_counter()
        fit_growth(visits, target_pct=80.0, seed=0, n_boot=500)
        times.append(time.perf_counter() - t_start)

    median = sorted(times)[len(times) // 2]
    lines = [
        f"culture.growth.fit_growth() CPU runtime -- {N_VISITS}-visit synthetic segment,",
        "2 candidate models (logistic + Gompertz) + 500-resample residual bootstrap,",
        f"{N_RUNS} calls on the same input (first call after one untimed warmup call):",
        "",
        *(f"  run {i + 1}: {t:.3f} s" for i, t in enumerate(times)),
        "",
        f"median: {median:.3f} s",
    ]
    os.makedirs(RESULTS_DIR, exist_ok=True)
    path = os.path.join(RESULTS_DIR, "growth_runtime.txt")
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"\nwrote {path}")


if __name__ == "__main__":
    main()
