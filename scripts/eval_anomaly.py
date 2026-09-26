"""
A4 — minimal density-conditioned anomaly scoring (cultureQC_upgrade_spec.md
§2A.5, §7), built and evaluated from the compute cache. CPU only.

Banks: normal patches (qctile) of the *tuning* C2C12 base sequences
(results/replay_fleet_split.csv), per confluency bin plus one global bank for
V4. C2C12 only: synthetic-tile patch embeddings are not in the Mac cache.
Every frame is scored against banks built without its own base sequence:
held-out frames against the bank of all 10 tuning sequences, a tuning frame
(normal or fault) against a bank rebuilt on the other 9 (leave one sequence
out, coreset rebuilt per fold, so both splits face banks built the same way).
Per-bin mean/SD/threshold come from the tuning normal frames' scores.

Evaluation, held-out only:
  - flag rate of held-out normal frames at the tuning thresholds (target: fpr)
  - V4: Spearman rho(score, confluency) on held-out normal frames, binned z vs
    global raw score (primary), per frame and per sequence
  - V5(b): AUROC held-out normal vs held-out contamination frames by severity
    (sprites per 256 px tile area); lamp dimming by factor (informational)
  - V5(a): AUROC on the synthetic test tiles per class and severity with a
    *CLS*-kNN scorer (bank: train normals, threshold: val normals) — a
    different scorer from the patch scorer above; it does not validate it.

Outputs:
    configs/anomaly.yaml                 bins, per-bin calibration, method, bank hash
    cache/anomaly/scores.parquet         every scored frame (gitignored; ~20 min to rebuild)
    cache/anomaly/banks.npz              the full-tuning banks (for the live path, B2)
    results/anomaly_summary.md, results/anomaly_v4.png, results/anomaly_v5.png

Usage:
    python scripts/eval_anomaly.py --cache-dir cache
"""

from __future__ import annotations

import argparse
import math
import os
import sys
import time

import numpy as np
import pandas as pd
import yaml

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from culture.anomaly import (bank_hash, bin_index, bin_label, greedy_coreset, image_score,  # noqa: E402
                             merge_bins, nn_distance)

DEFAULTS = {
    "crop_spec": "qctile",
    "bin_edges": [0.0, 20.0, 40.0, 60.0, 80.0, 100.0],
    "min_sequences_per_bin": 3,
    "coreset_frac": 0.10,
    "proj_dim": 128,
    "top_frac": 0.01,
    "fpr": 0.05,
    "seed": 0,
}
DATASET = "c2c12"


def _log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def frames_table(cache_dir: str, split_path: str) -> pd.DataFrame:
    """Every frame to score: C2C12 base frames and modified fault frames, with
    their own full-frame confluency, base sequence and split."""
    images = pd.read_parquet(os.path.join(cache_dir, "images.parquet"))
    conf = pd.read_parquet(os.path.join(cache_dir, "confluency.parquet"))
    full = conf[(conf.model_name == "seg") & (conf.crop_spec == "full")].drop_duplicates("image_sha256")
    pct = dict(zip(full.image_sha256, full.pct))
    split = pd.read_csv(split_path)
    base_split = split[split.kind == "base"].set_index("sequence_id").split

    base = images[images.dataset == DATASET][["image_sha256", "sequence_id", "frame_idx"]].copy()
    base["base_sequence_id"] = base.sequence_id
    base["kind"], base["severity"], base["fault_sequence_id"] = "normal", np.nan, ""
    base_key = {(r.sequence_id, int(r.frame_idx)): r.image_sha256 for r in base.itertuples()}

    man = pd.read_parquet(os.path.join(cache_dir, "sidecars", "fault_manifest.parquet"))
    mod = man[man.is_modified].copy()
    mod["kind"] = mod.fault_type
    mod["base_sha"] = [base_key.get((b, int(f))) for b, f in zip(mod.base_sequence_id, mod.frame_idx)]
    mod = mod[["image_sha256", "base_sequence_id", "kind", "severity", "fault_sequence_id", "base_sha", "frame_idx"]]
    df = pd.concat([base.drop(columns="sequence_id"), mod], ignore_index=True)
    df["split"] = df.base_sequence_id.map(base_split)
    if df.split.isna().any():
        raise SystemExit("frames whose base sequence is not in the split file")
    df["pct"] = df.image_sha256.map(pct)
    df["base_pct"] = df.base_sha.map(pct)
    if df.pct.isna().any():
        raise SystemExit(f"{int(df.pct.isna().sum())} frames without a full-frame seg row")
    return df.drop_duplicates("image_sha256").reset_index(drop=True)


def effective_edges(frames: pd.DataFrame, cfg: dict) -> tuple[list[float], dict]:
    edges0 = [float(e) for e in cfg["bin_edges"]]
    tune = frames[(frames.kind == "normal") & (frames.split == "tuning")]
    idx0 = tune.pct.apply(lambda p: bin_index(p, edges0))
    counts = [int(tune[idx0 == i].base_sequence_id.nunique()) for i in range(len(edges0) - 1)]
    edges = merge_bins(edges0, counts, cfg["min_sequences_per_bin"])
    idx = tune.pct.apply(lambda p: bin_index(p, edges))
    final = [int(tune[idx == i].base_sequence_id.nunique()) for i in range(len(edges) - 1)]
    if min(final) < cfg["min_sequences_per_bin"]:
        # merge_bins approximates merged counts by a sum; recheck with real distinct counts
        edges = merge_bins(edges, final, cfg["min_sequences_per_bin"])
    return edges, {"configured_edges": edges0, "tuning_sequences_per_configured_bin": counts}


def load_all_patches(cache_dir: str, shas, crop_spec: str) -> dict:
    out = {}
    for sha in shas:
        x = np.load(os.path.join(cache_dir, "embeddings", f"{sha}_{crop_spec}.npy")).astype(np.float32)
        out[sha] = (x / (np.linalg.norm(x, axis=1, keepdims=True) + 1e-8)).astype(np.float16)
    return out


def build_bank(patches: dict, shas: list[str], cfg: dict) -> np.ndarray:
    x = np.concatenate([patches[s] for s in shas]).astype(np.float32)
    n = max(1, int(math.ceil(cfg["coreset_frac"] * len(x))))
    return x[greedy_coreset(x, n, seed=cfg["seed"], proj_dim=cfg["proj_dim"])]


def score_frames(frames: pd.DataFrame, patches: dict, edges: list[float], cfg: dict) -> tuple[pd.DataFrame, dict]:
    """score_binned / score_global for every frame, each against banks that
    exclude the frame's own base sequence."""
    frames = frames.copy()
    frames["bin"] = frames.pct.apply(lambda p: bin_index(p, edges))
    tune = frames[(frames.kind == "normal") & (frames.split == "tuning")]
    tuning_seqs = sorted(tune.base_sequence_id.unique())
    folds = [None] + tuning_seqs
    frames["fold"] = [s if s in set(tuning_seqs) else None for s in frames.base_sequence_id]

    full_banks = {}
    scores_b = np.full(len(frames), np.nan)
    scores_g = np.full(len(frames), np.nan)
    for fold in folds:
        members = tune if fold is None else tune[tune.base_sequence_id != fold]
        todo = frames[frames.fold.isna()] if fold is None else frames[frames.fold == fold]
        if len(todo) == 0:
            continue
        banks = {}
        for b in range(len(edges) - 1):
            shas = list(members[members.bin == b].image_sha256)
            if shas:
                banks[b] = build_bank(patches, shas, cfg)
        banks["global"] = build_bank(patches, list(members.image_sha256), cfg)
        if fold is None:
            full_banks = banks
        for i, r in zip(todo.index, todo.itertuples()):
            q = patches[r.image_sha256].astype(np.float32)
            b = r.bin if r.bin in banks else min(banks.keys() - {"global"}, key=lambda k: abs(k - r.bin))
            scores_b[i] = image_score(nn_distance(q, banks[b]), cfg["top_frac"])
            scores_g[i] = image_score(nn_distance(q, banks["global"]), cfg["top_frac"])
        _log(f"fold {fold or 'all tuning'}: scored {len(todo)} frames; bank sizes "
             + ", ".join(f"{k}:{len(v)}" for k, v in banks.items()))
    frames["score_binned"], frames["score_global"] = scores_b, scores_g
    return frames, full_banks


def calibrate(frames: pd.DataFrame, edges: list[float], cfg: dict) -> dict:
    tune = frames[(frames.kind == "normal") & (frames.split == "tuning")]
    q = 1.0 - cfg["fpr"]
    bins = {}
    for b in range(len(edges) - 1):
        s = tune[tune.bin == b]
        bins[bin_label(b, edges)] = {
            "lo": edges[b], "hi": edges[b + 1], "n_frames": int(len(s)),
            "n_sequences": int(s.base_sequence_id.nunique()),
            "mean": round(float(s.score_binned.mean()), 6), "sd": round(float(s.score_binned.std(ddof=1)), 6),
            "threshold": round(float(s.score_binned.quantile(q)), 6)}
    g = tune.score_global
    glob = {"n_frames": int(len(tune)), "n_sequences": int(tune.base_sequence_id.nunique()),
            "mean": round(float(g.mean()), 6), "sd": round(float(g.std(ddof=1)), 6),
            "threshold": round(float(g.quantile(q)), 6)}
    return {"bins": bins, "global": glob}


def apply_calibration(frames: pd.DataFrame, cal: dict, edges: list[float]) -> pd.DataFrame:
    frames = frames.copy()
    labels = [bin_label(b, edges) for b in frames.bin]
    mean = np.array([cal["bins"][lb]["mean"] for lb in labels])
    sd = np.array([cal["bins"][lb]["sd"] for lb in labels])
    thr = np.array([cal["bins"][lb]["threshold"] for lb in labels])
    frames["bin_label"] = labels
    frames["z_binned"] = (frames.score_binned - mean) / sd
    frames["flag_binned"] = frames.score_binned > thr
    g = cal["global"]
    frames["z_global"] = (frames.score_global - g["mean"]) / g["sd"]
    frames["flag_global"] = frames.score_global > g["threshold"]
    return frames


def _auroc(neg, pos):
    from sklearn.metrics import roc_auc_score
    if len(neg) == 0 or len(pos) == 0:
        return None
    return float(roc_auc_score(np.r_[np.zeros(len(neg)), np.ones(len(pos))], np.r_[neg, pos]))


def v5a_cls_knn(cache_dir: str, manifest_path: str, cfg: dict) -> pd.DataFrame | None:
    """Synthetic tiles, CLS-kNN: bank = train normals, threshold = val normals, AUROC on test."""
    if not os.path.exists(manifest_path):
        return None
    images = pd.read_parquet(os.path.join(cache_dir, "images.parquet"))
    cls = pd.read_parquet(os.path.join(cache_dir, "embeddings_cls.parquet"))
    cls = cls[cls.crop_spec == "full"].drop_duplicates("image_sha256")
    tiles = images[images.dataset == "synth_tiles"][["image_sha256", "source_path"]].copy()
    tiles["tile_id"] = tiles.source_path.apply(os.path.basename)
    man = pd.read_csv(manifest_path)
    df = tiles.merge(man[["tile_id", "class", "severity", "split"]], on="tile_id").merge(
        cls[["image_sha256", "cls", "cls_dtype", "cls_dim"]], on="image_sha256")
    x = np.stack([np.frombuffer(r.cls, dtype=r.cls_dtype).reshape(r.cls_dim) for r in df.itertuples()]).astype(np.float32)
    x /= np.linalg.norm(x, axis=1, keepdims=True) + 1e-8
    train = (df["class"] == "normal") & (df.split == "train")
    d = nn_distance(x, x[train.to_numpy()])
    d[train.to_numpy()] = np.nan  # a train normal is its own nearest neighbour
    df["score"] = d
    val_n = df[(df.split == "val") & (df["class"] == "normal")].score
    thr = float(val_n.quantile(1 - cfg["fpr"]))
    test = df[df.split == "test"]
    neg = test[test["class"] == "normal"].score.to_numpy()
    rows = [{"class": "all non-normal", "severity": "all", "n": int((test["class"] != "normal").sum()),
             "auroc": _auroc(neg, test[test["class"] != "normal"].score.to_numpy()),
             "tpr_at_val_thr": float((test[test["class"] != "normal"].score > thr).mean())}]
    for (c, sev), g in test[test["class"] != "normal"].groupby(["class", "severity"]):
        rows.append({"class": c, "severity": sev, "n": int(len(g)), "auroc": _auroc(neg, g.score.to_numpy()),
                     "tpr_at_val_thr": float((g.score > thr).mean())})
    for c, g in test[test["class"] != "normal"].groupby("class"):
        rows.append({"class": c, "severity": "all", "n": int(len(g)), "auroc": _auroc(neg, g.score.to_numpy()),
                     "tpr_at_val_thr": float((g.score > thr).mean())})
    out = pd.DataFrame(rows)
    out.attrs.update({"n_test_normal": int(len(neg)), "val_fpr_at_thr": float((test[test['class'] == 'normal'].score > thr).mean()),
                      "n_bank": int(train.sum())})
    return out


def plots(frames: pd.DataFrame, v5: pd.DataFrame, edges, out_dir: str):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    held = frames[(frames.split == "heldout") & (frames.kind == "normal")]
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
    ax[0].scatter(held.pct, held.z_global, s=6, alpha=0.5)
    ax[0].set(title="Global bank (z vs global normal stats)", xlabel="full-frame confluency (%)", ylabel="z")
    ax[1].scatter(held.pct, held.z_binned, s=6, alpha=0.5, color="tab:orange")
    for e in edges[1:-1]:
        ax[1].axvline(e, color="grey", lw=0.8, ls="--")
    ax[1].set(title="Density-conditioned banks (z per bin)", xlabel="full-frame confluency (%)", ylabel="z")
    fig.suptitle("V4: anomaly score vs confluency, held-out normal C2C12 frames "
                 f"({held.base_sequence_id.nunique()} sequences, {len(held)} frames)")
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "anomaly_v4.png"), dpi=130)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.5, 4))
    for col, lab in [("auroc_binned", "binned z"), ("auroc_global", "global score")]:
        ax.plot(v5.band, v5[col], marker="o", label=lab)
    ax.axhline(0.85, color="grey", ls="--", lw=0.8)
    ax.set(ylim=(0, 1.02), xlabel="contamination severity (sprites per tile area)", ylabel="AUROC vs held-out normal",
           title="V5(b): held-out contamination frames")
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "anomaly_v5.png"), dpi=130)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cache-dir", default="cache")
    ap.add_argument("--split", default=os.path.join(REPO, "results", "replay_fleet_split.csv"))
    ap.add_argument("--tiles-manifest", default=os.path.join(REPO, "data", "tiles", "manifest.csv"))
    ap.add_argument("--config-out", default=os.path.join(REPO, "configs", "anomaly.yaml"))
    ap.add_argument("--out", default=os.path.join(REPO, "results"))
    ap.add_argument("--coreset-frac", type=float, default=DEFAULTS["coreset_frac"])
    ap.add_argument("--summary-only", action="store_true",
                    help="rewrite the summary and plots from cache/anomaly/scores.parquet and --config-out")
    args = ap.parse_args()
    cfg = {**DEFAULTS, "coreset_frac": args.coreset_frac}
    if args.summary_only:
        frames = pd.read_parquet(os.path.join(args.cache_dir, "anomaly", "scores.parquet"))
        with open(args.config_out) as f:
            doc = yaml.safe_load(f)
        write_summary(frames, doc["calibration"], doc["bins"]["edges"], doc,
                      v5a_cls_knn(args.cache_dir, args.tiles_manifest, cfg), args)
        return

    frames = frames_table(args.cache_dir, args.split)
    edges, bin_info = effective_edges(frames, cfg)
    _log(f"{len(frames)} frames to score; bins {edges}")
    patches = load_all_patches(args.cache_dir, frames.image_sha256, cfg["crop_spec"])
    frames, banks = score_frames(frames, patches, edges, cfg)
    cal = calibrate(frames, edges, cfg)
    frames = apply_calibration(frames, cal, edges)

    os.makedirs(os.path.join(args.cache_dir, "anomaly"), exist_ok=True)
    frames.drop(columns=["fold"]).to_parquet(os.path.join(args.cache_dir, "anomaly", "scores.parquet"), index=False)
    bank_arrays = {("bin_" + bin_label(k, edges) if k != "global" else "global"): v for k, v in banks.items()}
    np.savez(os.path.join(args.cache_dir, "anomaly", "banks.npz"), **bank_arrays)
    bhash = bank_hash([bank_arrays[k] for k in sorted(bank_arrays)])

    doc = {
        "method": {
            "backbone": "facebook/dinov2-small", "crop_spec": cfg["crop_spec"], "distance": "cosine, nearest patch",
            "image_score": f"mean of top {cfg['top_frac']:.0%} patch distances", "top_frac": cfg["top_frac"],
            "coreset": "greedy k-center on a seeded Gaussian projection", "coreset_frac": cfg["coreset_frac"],
            "proj_dim": cfg["proj_dim"], "seed": cfg["seed"],
            "references": ["AnomalyDINO (Damm et al., WACV 2025)", "PatchCore (Roth et al., CVPR 2022)"]},
        "bins": {"edges": edges, "bin_by": "full-frame Cellpose-SAM confluency",
                 "merge_rule": f"bins with < {cfg['min_sequences_per_bin']} tuning sequences merge into a neighbour",
                 **bin_info},
        "fpr": cfg["fpr"],
        "calibration": cal,
        "bank": {"datasets": [DATASET], "frames": "normal frames of the tuning base sequences",
                 "split_file": os.path.relpath(args.split, REPO), "sha256": bhash,
                 "sizes": {k: int(len(v)) for k, v in bank_arrays.items()},
                 "synthetic_tiles": "not included (no synthetic patch embeddings in the Mac cache)"},
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    with open(args.config_out, "w") as f:
        yaml.safe_dump(doc, f, sort_keys=False)

    write_summary(frames, cal, edges, doc, v5a_cls_knn(args.cache_dir, args.tiles_manifest, cfg), args)
    _log("done")


def write_summary(frames, cal, edges, doc, v5a, args):
    from scipy.stats import spearmanr

    held = frames[frames.split == "heldout"]
    hn = held[held.kind == "normal"]
    lines = ["# A4: density-conditioned anomaly scoring (minimal)", "",
             f"Generated {doc['generated_at']} by `scripts/eval_anomaly.py`. C2C12 images: Ker et al., *Sci Data* "
             "5:180237 (2018), CC BY 4.0; fault frames are simulated from them.", "",
             "**Method.** DINOv2-small patch embeddings of each frame's 256 px centre tile (`qctile`, about 4.5% of a "
             "1392×1040 frame). Patch distance = cosine distance to the nearest normal patch; image score = mean of "
             "the top 1% of patch distances (AnomalyDINO). Banks = greedy k-center coresets "
             f"({cfg_pct(doc)} of patches; PatchCore) of the tuning sequences' normal frames, one per confluency "
             "bin (bin = full-frame Cellpose-SAM confluency) and one global. C2C12 only: no synthetic tiles in the "
             "banks. Every frame is scored against banks rebuilt without its own base sequence.", "",
             f"Bins: {', '.join(bin_label(b, edges) for b in range(len(edges) - 1))}% (configured "
             f"{doc['bins']['configured_edges']}; {doc['bins']['merge_rule']}).", "",
             "## Per-bin calibration (tuning normal frames)", "",
             "| bin | tuning sequences | tuning frames | bank patches | mean | SD | threshold (5% FPR) | "
             "held-out normal frames | held-out flag rate |", "|---|---|---|---|---|---|---|---|---|"]
    for b in range(len(edges) - 1):
        lb = bin_label(b, edges)
        c = cal["bins"][lb]
        h = hn[hn.bin == b]
        lines.append(f"| {lb}% | {c['n_sequences']} | {c['n_frames']} | {doc['bank']['sizes'].get('bin_' + lb, 0)} | "
                     f"{c['mean']:.4f} | {c['sd']:.4f} | {c['threshold']:.4f} | {len(h)} | "
                     f"{h.flag_binned.mean():.1%} |" if len(h) else
                     f"| {lb}% | {c['n_sequences']} | {c['n_frames']} | {doc['bank']['sizes'].get('bin_' + lb, 0)} | "
                     f"{c['mean']:.4f} | {c['sd']:.4f} | {c['threshold']:.4f} | 0 | — |")
    g = cal["global"]
    lines += [f"| global | {g['n_sequences']} | {g['n_frames']} | {doc['bank']['sizes']['global']} | {g['mean']:.4f} "
              f"| {g['sd']:.4f} | {g['threshold']:.4f} | {len(hn)} | {hn.flag_global.mean():.1%} |", "",
              f"Held-out normal flag rate overall: binned {hn.flag_binned.mean():.1%}, global "
              f"{hn.flag_global.mean():.1%} (target {doc['fpr']:.0%}; {hn.base_sequence_id.nunique()} sequences). "
              "Per sequence (binned): " + ", ".join(
                  f"{s.replace('c2c12_', '').replace('_Data', '')} {v:.0%}"
                  for s, v in hn.groupby('base_sequence_id').flag_binned.mean().items()) + "."]

    rho_z = spearmanr(hn.z_binned, hn.pct).statistic
    rho_bs = spearmanr(hn.score_binned, hn.pct).statistic
    rho_g = spearmanr(hn.score_global, hn.pct).statistic
    per = []
    for s, gs in hn.groupby("base_sequence_id"):
        if gs.pct.nunique() > 2:
            per.append({"seq": s, "z_binned": spearmanr(gs.z_binned, gs.pct).statistic,
                        "global": spearmanr(gs.score_global, gs.pct).statistic})
    per = pd.DataFrame(per)
    v4_pass = abs(rho_z) <= 0.3 and abs(rho_z) < abs(rho_g)
    lines += ["", "## V4: does density conditioning remove the growth confound?", "",
              "Spearman ρ between anomaly score and full-frame confluency on held-out normal frames. Pass (spec): "
              "binned |ρ| ≤ 0.3 and clearly below global. Frames within a sequence follow time, so ρ per sequence "
              "is shown too.", "",
              "| score | ρ over all frames | median ρ per sequence (IQR) |", "|---|---|---|",
              f"| binned z (primary; what SPC trends) | {rho_z:+.2f} | {per.z_binned.median():+.2f} "
              f"({per.z_binned.quantile(.25):+.2f} to {per.z_binned.quantile(.75):+.2f}) |",
              f"| global raw score | {rho_g:+.2f} | {per['global'].median():+.2f} "
              f"({per['global'].quantile(.25):+.2f} to {per['global'].quantile(.75):+.2f}) |",
              f"| binned raw score (secondary) | {rho_bs:+.2f} | — |", "",
              f"n = {len(hn)} frames, {hn.base_sequence_id.nunique()} sequences ({len(per)} with a per-sequence ρ). "
              f"**V4: {'pass' if v4_pass else 'fail'}** on these numbers "
              f"(|ρ| binned {abs(rho_z):.2f} vs global {abs(rho_g):.2f}). Plot: `results/anomaly_v4.png`."]
    band = (hn.pct // 10 * 10).clip(upper=50)
    shape = hn.assign(band=band).groupby("band").agg(n=("pct", "size"), seqs=("base_sequence_id", "nunique"),
                                                     z_global=("z_global", "mean"), z_binned=("z_binned", "mean"))
    lines += ["", "**Shape diagnostic (not the V4 metric).** Spearman ρ only sees monotone trends. Mean z of held-out "
              "normal frames per 10-pp confluency band (global z uses the global bank's tuning mean/SD):", "",
              "| confluency | frames | sequences | mean z, global | mean z, binned |", "|---|---|---|---|---|"]
    for b, r in shape.iterrows():
        lab = f"{b:g}–{b + 10:g}%" if b < 50 else f"≥ {b:g}%"
        lines.append(f"| {lab} | {int(r.n)} | {int(r.seqs)} | {r.z_global:+.2f} | {r.z_binned:+.2f} |")

    hc = held[held.kind == "contamination_onset"].copy()
    bands = [(0, 150, "<150"), (150, 1e9, "≥150")]
    v5 = []
    for lo, hi, lab in bands:
        pos = hc[(hc.severity >= lo) & (hc.severity < hi)]
        v5.append({"band": lab, "n_frames": len(pos), "n_sequences": pos.fault_sequence_id.nunique(),
                   "auroc_binned": _auroc(hn.z_binned.to_numpy(), pos.z_binned.to_numpy()),
                   "auroc_global": _auroc(hn.score_global.to_numpy(), pos.score_global.to_numpy()),
                   "flag_binned": pos.flag_binned.mean() if len(pos) else np.nan})
    v5 = pd.DataFrame(v5)
    shift = (hc.pct - hc.base_pct)
    bin_moved = (hc.bin != hc.base_pct.apply(lambda p: bin_index(p, edges))).mean() if len(hc) else np.nan
    lines += ["", "## V5(b): held-out contamination frames vs held-out normal frames", "",
              "Severity = sprites per 256×256 px tile area (the ramp runs 20 → 400 after onset). Pass (spec): "
              "AUROC ≥ 0.85 at severity ≥ 150.", "",
              "| severity | frames | fault sequences | AUROC (binned z) | AUROC (global score) | flagged at bin threshold |",
              "|---|---|---|---|---|---|"]
    for r in v5.itertuples():
        lines.append(f"| {r.band} | {r.n_frames} | {r.n_sequences} | {fmt(r.auroc_binned)} | {fmt(r.auroc_global)} | "
                     f"{fmt_pct(r.flag_binned)} |")
    hi_auc = v5[v5.band == "≥150"].auroc_binned.iloc[0]
    lines += ["", f"**V5(b): {verdict(hi_auc, 0.85)}** (n = {hc.fault_sequence_id.nunique()} held-out contamination "
              "sequences; frames within a sequence are not independent). Contaminated frames are binned by their own "
              f"Cellpose-SAM confluency, as the live system would: the sprites shift it by a median {shift.median():+.1f} pp "
              f"from the base frame (IQR {shift.quantile(.25):+.1f} to {shift.quantile(.75):+.1f}), and "
              f"{bin_moved:.0%} of these frames land in a different bin than their base frame. Plot: "
              "`results/anomaly_v5.png`."]

    hd = held[held.kind == "lamp_dimming"]
    if len(hd):
        lines += ["", "Lamp dimming (informational; V7 wants it handled as instrument drift, not per flask):", "",
                  "| intensity factor | frames | AUROC (binned z) | flagged |", "|---|---|---|---|"]
        for lo, hi in [(0.0, 0.7), (0.7, 0.8), (0.8, 0.9), (0.9, 1.0)]:
            g = hd[(hd.severity > lo) & (hd.severity <= hi)]
            lines.append(f"| ({lo:g}, {hi:g}] | {len(g)} | {fmt(_auroc(hn.z_binned.to_numpy(), g.z_binned.to_numpy()))} | "
                         f"{fmt_pct(g.flag_binned.mean() if len(g) else np.nan)} |")

    lines += ["", "## V5(a): synthetic test tiles (CLS-kNN — a different scorer)", ""]
    if v5a is None:
        lines.append("Not run: `data/tiles/manifest.csv` is missing.")
    else:
        lines += ["Synthetic tiles have only CLS embeddings in the Mac cache, so this uses the image-level CLS "
                  "vector (cosine distance to the nearest train-normal CLS), not the patch scorer above. It says how "
                  "separable the synthetic classes are at image level; it does not validate the C2C12 path. "
                  f"Bank: {v5a.attrs['n_bank']} train normal tiles; threshold at 5% FPR on val normals (test normal "
                  f"FPR at it: {v5a.attrs['val_fpr_at_thr']:.1%}, n = {v5a.attrs['n_test_normal']}). Pass (spec): "
                  "AUROC ≥ 0.85 per class.", "",
                  "| class | severity | test tiles | AUROC | TPR at val threshold |", "|---|---|---|---|---|"]
        for r in v5a.itertuples():
            lines.append(f"| {r._1} | {r.severity} | {r.n} | {fmt(r.auroc)} | {r.tpr_at_val_thr:.0%} |")
        per_class = v5a[(v5a.severity == "all") & (v5a["class"] != "all non-normal")]
        lines += ["", f"**V5(a): {'pass' if (per_class.auroc >= 0.85).all() else 'fail'}** for the CLS-kNN scorer "
                  "(per class: " + ", ".join(f"{r._1} {r.auroc:.2f}" for r in per_class.itertuples()) + ")."]

    lines += ["", "## Notes", "",
              "- The confluency bin comes from the full frame, but the score from the centre tile only; a tile's "
              "local density can differ from its bin (STATUS item 11).",
              "- Tuning frames were scored leave-one-sequence-out, with each fold's coresets rebuilt, so the "
              "calibration and the held-out scores use banks built the same way.",
              "- Scores for every frame, tuning and held-out, faults included, are in `cache/anomaly/scores.parquet` "
              "for A6/A7 (regenerate with this script).", ""]
    plots(frames, v5, edges, args.out)
    with open(os.path.join(args.out, "anomaly_summary.md"), "w") as f:
        f.write("\n".join(lines))
    print("\n".join(lines))


def cfg_pct(doc):
    return f"{doc['method']['coreset_frac']:.0%}"


def fmt(x):
    return "—" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x:.2f}"


def fmt_pct(x):
    return "—" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x:.0%}"


def verdict(auc, thr):
    if auc is None or (isinstance(auc, float) and np.isnan(auc)):
        return "not measurable"
    return "pass" if auc >= thr else "fail"


if __name__ == "__main__":
    main()
