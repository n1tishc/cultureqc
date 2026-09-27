"""
B0: scale-matched QC classifier test (cultureQC_upgrade_specv3.md §2B.1).

Hypothesis (spec): C2C12 frames are at a different physical scale from the
LIVECell training tiles, so C2C12 cells read as "image_quality". Pixel sizes
from the papers (configs/qc.yaml): C2C12 1.3 µm/px, LIVECell 1.243 µm/px, so
f = 1.046. That is close to 1, so a strong effect is not expected; the test
is run as specified and its result recorded either way.

Protocol, fixed before the run:
 1. Frames. Normal: every frame of the 24 base C2C12 sequences. Faults: the
    post-onset simulated contamination-onset and lamp-dimming frames whose
    pixels differ from the base frame (is_modified and sha not a base frame;
    this drops the byte-identical lamp-dim onset frame and gives the same set
    with the manifest before and after 3d0c140). Split by
    results/replay_fleet_split.csv. The file sha of every fault frame must
    match the manifest.
 2. Tuning frames: unscaled (reference), f x {0.75, 1.0, 1.25} (selectable),
    f x {0.5, 2.0} (context only, never selectable).
 3. Choice, tuning only: the selectable multiplier meeting the most pass
    criteria; ties go to higher % normal called normal, then higher
    contamination recall, then the multiplier closest to 1.
 4. Held-out frames: unscaled and the chosen multiplier only. B0 passes if
    all three hold on held-out with the chosen multiplier: normal called
    normal >= 80%, contamination recall >= 85%, normal called contamination
    <= 5%. Fail -> B3 retrain.
 5. Call = arg-max class. Temperature scaling doesn't change the arg-max.
 Frame -> tile: cv2.IMREAD_GRAYSCALE, culture.qc.rescale_frame, then
 culture.cache.qc_tile_from (the cache's own path), culture.qc._preprocess.
 Parity: unscaled logits vs the cache's qc_effnetb0_v1 logits, when given.

Outputs (--out): classifier_scale_test.md, classifier_scale_test.csv,
classifier_scale_logits.parquet (cache logits schema, rescaled model_version
tags), classifier_scale_examples.png.

Runs where the frames are: nb/04b_classifier_scale_test.ipynb on Colab
(frames from the Drive archive staged/c2c12_prepared.zip, on local disk).

Usage:
    python scripts/classifier_scale_test.py --c2c12-dir /content/data/c2c12 \
        --fault-dir /content/data/c2c12_faults --cached-logits /content/cached_logits.parquet
    python scripts/classifier_scale_test.py ... --list-only   # frame counts, no inference
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np
import pandas as pd

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from culture.cache import image_sha256, qc_tile_from  # noqa: E402
from culture.qc import (CLASS_NAMES, MODEL_VERSION, load_qc_config, rescale_factor,  # noqa: E402
                        rescale_frame, rescaled_model_version)

SELECTABLE = (0.75, 1.0, 1.25)
CONTEXT = (0.5, 2.0)
FAULT_GROUPS = ("contamination_onset", "lamp_dimming")
PASS = {"normal_called_normal": (">=", 80.0), "contamination_recall": (">=", 85.0),
        "normal_called_contamination": ("<=", 5.0)}
N_EXAMPLES = 5


def select_frames(c2c12_frames: pd.DataFrame, fault_frames: pd.DataFrame, manifest: pd.DataFrame,
                  split: pd.DataFrame, sha_of=image_sha256) -> pd.DataFrame:
    """One row per frame: image_sha256, png_path, group, split, sequence_id."""
    base_split = split[split.kind == "base"].set_index("sequence_id").split
    fault_split = split[split.kind == "fault"].set_index("sequence_id").split

    normal = c2c12_frames[c2c12_frames.sequence_id.isin(base_split.index)].copy()
    normal["image_sha256"] = normal.png_path.map(sha_of)
    normal["group"] = "normal"
    normal["split"] = normal.sequence_id.map(base_split)

    m = manifest[manifest.fault_type.isin(FAULT_GROUPS) & manifest.is_modified
                 & ~manifest.image_sha256.isin(set(normal.image_sha256))]
    fault = fault_frames.merge(m[["fault_sequence_id", "frame_idx", "fault_type", "image_sha256"]],
                               left_on=["sequence_id", "frame_idx"],
                               right_on=["fault_sequence_id", "frame_idx"], how="inner")
    fault["file_sha"] = fault.png_path.map(sha_of)
    bad = fault[fault.file_sha != fault.image_sha256]
    if len(bad):
        raise ValueError(f"{len(bad)} fault frames differ from the manifest, e.g. {bad.png_path.iloc[0]}")
    fault["group"] = fault.fault_type
    fault["split"] = fault.sequence_id.map(fault_split)

    cols = ["image_sha256", "png_path", "group", "split", "sequence_id"]
    out = pd.concat([normal[cols], fault[cols]], ignore_index=True)
    if out.split.isna().any():
        raise ValueError(f"frames without a split: {out[out.split.isna()].sequence_id.unique()[:3]}")
    return out.drop_duplicates(["image_sha256", "group", "split"]).reset_index(drop=True)


def summarize(calls: np.ndarray, groups: np.ndarray) -> dict:
    """Headline metrics (%) from arg-max calls; NaN when a group is empty."""
    def pct(g, cls):
        sel = groups == g
        return 100.0 * float((calls[sel] == CLASS_NAMES.index(cls)).mean()) if sel.any() else float("nan")
    return {"normal_called_normal": pct("normal", "normal"),
            "contamination_recall": pct("contamination_onset", "contamination_suspected"),
            "normal_called_contamination": pct("normal", "contamination_suspected"),
            "dimmed_called_contamination": pct("lamp_dimming", "contamination_suspected")}


def criteria_met(s: dict) -> dict:
    return {k: (s[k] >= v if op == ">=" else s[k] <= v) for k, (op, v) in PASS.items()}


def choose(tuning: dict) -> float:
    """tuning: multiplier -> summarize() dict, selectable multipliers only."""
    def key(mult):
        s = tuning[mult]
        return (-sum(criteria_met(s).values()), -s["normal_called_normal"], -s["contamination_recall"],
                abs(mult - 1.0))
    return min(tuning, key=key)


def infer(paths: list[str], factors: dict, batch: int = 64) -> dict:
    """factors: name -> factor (None = unscaled). Returns name -> (n, 4) logits.
    Each frame is read once; every variant's tile comes from that read."""
    import cv2
    import torch
    from culture.qc import _get_model, _preprocess

    model = _get_model()
    device = next(model.parameters()).device
    out = {k: [] for k in factors}
    pending = []

    def run():
        x = torch.stack([t for _, t in pending]).to(device)
        with torch.no_grad():
            lg = model(x).float().cpu().numpy()
        for (name, _), row in zip(pending, lg):
            out[name].append(row)
        pending.clear()

    for i, p in enumerate(paths):
        img = cv2.imread(p, cv2.IMREAD_GRAYSCALE)
        if img is None:
            raise FileNotFoundError(p)
        for name, f in factors.items():
            pending.append((name, _preprocess(qc_tile_from(rescale_frame(img, f)))))
        if len(pending) >= batch:
            run()
        if (i + 1) % 500 == 0:
            print(f"  {i + 1}/{len(paths)} frames", flush=True)
    if pending:
        run()
    return {k: np.array(v) for k, v in out.items()}


def group_rows(phase, variant, mult, factor, logits, frames) -> list[dict]:
    probs = np.exp(logits - logits.max(1, keepdims=True))
    probs /= probs.sum(1, keepdims=True)
    calls = logits.argmax(1)
    rows = []
    for g in ["normal", *FAULT_GROUPS]:
        sel = (frames.group == g).to_numpy()
        if not sel.any():
            continue
        r = {"phase": phase, "variant": variant, "multiplier": mult, "factor": factor, "group": g,
             "n_frames": int(sel.sum()), "n_sequences": int(frames[sel].sequence_id.nunique())}
        for i, c in enumerate(CLASS_NAMES):
            r[f"called_{c}_pct"] = 100.0 * float((calls[sel] == i).mean())
        for i, c in enumerate(CLASS_NAMES):
            r[f"mean_softmax_{c}"] = float(probs[sel, i].mean())
        rows.append(r)
    return rows


def examples_png(frames, factor, chosen_logits, base_logits, out_path, seed=0):
    import cv2
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rng = np.random.default_rng(seed)
    picks = []
    for g in ("normal", "contamination_onset"):
        idx = np.flatnonzero((frames.group == g).to_numpy())
        picks += [(g, i) for i in sorted(rng.choice(idx, size=min(N_EXAMPLES, len(idx)), replace=False))]
    fig, ax = plt.subplots(2, len(picks), figsize=(2.1 * len(picks), 4.8))
    for c, (g, i) in enumerate(picks):
        img = cv2.imread(frames.png_path.iloc[i], cv2.IMREAD_GRAYSCALE)
        for r, (f, lg, lab) in enumerate([(None, base_logits, "unscaled"), (factor, chosen_logits, f"x{factor:.3f}")]):
            tile = qc_tile_from(rescale_frame(img, f))
            p = np.exp(lg[i] - lg[i].max()); p /= p.sum()
            k = int(p.argmax())
            ax[r, c].imshow(tile, cmap="gray", vmin=0, vmax=255)
            ax[r, c].set_title(f"{'normal' if g == 'normal' else 'contam.'} · {lab}\n→ {CLASS_NAMES[k]} {p[k]:.2f}",
                               fontsize=7)
            ax[r, c].axis("off")
    fig.suptitle("B0 held-out examples (C2C12, Ker et al. 2018, CC BY 4.0; contamination simulated): "
                 "256 px model input and arg-max call (softmax)", fontsize=8)
    fig.tight_layout()
    fig.savefig(out_path, dpi=110)
    plt.close(fig)


def fmt(v):
    return "—" if v is None or (isinstance(v, float) and np.isnan(v)) else f"{v:.1f}%"


def write_report(path, f0, cfg, frames, tune, chosen, held, parity, device, runtime_s):
    lines = [
        "# B0: scale-matched QC classifier test", "",
        f"Generated {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} by `scripts/classifier_scale_test.py` "
        f"({device}, {runtime_s / 60:.1f} min). Spec: `cultureQC_upgrade_specv3.md` §2B.1. "
        "Images: C2C12, Ker et al., *Sci Data* 5:180237 (2018), CC BY 4.0 (**real**); contamination and lamp "
        "dimming are **simulated faults**. Classifier `qc_effnetb0_v1`, trained on synthetic tiles only.", "",
        "## Scale", "",
        f"- C2C12: {cfg['rescale']['source_um_per_px']} µm/px (Ker et al. 2018, Methods). LIVECell training "
        f"tiles: {cfg['rescale']['target_um_per_px']} µm/px (Edlund et al. 2021, Methods: 704 × 520 px = "
        "0.875 × 0.645 mm²).",
        f"- f = {f0:.3f}. Selectable f × {{{', '.join(f'{m:g}' for m in SELECTABLE)}}}; "
        f"context only f × {{{', '.join(f'{m:g}' for m in CONTEXT)}}}.", "",
        "## Frames", "",
        "| split | group | frames | sequences |", "|---|---|---|---|"]
    for (s, g), d in frames.groupby(["split", "group"]):
        lines.append(f"| {s} | {g} | {len(d)} | {d.sequence_id.nunique()} |")
    lines += ["", "## Tuning (choice made here)", "",
              "| variant | factor | normal → normal | contamination recall | normal → contamination | "
              "dimmed → contamination | criteria met |", "|---|---|---|---|---|---|---|"]
    for name, (fac, s, selectable) in tune.items():
        met = sum(criteria_met(s).values())
        lines.append(f"| {name} | {'—' if fac is None else f'{fac:.3f}'} | {fmt(s['normal_called_normal'])} | "
                     f"{fmt(s['contamination_recall'])} | {fmt(s['normal_called_contamination'])} | "
                     f"{fmt(s['dimmed_called_contamination'])} | {f'{met}/3' if selectable else 'context'} |")
    lines += ["", f"Chosen on tuning: **multiplier {chosen[0]:g} (factor {chosen[1]:.3f})**.", "",
              "## Held-out (reported once)", "",
              "| variant | normal → normal (≥ 80%) | contamination recall (≥ 85%) | normal → contamination (≤ 5%) | "
              "dimmed → contamination |", "|---|---|---|---|---|"]
    for name, s in held.items():
        lines.append(f"| {name} | {fmt(s['normal_called_normal'])} | {fmt(s['contamination_recall'])} | "
                     f"{fmt(s['normal_called_contamination'])} | {fmt(s['dimmed_called_contamination'])} |")
    s = held["chosen"]
    ok = criteria_met(s)
    verdict = "PASS: adopt the rescale, skip the retrain" if all(ok.values()) else \
        "FAIL: go to B3 retrain (`nb/05`)"
    lines += ["", f"**B0 verdict: {verdict}.** "
              + "; ".join(f"{k.replace('_', ' ')} {'met' if v else 'not met'}" for k, v in ok.items()) + ".", "",
              "## Checks", "",
              f"- Parity, unscaled vs cache `{MODEL_VERSION}` logits: {parity}.",
              "- Unscaled held-out numbers should match `results/classifier_c2c12.md` (same frames, same model).",
              "- Frames within a sequence are not independent; held-out contamination is 2 sequences.",
              "- `classifier_scale_examples.png`: 5 normal + 5 contaminated held-out frames (seed 0), "
              "unscaled vs chosen.", ""]
    with open(path, "w") as fh:
        fh.write("\n".join(lines))
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--c2c12-dir", default="/content/data/c2c12")
    ap.add_argument("--fault-dir", default="/content/data/c2c12_faults")
    ap.add_argument("--split", default=os.path.join(REPO, "results", "replay_fleet_split.csv"))
    ap.add_argument("--cached-logits", default=None, help="cache logits.parquet for the parity check")
    ap.add_argument("--out", default=os.path.join(REPO, "results"))
    ap.add_argument("--batch", type=int, default=64)
    ap.add_argument("--list-only", action="store_true")
    args = ap.parse_args()

    t0 = time.time()
    frames = select_frames(pd.read_csv(os.path.join(args.c2c12_dir, "c2c12_frames.csv")),
                           pd.read_csv(os.path.join(args.fault_dir, "fault_frames.csv")),
                           pd.read_parquet(os.path.join(args.fault_dir, "fault_manifest.parquet")),
                           pd.read_csv(args.split))
    print(frames.groupby(["split", "group"]).agg(frames=("image_sha256", "size"),
                                                 sequences=("sequence_id", "nunique")))
    if args.list_only:
        return

    import torch
    device = f"cuda ({torch.cuda.get_device_name(0)})" if torch.cuda.is_available() else "cpu"
    cfg = load_qc_config()
    f0 = rescale_factor(cfg, multiplier=1.0, force=True)
    os.makedirs(args.out, exist_ok=True)
    rows, logit_rows = [], []

    def keep_logits(fr, factor, lg):
        tag = rescaled_model_version(factor)
        logit_rows.extend({"image_sha256": s, "crop_spec": "full", "model_name": "qc", "model_version": tag,
                           "logits": json.dumps([float(x) for x in v])} for s, v in zip(fr.image_sha256, lg))

    # Tuning: every variant; the choice is made here and nowhere else.
    tf = frames[frames.split == "tuning"].reset_index(drop=True)
    variants = {"unscaled": (None, None, False)}
    variants.update({f"f x {m:g}": (m, f0 * m, True) for m in SELECTABLE})
    variants.update({f"f x {m:g}": (m, f0 * m, False) for m in CONTEXT})
    print(f"tuning: {len(tf)} frames x {len(variants)} variants")
    tl = infer(tf.png_path.tolist(), {k: v[1] for k, v in variants.items()}, args.batch)
    tune = {}
    for name, (m, fac, selectable) in variants.items():
        tune[name] = (fac, summarize(tl[name].argmax(1), tf.group.to_numpy()), selectable)
        rows += group_rows("tuning", name, m, fac, tl[name], tf)
        if fac is not None:
            keep_logits(tf, fac, tl[name])
    mult = choose({v[0]: tune[k][1] for k, v in variants.items() if v[2]})
    chosen = (mult, f0 * mult)
    print(f"chosen on tuning: multiplier {mult:g}, factor {chosen[1]:.3f}")

    # Held-out: unscaled and the chosen multiplier only.
    hf = frames[frames.split == "heldout"].reset_index(drop=True)
    print(f"held-out: {len(hf)} frames x 2 variants")
    hl = infer(hf.png_path.tolist(), {"unscaled": None, "chosen": chosen[1]}, args.batch)
    held = {"unscaled": summarize(hl["unscaled"].argmax(1), hf.group.to_numpy()),
            "chosen": summarize(hl["chosen"].argmax(1), hf.group.to_numpy())}
    rows += group_rows("heldout", "unscaled", None, None, hl["unscaled"], hf)
    rows += group_rows("heldout", f"f x {mult:g} (chosen)", mult, chosen[1], hl["chosen"], hf)
    keep_logits(hf, chosen[1], hl["chosen"])

    parity = "not run (no --cached-logits)"
    if args.cached_logits:
        c = pd.read_parquet(args.cached_logits)
        c = c[(c.model_name == "qc") & (c.model_version == MODEL_VERSION)].drop_duplicates("image_sha256")
        ref = dict(zip(c.image_sha256, c.logits))
        diffs = [np.abs(np.array(json.loads(ref[s])) - v).max()
                 for fr, lg in ((tf, tl["unscaled"]), (hf, hl["unscaled"]))
                 for s, v in zip(fr.image_sha256, lg) if s in ref]
        parity = (f"{len(diffs)} of {len(tf) + len(hf)} frames matched by sha; max |Δlogit| "
                  f"{max(diffs):.2e}" if diffs else "no frames matched by sha")

    pd.DataFrame(rows).to_csv(os.path.join(args.out, "classifier_scale_test.csv"), index=False, float_format="%.4f")
    pd.DataFrame(logit_rows).to_parquet(os.path.join(args.out, "classifier_scale_logits.parquet"), index=False)
    examples_png(hf, chosen[1], hl["chosen"], hl["unscaled"], os.path.join(args.out, "classifier_scale_examples.png"))
    print(write_report(os.path.join(args.out, "classifier_scale_test.md"), f0, cfg, frames, tune, chosen, held,
                       parity, device, time.time() - t0))


if __name__ == "__main__":
    main()
