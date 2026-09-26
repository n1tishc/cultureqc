"""
A6 — minimal SPC on residuals (cultureQC_upgrade_spec.md §2A.7, §9.1; V6).

1. Residuals (cached in cache/spc/residuals.parquet; ~10 min, parallel):
   every A2 fleet stream (same cadences, FOVs, crop size, seed, split),
   per visit: growth z from culture.growth.one_step_ahead_series (skips
   quality-failed visits), anomaly z from A4 (cache/anomaly/scores.parquet),
   calibrated class probabilities, quality gate result, fault ground truth.
2. Standardise each residual by its mean/SD on trend-eligible visits of the
   *tuning* normal streams (all cells pooled); class residual = (p − mean)/SD.
3. Tuning: λ = 0.2 and k = 0.5 fixed; one multiplier c scales both limits
   (L = 2.86·c, h = 4·c). Chosen c = the smallest on the grid whose combined
   false-alarm rate on the tuning normal base streams (all cells pooled) is
   ≤ 1 per 100 flask-visits. Fault detection plays no part in the choice.
4. Report on held-out only, per cadence × FOV cell.

Counting rules (fixed before any held-out run):
  - false alarms: visits with ≥ 1 signal from the V6 monitor set, on base
    (normal) streams, per 100 visits (all visits; trend-eligible visits also
    shown). Fault twins repeat their base before onset, so they are not
    counted again; a twin's pre-onset signals are listed separately.
  - monitors restart after a signal.
  - detection: first signal at a visit after onset (visit hours since stream
    start > onset_hours); delay = its index among post-onset visits, the
    first post-onset visit being 1. A stream with no trend-eligible
    post-onset visit counts as "no SPC data", not dropped.
  - quality gate: REIMAGE (gate fail) and "first flag of any kind" are shown
    next to SPC, never counted as SPC detection.

Usage:
    python scripts/eval_spc.py --cache-dir cache            # residuals if missing, then evaluate
    python scripts/eval_spc.py --cache-dir cache --recompute
"""

from __future__ import annotations

import argparse
import importlib.util
import math
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd
import yaml

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from culture.spc import Monitor, Params, ewma_limit, run_monitor, run_monitors, standard_monitors  # noqa: E402

CLASSES = ["contamination_suspected", "detachment", "image_quality"]
GRID_C = [1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.8, 2.0, 2.25, 2.5, 3.0]
BASE = Params(lam=0.2, L=2.86, k=0.5, h=4.0)
MAX_FA_PER_100 = 1.0
V6_TYPES = ("contamination_onset", "growth_stall")


def _log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def _load_fleet():
    spec = importlib.util.spec_from_file_location("replay_fleet", os.path.join(REPO, "scripts", "replay_fleet.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# -- 1. residuals ---------------------------------------------------------------

_W = {}


def _init_worker(cache_dir):
    from culture.cache import Cache
    from culture.replay import ReplayTables
    _W["fleet"] = _load_fleet()
    _W["cache"] = Cache(cache_dir)
    _W["tables"] = ReplayTables(_W["cache"])
    _W["manifest"] = pd.read_parquet(os.path.join(cache_dir, "sidecars", "fault_manifest.parquet"))
    sc = pd.read_parquet(os.path.join(cache_dir, "anomaly", "scores.parquet"))
    _W["anomaly"] = dict(zip(sc.image_sha256, sc.z_binned))


def _stream_residuals(job):
    from culture.growth import one_step_ahead_series
    spec, cadence, n_fov = job
    f = _W["fleet"]
    visits = f._replay(_W["cache"], _W["tables"], _W["manifest"], spec, f.SEED, cadence, n_fov, f.CROP_FRAC)
    preds = {p.visit_id: p for p in one_step_ahead_series(visits, seed=f.SEED)}
    t0 = pd.Timestamp(visits[0]["timestamp"])
    rows = []
    for i, v in enumerate(visits):
        p = preds[v["visit_id"]]
        sha = v["image_sha256"][0]
        row = {"stream_id": spec["stream_id"], "base_sequence_id": spec["base_sequence_id"], "split": spec["split"],
               "fault_type": spec["fault_type"], "onset_hours": spec["onset_hours"], "cadence_h": cadence,
               "n_fov": n_fov, "visit_idx": i, "timestamp": v["timestamp"],
               "hours": (pd.Timestamp(v["timestamp"]) - t0).total_seconds() / 3600.0, "image_sha256": sha,
               "gate_pass": bool(v["quality"]["pass"]), "confluency": v["confluency_mean"],
               "growth_status": p.status, "growth_z": p.z if p.status == "OK" else np.nan,
               "expected": p.expected, "predictive_sd": p.predictive_sd,
               "anomaly_z": _W["anomaly"].get(sha, np.nan),
               "severity": v.get("fault", {}).get("severity", np.nan)}
        for c in CLASSES:
            row[f"p_{c}"] = (v["class_probs"] or {}).get(c, np.nan)
        rows.append(row)
    return rows


def compute_residuals(cache_dir: str, split_path: str, workers: int) -> pd.DataFrame:
    fleet = _load_fleet()
    seqs = pd.read_csv(os.path.join(cache_dir, "sidecars", "c2c12_sequences.csv"))
    manifest = pd.read_parquet(os.path.join(cache_dir, "sidecars", "fault_manifest.parquet"))
    split = pd.read_csv(split_path).set_index("sequence_id").split.to_dict()
    specs = fleet._stream_specs(seqs, manifest, split)
    jobs = [(s, c, n) for c in fleet.CADENCES for n in fleet.N_FOVS for s in specs]
    rows = []
    with ProcessPoolExecutor(max_workers=workers, initializer=_init_worker, initargs=(cache_dir,)) as ex:
        for i, r in enumerate(ex.map(_stream_residuals, jobs, chunksize=2)):
            rows.extend(r)
            if (i + 1) % 25 == 0:
                _log(f"{i + 1}/{len(jobs)} streams")
    return pd.DataFrame(rows)


# -- 2. standardisation -----------------------------------------------------------

def standardise(res: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    ref = res[(res.split == "tuning") & (res.fault_type == "none") & res.gate_pass]
    scales = {}
    out = res.copy()
    cols = {"growth": "growth_z", "anomaly": "anomaly_z", **{f"class_{c}": f"p_{c}" for c in CLASSES}}
    for name, col in cols.items():
        x = ref[col].dropna()
        m, s = float(x.mean()), float(x.std(ddof=1))
        scales[name] = {"source_column": col, "mean": round(m, 6), "sd": round(s, 6), "n_visits": int(len(x))}
        out[name] = np.where(out.gate_pass, (out[col] - m) / s, np.nan)
    # lag-1 autocorrelation within tuning normal streams (monitor limits assume independent points)
    for name in cols:
        acs = []
        for _, g in out[(out.split == "tuning") & (out.fault_type == "none")].groupby(["stream_id", "cadence_h", "n_fov"]):
            x = g[name].dropna().to_numpy()
            if len(x) > 3 and np.std(x) > 0:
                acs.append(float(np.corrcoef(x[:-1], x[1:])[0, 1]))
        scales[name]["lag1_autocorr_median"] = round(float(np.median(acs)), 3) if acs else None
    return out, scales


# -- 3/4. monitors and metrics ------------------------------------------------------

def scaled(c: float) -> Params:
    return Params(lam=BASE.lam, L=BASE.L * c, k=BASE.k, h=BASE.h * c)


def run_all(res: pd.DataFrame, monitors: list[Monitor], p: Params) -> pd.DataFrame:
    """res plus a `signals` column (list of reason codes) per visit."""
    parts = []
    for _, g in res.groupby(["stream_id", "cadence_h", "n_fov"], sort=False):
        g = g.sort_values("visit_idx")
        resid = g[[m.residual for m in monitors]].to_dict("records")
        resid = [{k: (None if pd.isna(v) else float(v)) for k, v in r.items()} for r in resid]
        parts.append(g.assign(signals=run_monitors(resid, monitors, p)))
    return pd.concat(parts)


def false_alarms(sig: pd.DataFrame) -> dict:
    base = sig[sig.fault_type == "none"]
    n_sig = int(base.signals.apply(bool).sum())
    n_elig = int(base.gate_pass.sum())
    return {"visits": int(len(base)), "trend_eligible": n_elig, "signals": n_sig,
            "per_100": 100.0 * n_sig / max(len(base), 1), "per_100_eligible": 100.0 * n_sig / max(n_elig, 1),
            "streams": int(base.stream_id.nunique())}


def detection(sig: pd.DataFrame, fault_type: str) -> dict:
    rows = []
    for (sid, cad, nf), g in sig[sig.fault_type == fault_type].groupby(["stream_id", "cadence_h", "n_fov"]):
        g = g.sort_values("visit_idx")
        post = g[g.hours > g.onset_hours.iloc[0]].reset_index(drop=True)
        pre = g[g.hours <= g.onset_hours.iloc[0]]
        spc_idx = next((i + 1 for i, s in enumerate(post.signals) if s), None)
        gate_idx = next((i + 1 for i, ok in enumerate(post.gate_pass) if not ok), None)
        anyf = [i for i in (spc_idx, gate_idx) if i is not None]
        rows.append({"stream_id": sid, "cadence_h": cad, "n_fov": nf, "post_visits": len(post),
                     "post_eligible": int(post.gate_pass.sum()), "pre_onset_signals": int(pre.signals.apply(bool).sum()),
                     "spc_delay": spc_idx, "gate_delay": gate_idx, "any_delay": min(anyf) if anyf else None,
                     "first_codes": ";".join(post.signals.iloc[spc_idx - 1]) if spc_idx else ""})
    return pd.DataFrame(rows)


def per_monitor_fa(sig: pd.DataFrame) -> pd.Series:
    base = sig[sig.fault_type == "none"]
    codes = [c for s in base.signals for c in s]
    return pd.Series(codes, dtype=object).value_counts()


# -- main ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cache-dir", default="cache")
    ap.add_argument("--split", default=os.path.join(REPO, "results", "replay_fleet_split.csv"))
    ap.add_argument("--recompute", action="store_true")
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 2))
    ap.add_argument("--config-out", default=os.path.join(REPO, "configs", "spc.yaml"))
    ap.add_argument("--out", default=os.path.join(REPO, "results"))
    args = ap.parse_args()

    path = os.path.join(args.cache_dir, "spc", "residuals.parquet")
    if args.recompute or not os.path.exists(path):
        _log("computing residuals")
        res = compute_residuals(args.cache_dir, args.split, args.workers)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        res.to_parquet(path, index=False)
    res = pd.read_parquet(path)
    res, scales = standardise(res)

    monitors = standard_monitors(CLASSES)
    tune = res[res.split == "tuning"]
    sweep = []
    for c in GRID_C:
        sig = run_all(tune, monitors, scaled(c))
        fa = false_alarms(sig)
        det = pd.concat([detection(sig, t).assign(fault_type=t) for t in V6_TYPES])
        sweep.append({"c": c, "L": BASE.L * c, "h": BASE.h * c, "fa_per_100": fa["per_100"],
                      "detected": int(det.spc_delay.notna().sum()), "fault_runs": int(len(det))})
    sweep = pd.DataFrame(sweep)
    ok = sweep[sweep.fa_per_100 <= MAX_FA_PER_100]
    chosen_c = float(ok.c.min()) if len(ok) else float(sweep.c.max())
    p = scaled(chosen_c)
    _log(f"chosen c = {chosen_c} (L = {p.L:.3f}, h = {p.h:.2f}); tuning FA {sweep.set_index('c').fa_per_100[chosen_c]:.2f}/100")

    held = res[res.split == "heldout"]
    sig = run_all(held, monitors, p)
    extra = run_all(held, [Monitor("growth", k, "upper", "GROWTH_ABOVE_EXPECTED") for k in ("ewma", "cusum")], p)

    doc = {
        "params": {"ewma_lambda": p.lam, "ewma_L": round(p.L, 4), "cusum_k": p.k, "cusum_h": round(p.h, 4)},
        "starting_values": {"ewma_lambda": BASE.lam, "ewma_L": BASE.L, "cusum_k": BASE.k, "cusum_h": BASE.h,
                            "note": "λ and L from the spec (§2A.7); CUSUM k and h are starting values, not from the spec"},
        "selection": {"rule": f"smallest c on {GRID_C} (L = {BASE.L}·c, h = {BASE.h}·c; λ, k fixed) with combined "
                              f"false alarms ≤ {MAX_FA_PER_100} per 100 flask-visits on the tuning normal base streams "
                              "(all cadence × FOV cells pooled); fault detection not used",
                      "chosen_c": chosen_c, "met": bool(len(ok))},
        "monitors": [f"{m.reason}:{m.residual}:{m.kind}:{m.side}" for m in monitors],
        "reset_after_signal": True,
        "residual_standardisation": scales,
        "source": {"split_file": os.path.relpath(args.split, REPO), "residuals": "cache/spc/residuals.parquet"},
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    with open(args.config_out, "w") as f:
        yaml.safe_dump(doc, f, sort_keys=False)
    write_summary(res, sig, extra, sweep, doc, p, monitors, args)


def _fmt_delay(s):
    s = s.dropna()
    return f"{s.median():g}" if len(s) else "—"


def write_summary(res, sig, extra, sweep, doc, p, monitors, args):
    lines = ["# A6: SPC on residuals (minimal)", "",
             f"Generated {doc['generated_at']} by `scripts/eval_spc.py`. C2C12 images: Ker et al., *Sci Data* 5:180237 "
             "(2018), CC BY 4.0; visits are simulated from them (replay) and the faults are simulated.", "",
             "**Residuals** (per trend-eligible visit, i.e. passing the quality gate): growth = one-step-ahead "
             "(observed − expected) / predictive SD (needs 5 earlier visits); anomaly = A4's per-bin z; failure class "
             "= calibrated probability of each of contamination_suspected, detachment, image_quality. Each is "
             "standardised by its mean/SD on the tuning normal streams:", "",
             "| residual | tuning mean | tuning SD | visits | median lag-1 autocorrelation |", "|---|---|---|---|---|"]
    for name, s in doc["residual_standardisation"].items():
        lines.append(f"| {name} ({s['source_column']}) | {s['mean']:+.3f} | {s['sd']:.3f} | {s['n_visits']} | "
                     f"{s['lag1_autocorr_median']} |")
    lines += ["", "EWMA and CUSUM limits assume independent points; positive autocorrelation raises the false-alarm "
              "rate above the nominal one.", "",
              f"**Monitors:** EWMA + one-sided tabular CUSUM on each residual (growth: lower side, "
              "GROWTH_BELOW_EXPECTED; anomaly: upper, ANOMALY_DRIFT; each class: upper, FAILURE_CLASS_DRIFT); "
              f"{len(monitors)} monitors, restarted after each signal.", "",
              "## Tuning (tuning fleet only)", "",
              f"λ = {BASE.lam} and k = {BASE.k} fixed; L = {BASE.L}·c, h = {BASE.h}·c. {doc['selection']['rule']}.", "",
              "| c | L | h | false alarms / 100 visits (tuning normal) | tuning fault runs detected (not used to choose) |",
              "|---|---|---|---|---|"]
    for r in sweep.itertuples():
        mark = " ← chosen" if r.c == doc["selection"]["chosen_c"] else ""
        lines.append(f"| {r.c:g}{mark} | {r.L:.2f} | {r.h:.2f} | {r.fa_per_100:.2f} | {r.detected}/{r.fault_runs} |")
    if not doc["selection"]["met"]:
        lines += ["", f"**No grid point meets ≤ {MAX_FA_PER_100} per 100 on tuning; the largest c is used.**"]

    lines += ["", f"## V6 on the held-out fleet (L = {p.L:.2f}, h = {p.h:.2f})", "",
              "Pass (spec): ≤ 1 false alarm per 100 flask-visits; detection ≥ 90% and median delay ≤ 3 visits for "
              "contamination and growth stall. Held-out has 2 streams per fault type, so detection is 0/2, 1/2 or 2/2 "
              "per cell; 90% means 2/2. Delay counts the first visit after onset as 1.", "",
              "| cadence | FOVs | false alarms / 100 visits | per 100 trend-eligible | REIMAGE on normal visits "
              "| contamination: SPC detected | median delay | growth stall: SPC detected | median delay |",
              "|---|---|---|---|---|---|---|---|---|"]
    cells = sorted(sig.groupby(["cadence_h", "n_fov"]).groups)
    det_all = []
    for cad, nf in cells:
        s = sig[(sig.cadence_h == cad) & (sig.n_fov == nf)]
        fa = false_alarms(s)
        base = s[s.fault_type == "none"]
        dets = {t: detection(s, t) for t in V6_TYPES}
        for t, d in dets.items():
            det_all.append(d.assign(fault_type=t))
        cc, gs = dets["contamination_onset"], dets["growth_stall"]
        lines.append(f"| {cad:g} h | {nf} | {fa['per_100']:.2f} ({fa['signals']}/{fa['visits']}) | "
                     f"{fa['per_100_eligible']:.2f} | {100 * (~base.gate_pass).mean():.1f}% | "
                     f"{int(cc.spc_delay.notna().sum())}/{len(cc)} | {_fmt_delay(cc.spc_delay)} | "
                     f"{int(gs.spc_delay.notna().sum())}/{len(gs)} | {_fmt_delay(gs.spc_delay)} |")
    det_all = pd.concat(det_all)
    fa_all = false_alarms(sig)
    v6_fa = fa_all["per_100"] <= 1.0
    v6_det = all(det_all[det_all.fault_type == t].spc_delay.notna().mean() >= 0.9 for t in V6_TYPES)
    v6_delay = all((det_all[det_all.fault_type == t].spc_delay.dropna().median() <= 3)
                   if det_all[det_all.fault_type == t].spc_delay.notna().any() else False for t in V6_TYPES)
    lines += ["", f"All cells pooled: {fa_all['per_100']:.2f} false alarms per 100 visits ({fa_all['signals']}/"
              f"{fa_all['visits']}, {fa_all['streams']} streams × cells). **V6: "
              f"false alarms {'pass' if v6_fa else 'fail'}; detection {'pass' if v6_det else 'fail'}; "
              f"delay {'pass' if v6_delay else 'fail'}** (n = 2 streams per fault type).", "",
              "### Per fault stream (held-out)", "",
              "SPC, the quality gate (REIMAGE) and the first flag of either kind, in visits after onset. "
              "*post-onset eligible*: visits after onset that pass the gate (the only ones SPC sees).", "",
              "| fault | stream | cadence | FOVs | post-onset visits | post-onset eligible | SPC delay | first SPC codes "
              "| REIMAGE delay | first flag of any kind | pre-onset SPC signals |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in det_all.sort_values(["fault_type", "stream_id", "cadence_h", "n_fov"]).itertuples():
        d = lambda x: "—" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{int(x)}"  # noqa: E731
        spc = d(r.spc_delay) if r.post_eligible else "no SPC data"
        lines.append(f"| {r.fault_type} | {r.stream_id.replace('c2c12_', '')} | {r.cadence_h:g} h | {r.n_fov} | "
                     f"{r.post_visits} | {r.post_eligible} | {spc} | {r.first_codes.replace(';', ', ') or '—'} | "
                     f"{d(r.gate_delay)} | {d(r.any_delay)} | {r.pre_onset_signals} |")

    pm = per_monitor_fa(sig)
    lines += ["", "### False alarms by monitor (held-out normal streams, all cells)", "",
              "| monitor | signals |", "|---|---|"] + [f"| {k} | {v} |" for k, v in pm.items()]
    by_seq = sig[sig.fault_type == "none"].groupby("base_sequence_id").signals.apply(lambda s: int(s.apply(bool).sum()))
    lines += ["", "Signals per held-out normal sequence (all cells): " + ", ".join(
        f"{k.replace('c2c12_', '').replace('_Data', '')} {v}" for k, v in by_seq.items()) + "."]

    dim = detection(sig, "lamp_dimming")
    lines += ["", "### Lamp dimming (context for A7; V7 wants no per-flask flags)", "",
              f"Held-out dimming streams × cells: {len(dim)}; with a per-flask SPC signal after onset: "
              f"{int(dim.spc_delay.notna().sum())}; with a REIMAGE after onset: {int(dim.gate_delay.notna().sum())}."]

    ex_n = extra[extra.fault_type == "none"].signals.apply(bool).sum()
    ex_c = detection(extra, "contamination_onset")
    lines += ["", "### Spec addition, not in V6: growth above expected", "",
              "Contamination sprites raise the Cellpose confluency reading (A4: median +59 pp), so an upper-side "
              "growth monitor (GROWTH_ABOVE_EXPECTED) was run separately with the same limits: "
              f"{ex_n} signals on held-out normal visits ({100 * ex_n / max((extra.fault_type == 'none').sum(), 1):.2f} per 100); "
              f"contamination streams × cells detected: {int(ex_c.spc_delay.notna().sum())}/{len(ex_c)}.", "",
              "## Notes", "",
              "- Anomaly and class residuals are per frame, so the 1-FOV and 3-FOV cells differ only in the growth "
              "residual; they are not independent evidence.",
              "- At 12 h, fault streams have 3–4 visits up to onset (`results/replay_fleet_summary.md`), so the "
              "growth residual cannot score the first visits after onset.",
              "- Charts: `results/spc_examples.png` (held-out, 6 h, 1 FOV); trade-off: `results/spc_tradeoff.png`.", ""]
    plots(sig, sweep, p, doc, args.out)
    with open(os.path.join(args.out, "spc_summary.md"), "w") as f:
        f.write("\n".join(lines))
    print("\n".join(lines))


def plots(sig, sweep, p, doc, out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(6.5, 4))
    ax.plot(sweep.c, sweep.fa_per_100, marker="o", label="false alarms / 100 visits (tuning normal)")
    ax2 = ax.twinx()
    ax2.plot(sweep.c, sweep.detected / sweep.fault_runs, marker="s", color="tab:orange",
             label="tuning fault runs detected (fraction)")
    ax.axhline(MAX_FA_PER_100, color="grey", ls="--", lw=0.8)
    ax.axvline(doc["selection"]["chosen_c"], color="grey", ls=":", lw=0.8)
    ax.set(xlabel="limit multiplier c (L = 2.86c, h = 4c)", ylabel="false alarms / 100 visits")
    ax2.set(ylabel="fraction detected", ylim=(0, 1.05))
    fig.legend(loc="upper right", fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(out, "spc_tradeoff.png"), dpi=130)
    plt.close(fig)

    cell = sig[(sig.cadence_h == 6.0) & (sig.n_fov == 1)]
    picks = []
    for t in ("none", "contamination_onset", "growth_stall"):
        ids = sorted(cell[cell.fault_type == t].stream_id.unique())
        if ids:
            picks.append((t, ids[0]))
    fig, axes = plt.subplots(len(picks), 2, figsize=(11, 3 * len(picks)), squeeze=False)
    for row, (t, sid) in enumerate(picks):
        g = cell[cell.stream_id == sid].sort_values("visit_idx")
        for col, (res, side) in enumerate([("growth", "lower"), ("anomaly", "upper")]):
            ax = axes[row][col]
            z = [None if pd.isna(x) else float(x) for x in g[res]]
            e, tt, stat, lims, xs = [], 0, 0.0, [], []
            for h, x in zip(g.hours, z):
                if x is None:
                    continue
                tt += 1
                stat = p.lam * x + (1 - p.lam) * stat
                lim = ewma_limit(p.lam, p.L, tt)
                e.append(stat)
                lims.append(-lim if side == "lower" else lim)
                xs.append(h)
                if (side == "lower" and stat < -lim) or (side == "upper" and stat > lim):
                    stat, tt = 0.0, 0
            ax.plot(g.hours, g[res], "o", ms=3, alpha=0.5, label="z")
            ax.plot(xs, e, "-", label="EWMA")
            ax.plot(xs, lims, "--", color="red", lw=0.8, label="limit")
            if t != "none":
                ax.axvline(g.onset_hours.iloc[0], color="black", lw=0.8, ls=":")
            ax.set_title(f"{t}: {sid.replace('c2c12_', '').replace('_Data', '')} — {res}", fontsize=8)
            ax.set(xlabel="hours", ylabel="z")
            ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(os.path.join(out, "spc_examples.png"), dpi=110)
    plt.close(fig)


if __name__ == "__main__":
    main()
