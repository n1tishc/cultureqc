"""
B2: does the confluency confidence predict the reading's error?

Data, metrics and the decision rule were pre-registered in
results/confidence_vs_error.md (commit 3a15fda) before this script existed;
it computes exactly those and appends the results below the pre-registration,
which it leaves as it is.

No model runs. Inputs:
  results/confluency_real.csv      the 33 held-out EVICAN images (primary)
  results/confluency_cutoff.csv    the 65 calibration images (secondary)
  data/sources/evican/*.json       image sizes of the 65
  cache/confluency.parquet, cache/images.parquet, results/replay_fleet_split.csv
                                   held-out C2C12 full frames (metric 3 only)

    .venv/bin/python scripts/confidence_vs_error.py

Outputs: results/confidence_vs_error.{md,csv,png}
"""

from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd
from scipy.stats import rankdata, spearmanr

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS = os.path.join(REPO, "results")
OUT_MD = os.path.join(RESULTS, "confidence_vs_error.md")
OUT_CSV = os.path.join(RESULTS, "confidence_vs_error.csv")
OUT_PNG = os.path.join(RESULTS, "confidence_vs_error.png")
EVICAN_DIR = os.path.join(REPO, "data", "sources", "evican")
TIERS = ["easy", "medium", "difficult"]
PREREG_COMMIT = "3a15fda"
B = 10_000
RESULTS_HEADER = "\n## Results\n"


# ---------------------------------------------------------------- data

def primary() -> pd.DataFrame:
    df = pd.read_csv(os.path.join(RESULTS, "confluency_real.csv"))
    assert len(df) == 33, len(df)
    return pd.DataFrame({"set": "eval33 (primary)", "file_name": df.file_name, "gt_pct": df.gt_pct,
                         "pct": df.cultureqc_pct, "confidence": df.cultureqc_confidence,
                         "width": df.width, "height": df.height})


def secondary() -> pd.DataFrame:
    df = pd.read_csv(os.path.join(RESULTS, "confluency_cutoff.csv"))
    df = df[df.split == "calib65"]
    assert len(df) == 65, len(df)
    sizes = {}
    for tier in TIERS:
        with open(os.path.join(EVICAN_DIR, f"instances_eval2019_{tier}_EVICAN2.json")) as f:
            for im in json.load(f)["images"]:
                sizes[im["file_name"]] = (im["width"], im["height"])
    return pd.DataFrame({"set": "calib65 (secondary)", "file_name": df.file_name.values,
                         "gt_pct": df.gt_pct.values, "pct": df.pct_cut0.values,
                         "confidence": df.conf_cut0.values,
                         "width": [sizes[n][0] for n in df.file_name], "height": [sizes[n][1] for n in df.file_name]})


def c2c12_heldout() -> pd.DataFrame:
    conf = pd.read_parquet(os.path.join(REPO, "cache", "confluency.parquet"))
    conf = conf[(conf.model_name == "seg") & (conf.model_version == "cpsam_v2") & (conf.crop_spec == "full")]
    images = pd.read_parquet(os.path.join(REPO, "cache", "images.parquet"))[["image_sha256", "dataset", "sequence_id"]]
    split = pd.read_csv(os.path.join(RESULTS, "replay_fleet_split.csv"))
    held = set(split[(split.kind == "base") & (split.split == "heldout")].sequence_id)
    df = conf.merge(images, on="image_sha256", how="left", validate="one_to_one")
    return df[(df.dataset == "c2c12") & df.sequence_id.isin(held)][["sequence_id", "pct", "confidence"]]


# ---------------------------------------------------------------- metrics

def rho(x, y) -> float:
    if np.ptp(x) == 0 or np.ptp(y) == 0:
        return float("nan")
    return float(spearmanr(x, y).statistic)


def partial_rho(x, y, z) -> float:
    rx, ry, rz = rankdata(x), rankdata(y), rankdata(z)
    if min(np.ptp(rx), np.ptp(ry), np.ptp(rz)) == 0:
        return float("nan")
    r = np.corrcoef([rx, ry, rz])
    rxy, rxz, ryz = r[0, 1], r[0, 2], r[1, 2]
    den = np.sqrt((1 - rxz ** 2) * (1 - ryz ** 2))
    return float((rxy - rxz * ryz) / den) if den > 0 else float("nan")


def ci(values) -> dict:
    v = np.asarray(values, float)
    ok = v[~np.isnan(v)]
    return {"lo": float(np.percentile(ok, 2.5)), "hi": float(np.percentile(ok, 97.5)),
            "dropped": int(np.isnan(v).sum())}


def risk_curve(conf, err) -> np.ndarray:
    """Risk at each coverage k/n, highest confidence kept first; each tie group's
    errors replaced by the group's mean, which is the exact expectation over
    random orderings within ties."""
    conf, err = np.asarray(conf, float), np.asarray(err, float)
    order = np.argsort(-conf, kind="stable")
    c, e = conf[order], err[order]
    _, inv = np.unique(c, return_inverse=True)
    e = (np.bincount(inv, weights=e) / np.bincount(inv))[inv]
    return np.cumsum(e) / np.arange(1, len(e) + 1)


def aurc(conf, err) -> float:
    return float(risk_curve(conf, err).mean())


def oracle_curve(err) -> np.ndarray:
    e = np.sort(np.asarray(err, float))
    return np.cumsum(e) / np.arange(1, len(e) + 1)


def study(df: pd.DataFrame) -> dict:
    conf = df.confidence.to_numpy(float)
    err = (df.pct - df.gt_pct).abs().to_numpy(float)
    gt = df.gt_pct.to_numpy(float)
    n = len(df)

    idx = np.random.default_rng(0).integers(0, n, size=(B, n))
    boot_err = [rho(conf[i], err[i]) for i in idx]
    boot_part = [partial_rho(conf[i], err[i], gt[i]) for i in idx]
    boot_gt = [rho(conf[i], gt[i]) for i in idx]

    obs = aurc(conf, err)
    perm_rng = np.random.default_rng(0)
    perm = np.array([aurc(conf[perm_rng.permutation(n)], err) for _ in range(B)])

    return {
        "n": n, "mae": float(err.mean()),
        "below20": int((gt < 20).sum()), "gt_min": float(gt.min()), "gt_max": float(gt.max()),
        "conf_min": float(conf.min()), "conf_max": float(conf.max()),
        "n_conf_distinct": int(len(np.unique(conf))),
        "rho_err": rho(conf, err), "rho_err_ci": ci(boot_err),
        "partial": partial_rho(conf, err, gt), "partial_ci": ci(boot_part),
        "rho_gt": rho(conf, gt), "rho_gt_ci": ci(boot_gt),
        "aurc": obs, "aurc_random": float(err.mean()), "aurc_oracle": float(oracle_curve(err).mean()),
        "perm_p": float((1 + (perm <= obs).sum()) / (B + 1)),
        "curve": risk_curve(conf, err), "oracle": oracle_curve(err),
    }


def c2c12_study(df: pd.DataFrame) -> dict:
    seqs = sorted(df.sequence_id.unique())
    by_seq = {s: df[df.sequence_id == s] for s in seqs}
    rng = np.random.default_rng(0)
    boot = []
    for _ in range(B):
        pick = rng.integers(0, len(seqs), size=len(seqs))
        d = pd.concat([by_seq[seqs[i]] for i in pick])
        boot.append(rho(d.confidence.to_numpy(float), d.pct.to_numpy(float)))
    return {"n": len(df), "sequences": len(seqs), "pct_max": float(df.pct.max()),
            "rho": rho(df.confidence.to_numpy(float), df.pct.to_numpy(float)), "ci": ci(boot)}


def decide(s: dict) -> dict:
    a = s["rho_err"] <= -0.3 and s["rho_err_ci"]["hi"] < 0
    b = s["perm_p"] < 0.05
    return {"a": bool(a), "b": bool(b), "keep": bool(a and b)}


# ---------------------------------------------------------------- outputs

def plot(studies: list[tuple[str, dict]]):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, len(studies), figsize=(5.2 * len(studies), 4.0), dpi=150)
    for ax, (title, s) in zip(np.atleast_1d(axes), studies):
        cov = np.arange(1, s["n"] + 1) / s["n"]
        ax.plot(cov, s["curve"], color="#1f6f8b", lw=2, label=f"by confidence (AURC {s['aurc']:.2f})")
        ax.axhline(s["aurc_random"], color="#888", ls="--", lw=1.2, label=f"random order (= MAE {s['aurc_random']:.2f})")
        ax.plot(cov, s["oracle"], color="#c46b2d", lw=1.2, ls=":", label=f"oracle (AURC {s['aurc_oracle']:.2f})")
        ax.set_title(f"{title}, n = {s['n']}", fontsize=10)
        ax.set_xlabel("coverage (share of images kept, highest confidence first)")
        ax.set_ylabel("mean |error| of kept images (pp)")
        ax.set_xlim(0, 1)
        ax.set_ylim(bottom=0)
        ax.legend(fontsize=8, frameon=False)
    fig.suptitle("Risk–coverage of the confluency confidence (shipped cutoff 0.0)", fontsize=11)
    fig.tight_layout()
    fig.savefig(OUT_PNG)
    plt.close(fig)


def fmt_ci(c: dict) -> str:
    out = f"[{c['lo']:+.2f}, {c['hi']:+.2f}]"
    return out + (f" ({c['dropped']} undefined resamples dropped)" if c["dropped"] else "")


def zero_reads(df: pd.DataFrame) -> dict:
    z = df[df.pct == 0]
    return {"n": len(z), "of": len(df), "gt": ", ".join(f"{v:.1f}%" for v in sorted(z.gt_pct)) or "—",
            "conf": ", ".join(f"{v:.2f}" for v in sorted(z.confidence)) or "—"}


def top_scored(df: pd.DataFrame, k: int = 3) -> dict:
    g = df.assign(err=(df.pct - df.gt_pct).abs()).sort_values("confidence", ascending=False, kind="stable")
    g = g.reset_index(drop=True)
    worst = g.loc[g.err.idxmax()]
    return {"k": k, "errs": ", ".join(f"{v:.1f}" for v in sorted(g.err.head(k), reverse=True)),
            "max": float(worst.err), "conf": float(worst.confidence),
            "at_least": int((g.confidence >= worst.confidence).sum()), "of": len(g)}


def results_md(p: dict, s: dict, c: dict, d: dict, zeros: list[tuple[str, dict]],
               tops: list[tuple[str, dict]]) -> str:
    verdict = ("**Keep the name \"confidence\".**" if d["keep"] else
               "**Rename: the displayed label becomes \"Boundary ambiguity\" (1 − confidence).**")
    lines = [
        RESULTS_HEADER,
        f"Computed by `scripts/confidence_vs_error.py` after the pre-registration above (commit "
        f"`{PREREG_COMMIT}`); nothing above this section was changed. Per-image values: "
        "`results/confidence_vs_error.csv`. Curves: `results/confidence_vs_error.png`.",
        "",
        "### Decision (on the 33 held-out images)",
        "",
        f"- (a) ρ(confidence, |error|) = **{p['rho_err']:+.2f}**, 95% CI {fmt_ci(p['rho_err_ci'])}: "
        f"{'passes' if d['a'] else 'fails'} (needs ≤ −0.30 with the CI below 0).",
        f"- (b) AURC **{p['aurc']:.2f}** pp vs random {p['aurc_random']:.2f} pp, permutation p = "
        f"**{p['perm_p']:.3f}**: {'passes' if d['b'] else 'fails'} (needs p < 0.05).",
        "",
        verdict,
        "",
        "### All metrics",
        "",
        "| Metric | 33 held-out (primary) | 65 calibration (secondary) |",
        "|---|---|---|",
        f"| ρ(confidence, \\|error\\|), 95% CI | {p['rho_err']:+.2f} {fmt_ci(p['rho_err_ci'])} | "
        f"{s['rho_err']:+.2f} {fmt_ci(s['rho_err_ci'])} |",
        f"| Partial ρ, controlling for GT confluency | {p['partial']:+.2f} {fmt_ci(p['partial_ci'])} | "
        f"{s['partial']:+.2f} {fmt_ci(s['partial_ci'])} |",
        f"| ρ(confidence, GT confluency) | {p['rho_gt']:+.2f} {fmt_ci(p['rho_gt_ci'])} | "
        f"{s['rho_gt']:+.2f} {fmt_ci(s['rho_gt_ci'])} |",
        f"| AURC by confidence (pp) | {p['aurc']:.2f} | {s['aurc']:.2f} |",
        f"| AURC, random order = MAE (pp) | {p['aurc_random']:.2f} | {s['aurc_random']:.2f} |",
        f"| AURC, oracle (pp) | {p['aurc_oracle']:.2f} | {s['aurc_oracle']:.2f} |",
        f"| Permutation p, AURC vs random | {p['perm_p']:.3f} | {s['perm_p']:.3f} |",
        f"| Confidence range (distinct values) | {p['conf_min']:.3f}–{p['conf_max']:.3f} ({p['n_conf_distinct']}) | "
        f"{s['conf_min']:.3f}–{s['conf_max']:.3f} ({s['n_conf_distinct']}) |",
        f"| GT confluency range; images below 20% | {p['gt_min']:.1f}–{p['gt_max']:.1f}%; {p['below20']} | "
        f"{s['gt_min']:.1f}–{s['gt_max']:.1f}%; {s['below20']} |",
        "",
        "The 65 are the cutoff study's rerun of the same call (float16 maps), reported, not used for the decision.",
        "",
        "### Density on held-out C2C12 frames (metric 3)",
        "",
        f"Spearman ρ(confidence, Cellpose-SAM's own reading) = **{c['rho']:+.2f}**, 95% CI {fmt_ci(c['ci'])} "
        f"(sequence bootstrap), on {c['n']} full frames from {c['sequences']} held-out sequences, readings up to "
        f"{c['pct_max']:.1f}%. The density proxy is the model's reading, not an expert mask.",
        "",
        "### Post hoc, not pre-registered",
        "",
        "Found by reading the risk–coverage plot after the decision above; it is an observation, not a test. "
        "The risk–coverage curves start high because the highest-scoring images include large misses: "
        + "; ".join(f"on the {name}, the top {t['k']} by score are off by {t['errs']} pp, and the largest error "
                    f"({t['max']:.1f} pp) scores {t['conf']:.3f}, a score {t['at_least']} of {t['of']} images "
                    "reach or exceed" for name, t in tops)
        + ". When Cellpose-SAM reads 0% "
        "(no pixel above the cutoff), few pixels are near the cutoff either, so the score is high and the "
        "frame is not sent to review:",
        "",
        "| Set | Images read as 0.0% | Their GT confluency | Their confidence |",
        "|---|---|---|---|",
        *[f"| {name} | {z['n']} of {z['of']} | {z['gt']} | {z['conf']} |" for name, z in zeros],
        "",
        "### Caveat",
        "",
        f"n = 33, {p['below20']} of them below 20% GT (range {p['gt_min']:.1f}–{p['gt_max']:.1f}%); low power; the set "
        "does not cover the passage band. A pass would be weak evidence; a fail on (a) or (b) is a failed check of "
        "the name, not proof that the score carries no information.",
        "",
    ]
    return "\n".join(lines)


def main():
    p_df, s_df = primary(), secondary()
    p, s = study(p_df), study(s_df)
    c = c2c12_study(c2c12_heldout())
    d = decide(p)

    out = pd.concat([p_df, s_df], ignore_index=True)
    out["abs_error"] = (out.pct - out.gt_pct).abs().round(2)
    out["px"] = out.width * out.height
    out.to_csv(OUT_CSV, index=False)
    plot([("33 held-out EVICAN (primary)", p), ("65 calibration EVICAN (secondary)", s)])

    with open(OUT_MD) as f:
        prereg = f.read().split(RESULTS_HEADER)[0].rstrip("\n") + "\n"
    with open(OUT_MD, "w") as f:
        f.write(prereg + results_md(p, s, c, d, [("33 held-out", zero_reads(p_df)),
                                                 ("65 calibration", zero_reads(s_df))],
                                    [("33 held-out", top_scored(p_df)), ("65 calibration", top_scored(s_df, 4))]))

    print(f"rho(conf, |err|) = {p['rho_err']:+.3f} CI [{p['rho_err_ci']['lo']:+.3f}, {p['rho_err_ci']['hi']:+.3f}]; "
          f"partial {p['partial']:+.3f}; rho(conf, GT) {p['rho_gt']:+.3f}; AURC {p['aurc']:.2f} vs random "
          f"{p['aurc_random']:.2f} / oracle {p['aurc_oracle']:.2f}, p = {p['perm_p']:.4f}; C2C12 rho(conf, pct) "
          f"{c['rho']:+.3f} -> {'KEEP' if d['keep'] else 'RENAME'}")


if __name__ == "__main__":
    main()
