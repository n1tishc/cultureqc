"""
Replication of the sealed mCellSeg test with the two halves swapped (pre-registered in
results/confluency_mcellseg_swap.md, committed before any swapped map is computed).

The 90 images that were the sealed test become the calibration images; the 79 that were calibration images
become the test images. Same four setups, same recipe, same grid, same rules and criteria as
results/confluency_mcellseg.md; the functions are imported from scripts/confluency_mcellseg.py unchanged.
Arms Z, C and F only (R was secondary there and did not help).

GPU steps run on Colab (nb/07_confluency_replication.ipynb):

    python scripts/confluency_mcellseg_swap.py train     # fine-tune: two cross-fit folds of the 90, then all 90
    python scripts/confluency_mcellseg_swap.py ftmaps    # out-of-fold maps of the 90, final-model maps of the 79
    python scripts/confluency_mcellseg_swap.py curves    # -> results/confluency_mcellseg_swap_curves.json

CPU, on the Mac, once:

    .venv/bin/python scripts/confluency_mcellseg_swap.py score
    .venv/bin/python scripts/confluency_mcellseg_swap.py figure

Z and C read the zero-shot curves already committed in results/confluency_mcellseg_curves.json.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))
os.chdir(REPO)

import confluency_mcellseg as m  # noqa: E402

ARM_DIR = "ft_swap"                          # maps under cache/probmaps_mcellseg/ft_swap
CURVES = os.path.join("results", "confluency_mcellseg_swap_curves.json")
OUT_MD = os.path.join("results", "confluency_mcellseg_swap.md")
OUT_CSV = os.path.join("results", "confluency_mcellseg_swap.csv")
OUT_JSON = os.path.join("results", "confluency_mcellseg_swap.json")
OUT_PNG = os.path.join("results", "confluency_mcellseg_swap.png")
FT_RUNS = {"mcellseg_swap_ftA": "B", "mcellseg_swap_ftB": "A", "mcellseg_swap_ftF": None}   # run -> fold trained on
ARMS = ("Z", "C", "F")


def swapped() -> tuple[list[dict], list[str]]:
    """The committed split with the roles of the two halves exchanged, in the four setups of the sealed test.
    The setups stay the sealed test's four (polymer_lowmag would reach 9 calibration images after the swap,
    all from one unit, and is left out as before)."""
    its = m.loaded()
    cal = json.load(open(m.SPLIT_JSON))["calibrated_setups"]
    assert cal == m.calibrated_setups(its), cal
    for i in its:
        i["v1_split"] = i["split"]
        i["split"] = {"calib": "test", "test": "calib"}[i["split"]]
    return its, cal


def folds(its: list[dict], cal: list[str]) -> None:
    """As confluency_mcellseg.ft_folds, on the swapped calibration images: units of each setup, ranked by mean
    expert confluency, alternate folds A and B."""
    by = defaultdict(lambda: defaultdict(list))
    for i in its:
        if i["setup"] in cal and i["split"] == "calib":
            by[i["setup"]][i["unit"]].append(i)
    for s, units in by.items():
        order = sorted(units, key=lambda u: (np.mean([i["gt"] for i in units[u]]), u))
        for k, u in enumerate(order):
            for i in units[u]:
                i["fold"] = "A" if k % 2 == 0 else "B"


# ── GPU steps (Colab) ───────────────────────────────────────────────────────

def cmd_train(a):
    from confluency_finetune import RUNS, train_run
    its, cal = swapped()
    folds(its, cal)
    for run, fold in FT_RUNS.items():
        if os.path.exists(os.path.join(RUNS, run, "manifest.json")):
            continue
        pool = [i for i in its if "fold" in i and (fold is None or i["fold"] == fold)]
        man = train_run(run, pool, label_fn=m.instance_mask)
        print(json.dumps({k: man[k] for k in ("run", "n", "weights_sha256", "seconds")}), flush=True)


def cmd_ftmaps(a):
    from confluency_finetune import model
    its, cal = swapped()
    folds(its, cal)
    jobs = {"mcellseg_swap_ftA": [i for i in its if i.get("fold") == "A"],
            "mcellseg_swap_ftB": [i for i in its if i.get("fold") == "B"],
            "mcellseg_swap_ftF": [i for i in its if i["setup"] in cal and i["split"] == "test"]}
    for run, todo in jobs.items():
        mdl = model(run)
        for i in todo:
            m.cached(ARM_DIR, i["name"], lambda: mdl.eval(m.gray(i["path"]), diameter=None, channels=[0, 0],
                                                         compute_masks=False)[1][2])
        print(run, len(todo), flush=True)


def cmd_curves(a):
    from confluency_finetune import RUNS, environment
    its, cal = swapped()
    rows = {}
    for i in its:
        p = os.path.join(m.MAPS, ARM_DIR, i["name"] + ".npz")
        if i["setup"] in cal and os.path.exists(p):
            rows[i["name"]] = [float(x) for x in m.curve(np.load(p)["prob"].astype(np.float32))]
    out = {"generated_by": "scripts/confluency_mcellseg_swap.py curves", "environment": environment(), "grid": m.GRID,
           "maps": {ARM_DIR: rows}, "manifests": {}}
    for run in FT_RUNS:
        mp = os.path.join(RUNS, run, "manifest.json")
        if os.path.exists(mp):
            out["manifests"][run] = json.load(open(mp))
    print(ARM_DIR, len(rows), "of", sum(i["setup"] in cal for i in its), flush=True)
    json.dump(out, open(CURVES, "w"))
    print("wrote", CURVES)


# ── scoring (once) ──────────────────────────────────────────────────────────

def calls(rows: list[dict], cal: list[str], key_f: str) -> dict:
    """Fit C and F per setup on the calibration rows, then read and call every row (rules_v0.5, T = 80)."""
    j0 = m.GRID.index(0.0)
    prof = {}
    for s in cal:
        calib = [r for r in rows if r["setup"] == s and r["split"] == "calib"]
        for arm, key in (("C", "curve_Z"), ("F", key_f)):
            prof[(arm, s)] = m.fit_setup([{"curve": r[key], "gt": r["gt"], "unit": r["unit"]} for r in calib])
    for r in rows:
        r["Z"], r["Z_band"] = float(r["curve_Z"][j0]), None
        r["Z_call"] = m.uncalibrated_call(r["Z"])
        for arm, key in (("C", "curve_Z"), ("F", key_f)):
            p = prof[(arm, r["setup"])]
            r[arm], r[f"{arm}_band"] = float(r[key][p["j"]]), p["band_pp"]
            r[f"{arm}_call"] = m.cal_call(r[arm], p["band_pp"])
    return prof


def contrast(test: list[dict], rng) -> dict:
    d = m.dense(test)
    return {"mae_60_90_diff": m.mae(d, "C") - m.mae(d, "F"),
            "ci": m.clustered(d, lambda x: m.mae(x, "C") - m.mae(x, "F"), rng),
            "mae_all_diff": m.mae(test, "C") - m.mae(test, "F"),
            "ci_all": m.clustered(test, lambda x: m.mae(x, "C") - m.mae(x, "F"), rng)}


def cmd_score(a):
    if "\n## Results" in open(OUT_MD).read():
        sys.exit("results section already present; the replication is scored once")
    its, cal = swapped()
    folds(its, cal)
    Cz = json.load(open(m.CURVES))                  # committed with the sealed test (zero-shot and its F maps)
    Cs = json.load(open(CURVES))
    assert Cz["grid"] == Cs["grid"] == m.GRID

    def base(i, split):
        return {k: i[k] for k in ("name", "setup", "unit", "gt")} | {
            "split": split, "fold": i.get("fold"), "cluster": i["setup"] + "/" + i["unit"],
            "curve_Z": np.array(Cz["maps"]["zero"][i["name"]])}

    # the replication: swapped roles
    rows = []
    for i in its:
        if i["setup"] in cal:
            r = base(i, i["split"])
            if i["name"] not in Cs["maps"][ARM_DIR]:
                sys.exit(f"no swapped fine-tuned reading for {i['name']}: run train / ftmaps / curves on Colab first")
            r["curve_F"] = np.array(Cs["maps"][ARM_DIR][i["name"]])
            rows.append(r)
    prof = calls(rows, cal, "curve_F")
    test = [r for r in rows if r["split"] == "test"]

    # the sealed test's rows, recomputed from its committed curves (checked against its committed CSV)
    v1 = []
    for i in its:
        if i["setup"] in cal:
            r = base(i, i["v1_split"])
            r["curve_F1"] = np.array(Cz["maps"]["ft"][i["name"]])
            v1.append(r)
    calls(v1, cal, "curve_F1")
    v1_test = [r for r in v1 if r["split"] == "test"]
    sealed = {r["name"]: r for r in csv.DictReader(open(m.OUT_CSV))}
    for r in v1_test:
        for arm in ARMS:
            assert abs(r[arm] - float(sealed[r["name"]][f"{arm}_reading"])) < 1e-3 and r[f"{arm}_call"] == sealed[r["name"]][f"{arm}_call"], r["name"]

    rng = np.random.default_rng(0)
    res = {"generated_by": "scripts/confluency_mcellseg_swap.py score",
           "scored_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"), "computed_on": Cs["environment"],
           "fine_tuned_runs": {k: {f: v.get(f) for f in ("run", "n", "weights_sha256", "seconds")}
                               for k, v in Cs["manifests"].items()},
           "calibrated_setups": cal,
           "profiles": {f"{arm}/{s}": {k: v for k, v in p.items() if k != "j"} for (arm, s), p in prof.items()},
           "criteria": {arm: m.criteria(test, arm, rng) for arm in ARMS},
           "contrast": contrast(test, rng)}
    both = v1_test + test
    res["both_halves"] = {"n": len(both), "criteria": {arm: m.criteria(both, arm, rng) for arm in ARMS},
                          "contrast": contrast(both, rng)}
    res["per_setup"] = {}
    for s in cal:
        g = [r for r in test if r["setup"] == s]
        res["per_setup"][s] = {arm: {"n": len(g), "mae": m.mae(g, arm), "bias": m.bias(g, arm),
                                     "n_60_90": len(m.dense(g)),
                                     "mae_60_90": m.mae(m.dense(g), arm) if m.dense(g) else None,
                                     "bias_60_90": m.bias(m.dense(g), arm) if m.dense(g) else None,
                                     "calls_60_100": {c: sum(r[f"{arm}_call"] == c for r in g if r["gt"] >= m.LO)
                                                      for c in ("passage", "continue", "review")},
                                     "covered": (sum(abs(r[arm] - r["gt"]) <= r[f"{arm}_band"] for r in g)
                                                 if arm != "Z" else None)}
                               for arm in ARMS}
    with open(OUT_CSV, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["name", "setup", "unit", "split", "fold", "gt_pct"] + [f"{x}_{k}" for x in ARMS for k in ("reading", "band", "call")])
        for r in rows:
            w.writerow([r["name"], r["setup"], r["unit"], r["split"], r["fold"] or "", round(r["gt"], 3)] +
                       [("" if r.get(f"{x}{k}") is None else (round(r[f"{x}{k}"], 3) if isinstance(r[f"{x}{k}"], float) else r[f"{x}{k}"]))
                        for x in ARMS for k in ("", "_band", "_call")])
    json.dump(res, open(OUT_JSON, "w"), indent=1, default=float)
    write_md(res)
    print(json.dumps({k: res[k] for k in ("criteria", "contrast")} | {"both_halves": res["both_halves"]}, indent=1, default=float)[:8000])


def table(lines: list[str], c: dict) -> None:
    lines += ["| | " + " | ".join(f"{a}: {m.ARMS[a]}" for a in ARMS) + " |", "|---|---|---|---|"]

    def row(label, f):
        lines.append(f"| {label} | " + " | ".join(f(c[a]) for a in ARMS) + " |")

    def ci(x, k, s):
        return "" if x[k] is None else f" ({x[k][0]:{s}} to {x[k][1]:{s}})"
    row("B1 MAE, all test images (95% interval)", lambda x: f"{x['B1_mae']:.2f}{ci(x, 'B1_ci', '.2f')} **{x['verdicts']['B1']}**")
    row("B2 MAE, 60–90%", lambda x: f"{x['B2_mae']:.2f}{ci(x, 'B2_ci', '.2f')} **{x['verdicts']['B2']}**")
    row("B3 mean signed error, 60–90%", lambda x: f"{x['B3_bias']:+.2f}{ci(x, 'B3_ci', '+.2f')} **{x['verdicts']['B3']}**")
    row("B4 calls at T = 80 on 60–100% (passage / continue / review; agree of decided)",
        lambda x: f"{x['B4_passage']} / {x['B4_continue']} / {x['B4_review']}; {x['B4_agree']} of {x['B4_decided']} **{x['verdicts']['B4']}**")
    row("B5 band coverage, all test images", lambda x: (f"{x['B5_covered']} of {x['B5_n']} ({100 * x['B5_coverage']:.1f}%) **{x['verdicts']['B5']}**"
                                                      if x["B5_coverage"] is not None else "no band"))
    row("ready (≥ 80%) called continue", lambda x: str(x["B4_ready_called_continue"]))
    row("share of test images sent to a person", lambda x: f"{100 * x['review_share']:.1f}%")


def write_md(res: dict) -> None:
    c = res["criteria"]
    lines = ["", "## Results", "",
             f"Scored {res['scored_at']} by `scripts/confluency_mcellseg_swap.py score`; one row per image in `{OUT_CSV}`.", "",
             f"Test images (the sealed test's calibration images): {c['C']['n']}; {c['C']['n_60_90']} at 60–90%, "
             f"{c['C']['n_60_100']} at 60–100%, {c['C']['n_ge_T']} at or above 80%.", ""]
    table(lines, c)
    k = res["contrast"]
    lines += ["", f"Pre-registered contrast, MAE(C) − MAE(F) at 60–90%: {k['mae_60_90_diff']:+.2f} pp "
              f"({k['ci'][0]:+.2f} to {k['ci'][1]:+.2f}); all test images {k['mae_all_diff']:+.2f} pp "
              f"({k['ci_all'][0]:+.2f} to {k['ci_all'][1]:+.2f}).", "",
              "Profiles fitted on the swapped calibration images (cutoff, band, n):", ""]
    for name, p in res["profiles"].items():
        lines.append(f"- {name}: cutoff {p['cutoff']:+.1f}, band ±{m.fmt(p['band_pp'])} pp, n = {p['n_calib']}, calibration MAE {p['calib_mae']:.2f}")
    lines += ["", "Per setup (test images; MAE / bias, then 60–90%; calls on 60–100% as passage / continue / to a person; within band):", "",
              "| setup | n | arm | MAE / bias | n 60–90 | MAE / bias 60–90 | calls 60–100% | within band |", "|---|---|---|---|---|---|---|---|"]
    for s, v in res["per_setup"].items():
        for a in ARMS:
            x = v[a]
            lines.append(f"| {s if a == 'Z' else ''} | {x['n'] if a == 'Z' else ''} | {a} | {x['mae']:.2f} / {x['bias']:+.2f} | "
                         f"{x['n_60_90'] if a == 'Z' else ''} | "
                         + (f"{x['mae_60_90']:.2f} / {x['bias_60_90']:+.2f}" if x["mae_60_90"] is not None else "—")
                         + f" | {x['calls_60_100']['passage']} / {x['calls_60_100']['continue']} / {x['calls_60_100']['review']} | "
                         + (f"{x['covered']} of {x['n']}" if x["covered"] is not None else "no band") + " |")
    b = res["both_halves"]
    lines += ["", f"### Both halves together (secondary): {b['n']} images, each read by models that never trained on it", ""]
    table(lines, b["criteria"])
    k = b["contrast"]
    lines += ["", f"MAE(C) − MAE(F) at 60–90%: {k['mae_60_90_diff']:+.2f} pp ({k['ci'][0]:+.2f} to {k['ci'][1]:+.2f}); "
              f"all images {k['mae_all_diff']:+.2f} pp ({k['ci_all'][0]:+.2f} to {k['ci_all'][1]:+.2f}).", ""]
    with open(OUT_MD, "a") as fh:
        fh.write("\n".join(lines))


def cmd_figure(a):
    """Reading vs expert confluency on the swapped test images, one panel per arm. Computes nothing."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import pandas as pd
    df = pd.read_csv(OUT_CSV)
    res = json.load(open(OUT_JSON))
    d = df[df.split == "test"]
    colours = {"cd7_huvec_dic": "#2563eb", "lsm_hek_1024": "#dc2626", "oir_1024": "#059669", "lsm_2796": "#9333ea"}
    fig, axes = plt.subplots(1, 3, figsize=(12.5, 4.6))
    x = np.linspace(0, 100, 2)
    for ax, arm in zip(axes, ARMS):
        c = res["criteria"][arm]
        ax.axvspan(m.LO, m.HI, color="#f59e0b", alpha=0.08, lw=0)
        ax.plot(x, x, color="#111", lw=0.8)
        for s, g in d.groupby("setup"):
            ax.scatter(g.gt_pct, g[f"{arm}_reading"], s=14, color=colours.get(s, "#555"), alpha=0.8, label=s)
        ax.axhline(m.T, color="#f59e0b", lw=0.8, ls="--")
        ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.set_aspect("equal")
        ax.set_xlabel("expert confluency (%)")
        ax.set_title(f"{arm}: {m.SHORT[arm]}\nall: MAE {c['B1_mae']:.1f} pp   60–90%: MAE {c['B2_mae']:.1f}, bias {c['B3_bias']:+.1f}",
                     fontsize=8.5)
    axes[0].set_ylabel("reading (%)")
    axes[0].legend(loc="upper left", fontsize=7, frameon=False)
    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=140)
    print("wrote", OUT_PNG)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for c in ("train", "ftmaps", "curves", "score", "figure"):
        sub.add_parser(c)
    a = ap.parse_args()
    {"train": cmd_train, "ftmaps": cmd_ftmaps, "curves": cmd_curves, "score": cmd_score, "figure": cmd_figure}[a.cmd](a)


if __name__ == "__main__":
    main()
