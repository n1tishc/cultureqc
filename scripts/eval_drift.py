"""
A7 — minimal instrument-drift monitor on the replay fleet
(cultureQC_upgrade_spec.md §2A.8, §10; V7). Method: culture/drift.py.

Inputs: A6's per-visit table (cache/spc/residuals.parquet: every A2 stream,
cadence and FOV cell) for visit times, anomaly z, gate result and per-flask
SPC signals (A6 monitors at configs/spc.yaml's limits); exposure from
cache/quality.parquet (every visit, gate failures included).

Fleets (one instrument each, flasks aligned on hours since start), per split
and cadence × FOV cell:
  - normal:  all base streams of the split
  - dimming: every flask's lamp-dimming twin (common onset 40 h)
  - single:  the normal fleet with one flask replaced by its contamination
             or growth-stall twin (one fleet per fault stream)

Reference and limits come from tuning only: the expected exposure change vs
age from tuning base-sequence frames; population mean/SD from the tuning
normal fleet (n_fov = 1; the population inputs are per frame, so FOV count
does not change them); limit multiplier c = the smallest on the grid with no
INSTRUMENT_DRIFT window on the tuning normal fleets (λ = 0.2, L = 2.86·c).
That selection has little power (one population series per cadence); it is
reported as such.

Counting rules (fixed before any held-out run):
  - per-flask culture flags = A6 SPC signals (ANOMALY_DRIFT,
    FAILURE_CLASS_DRIFT, GROWTH_BELOW_EXPECTED). Suppression is applied to all
    of them (spec §10 names anomaly-drift flags only; the others are a spec
    extension, shown per code so the spec-scope result stays visible).
  - REIMAGE (quality-gate failure) is an image action, not a culture flag: it
    is never suppressed and not counted in V7's culture-flag rule, but it is
    reported next to the verdict. Rolling N REIMAGEs into one instrument
    action is a B5/B6 decision-logic question.
  - post-onset = visit hours > onset_hours.
  - V7 (a), dimming: INSTRUMENT_DRIFT active in some window ending after
    onset in every held-out cell, and no unsuppressed post-onset
    ANOMALY_DRIFT flag on the dimming fleet (spec scope; the all-codes count
    is shown as the extension).
  - V7 (b), single-flask faults: no INSTRUMENT_DRIFT window in any held-out
    single-flask fleet, none of the fault flask's flags suppressed, and the
    fault flask has an unsuppressed post-onset flag (SPC or REIMAGE). Whether
    SPC itself catches the fault is A6's result.
  - drift delay = end of the first active window ending after onset, minus onset (h).

Usage:
    python scripts/eval_drift.py --cache-dir cache
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import sys
import time

import numpy as np
import pandas as pd
import yaml

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from culture.drift import (Reference, episodes, ewma_state, fit_reference, population_series,  # noqa: E402
                           relative_log, suppressed)
from culture.spc import Params, standard_monitors  # noqa: E402

LAM = 0.2
L0 = 2.86
GRID_C = [1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0]
BASELINE_H = 24.0
REF_BIN_H = 6.0
MIN_FLASKS = 5  # per reference bin and per population window
INPUTS = {"exposure": "two", "anomaly": "upper"}  # population input -> EWMA side
SINGLE_TYPES = ("contamination_onset", "growth_stall")


def _log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def _load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(REPO, "scripts", f"{name}.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# -- inputs -----------------------------------------------------------------------

def build_reference(cache_dir: str, flasks: set[str]) -> Reference:
    frames = pd.read_csv(os.path.join(cache_dir, "sidecars", "c2c12_frames.csv"))
    images = pd.read_parquet(os.path.join(cache_dir, "images.parquet"), columns=["image_sha256", "sequence_id", "frame_idx"])
    q = pd.read_parquet(os.path.join(cache_dir, "quality.parquet"), columns=["image_sha256", "exposure_mean"])
    f = frames[frames.sequence_id.isin(flasks)].merge(images, on=["sequence_id", "frame_idx"]).merge(q, on="image_sha256")
    rel = relative_log(f.exposure_mean, f.hours_since_start, f.sequence_id, BASELINE_H)
    return fit_reference(rel, f.hours_since_start, f.sequence_id, BASELINE_H, REF_BIN_H, MIN_FLASKS)


def per_visit(cache_dir: str) -> pd.DataFrame:
    """A6 visits + A6 SPC signals (list of codes per visit) + per-flask log
    exposure relative to its baseline."""
    spc = _load("eval_spc")
    res = pd.read_parquet(os.path.join(cache_dir, "spc", "residuals.parquet"))
    q = pd.read_parquet(os.path.join(cache_dir, "quality.parquet"), columns=["image_sha256", "exposure_mean"])
    res = res.merge(q, on="image_sha256", how="left")
    cfg = yaml.safe_load(open(os.path.join(REPO, "configs", "spc.yaml")))
    p = Params(lam=cfg["params"]["ewma_lambda"], L=cfg["params"]["ewma_L"], k=cfg["params"]["cusum_k"],
               h=cfg["params"]["cusum_h"])
    std, _ = spc.standardise(res)  # same tuning scales as A6 (recomputed from the same table)
    sig = spc.run_all(std, standard_monitors(spc.CLASSES), p)
    sig["rel"] = np.nan
    for _, g in sig.groupby(["stream_id", "cadence_h", "n_fov"]):
        sig.loc[g.index, "rel"] = relative_log(g.exposure_mean, g.hours, g.stream_id, BASELINE_H)
    sig["anomaly"] = sig.anomaly_z  # unmasked: gate failures included
    sig["flask"] = sig.base_sequence_id
    return sig


def with_exposure(sig: pd.DataFrame, ref: Reference, per_flask: dict[str, Reference] | None = None) -> pd.DataFrame:
    """Exposure z from `ref`, or from `per_flask[flask]` where given (leave-one-flask-out references)."""
    out = sig.copy()
    exp, sd = ref.at(out.hours.to_numpy())
    out["exposure"] = (out.rel - exp) / sd
    for fl, r in (per_flask or {}).items():
        m = out.flask == fl
        e, s = r.at(out.hours[m].to_numpy())
        out.loc[m, "exposure"] = (out.rel[m] - e) / s
    return out


def fleets(v: pd.DataFrame, split: str) -> dict[str, pd.DataFrame]:
    s = v[v.split == split]
    base = s[s.fault_type == "none"]
    out = {"normal": base, "dimming": s[s.fault_type == "lamp_dimming"]}
    for sid in sorted(s[s.fault_type.isin(SINGLE_TYPES)].stream_id.unique()):
        f = s[s.stream_id == sid]
        out[f"single:{sid}"] = pd.concat([base[base.flask != f.flask.iloc[0]], f])
    return out


# -- population monitor --------------------------------------------------------------

def population(fleet: pd.DataFrame, cadence: float) -> pd.DataFrame:
    out = None
    for name in INPUTS:
        ps = population_series(fleet, name, cadence, BASELINE_H, MIN_FLASKS).rename(columns={"median": name})
        out = ps if out is None else out.merge(ps[["window", name]], on="window")
    return out


def pop_scales(v: pd.DataFrame) -> dict:
    parts = []
    for cad in sorted(v.cadence_h.unique()):
        f = v[(v.split == "tuning") & (v.fault_type == "none") & (v.cadence_h == cad) & (v.n_fov == 1)]
        parts.append(population(f, cad))
    allp = pd.concat(parts)
    return {n: {"mean": float(allp[n].mean()), "sd": float(allp[n].std(ddof=1)), "n_windows": int(allp[n].notna().sum())}
            for n in INPUTS}


def flask_spread(v: pd.DataFrame) -> dict:
    """Per input, the median over tuning normal windows (n_fov = 1, both
    cadences, from baseline_hours) of the SD across flasks of their value in
    the window. Used only by the post-hoc diagnostic."""
    out = {}
    for n in INPUTS:
        sds = []
        for cad in sorted(v.cadence_h.unique()):
            f = v[(v.split == "tuning") & (v.fault_type == "none") & (v.cadence_h == cad) & (v.n_fov == 1)
                  & (v.hours >= BASELINE_H)].dropna(subset=[n]).copy()
            f["w"] = np.floor(f.hours / cad)
            last = f.sort_values("hours").groupby(["w", "flask"]).tail(1)
            sds += [float(g[n].std(ddof=1)) for _, g in last.groupby("w") if len(g) >= MIN_FLASKS]
        out[n] = float(np.median(sds))
    return out


def monitor(fleet: pd.DataFrame, cadence: float, scales: dict, c: float, spread: dict | None = None) -> pd.DataFrame:
    """Population EWMAs. Default z = (median − tuning mean) / tuning SD of the
    population series. With `spread` (post-hoc diagnostic): z = (median −
    tuning mean) / (1.2533 · spread / sqrt(n active flasks)), the standard
    error of a median of n independent flasks."""
    pop = population(fleet, cadence)
    active = np.zeros(len(pop), dtype=bool)
    for n, side in INPUTS.items():
        if spread is None:
            z = (pop[n] - scales[n]["mean"]) / scales[n]["sd"]
        else:
            z = (pop[n] - scales[n]["mean"]) / (1.2533 * spread[n] / np.sqrt(pop.n_flasks.clip(lower=1)))
        stats, hit = ewma_state([None if pd.isna(x) else float(x) for x in z], LAM, L0 * c, side)
        pop[f"{n}_z"], pop[f"{n}_ewma"], pop[f"{n}_hit"] = z, stats, hit
        active |= np.array(hit)
    pop["active"] = active
    return pop


def run_variant(v: pd.DataFrame, cells, spread: dict | None = None, c_fixed: float | None = None):
    """Scales from tuning, c from the tuning normal fleets (unless fixed), then every held-out fleet × cell."""
    scales = pop_scales(v)
    tune = fleets(v, "tuning")["normal"]
    sweep = []
    for c in GRID_C:
        pops = [monitor(tune[(tune.cadence_h == cad) & (tune.n_fov == nf)], cad, scales, c, spread) for cad, nf in cells]
        sweep.append({"c": c, "L": L0 * c, "episodes": sum(episodes(list(p.active)) for p in pops),
                      "active_windows": sum(int(p.active.sum()) for p in pops)})
    sweep = pd.DataFrame(sweep)
    ok = sweep[sweep.episodes == 0]
    c = c_fixed if c_fixed is not None else (float(ok.c.min()) if len(ok) else float(sweep.c.max()))
    results = {}
    for name, fleet in fleets(v, "heldout").items():
        for cad, nf in cells:
            f = fleet[(fleet.cadence_h == cad) & (fleet.n_fov == nf)]
            pop = monitor(f, cad, scales, c, spread)
            results[(name, cad, nf)] = (pop, evaluate(f, pop, cad))
    return scales, sweep, c, results


def evaluate(fleet: pd.DataFrame, pop: pd.DataFrame, cadence: float) -> pd.DataFrame:
    """Per visit: flags, suppression, post-onset."""
    act = set(pop.window[pop.active])
    f = fleet.copy()
    f["suppressed"] = suppressed(f.hours, cadence, act)
    f["post"] = f.hours > f.onset_hours.fillna(np.inf)
    return f


# -- main --------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cache-dir", default="cache")
    ap.add_argument("--split", default=os.path.join(REPO, "results", "replay_fleet_split.csv"))
    ap.add_argument("--config-out", default=os.path.join(REPO, "configs", "drift.yaml"))
    ap.add_argument("--out", default=os.path.join(REPO, "results"))
    args = ap.parse_args()

    split = pd.read_csv(args.split)
    tuning = set(split[split.split == "tuning"].sequence_id)
    ref = build_reference(args.cache_dir, tuning)
    loo = {fl: build_reference(args.cache_dir, tuning - {fl}) for fl in sorted(tuning)}
    _log(f"reference knots {len(ref.hours)} ({ref.hours[0]:g}–{ref.hours[-1]:g} h)")
    v = per_visit(args.cache_dir)
    cells = sorted(v.groupby(["cadence_h", "n_fov"]).groups)
    ve = with_exposure(v, ref)
    scales, sweep, c, results = run_variant(ve, cells)  # the V7 verdict (as pre-registered)
    _log(f"chosen c = {c} (L = {L0 * c:.2f})")
    # checked after the held-out run: tuning flasks scored against leave-one-flask-out references
    loo_sd = pop_scales(with_exposure(v, ref, loo))["exposure"]["sd"]
    # post-hoc diagnostic (not a verdict): population z on the standard error of a median of n flasks
    spread = flask_spread(ve)
    diag = run_variant(ve, cells, spread=spread, c_fixed=c)[3]

    doc = {
        "params": {"ewma_lambda": LAM, "ewma_L": round(L0 * c, 4), "limit_multiplier_c": c},
        "inputs": {n: {"side": s} for n, s in INPUTS.items()},
        "baseline_hours": BASELINE_H,
        "min_flasks_per_window": MIN_FLASKS,
        "window": "visit cadence",
        "exposure_reference": {"bin_hours": REF_BIN_H, "hours": [round(h, 2) for h in ref.hours],
                               "expected_log_change": [round(e, 5) for e in ref.expected],
                               "sd": [round(s, 5) for s in ref.sd],
                               "source": "tuning base-sequence frames (hourly), results/replay_fleet_split.csv"},
        "population_standardisation": {n: {k: (round(x, 5) if isinstance(x, float) else x) for k, x in s.items()}
                                       for n, s in scales.items()},
        "population_standardisation_source": "tuning normal fleet population series (window-to-window SD); "
                                             "known flaw, see results/drift_summary.md (post-hoc diagnostic)",
        "selection": {"rule": f"smallest c on {GRID_C} (L = {L0}·c) with no INSTRUMENT_DRIFT window on the tuning "
                              "normal fleets (all cadence × FOV cells)", "chosen_c": c, "met": bool((sweep.episodes == 0).any())},
        "suppression": "all per-flask SPC culture flags in windows with INSTRUMENT_DRIFT active (spec §10: anomaly "
                       "drift; other codes are an extension); REIMAGE never suppressed",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    with open(args.config_out, "w") as fh:
        yaml.safe_dump(doc, fh, sort_keys=False, allow_unicode=True)
    write_summary(results, cells, sweep, doc, ref, scales, args.out, loo_sd, diag, spread)
    plots(results, doc, args.out)


def _flags(e: pd.DataFrame, codes_prefix: str | None = None) -> pd.Series:
    if codes_prefix is None:
        return e.signals.apply(bool)
    return e.signals.apply(lambda s: any(x.startswith(codes_prefix) for x in s))


def v7(results, cells) -> dict:
    """The docstring's V7 rules on one set of held-out results, clause by clause."""
    out = {"a_raised": True, "a_anomaly_unsup": 0, "all_unsup": 0, "normal_episodes": {}, "normal_windows": {},
           "normal_first_end": {}, "delay_h": {}, "normal_suppressed": 0,
           "b_no_drift": True, "b_none_suppressed": True, "b_flagged": {}}
    for cad, nf in cells:
        npop, ne = results[("normal", cad, nf)]
        dpop, de = results[("dimming", cad, nf)]
        onset = float(de.onset_hours.iloc[0])
        post_active = dpop[(dpop.end > onset) & dpop.active]
        p = de[de.post]
        out["a_raised"] &= bool(len(post_active))
        out["a_anomaly_unsup"] += int((_flags(p, "ANOMALY_DRIFT") & ~p.suppressed).sum())
        out["all_unsup"] += int((_flags(p) & ~p.suppressed).sum())
        out["normal_episodes"][(cad, nf)] = episodes(list(npop.active))
        out["normal_windows"][(cad, nf)] = int(npop.active.sum())
        out["normal_first_end"][(cad, nf)] = float(npop.end[npop.active].iloc[0]) if npop.active.any() else None
        out["normal_suppressed"] += int((_flags(ne) & ne.suppressed).sum())
        out["delay_h"][(cad, nf)] = float(post_active.end.iloc[0] - onset) if len(post_active) else None
    for name in sorted(k for k in {r[0] for r in results} if k.startswith("single:")):
        sid = name.split(":", 1)[1]
        for cad, nf in cells:
            pop, e = results[(name, cad, nf)]
            ff = e[e.stream_id == sid].sort_values("visit_idx")
            p = ff[ff.post]
            out["b_no_drift"] &= not pop.active.any()
            out["b_none_suppressed"] &= int((_flags(ff) & ff.suppressed).sum()) == 0
            ft = ff.fault_type.iloc[0]
            got = bool(((_flags(p) & ~p.suppressed) | ~p.gate_pass).any())
            n_ok, n = out["b_flagged"].get(ft, (0, 0))
            out["b_flagged"][ft] = (n_ok + got, n + 1)
    out["a"] = out["a_raised"] and out["a_anomaly_unsup"] == 0
    out["b"] = out["b_no_drift"] and out["b_none_suppressed"] and all(k == n for k, n in out["b_flagged"].values())
    return out


def _cell(k):
    return f"{k[0]:g} h/{k[1]} FOV"


def write_summary(results, cells, sweep, doc, ref, scales, out, loo_sd, diag, spread):
    c = doc["selection"]["chosen_c"]
    vv = v7(results, cells)
    lines = ["# A7: instrument-drift monitor (minimal)", "",
             f"Generated {doc['generated_at']} by `scripts/eval_drift.py`. C2C12 images: Ker et al., *Sci Data* 5:180237 "
             "(2018), CC BY 4.0; visits, lamp dimming and single-flask faults are simulated (replay).", "",
             "**Method** (`culture/drift.py`): flasks aligned on hours since start. Per visit, exposure = log exposure "
             f"relative to the flask's own first {BASELINE_H:g} h, minus the expected change at that age, over the "
             "expected SD (reference from tuning base-sequence frames), and A4's anomaly z. Every visit counts, gate "
             "failures included. Per window (width = cadence), the median over active flasks (≥ "
             f"{MIN_FLASKS}) of each, standardised by the mean/SD of the tuning normal fleet's population series; EWMA "
             f"(λ = {LAM}) on each (exposure two-sided, anomaly upper). INSTRUMENT_DRIFT is active in every window where "
             "either EWMA is beyond its limit; per-flask SPC flags (A6) in active windows are kept but marked "
             "suppressed.", "",
             "Exposure reference (expected log change vs age; 6 h bins, flat beyond the last bin with ≥ "
             f"{MIN_FLASKS} tuning flasks): " + ", ".join(f"{h:g} h {e:+.3f} (SD {s:.3f})" for h, e, s in
                                                           zip(ref.hours, ref.expected, ref.sd)) + ".", "",
             "Population standardisation (tuning normal fleet, n_fov = 1, both cadences): " + "; ".join(
                 f"{n} mean {s['mean']:+.3f}, SD {s['sd']:.3f} ({s['n_windows']} windows)" for n, s in scales.items())
             + ".", "",
             "## Limit selection (tuning normal fleets only)", "",
             f"{doc['selection']['rule']}. Little power: one population series per cadence cell, so zero tuning alarms "
             "at the smallest c says little about held-out behaviour.", "",
             "| c | L | tuning normal: drift episodes | active windows |", "|---|---|---|---|"]
    for r in sweep.itertuples():
        lines.append(f"| {r.c:g}{' ← chosen' if r.c == c else ''} | {r.L:.2f} | {r.episodes} | {r.active_windows} |")

    lines += ["", f"## V7 on the held-out fleet (L = {L0 * c:.2f})", "",
              "Pass (spec): dimming → `INSTRUMENT_DRIFT`, not per-flask flags; single-flask faults still flagged. "
              "Counting rules are in the script docstring, fixed before the held-out run; this is that run.", "",
              "### Normal and dimming fleets", "",
              "| cadence | FOVs | normal: drift episodes (windows) | normal: first drift window ends | normal: flags "
              "suppressed | dimming: drift delay after onset | post-onset SPC flags: anomaly drift (unsuppressed / "
              "total) | all codes (unsuppressed / total) | post-onset REIMAGE visits (flasks) |",
              "|---|---|---|---|---|---|---|---|---|"]
    for cad, nf in cells:
        k = (cad, nf)
        _, ne = results[("normal", cad, nf)]
        _, de = results[("dimming", cad, nf)]
        p = de[de.post]
        a_all, a_un = _flags(p, "ANOMALY_DRIFT"), _flags(p, "ANOMALY_DRIFT") & ~p.suppressed
        f_all, f_un = _flags(p), _flags(p) & ~p.suppressed
        reim = p[~p.gate_pass]
        first = vv["normal_first_end"][k]
        delay = vv["delay_h"][k]
        lines.append(f"| {cad:g} h | {nf} | {vv['normal_episodes'][k]} ({vv['normal_windows'][k]}) | "
                     f"{f'{first:g} h' if first is not None else '—'} | {int((_flags(ne) & ne.suppressed).sum())} | "
                     f"{f'{delay:g} h' if delay is not None else 'not raised'} | {int(a_un.sum())} / {int(a_all.sum())} "
                     f"| {int(f_un.sum())} / {int(f_all.sum())} | {len(reim)} ({reim.flask.nunique()}/"
                     f"{de.flask.nunique()}) |")

    lines += ["", "### Single-flask fault fleets (13 normal flasks + 1 fault twin)", "",
              "| fault stream | cadence | FOVs | drift windows | fault flask post-onset: SPC flags (suppressed) | "
              "REIMAGE visits | first flag after onset (visits) |", "|---|---|---|---|---|---|---|"]
    for name in sorted(k for k in {r[0] for r in results} if k.startswith("single:")):
        for cad, nf in cells:
            pop, e = results[(name, cad, nf)]
            sid = name.split(":", 1)[1]
            ff = e[e.stream_id == sid].sort_values("visit_idx")
            p = ff[ff.post]
            spc_f = _flags(p)
            flagged = (spc_f & ~p.suppressed) | ~p.gate_pass
            first = next((i + 1 for i, x in enumerate(flagged) if x), None)
            lines.append(f"| {ff.fault_type.iloc[0]}: {sid.replace('c2c12_', '').replace('_Data', '')} | {cad:g} h | {nf} "
                         f"| {int(pop.active.sum())} | {int(spc_f.sum())} ({int((spc_f & p.suppressed).sum())}) | "
                         f"{int((~p.gate_pass).sum())} | {first if first else '—'} |")

    flagged_txt = "; ".join(f"{t} {k}/{n} streams × cells" for t, (k, n) in sorted(vv["b_flagged"].items()))
    lines += ["", "### Verdict", "",
              f"- **V7 (a) dimming: {'pass' if vv['a'] else 'fail'} by the rule, but not evidence.** INSTRUMENT_DRIFT "
              f"was raised after onset in every cell ({', '.join(f'{_cell(k)} {d:g} h' for k, d in vv['delay_h'].items() if d is not None)}) "
              f"and {vv['a_anomaly_unsup']} post-onset anomaly-drift flags were left unsuppressed ({vv['all_unsup']} of "
              "any SPC code). The held-out **normal** fleet was in drift from the same windows (first drift window "
              "ends " + ", ".join(f"{_cell(k)} {v:g} h" for k, v in vv["normal_first_end"].items() if v is not None)
              + "), so the monitor did not tell dimming from normal. The suppression is from the same false drift.",
              f"- **V7 (b) single-flask: {'pass' if vv['b'] else 'fail'}.** By clause: no drift window "
              f"{'pass' if vv['b_no_drift'] else 'fail'} (A7's own failure: every single-flask fleet inherits the "
              f"normal fleet's false drift); nothing on the fault flask suppressed "
              f"{'pass' if vv['b_none_suppressed'] else 'fail'}; fault flask flagged after onset: {flagged_txt} "
              "(inherited from A6: SPC catches neither fault, REIMAGE catches contamination, nothing flags the "
              "stall, so this clause fails whatever the drift monitor does).",
              f"- Normal fleet false alarms: {sum(vv['normal_episodes'].values())} drift episodes across cells; "
              f"{vv['normal_suppressed']} real per-flask SPC flags on normal flasks were hidden by them.", "",
              "**REIMAGE is not suppressed and not in the culture-flag count.** Under dimming, most flasks get REIMAGE "
              "after onset (column above): one per-flask image action each, which is what V7 wants to avoid. "
              "Rolling them into one instrument action while INSTRUMENT_DRIFT is active is a B5/B6 decision-logic "
              "question (§11.1 currently ranks REIMAGE first).", "",
              "### Why the normal fleet drifts", "",
              f"The tuning population SD ({scales['exposure']['sd']:.3f}, exposure) is the window-to-window SD of one "
              "fleet's median. Because the reference is itself the median over the tuning flasks, that median sits "
              "near zero by construction, and its SD says nothing about how far another fleet's median can sit. The "
              "held-out normal median sits at about −0.2 per-flask z, far beyond that SD, so the EWMA drifts out and "
              "stays out. This was checked after the held-out run: scoring each tuning flask against a reference "
              f"fitted without it gives SD {loo_sd:.3f}, so in-sample fitting is not the cause.", "",
              "## Post-hoc diagnostic (not a verdict; chosen after seeing held-out results)", "",
              "Candidate B5 design change: standardise each window's median by the standard error of a median of n "
              "independent flasks, 1.2533 · s / √n, where s is the between-flask SD within a window on the tuning "
              "normal fleet (" + ", ".join(f"{n} s = {v:.3f}" for n, v in spread.items()) + f"). Same λ and L "
              f"({L0 * c:.2f}, not reselected), both inputs. It assumes flasks are independent; tuning flasks cluster "
              "by experiment (per-flask mean exposure z up to +1.7 in 090325), so the effective n is below the "
              "count and this SE is optimistic.", "",
              "| cadence | FOVs | normal: drift episodes (windows; by input) | dimming: drift delay after onset | "
              "dimming: pre-onset drift windows | single-flask fleets with a drift window |", "|---|---|---|---|---|---|"]
    for cad, nf in cells:
        npop, _ = diag[("normal", cad, nf)]
        dpop, de = diag[("dimming", cad, nf)]
        onset = float(de.onset_hours.iloc[0])
        post_active = dpop[(dpop.end > onset) & dpop.active]
        by_input = ", ".join(f"{n} {int(npop[f'{n}_hit'].sum())}" for n in INPUTS)
        singles = [k for k in diag if k[0].startswith("single:") and k[1:] == (cad, nf)]
        n_single = sum(bool(diag[k][0].active.any()) for k in singles)
        lines.append(f"| {cad:g} h | {nf} | {episodes(list(npop.active))} ({int(npop.active.sum())}; {by_input}) | "
                     f"{f'{post_active.end.iloc[0] - onset:g} h' if len(post_active) else 'not raised'} | "
                     f"{int(dpop[(dpop.end <= onset) & dpop.active].shape[0])} | {n_single}/{len(singles)} |")

    lines += ["", "## Notes", "",
              "- The easiest case for a population monitor: every flask dims at the same age, with the same ramp, and "
              "flasks are age-aligned. Staggered flask ages and gradual real drift are untested.",
              "- Every stream uses replay seed 0, so all flasks share visit times; at 6 h one window (42–48 h) has no "
              "visits, which splits one continuous drift into two episodes.",
              "- Exposure and anomaly are per frame, so the 1- and 3-FOV cells share the population series; they "
              "differ only in the per-flask growth flags.",
              "- A drift that starts inside a flask's first 24 h shifts its own baseline and is invisible for that "
              "flask.",
              "- Fleet view: `results/drift_fleet.png` (held-out, 6 h, 1 FOV, the verdict run).", ""]
    with open(os.path.join(out, "drift_summary.md"), "w") as fh:
        fh.write("\n".join(lines))
    print("\n".join(lines))


def plots(results, doc, out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    L = doc["params"]["ewma_L"]
    fig, axes = plt.subplots(3, 2, figsize=(12, 9), sharex=True)
    for col, name in enumerate(("normal", "dimming")):
        pop, e = results[(name, 6.0, 1)]
        ax = axes[0][col]
        for fl, g in e.sort_values("hours").groupby("flask"):
            ax.plot(g.hours, g.exposure, color="grey", lw=0.6, alpha=0.6)
        ax.plot(pop.end, pop.exposure, "k-o", ms=3, label="fleet median (per window)")
        ax.set(ylabel="exposure z (per flask)", title=f"held-out {name} fleet, 6 h, 1 FOV")
        ax.legend(fontsize=7)
        ax = axes[1][col]
        t = pop.exposure_z.notna().cumsum().to_numpy()
        lim = L * np.sqrt(LAM / (2 - LAM) * (1 - (1 - LAM) ** (2 * t)))
        ax.plot(pop.end, pop.exposure_ewma, "-o", ms=3, label="EWMA exposure (two-sided)")
        ax.plot(pop.end, pop.anomaly_ewma, "-s", ms=3, label="EWMA anomaly (upper)")
        ax.plot(pop.end, lim, "r--", lw=0.8, label="± limit")
        ax.plot(pop.end, -lim, "r--", lw=0.8)
        for r in pop[pop.active].itertuples():
            ax.axvspan(r.start, r.end, color="orange", alpha=0.25, lw=0)
        ax.set(ylabel="population EWMA")
        ax.legend(fontsize=7)
        ax = axes[2][col]
        flasks = sorted(e.flask.unique())
        for i, fl in enumerate(flasks):
            g = e[e.flask == fl]
            s = g[g.signals.apply(bool)]
            ax.plot(s[~s.suppressed].hours, [i] * (~s.suppressed).sum(), "o", color="tab:red", ms=5)
            ax.plot(s[s.suppressed].hours, [i] * s.suppressed.sum(), "o", mfc="none", color="tab:red", ms=5)
            r = g[~g.gate_pass]
            ax.plot(r.hours, [i] * len(r), "x", color="tab:blue", ms=4)
        ax.set_yticks(range(len(flasks)), [f.replace("c2c12_", "").replace("_exp1", "").replace("_Data", "")
                                           for f in flasks], fontsize=6)
        ax.set(xlabel="hours since flask start", ylabel="flask")
        ax.set_title("per-flask: ● SPC flag, ○ suppressed, × REIMAGE", fontsize=8)
        if name == "dimming":
            for a in axes[:, col]:
                a.axvline(float(e.onset_hours.iloc[0]), color="black", ls=":", lw=0.8)
    fig.tight_layout()
    fig.savefig(os.path.join(out, "drift_fleet.png"), dpi=110)
    plt.close(fig)


if __name__ == "__main__":
    main()
