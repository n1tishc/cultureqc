"""
V2 and V10 — does growth between visits beat FOV noise, and do experiments
grow distinguishably (cultureQC_upgrade_spec.md §2A.10).

V2: median per-visit confluency increment in the 30–70% range, divided by
σ_fov, per cadence (6 h, 12 h) and FOV count (1, 3). Pass: ≥ 2 at 1 FOV.
  - streams: held-out normal base streams of the A2 fleet
    (cache/spc/residuals.parquet: visit times and frames as replayed).
  - increment: full-frame Cellpose-SAM confluency at visit i+1 minus at
    visit i (the growth signal, free of crop noise), for pairs whose visit-i
    full-frame confluency is in [30, 70].
  - σ_fov: configs/noise.yaml `entries.c2c12`, crop_frac 0.25 (the replay
    FOV size), evaluated at visit i's full-frame confluency, divided by
    sqrt(n_fov) (independent positions, as configs/growth.yaml assumes).
  - also shown: the measured visit-level error (replayed visit mean minus
    the frame's full-frame value) per FOV count, and the ratio on it.
    Comparing two noisy readings adds a sqrt(2); the spec's ratio does not
    include it, so it is shown separately.
V10 (informational): culture.growth.fit_growth on each held-out sequence's
hourly full-frame series; early-phase confluency-area doubling time and
chosen model, per experiment (media conditions are not resolved in C2C12's
metadata here: condition = "unknown").

Usage:
    python scripts/eval_growth_signal.py --cache-dir cache
"""

from __future__ import annotations

import argparse
import os
import sys
import time

import numpy as np
import pandas as pd
import yaml

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

BAND = (30.0, 70.0)
CROP_FRAC = "0.25"
PASS_RATIO = 2.0


def full_frame(cache_dir: str) -> dict:
    c = pd.read_parquet(os.path.join(cache_dir, "confluency.parquet"))
    c = c[(c.model_name == "seg") & (c.crop_spec == "full")]
    return dict(zip(c.image_sha256, c.pct))


def sigma_fov(pct, noise: dict) -> np.ndarray:
    e = noise["entries"]["c2c12"]["crop_fracs"][CROP_FRAC]
    return np.maximum(e["intercept"] + e["slope"] * np.asarray(pct, dtype=float), 0.0)


def v2(cache_dir: str, noise: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    res = pd.read_parquet(os.path.join(cache_dir, "spc", "residuals.parquet"))
    res = res[(res.split == "heldout") & (res.fault_type == "none")].copy()
    ff = full_frame(cache_dir)
    res["full"] = res.image_sha256.map(ff)
    if res.full.isna().any():
        raise ValueError("visit frame without a full-frame confluency row")
    res["visit_err"] = res.confluency - res.full
    pairs = []
    for (sid, cad, nf), g in res.groupby(["stream_id", "cadence_h", "n_fov"]):
        g = g.sort_values("visit_idx")
        a, b = g.iloc[:-1], g.iloc[1:]
        pairs.append(pd.DataFrame({"stream_id": sid, "cadence_h": cad, "n_fov": nf, "hours": a.hours.to_numpy(),
                                   "dt": b.hours.to_numpy() - a.hours.to_numpy(), "full_i": a.full.to_numpy(),
                                   "increment": b.full.to_numpy() - a.full.to_numpy()}))
    pairs = pd.concat(pairs, ignore_index=True)
    pairs["sigma_fov"] = sigma_fov(pairs.full_i, noise) / np.sqrt(pairs.n_fov)
    pairs["ratio"] = pairs.increment / pairs.sigma_fov
    pairs["in_band"] = pairs.full_i.between(*BAND)
    return pairs, res


def v10(cache_dir: str, split_path: str) -> pd.DataFrame:
    from culture.growth import fit_growth
    spec = importlib_backtest()
    split = pd.read_csv(split_path)
    held = split[(split.split == "heldout") & (split.kind == "base")].sequence_id.tolist()
    series = spec.full_frame_series(cache_dir, held)
    rows = []
    for sid, g in series.groupby("sequence_id"):
        visits = [{"segment_id": sid, "visit_id": f"{sid}:{i}", "timestamp": pd.Timestamp(t).isoformat(),
                   "confluency_mean": float(p), "confluency_sd": 0.0, "crop_specs": ["full"],
                   "source_dataset": "c2c12"} for i, (t, p) in enumerate(zip(g.t, g.pct))]
        r = fit_growth(visits, seed=0, n_boot=50)
        rows.append({"sequence_id": sid, "experiment": sid.split("_")[1], "status": r.status,
                     "chosen_model": r.chosen_model, "area_doubling_h": r.area_doubling_time_hours,
                     "start_pct": float(g.pct.iloc[0]), "end_pct": float(g.pct.iloc[-1]),
                     "span_h": float(g.hours.max())})
    return pd.DataFrame(rows)


def importlib_backtest():
    import importlib.util
    s = importlib.util.spec_from_file_location("backtest_growth", os.path.join(REPO, "scripts", "backtest_growth.py"))
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cache-dir", default="cache")
    ap.add_argument("--split", default=os.path.join(REPO, "results", "replay_fleet_split.csv"))
    ap.add_argument("--out", default=os.path.join(REPO, "results"))
    args = ap.parse_args()
    noise = yaml.safe_load(open(os.path.join(REPO, "configs", "noise.yaml")))
    pairs, visits = v2(args.cache_dir, noise)
    pairs.to_csv(os.path.join(args.out, "growth_signal_v2_pairs.csv"), index=False, float_format="%.4f")
    rates = v10(args.cache_dir, args.split)
    rates.to_csv(os.path.join(args.out, "growth_signal_v10.csv"), index=False, float_format="%.4f")
    write_summary(pairs, visits, rates, noise, args.out)
    plot(pairs, noise, args.out)


def write_summary(pairs, visits, rates, noise, out):
    e = noise["entries"]["c2c12"]["crop_fracs"][CROP_FRAC]
    band = pairs[pairs.in_band]
    lines = ["# V2 and V10: growth signal vs FOV noise", "",
             f"Generated {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} by `scripts/eval_growth_signal.py`. "
             "C2C12 images: Ker et al., *Sci Data* 5:180237 (2018), CC BY 4.0; visits are simulated from them (replay). "
             "Held-out normal streams only.", "",
             "## V2: increment ÷ σ_fov", "",
             f"Increment = full-frame Cellpose-SAM confluency at the next visit minus this visit, for visits at "
             f"{BAND[0]:g}–{BAND[1]:g}% (full frame). σ_fov = {e['intercept']:.3f} + {e['slope']:.4f} × confluency "
             f"(`configs/noise.yaml` entries.c2c12, crop_frac {CROP_FRAC}, the replay FOV size) / √n_fov. Pass (spec): "
             f"median ratio ≥ {PASS_RATIO:g} at 1 FOV.", "",
             f"Held-out C2C12 sequences peak at {visits.full.max():.0f}% here, so the band is effectively "
             f"{BAND[0]:g}–{visits.full.max():.0f}%: {band.stream_id.nunique()} of "
             f"{pairs.stream_id.nunique()} held-out streams contribute.", "",
             "| cadence | FOVs | pairs in band (streams) | median increment (pp) | median σ_fov/√n (pp) | median ratio | "
             "IQR of ratio | V2 |", "|---|---|---|---|---|---|---|---|"]
    verdict = {}
    for (cad, nf), g in band.groupby(["cadence_h", "n_fov"]):
        med = float(g.ratio.median())
        q1, q3 = g.ratio.quantile([0.25, 0.75])
        ok = med >= PASS_RATIO
        verdict[(cad, nf)] = ok
        lines.append(f"| {cad:g} h | {nf} | {len(g)} ({g.stream_id.nunique()}) | {g.increment.median():.2f} | "
                     f"{g.sigma_fov.median():.2f} | **{med:.2f}** | {q1:.2f}–{q3:.2f} | "
                     f"{'pass' if ok else 'fail'}{'' if nf == 1 else ' (context)'} |")
    lines += ["", "**Measured visit-level error** (replayed visit mean minus the same frame's full-frame value; "
              f"visits at {BAND[0]:g}–{BAND[1]:g}%), against the σ_fov model:", "",
              "| FOVs | visits | mean error (pp) | SD (pp) | model σ_fov/√n at the median confluency (pp) | "
              "median increment ÷ measured SD, 6 h | 12 h |", "|---|---|---|---|---|---|---|"]
    vb = visits[visits.full.between(*BAND)]
    for nf, g in vb.groupby("n_fov"):
        sd = float(g.visit_err.std(ddof=1))
        model = float(sigma_fov([g.full.median()], noise)[0] / np.sqrt(nf))
        r6 = band[(band.cadence_h == 6.0) & (band.n_fov == nf)].increment.median() / sd
        r12 = band[(band.cadence_h == 12.0) & (band.n_fov == nf)].increment.median() / sd
        lines.append(f"| {nf} | {len(g)} | {g.visit_err.mean():+.2f} | {sd:.2f} | {model:.2f} | {r6:.2f} | {r12:.2f} |")
    lines += ["", "The same frames are replayed at 1 and 3 FOVs and in both cadences, so the rows are not independent.",
              "A difference of two noisy readings has √2 × the noise of one; the spec's ratio leaves that out, so the "
              "signal-to-noise of one increment is the ratio ÷ 1.41.", ""]
    one = [ok for (cad, nf), ok in verdict.items() if nf == 1]
    three = [ok for (cad, nf), ok in verdict.items() if nf == 3]
    lines.append(f"**V2 at 1 FOV: {'pass' if all(one) else 'fail'}** "
                 f"({', '.join(f'{cad:g} h {band[(band.cadence_h == cad) & (band.n_fov == 1)].ratio.median():.2f}' for cad in sorted(band.cadence_h.unique()))}). "
                 f"At 3 FOVs: {'pass' if all(three) else 'fail'} "
                 f"({', '.join(f'{cad:g} h {band[(band.cadence_h == cad) & (band.n_fov == 3)].ratio.median():.2f}' for cad in sorted(band.cadence_h.unique()))}).")
    e5 = noise["entries"]["c2c12"]["crop_fracs"]["0.5"]
    r5 = band.increment / (np.maximum(e5["intercept"] + e5["slope"] * band.full_i, 0.0) / np.sqrt(band.n_fov))
    r5 = r5.groupby([band.cadence_h, band.n_fov]).median()
    lines += ["", "FOV size matters as much as FOV count. The replay FOV is a 0.25-frac crop (348 × 260 of a "
              "1392 × 1040 frame, an A2 choice). With the 0.5-frac σ_fov fit from the same noise config "
              f"(σ = {e5['intercept']:.3f} + {e5['slope']:.4f} × confluency), same increments: median ratio " +
              ", ".join(f"{cad:g} h/{nf} FOV {v:.2f}" for (cad, nf), v in r5.items()) +
              " (context; not replayed at that size)."]
    allr = pairs.groupby(["cadence_h", "n_fov"]).ratio.median()
    lines += ["", "All confluencies, for context (not the spec's band): median ratio " +
              ", ".join(f"{cad:g} h/{nf} FOV {v:.2f}" for (cad, nf), v in allr.items()) + ".", "",
              "Plot: `results/growth_signal_v2.png`; every pair: `results/growth_signal_v2_pairs.csv`.", "",
              "## V10 (informational): growth per experiment", "",
              "`culture.growth.fit_growth` on each held-out sequence's hourly full-frame series (condition metadata "
              "is \"unknown\" in this C2C12 import, so grouped by experiment). Confluency-area doubling time, early "
              "phase — a rate of confluency, not cell doubling time.", "",
              "| experiment | sequences | fits OK | chosen model (logistic/gompertz) | area doubling time, median (range), h | "
              "start → end confluency, median (%) |", "|---|---|---|---|---|---|"]
    for ex, g in rates.groupby("experiment"):
        ok = g[g.status == "OK"]
        d = ok.area_doubling_h.dropna()
        lines.append(f"| {ex} | {len(g)} | {len(ok)} | {int((ok.chosen_model == 'logistic').sum())}/"
                     f"{int((ok.chosen_model == 'gompertz').sum())} | "
                     f"{f'{d.median():.1f} ({d.min():.1f}–{d.max():.1f})' if len(d) else '—'} | "
                     f"{g.start_pct.median():.1f} → {g.end_pct.median():.1f} |")
    lines += ["", "Per sequence: `results/growth_signal_v10.csv`.", ""]
    with open(os.path.join(out, "growth_signal_summary.md"), "w") as f:
        f.write("\n".join(lines))
    print("\n".join(lines))


def plot(pairs, noise, out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    cads = sorted(pairs.cadence_h.unique())
    fig, axes = plt.subplots(1, len(cads), figsize=(11, 4), sharey=True)
    xs = np.linspace(0, max(60.0, pairs.full_i.max()), 200)
    for ax, cad in zip(np.atleast_1d(axes), cads):
        g = pairs[(pairs.cadence_h == cad) & (pairs.n_fov == 1)]
        ax.scatter(g.full_i, g.increment, s=10, alpha=0.6, label="increment to next visit (full frame)")
        for nf, ls in ((1, "-"), (3, "--")):
            ax.plot(xs, PASS_RATIO * sigma_fov(xs, noise) / np.sqrt(nf), "r" + ls, lw=1,
                    label=f"{PASS_RATIO:g} × σ_fov/√{nf} (V2 pass line, {nf} FOV)")
        ax.axvspan(*BAND, color="grey", alpha=0.12, lw=0)
        ax.axhline(0, color="black", lw=0.5)
        ax.set(title=f"held-out normal, {cad:g} h cadence", xlabel="full-frame confluency at visit (%)")
    np.atleast_1d(axes)[0].set_ylabel("increment (pp)")
    np.atleast_1d(axes)[0].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(os.path.join(out, "growth_signal_v2.png"), dpi=120)
    plt.close(fig)


if __name__ == "__main__":
    main()
