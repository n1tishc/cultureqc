#!/usr/bin/env python3
"""
scripts/contamination_scale.py — V5 at a realistic bacterial scale.

The contamination fault set (scripts/make_fault_set.py, run in nb/03) pastes
DeepBacs bacteria, imaged at 79 nm/px, pixel for pixel into 1.3 µm/px C2C12
frames, so they are 16.5× too large (docs/ARCHITECTURE_VALIDATION.md, V5
correction). This script rebuilds the same fault frames with the bacteria
shrunk to the frame's pixel size and scores them with the live path's models on
this machine. The design was fixed before any realistic-scale output was seen:

  - sprite scale 0.079 / 1.3 (1/16.46); same seed, sequences, onset, density
    ramp (20 -> 400 sprites per 256 px tile area) and frames as the original;
  - frozen anomaly calibration (configs/anomaly.yaml), frozen rules, frozen
    confidence floor; nothing is tuned, and the result is reported as it comes;
  - two variants: with the simulator's turbidity haze, as the original, and
    without it, because the haze strength follows the sprite count, not the
    sprite size, so on its own it could make a flag look like detection;
  - controls: at scale 1 the same builder must reproduce the original fault
    frames byte for byte (sha256 in the cache's fault_manifest.parquet), and
    the same scorer on those frames is compared with the cache's values.

Scoring follows scripts/eval_anomaly.py: held-out frames against the full
tuning banks (the live path's banks.npz), tuning frames against a bank rebuilt
without their own base sequence. Bins, per-bin thresholds and z come from
configs/anomaly.yaml.

Subcommands (outputs under --work, default data/contamination_scale/, not committed):
  fetch   raw TIFFs of the needed base frames from OSF (inventory from
          `scripts/fetch_c2c12.py discover`), converted with the stored
          normalization; every PNG is checked against the cache's sha256
  build   fault frames for one variant (--scale, --no-haze)
  score   confluency, confidence, quality gate and anomaly score per frame
  report  results/contamination_scale.md from the scored variants

C2C12 images: Ker et al., Sci Data 5:180237 (2018), CC BY 4.0. Bacteria:
DeepBacs (Zenodo 5550935), 79 nm/px.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import time

import numpy as np
import pandas as pd

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in (REPO, os.path.join(REPO, "scripts")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import make_fault_set as mfs  # noqa: E402

REALISTIC = round(0.079 / 1.3, 6)          # DeepBacs 79 nm/px -> C2C12 1.3 µm/px
SIDECARS = os.path.join(REPO, "cache", "sidecars")
WORK = os.path.join(REPO, "data", "contamination_scale")
SPRITE_DIR = os.path.join(REPO, "data", "sprites", "bacteria")
DEMO_FIGURE = os.path.join(REPO, "demo", "figures", "contamination_scale.png")


def variant_name(scale: float, haze: bool) -> str:
    return f"scale{scale:g}_{'haze' if haze else 'nohaze'}"


def _sha(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def fault_frames() -> tuple[dict, pd.DataFrame]:
    """The original contamination design and its post-onset grid, per sequence."""
    with open(os.path.join(SIDECARS, "fault_config.json")) as f:
        cfg = json.load(f)
    frames = pd.read_csv(os.path.join(SIDECARS, "c2c12_frames.csv"))
    seqs = pd.read_csv(os.path.join(SIDECARS, "c2c12_sequences.csv"))
    seq_ids = sorted(seqs.sequence_id)
    order = np.random.default_rng(cfg["seed"]).permutation(len(seq_ids))
    ids = [seq_ids[i] for i in order[:cfg["contamination"]["n_sequences"]]]
    if ids != cfg["contamination_sequences"]:
        raise SystemExit(f"sequence choice does not reproduce: {ids} vs {cfg['contamination_sequences']}")
    cc, rows = cfg["contamination"], []
    for sid in ids:
        base = frames[frames.sequence_id == sid].sort_values("hours_since_start")
        onset_h = cc["onset_frac"] * base.hours_since_start.max()
        for _, r in mfs._post_onset_grid(base, onset_h, cc["stride_hours"]).iterrows():
            rows.append({"base_sequence_id": sid, "fault_sequence_id": f"{sid}__fault_contam",
                         "onset_hours": onset_h, "frame_idx": int(r.frame_idx), "timestamp": r.timestamp,
                         "hours_since_start": float(r.hours_since_start),
                         "severity": float(mfs._ramp(r.hours_since_start, onset_h, cc["ramp_hours"],
                                                     cc["density_start"], cc["density_end"]))})
    return cfg, pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# fetch
# ---------------------------------------------------------------------------

def cmd_fetch(a):
    import fetch_c2c12 as fc

    _, grid = fault_frames()
    seqs = pd.read_csv(os.path.join(SIDECARS, "c2c12_sequences.csv")).set_index("sequence_id")
    with open(os.path.join(SIDECARS, "c2c12_normalization.json")) as f:
        norm = json.load(f)
    with open(a.inventory) as f:
        inv = json.load(f)
    listing = {tf["path"].rstrip("/"): tf["listing"] for tf in inv["tiff_folders"]}
    images = pd.read_parquet(os.path.join(REPO, "cache", "images.parquet"))
    want_sha = {(r.sequence_id, int(r.frame_idx)): r.image_sha256
                for r in images[images.dataset == "c2c12"].itertuples()}
    bad = []
    for sid, g in grid.groupby("base_sequence_id"):
        path = seqs.loc[sid, "source_path"].rstrip("/")
        key = next((k for k in listing if k.endswith(path) or path.endswith(k)), None)
        if key is None:
            raise SystemExit(f"{sid}: {path} not in the inventory")
        entries = [e for e in fc._list_full(listing[key]) if e["name"].lower().endswith(fc.TIFF_EXT)]
        by_idx = {fc.frame_index(e["name"]): e for e in entries}
        for fi in sorted(g.frame_idx):
            raw = os.path.join(a.work, "raw", sid, f"{fi:05d}.tif")
            png = os.path.join(a.work, "base", sid, f"{fi:05d}.png")
            fc._download(by_idx[fi]["download"], raw)
            fc.write_png(png, fc.to_uint8(fc.read_raw(raw), norm))
            if _sha(png) != want_sha.get((sid, fi)):
                bad.append(f"{sid}/{fi}")
        print(f"{sid}: {len(g)} base frames")
    print(f"base PNGs matching the cache's sha256: {len(grid) - len(bad)}/{len(grid)}", bad or "")
    with open(os.path.join(a.work, "fetch.json"), "w") as f:
        json.dump({"n": len(grid), "matching": len(grid) - len(bad), "mismatched": bad}, f)
    if bad:
        raise SystemExit("base frames differ from the originals")


# ---------------------------------------------------------------------------
# build
# ---------------------------------------------------------------------------

def scale_sprites(sprites: list[np.ndarray], factor: float) -> list[np.ndarray]:
    """Shrink RGBA sprites by `factor` (area-averaged, so a sub-pixel bacterium
    becomes a partly transparent pixel). Each sprite is first padded to a square
    as wide as its diagonal, so add_bacteria's rotation cannot clip it; the
    colour is averaged premultiplied by alpha, and pixels the bacterium does not
    cover take its mean grey, so add_bacteria's contrast match sees the
    bacterium's own brightness."""
    import cv2

    if factor == 1.0:
        return sprites
    out = []
    for s in sprites:
        h, w = s.shape[:2]
        n = max(1, int(math.ceil(math.hypot(h, w) * factor)))
        d = int(round(n / factor))                 # canvas so that n / d is the factor to within 1/d
        if d < math.hypot(h, w):
            n += 1
            d = int(round(n / factor))
        pad = np.zeros((d, d, 4), np.float32)
        y0, x0 = (d - h) // 2, (d - w) // 2
        pad[y0:y0 + h, x0:x0 + w] = s
        alpha, grey = pad[..., 3] / 255.0, pad[..., 0]
        a_s = cv2.resize(alpha, (n, n), interpolation=cv2.INTER_AREA)
        pg_s = cv2.resize(grey * alpha, (n, n), interpolation=cv2.INTER_AREA)
        mean_grey = float((grey * alpha).sum() / max(alpha.sum(), 1e-6))
        g_s = np.where(a_s > 1e-3, pg_s / np.maximum(a_s, 1e-3), mean_grey)
        out.append(np.dstack([g_s, g_s, g_s, a_s * 255.0]).clip(0, 255).round().astype(np.uint8))
    return out


def inject(img8: np.ndarray, sprites: list, density_per_tile: float, synth, rng, haze: bool) -> tuple:
    """make_fault_set.inject_bacteria_frame, plus: the placed count is returned,
    and the haze can be left off. Its random grid is drawn either way, so both
    variants place the same bacteria in the same spots."""
    import cv2

    h, w = img8.shape[:2]
    total = int(round(density_per_tile * (h * w) / mfs.TILE_AREA))
    bg_mask = ~synth.get_cell_mask(img8)
    out, placed_total, key = img8.copy(), 0, "__fault_call__"
    try:
        remaining = total
        while remaining > 0:
            n = min(mfs.SPRITES_PER_CALL, remaining)
            synth.SEVERITY_RANGES[key] = (n, n + 1)
            out, placed = synth.add_bacteria(out, bg_mask, sprites, severity=key, rng=rng)
            placed_total += placed
            remaining -= n
    finally:
        synth.SEVERITY_RANGES.pop(key, None)
    s = min(placed_total * mfs.TILE_AREA / (h * w) / 2000.0, 0.3)
    if s > 0.01:
        gh, gw = max(1, h // 16), max(1, w // 16)
        grid = rng.uniform(0.9, 1.1, size=(gh, gw)).astype(np.float32)
        if haze:
            grid = cv2.resize(grid, (w, h), interpolation=cv2.INTER_CUBIC)
            f = out.astype(np.float32)
            f = f * (1 - s) + f * grid * s
            m = f.mean()
            f = m + (f - m) * (1 - s * 0.5)
            out = np.clip(f, 0, 255).astype(np.uint8)
    return out, total, placed_total


def cmd_build(a):
    import cv2

    cfg, grid = fault_frames()
    synth = mfs._load_synth(REPO)
    sprites = scale_sprites(synth.load_sprites(a.sprite_dir), a.scale)
    name = variant_name(a.scale, not a.no_haze)
    out_dir = os.path.join(a.work, name)
    rows = []
    for fid, g in grid.groupby("fault_sequence_id", sort=False):
        rng = np.random.default_rng(int(hashlib.sha256(f"{cfg['seed']}|{fid}".encode()).hexdigest()[:8], 16))
        for r in g.itertuples():
            img8 = cv2.imread(os.path.join(a.work, "base", r.base_sequence_id, f"{r.frame_idx:05d}.png"),
                              cv2.IMREAD_GRAYSCALE)
            img, target, placed = inject(img8, sprites, r.severity, synth, rng, haze=not a.no_haze)
            path = os.path.join(out_dir, "png", fid, f"{r.frame_idx:05d}.png")
            if os.path.exists(path):
                os.remove(path)
            mfs._write_png(path, img)
            rows.append({**r._asdict(), "png_path": path, "image_sha256": _sha(path),
                         "sprites_target": target, "sprites_placed": placed})
    man = pd.DataFrame(rows).drop(columns="Index")
    sizes = [max(s.shape[:2]) for s in sprites]
    meta = {"variant": name, "scale": a.scale, "haze": not a.no_haze, "n_sprites": len(sprites),
            "sprite_longest_side_px": {"median": float(np.median(sizes)), "min": int(min(sizes)),
                                       "max": int(max(sizes))},
            "built_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    orig = pd.read_parquet(os.path.join(SIDECARS, "fault_manifest.parquet"))
    orig = orig[(orig.fault_type == "contamination_onset") & orig.is_modified]
    ref = dict(zip(zip(orig.fault_sequence_id, orig.frame_idx), orig.image_sha256))
    meta["same_bytes_as_original"] = int(sum(ref.get((r.fault_sequence_id, r.frame_idx)) == r.image_sha256
                                             for r in man.itertuples()))
    meta["n_frames"] = len(man)
    man.to_parquet(os.path.join(out_dir, "manifest.parquet"), index=False)
    with open(os.path.join(out_dir, "variant.json"), "w") as f:
        json.dump(meta, f, indent=2)
    print(json.dumps(meta), f"| placed/target {man.sprites_placed.sum()}/{man.sprites_target.sum()}")


# ---------------------------------------------------------------------------
# score
# ---------------------------------------------------------------------------

def _loo_banks(fold: str, cfg: dict) -> dict:
    """Tuning-normal banks without `fold`'s frames, built as eval_anomaly.py does."""
    sys.path.insert(0, os.path.join(REPO, "scripts"))
    import eval_anomaly as ea

    scores = pd.read_parquet(os.path.join(REPO, "cache", "anomaly", "scores.parquet"))
    tune = scores[(scores.kind == "normal") & (scores.split == "tuning")]
    members = tune[tune.base_sequence_id != fold]
    patches = ea.load_all_patches(os.path.join(REPO, "cache"), members.image_sha256, ea.DEFAULTS["crop_spec"])
    bcfg = {**ea.DEFAULTS, "coreset_frac": cfg["method"]["coreset_frac"]}
    return {int(b): ea.build_bank(patches, list(members[members.bin == b].image_sha256), bcfg)
            for b in sorted(members.bin.unique())}


def _quality_c2c12(img: np.ndarray):
    """The quality gate with the thresholds calibrated on C2C12 (configs/quality.yaml
    entries.c2c12), as the replays and results/quality_gate_c2c12.md use."""
    from culture.cache import quality_metrics
    from culture.quality import evaluate_thresholds

    m = quality_metrics(img)
    return evaluate_thresholds(m["blur_laplacian_var"], m["exposure_mean"], m["uniformity_block_std"],
                               dataset="c2c12")


def cmd_score(a):
    import cv2

    from culture.anomaly import (bin_index, bin_label, image_score, load_anomaly_config, load_banks,
                                 nn_distance, score_patches)
    from culture.cache import dino_embed, qc_tile_from
    from culture.seg import cpsam_confluency

    cfg = load_anomaly_config()
    full, reason = load_banks(cfg)
    if full is None:
        raise SystemExit(reason)
    edges = cfg["bins"]["edges"]
    split = pd.read_csv(os.path.join(REPO, "results", "replay_fleet_split.csv"))
    split = split[split.kind == "base"].set_index("sequence_id").split
    images = pd.read_parquet(os.path.join(REPO, "cache", "images.parquet"))
    conf = pd.read_parquet(os.path.join(REPO, "cache", "confluency.parquet"))
    conf = conf[(conf.model_name == "seg") & (conf.crop_spec == "full")].drop_duplicates("image_sha256")
    pct = dict(zip(conf.image_sha256, conf.pct))
    base_sha = {(r.sequence_id, int(r.frame_idx)): r.image_sha256
                for r in images[images.dataset == "c2c12"].itertuples()}

    out_dir = os.path.join(a.work, a.variant)
    man = pd.read_parquet(os.path.join(out_dir, "manifest.parquet"))
    loo: dict = {}
    rows = []
    for i, r in enumerate(man.itertuples()):
        t0 = time.perf_counter()
        img = cv2.imread(r.png_path, cv2.IMREAD_GRAYSCALE)
        c = cpsam_confluency(img, method="probmap")
        q = _quality_c2c12(img)
        patches = dino_embed(qc_tile_from(img))["patches"]
        sp = split[r.base_sequence_id]
        b = bin_index(c.pct, edges)
        label = bin_label(b, edges)
        cal = cfg["calibration"]["bins"][label]
        if sp == "heldout":
            score = score_patches(patches, c.pct, cfg, full).score
        else:
            if r.base_sequence_id not in loo:
                loo[r.base_sequence_id] = _loo_banks(r.base_sequence_id, cfg)
            banks = loo[r.base_sequence_id]
            x = patches.astype(np.float16).astype(np.float32)
            x = x / (np.linalg.norm(x, axis=1, keepdims=True) + 1e-8)
            bb = b if b in banks else min(banks, key=lambda k: abs(k - b))
            score = float(image_score(nn_distance(x, banks[bb]), cfg["method"]["top_frac"]))
        bs = base_sha[(r.base_sequence_id, int(r.frame_idx))]
        rows.append({"fault_sequence_id": r.fault_sequence_id, "base_sequence_id": r.base_sequence_id,
                     "split": sp, "frame_idx": int(r.frame_idx), "hours_since_start": r.hours_since_start,
                     "severity": r.severity, "sprites_target": r.sprites_target, "sprites_placed": r.sprites_placed,
                     "image_sha256": r.image_sha256, "base_sha": bs, "base_pct": pct.get(bs),
                     "pct": round(float(c.pct), 4), "confidence": round(float(c.confidence), 4),
                     "quality_pass": bool(q.passed), "bin": b, "bin_label": label,
                     "score": round(float(score), 6), "z": round((score - cal["mean"]) / cal["sd"], 4),
                     "threshold": cal["threshold"], "flag": bool(score > cal["threshold"]),
                     "seconds": round(time.perf_counter() - t0, 2)})
        print(f"{i + 1}/{len(man)} {r.fault_sequence_id[6:24]} {r.frame_idx:5d} sev {r.severity:5.0f} "
              f"pct {c.pct:5.1f} (base {pct.get(bs, float('nan')):5.1f}) score {score:.3f} "
              f"flag {rows[-1]['flag']!s:5} {rows[-1]['seconds']:.1f}s", flush=True)
    pd.DataFrame(rows).to_parquet(os.path.join(out_dir, "scores.parquet"), index=False)


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------

FLOOR = 0.30                    # culture/rules.py default confidence floor
TARGETS = (80.0, 50.0)          # the default target and the replays' target
BANDS = [(0, 100), (100, 200), (200, 300), (300, 401)]


def _auroc(neg, pos):
    from sklearn.metrics import roc_auc_score
    if len(neg) == 0 or len(pos) == 0:
        return float("nan")
    return float(roc_auc_score(np.r_[np.zeros(len(neg)), np.ones(len(pos))], np.r_[neg, pos]))


def _pct(x):
    return "—" if x != x else f"{x:.0%}"


def _f2(x):
    return "—" if x != x else f"{x:.2f}"


def example_figure(work: str, variants: list[str], out_png: str) -> str:
    """256 px centre tiles (the anomaly check's crop) of one late frame: base and each variant."""
    import cv2
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    man = pd.read_parquet(os.path.join(work, variants[0], "manifest.parquet"))
    held = man[man.fault_sequence_id.str.contains("090318_exp1_F0005")]
    r = held.sort_values("severity").iloc[-1]
    paths = []
    for v in variants:
        m = pd.read_parquet(os.path.join(work, v, "manifest.parquet"))
        p = m[(m.fault_sequence_id == r.fault_sequence_id) & (m.frame_idx == r.frame_idx)].png_path.iloc[0]
        paths.append((VARIANT_LABELS[v], p))
    fig, ax = plt.subplots(1, len(paths), figsize=(3.2 * len(paths), 3.6))
    for k, (lab, p) in enumerate(paths):
        img = cv2.imread(p, cv2.IMREAD_GRAYSCALE)
        h, w = img.shape
        ax[k].imshow(img[h // 2 - 128:h // 2 + 128, w // 2 - 128:w // 2 + 128], cmap="gray", vmin=0, vmax=255)
        ax[k].set_title(lab, fontsize=8)
        ax[k].axis("off")
    fig.suptitle(f"{r.fault_sequence_id.replace('__fault_contam', '')}, frame {int(r.frame_idx)}, "
                 f"{r.severity:.0f} bacteria per 256 px tile area; 256 px centre tile (333 µm)", fontsize=8)
    fig.tight_layout()
    fig.savefig(out_png, dpi=130)
    plt.close(fig)
    return f"{r.fault_sequence_id}, frame {int(r.frame_idx)}"


VARIANT_LABELS: dict[str, str] = {}


def _example_pixel_check(work: str) -> list[tuple]:
    """The stored contamination examples (original fault frames) vs the scale-1 rebuild."""
    import cv2

    with open(os.path.join(REPO, "demo", "examples", "examples.json")) as f:
        ex = [e for e in json.load(f)["examples"] if e["kind"] == "c2c12_contamination"]
    out = []
    for e in ex:
        a = cv2.imread(os.path.join(REPO, "demo", "examples", e["image"]), cv2.IMREAD_GRAYSCALE)
        b = cv2.imread(os.path.join(work, variant_name(1.0, True), "png", e["sequence"],
                                    f"{int(e['frame']):05d}.png"), cv2.IMREAD_GRAYSCALE)
        d = np.abs(a.astype(int) - b.astype(int))
        out.append((e["id"], int((d > 0).sum()), int(d.size), int(d.max())))
    return out


def cmd_clean(a):
    """The control variant: the same frames with no fault, scored by the same
    `score` step, so contaminated-vs-clean differences are measured on one platform."""
    _, grid = fault_frames()
    out_dir = os.path.join(a.work, "clean")
    os.makedirs(out_dir, exist_ok=True)
    rows = []
    for r in grid.itertuples():
        path = os.path.join(a.work, "base", r.base_sequence_id, f"{r.frame_idx:05d}.png")
        rows.append({**r._asdict(), "png_path": path, "image_sha256": _sha(path),
                     "sprites_target": 0, "sprites_placed": 0})
    pd.DataFrame(rows).drop(columns="Index").to_parquet(os.path.join(out_dir, "manifest.parquet"), index=False)
    with open(os.path.join(out_dir, "variant.json"), "w") as f:
        json.dump({"variant": "clean", "n_frames": len(rows)}, f, indent=2)
    print(f"clean control: {len(rows)} frames")


def _bacterium_length_px(sprite_dir: str) -> float:
    """Median bacterium length in the DeepBacs sprites, px at 79 nm/px (longest
    side of the minimum-area rectangle around the alpha mask)."""
    import cv2

    synth = mfs._load_synth(REPO)
    lengths = []
    for s in synth.load_sprites(sprite_dir):
        pts = cv2.findNonZero((s[..., 3] > 127).astype(np.uint8))
        if pts is not None:
            lengths.append(max(cv2.minAreaRect(pts)[1]))
    return float(np.median(lengths))


def cmd_report(a):
    import cv2

    orig_v = variant_name(1.0, True)
    variants = ["clean", orig_v, variant_name(REALISTIC, True), variant_name(REALISTIC, False)]
    VARIANT_LABELS.update({"clean": "no fault (control)", orig_v: "original: 16.5× too large, haze",
                           variants[2]: "realistic size, haze", variants[3]: "realistic size, no haze"})
    meta = {v: json.load(open(os.path.join(a.work, v, "variant.json"))) for v in variants}
    sc = {v: pd.read_parquet(os.path.join(a.work, v, "scores.parquet")) for v in variants}
    key = ["fault_sequence_id", "frame_idx"]
    for v, s in sc.items():                  # the gate from the PNGs, C2C12 thresholds (cheap, no model)
        man = pd.read_parquet(os.path.join(a.work, v, "manifest.parquet"))
        path = dict(zip(zip(man.fault_sequence_id, man.frame_idx), man.png_path))
        s["quality_pass"] = [bool(_quality_c2c12(cv2.imread(path[(r.fault_sequence_id, r.frame_idx)],
                                                                cv2.IMREAD_GRAYSCALE)).passed) for r in s.itertuples()]
        c = sc["clean"][key + ["pct", "flag"]].rename(columns={"pct": "clean_pct", "flag": "clean_flag"})
        sc[v] = s.drop(columns=[x for x in ("clean_pct", "clean_flag") if x in s]).merge(c, on=key, how="left")
    fetch = json.load(open(os.path.join(a.work, "fetch.json")))
    cache_scores = pd.read_parquet(os.path.join(REPO, "cache", "anomaly", "scores.parquet"))
    hn = cache_scores[(cache_scores.kind == "normal") & (cache_scores.split == "heldout")]
    cache_cols = cache_scores[["image_sha256", "pct", "score_binned", "flag_binned"]].rename(columns={"pct": "cache_pct"})

    fm = pd.read_parquet(os.path.join(SIDECARS, "fault_manifest.parquet"))
    fm = fm[(fm.fault_type == "contamination_onset") & fm.is_modified]
    orig_sha = dict(zip(zip(fm.fault_sequence_id, fm.frame_idx), fm.image_sha256))

    def vs_cache(s, by_original=False):
        # the scale-1 rebuild differs from the originals in the last bit, so match it by frame
        s = s.assign(image_sha256=[orig_sha[(r.fault_sequence_id, r.frame_idx)] for r in s.itertuples()]) \
            if by_original else s
        o = s.merge(cache_cols, on="image_sha256", how="left")
        assert o.cache_pct.notna().all()
        return (o.pct - o.cache_pct).abs(), (o.score - o.score_binned).abs(), int((o.flag == o.flag_binned).sum()), len(o)

    p_o, s_o, ag_o, n_o = vs_cache(sc[orig_v], by_original=True)
    p_c, s_c, ag_c, n_c = vs_cache(sc["clean"])
    length = _bacterium_length_px(a.sprite_dir)
    fig_png = os.path.join(REPO, "results", "contamination_scale_examples.png")
    fig_note = example_figure(a.work, variants, fig_png)
    os.makedirs(os.path.dirname(DEMO_FIGURE), exist_ok=True)
    import shutil
    shutil.copyfile(fig_png, DEMO_FIGURE)             # shown in the console's Detectability tab

    lines = [
        "# Contamination at a realistic bacterial size",
        "",
        f"Generated {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} by `scripts/contamination_scale.py` "
        "on the Mac (Apple MPS), with the live path's models: Cellpose-SAM (cpsam_v2), the quality gate "
        "(C2C12 thresholds), and DINOv2-small with the frozen anomaly calibration in `configs/anomaly.yaml`. "
        "C2C12 images: Ker et al., *Sci Data* 5:180237 (2018), CC BY 4.0. Bacteria: DeepBacs "
        "(Zenodo 5550935), 79 nm/px.",
        "",
        "## Why",
        "",
        "The original contamination fault set pastes DeepBacs bacteria pixel for pixel into 1.3 µm/px C2C12 "
        "frames, so they are 16.5× too long (docs/ARCHITECTURE_VALIDATION.md, V5 correction). Here the same "
        f"frames are rebuilt with the bacteria shrunk by 0.079 / 1.3 = {REALISTIC:.4f}, area-averaged, so a "
        "bacterium narrower than a pixel darkens part of one pixel. The median bacterium in the sprite "
        f"library is {length:.0f} px long at 79 nm/px ({length * 0.079:.1f} µm): {length:.0f} px "
        f"({length * 1.3:.0f} µm) as originally pasted, {length * REALISTIC:.1f} px as pasted here. Bacteria "
        "are placed on background pixels only, and one narrower than a pixel darkens it by a few grey levels, "
        "so fewer are visible in the plot than were placed.",
        "",
        "## Design",
        "",
        "Fixed before any realistic-size output was seen:",
        "",
        "- Same 4 sequences, onset, frames, seed and density ramp as the original (20 → 400 bacteria per "
        "256 px tile area over 24 h after onset); only the bacterium size changes.",
        "- Frozen anomaly thresholds, confidence floor (0.30) and rules; nothing is tuned on these frames, and "
        "the density is not extended past the original 400.",
        "- Two realistic variants: with the simulator's turbidity haze, as the original, and without it. The "
        "haze strength follows the bacterium count, not the size, so on its own it could make a flag look "
        "like detection. Both variants place the same bacteria in the same spots.",
        "- Held-out frames are scored against the full tuning banks (the live path's), tuning frames against "
        "banks rebuilt without their own sequence, as in `scripts/eval_anomaly.py`.",
        "",
        "Changed after the first variant's output was seen, and why:",
        "",
        "- The score step first ran the quality gate with the default thresholds; the C2C12 thresholds are "
        "the ones every other C2C12 result uses, so the gate is recomputed from the PNGs with them (no model).",
        "- A control was added: the same 97 frames with no fault, scored here. The first comparison was "
        "against the cache's values from the Colab GPU, which mixes the bacteria's effect with the "
        "platform's; contaminated-vs-clean below is measured on this Mac only.",
        "",
        "## Controls",
        "",
        f"- Base frames re-downloaded from OSF and converted with the stored normalization: "
        f"{fetch['matching']}/{fetch['n']} byte-identical to the frames in the compute cache.",
        f"- The builder at scale 1 with haze rebuilds the original fault frames: "
        f"{meta[orig_v]['same_bytes_as_original']}/{meta[orig_v]['n_frames']} byte-identical (the manifest's "
        "sha256). The two frames kept as demo examples show why the rest are not: "
        + "; ".join(f"{k}, {n:,} of {tot:,} pixels differ, by at most {mx} grey level"
                    for k, n, tot, mx in _example_pixel_check(a.work))
        + ". The same bacteria land in the same places; the last-bit differences come from floating-point "
        "rounding on this Mac (ARM) against Colab (x86).",
        f"- This Mac vs the cache (Colab GPU), clean frames: confluency differs by a median "
        f"{p_c.median():.2f} pp (max {p_c.max():.2f}), anomaly score by a median {s_c.median():.4f} "
        f"(max {s_c.max():.4f}), the flag agrees on {ag_c}/{n_c}. Original fault frames: "
        f"{p_o.median():.2f} pp (max {p_o.max():.2f}), {s_o.median():.4f} (max {s_o.max():.4f}), "
        f"{ag_o}/{n_o}.",
        "",
        "## Results",
        "",
        f"All {len(sc['clean'])} frames (4 sequences, both splits) unless marked held-out "
        f"({int((sc['clean'].split == 'heldout').sum())} frames, 2 sequences). Frames within a sequence are not "
        "independent. Shifts are paired: the same frame with the fault minus without it, both scored here. "
        f"AUROC, as V5(b): held-out frames of the column vs the {len(hn)} held-out normal frames in the cache "
        "(binned z; the cache's side was scored on the Colab GPU).",
        "",
        "| | " + " | ".join(VARIANT_LABELS[v] for v in variants) + " |",
        "|---|" + "---|" * len(variants),
    ]

    def row(label, fn):
        lines.append(f"| {label} | " + " | ".join(fn(sc[v]) for v in variants) + " |")

    def band(s, lo, hi):
        return s[(s.severity >= lo) & (s.severity < hi)]

    row("bacteria placed / asked for", lambda s: (f"{int(s.sprites_placed.sum()):,} / {int(s.sprites_target.sum()):,}"
                                                   if s.sprites_target.sum() else "—"))
    row("held-out AUROC, all frames", lambda s: _f2(_auroc(hn.z_binned.to_numpy(), s[s.split == "heldout"].z.to_numpy())))
    row("held-out AUROC, ≥ 150 per tile", lambda s: _f2(_auroc(
        hn.z_binned.to_numpy(), s[(s.split == "heldout") & (s.severity >= 150)].z.to_numpy())))
    row("anomaly flag, all frames", lambda s: f"{int(s.flag.sum())} of {len(s)} ({_pct(s.flag.mean())})")
    row("anomaly flag, held-out", lambda s: f"{int(s[s.split == 'heldout'].flag.sum())} of {int((s.split == 'heldout').sum())}")
    for lo, hi in BANDS:
        row(f"anomaly flag, {lo}–{min(hi, 400)} per tile", lambda s, lo=lo, hi=hi: (
            f"{int(band(s, lo, hi).flag.sum())} of {len(band(s, lo, hi))}"))
    row("confluency, median (range)", lambda s: f"{s.pct.median():.1f}% ({s.pct.min():.1f}–{s.pct.max():.1f})")
    row("confluency shift vs the clean frame, median (IQR)", lambda s: (
        "—" if s is sc["clean"] else
        (lambda d: f"{d.median():+.1f} pp ({d.quantile(.25):+.1f} to {d.quantile(.75):+.1f})")(s.pct - s.clean_pct)))
    row("quality gate fails (REIMAGE)", lambda s: f"{int((~s.quality_pass).sum())} of {len(s)}")
    row(f"confidence below the floor ({FLOOR})", lambda s: f"{int((s.confidence < FLOOR).sum())} of {len(s)}")
    for t in TARGETS:
        def elig(s, t=t):
            return s[(s.confidence >= FLOOR) & (s.pct >= t)]
        row(f"target {t:.0f}%: reach it (confidence ≥ floor)",
            lambda s, e=elig, t=t: f"{len(e(s))}" if len(e(s)) else
            f"none (highest {s[s.confidence >= FLOOR].pct.max():.1f}%)")
        row(f"target {t:.0f}%: of those, held by the flag", lambda s, e=elig: f"{int(e(s).flag.sum())}" if len(e(s)) else "—")

    lines += [
        "",
        "Reference, from `results/anomaly_summary.md`: held-out normal frames are flagged at 14.7% in the "
        "0–20% bin, 3.8% in 20–40% and 0.6% in 40–100% (thresholds set for 5% on tuning normals).",
        "",
        f"Plot: `results/contamination_scale_examples.png` (copied to `demo/figures/contamination_scale.png` for "
        f"the console's Detectability tab), the anomaly check's 256 px centre tile of {fig_note}.",
        "",
        "## Per-frame scores",
        "",
        "`results/contamination_scale.csv`: one row per frame and variant.",
    ]
    allrows = pd.concat([s.assign(variant=v) for v, s in sc.items()], ignore_index=True)
    allrows.drop(columns=["seconds"]).to_csv(os.path.join(REPO, "results", "contamination_scale.csv"), index=False)
    with open(os.path.join(REPO, "results", "contamination_scale.md"), "w") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--work", default=WORK)
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch")
    f.add_argument("--inventory", required=True)
    b = sub.add_parser("build")
    b.add_argument("--scale", type=float, default=REALISTIC)
    b.add_argument("--no-haze", action="store_true")
    b.add_argument("--sprite-dir", default=SPRITE_DIR)
    s = sub.add_parser("score")
    s.add_argument("--variant", required=True)
    sub.add_parser("clean")
    r = sub.add_parser("report")
    r.add_argument("--sprite-dir", default=SPRITE_DIR)
    a = ap.parse_args()
    {"fetch": cmd_fetch, "build": cmd_build, "clean": cmd_clean, "score": cmd_score, "report": cmd_report}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
