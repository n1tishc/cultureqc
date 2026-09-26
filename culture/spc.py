"""
cultureqc.spc — SPC monitors on per-visit residuals (A6 minimal;
cultureQC_upgrade_spec.md §2A.7, §9.1).

Residuals, not raw series: each is a standardised z per trend-eligible visit
(growth: one-step-ahead (observed − expected)/predictive SD; anomaly: A4's
per-bin z; failure class: calibrated probability vs its normal reference).
None marks a visit with no residual (too few prior visits, quality-gate
failure), which the monitors skip without updating.

Monitors, one-sided, each with its own reason code:
  - EWMA  E_t = λ z_t + (1 − λ) E_{t−1}, E_0 = 0, signal when E_t crosses
    ± L · sqrt(λ / (2 − λ) · (1 − (1 − λ)^{2t})) (time-varying limit, t = points since reset)
  - tabular CUSUM  S_t = max(0, S_{t−1} ± z_t − k), signal when S_t > h
A monitor restarts from zero after it signals, so repeated signals are
separate episodes.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Monitor:
    residual: str  # key into a visit's residual dict
    kind: str  # "ewma" | "cusum"
    side: str  # "upper" | "lower"
    reason: str


@dataclass(frozen=True)
class Params:
    lam: float = 0.2
    L: float = 2.86
    k: float = 0.5
    h: float = 4.0


def ewma_limit(lam: float, L: float, t: int) -> float:
    return L * math.sqrt(lam / (2.0 - lam) * (1.0 - (1.0 - lam) ** (2 * t)))


def run_monitor(z: list[float | None], mon: Monitor, p: Params) -> list[bool]:
    """Signal flags, one per entry of `z` (None: skipped, never signals)."""
    sign = 1.0 if mon.side == "upper" else -1.0
    out, stat, t = [], 0.0, 0
    for x in z:
        if x is None or (isinstance(x, float) and math.isnan(x)):
            out.append(False)
            continue
        t += 1
        if mon.kind == "ewma":
            stat = p.lam * x + (1.0 - p.lam) * stat
            fired = sign * stat > ewma_limit(p.lam, p.L, t)
        elif mon.kind == "cusum":
            stat = max(0.0, stat + sign * x - p.k)
            fired = stat > p.h
        else:
            raise ValueError(f"unknown monitor kind {mon.kind!r}")
        out.append(bool(fired))
        if fired:
            stat, t = 0.0, 0
    return out


def run_monitors(residuals: list[dict], monitors: list[Monitor], p: Params) -> list[list[str]]:
    """Per visit (in order), the reason codes of the monitors that signalled.
    `residuals[i]` maps residual name -> z or None."""
    flags = [[] for _ in residuals]
    for mon in monitors:
        fired = run_monitor([r.get(mon.residual) for r in residuals], mon, p)
        for i, f in enumerate(fired):
            if f:
                flags[i].append(f"{mon.reason}:{mon.residual}:{mon.kind}")
    return flags


def standard_monitors(class_names: list[str], growth_upper: bool = False) -> list[Monitor]:
    """The spec's residuals and reason codes (§9.1): growth below expected,
    anomaly drift, failure-class drift per class; EWMA + CUSUM each.
    `growth_upper` adds GROWTH_ABOVE_EXPECTED (not in the spec)."""
    mons = []
    for kind in ("ewma", "cusum"):
        mons.append(Monitor("growth", kind, "lower", "GROWTH_BELOW_EXPECTED"))
        mons.append(Monitor("anomaly", kind, "upper", "ANOMALY_DRIFT"))
        for c in class_names:
            mons.append(Monitor(f"class_{c}", kind, "upper", "FAILURE_CLASS_DRIFT"))
        if growth_upper:
            mons.append(Monitor("growth", kind, "upper", "GROWTH_ABOVE_EXPECTED"))
    return mons
