#!/usr/bin/env python3
"""
scripts/make_fault_set.py — Phase A3 fault set (cultureQC_upgrade.md §2A.3).

Builds three SIMULATED fault families on top of the real C2C12 sequences that
scripts/fetch_c2c12.py produced. Every output row is labelled provenance="simulated".

  contamination_onset  (culture fault, needs inference)
      From an onset time onward, bacterial sprites are composited onto the frame
      with the repo's OWN generator (scripts/synth_contamination.py::add_bacteria),
      at a sprite density that ramps up over time. Density is expressed per
      256x256 tile-area so it matches the training tiles' severity scale
      (early 30-150, mid 150-600, late 600-2000 sprites per tile).
      Turbidity haze: add_bacteria() adds haze with strength min(placed/2000, 0.3)
      from the count placed *in that call*. Calling it once on a full 1392x1040
      frame (~22 tile-areas) would saturate haze almost immediately — far hazier
      than any training tile at the same density. So sprites are placed in calls
      of <=20 (below add_bacteria's haze threshold) and ONE frame-level haze is
      applied afterwards with the same formula evaluated at the per-tile density,
      on a 16-px haze grid (same spatial scale as a 256-px tile's 16x16 grid).

  growth_stall         (culture fault, NO inference)
      After onset, the flask advances through its own recorded frames more slowly
      (time dilation, default 0.4x): the virtual timeline keeps going but the
      culture "grows" at 40% speed. Pure metadata — reuses already-cached frames.

  lamp_dimming         (instrument fault, needs inference)
      From an onset time (in hours since each sequence's start), EVERY selected
      sequence's raw 16-bit frames are scaled by a factor ramping 1.0 -> min_factor,
      THEN passed through the SAME fixed normalization as the originals — so the
      8-bit frames get genuinely darker, as they would if the lamp dimmed.

Outputs (in --out):
  png/<fault_sequence_id>/<frame_idx>.png   modified frames (contamination, dimming)
  fault_frames.csv      one row per NEW image to cache: png_path, dataset,
                        sequence_id (= fault_sequence_id), frame_idx, timestamp
  fault_manifest.parquet   the full composed timeline of every fault sequence:
                        pre-onset rows point at the ORIGINAL cached frame's sha256,
                        post-onset rows at the modified frame's sha256 (or, for
                        growth_stall, at the dilated source frame's sha256).
                        Phase A2's replay needs a small adapter to read this
                        (images.parquet holds one sequence_id per sha256, so a fault
                        sequence can't "share" its pre-onset frames through it).

Deterministic given --seed: same inputs -> same PNG bytes -> same cache keys.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

TILE_AREA = 256 * 256
SPRITES_PER_CALL = 20  # add_bacteria adds haze only when placed > 20 in one call


def _load_synth(repo_root: str):
    path = os.path.join(repo_root, "scripts", "synth_contamination.py")
    spec = importlib.util.spec_from_file_location("synth_contamination", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _sha(path: str) -> str:
    from culture.cache import image_sha256  # same identity as cache keys

    return image_sha256(path)


def _write_png(path: str, img8: np.ndarray) -> None:
    import cv2

    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.exists(path):
        tmp = path + ".tmp.png"
        cv2.imwrite(tmp, img8, [cv2.IMWRITE_PNG_COMPRESSION, 3])
        os.replace(tmp, path)


def _ramp(t_h: float, onset_h: float, ramp_h: float, start: float, end: float) -> float:
    if t_h < onset_h:
        return start
    u = min(1.0, (t_h - onset_h) / max(ramp_h, 1e-6))
    return start + u * (end - start)


def _post_onset_grid(frames: pd.DataFrame, onset_h: float, stride_h: float) -> pd.DataFrame:
    """Frames after onset, thinned to roughly one per stride_h (fault frames need
    inference; replay only needs a frame near each visit time)."""
    post = frames[frames.hours_since_start >= onset_h].sort_values("hours_since_start")
    keep, last = [], -1e9
    for i, r in post.iterrows():
        if r.hours_since_start - last >= stride_h - 1e-6:
            keep.append(i)
            last = r.hours_since_start
    return post.loc[keep]


# ---------------------------------------------------------------------------
# fault recipes
# ---------------------------------------------------------------------------

def inject_bacteria_frame(img8: np.ndarray, sprites: list, density_per_tile: float, synth, rng) -> np.ndarray:
    import cv2

    h, w = img8.shape[:2]
    total = int(round(density_per_tile * (h * w) / TILE_AREA))
    cell_mask = synth.get_cell_mask(img8)
    bg_mask = ~cell_mask
    out = img8.copy()
    placed_total = 0
    key = "__fault_call__"
    try:
        remaining = total
        while remaining > 0:
            n = min(SPRITES_PER_CALL, remaining)
            synth.SEVERITY_RANGES[key] = (n, n + 1)  # exact count per call
            out, placed = synth.add_bacteria(out, bg_mask, sprites, severity=key, rng=rng)
            placed_total += placed
            remaining -= n
    finally:
        synth.SEVERITY_RANGES.pop(key, None)

    # frame-level haze: same formula as add_bacteria, at the per-tile density
    placed_per_tile = placed_total * TILE_AREA / (h * w)
    s = min(placed_per_tile / 2000.0, 0.3)
    if s > 0.01:
        gh, gw = max(1, h // 16), max(1, w // 16)
        haze = rng.uniform(0.9, 1.1, size=(gh, gw)).astype(np.float32)
        haze = cv2.resize(haze, (w, h), interpolation=cv2.INTER_CUBIC)
        f = out.astype(np.float32)
        f = f * (1 - s) + f * haze * s
        m = f.mean()
        f = m + (f - m) * (1 - s * 0.5)
        out = np.clip(f, 0, 255).astype(np.uint8)
    return out


# ---------------------------------------------------------------------------
# main builder
# ---------------------------------------------------------------------------

DEFAULTS = {
    "seed": 0,
    "contamination": {"n_sequences": 4, "onset_frac": 0.45, "ramp_hours": 24.0,
                      "density_start": 20.0, "density_end": 400.0, "stride_hours": 2.0},
    "growth_stall": {"n_sequences": 4, "onset_frac": 0.35, "dilation": 0.4, "grid_hours": 1.0},
    "lamp_dimming": {"onset_hours": 40.0, "ramp_hours": 24.0, "min_factor": 0.65, "stride_hours": 2.0},
}


def build(c2c12_dir: str, out_dir: str, sprite_dir: str, repo_root: str, cfg: dict | None = None) -> dict:
    global _REPO_ROOT
    _REPO_ROOT = repo_root
    for p in (repo_root, os.path.join(repo_root, "scripts")):
        if p not in sys.path:
            sys.path.insert(0, p)
    from fetch_c2c12 import read_raw, to_uint8  # same normalization code as the originals

    cfg = json.loads(json.dumps(DEFAULTS if cfg is None else cfg))
    rng_master = np.random.default_rng(cfg["seed"])
    synth = _load_synth(repo_root)
    sprites = synth.load_sprites(sprite_dir)
    if not sprites:
        raise SystemExit(f"no RGBA sprites in {sprite_dir} — run scripts/extract_sprites.py first")

    frames = pd.read_csv(os.path.join(c2c12_dir, "c2c12_frames.csv"))
    seqs = pd.read_csv(os.path.join(c2c12_dir, "c2c12_sequences.csv"))
    with open(os.path.join(c2c12_dir, "c2c12_normalization.json")) as f:
        norm = json.load(f)
    frames["image_sha256"] = [_sha(p) for p in frames.png_path]

    seq_ids = sorted(seqs.sequence_id)
    order = rng_master.permutation(len(seq_ids))
    n_c, n_g = cfg["contamination"]["n_sequences"], cfg["growth_stall"]["n_sequences"]
    contam_ids = [seq_ids[i] for i in order[:n_c]]
    stall_ids = [seq_ids[i] for i in order[n_c:n_c + n_g]]  # disjoint from contamination

    new_images, manifest = [], []

    def compose(fault_id, base_id, ftype, onset_h, post_rows):
        base = frames[frames.sequence_id == base_id].sort_values("hours_since_start")
        onset_idx = None
        for _, r in base[base.hours_since_start < onset_h].iterrows():
            manifest.append({"fault_sequence_id": fault_id, "base_sequence_id": base_id, "fault_type": ftype,
                             "onset_hours": onset_h, "frame_idx": int(r.frame_idx), "timestamp": r.timestamp,
                             "hours_since_start": float(r.hours_since_start), "image_sha256": r.image_sha256,
                             "is_modified": False, "severity": 0.0, "provenance": "simulated"})
        for row in post_rows:
            onset_idx = row["frame_idx"] if onset_idx is None else onset_idx
            manifest.append({"fault_sequence_id": fault_id, "base_sequence_id": base_id, "fault_type": ftype,
                             "onset_hours": onset_h, **row, "provenance": "simulated"})
        return onset_idx

    # -- contamination onset --
    import cv2

    cc = cfg["contamination"]
    for sid in contam_ids:
        base = frames[frames.sequence_id == sid].sort_values("hours_since_start")
        span = base.hours_since_start.max()
        onset_h = cc["onset_frac"] * span
        fault_id = f"{sid}__fault_contam"
        # stable per-sequence seed (Python's hash() is salted per process -> non-deterministic)
        rng = np.random.default_rng(int(hashlib.sha256(f"{cfg['seed']}|{fault_id}".encode()).hexdigest()[:8], 16))
        post = []
        for _, r in _post_onset_grid(base, onset_h, cc["stride_hours"]).iterrows():
            dens = _ramp(r.hours_since_start, onset_h, cc["ramp_hours"], cc["density_start"], cc["density_end"])
            img8 = cv2.imread(r.png_path, cv2.IMREAD_GRAYSCALE)
            out_path = os.path.join(out_dir, "png", fault_id, f"{int(r.frame_idx):05d}.png")
            if not os.path.exists(out_path):
                _write_png(out_path, inject_bacteria_frame(img8, sprites, dens, synth, rng))
            sha = _sha(out_path)
            new_images.append({"png_path": out_path, "dataset": "c2c12_fault_contam", "sequence_id": fault_id,
                               "frame_idx": int(r.frame_idx), "timestamp": r.timestamp})
            post.append({"frame_idx": int(r.frame_idx), "timestamp": r.timestamp,
                         "hours_since_start": float(r.hours_since_start), "image_sha256": sha,
                         "is_modified": True, "severity": float(dens)})
        compose(fault_id, sid, "contamination_onset", onset_h, post)

    # -- growth stall (metadata only) --
    gc = cfg["growth_stall"]
    for sid in stall_ids:
        base = frames[frames.sequence_id == sid].sort_values("hours_since_start").reset_index(drop=True)
        span = base.hours_since_start.max()
        onset_h = gc["onset_frac"] * span
        fault_id = f"{sid}__fault_stall"
        t0 = datetime.fromisoformat(base.timestamp.iloc[0]) - timedelta(hours=float(base.hours_since_start.iloc[0]))
        post, t = [], onset_h
        while t <= span + 1e-6:
            src_h = onset_h + (t - onset_h) * gc["dilation"]
            src = base.iloc[(base.hours_since_start - src_h).abs().idxmin()]
            ts = (t0 + timedelta(hours=t)).isoformat()
            post.append({"frame_idx": int(round(t * 60 / 5)), "timestamp": ts, "hours_since_start": float(t),
                         "image_sha256": src.image_sha256, "is_modified": False,
                         "severity": float(gc["dilation"]), "source_frame_idx": int(src.frame_idx)})
            t += gc["grid_hours"]
        compose(fault_id, sid, "growth_stall", onset_h, post)

    # -- lamp dimming (every sequence) --
    lc = cfg["lamp_dimming"]
    for sid in seq_ids:
        base = frames[frames.sequence_id == sid].sort_values("hours_since_start")
        fault_id = f"{sid}__fault_dim"
        post = []
        for _, r in _post_onset_grid(base, lc["onset_hours"], lc["stride_hours"]).iterrows():
            fac = _ramp(r.hours_since_start, lc["onset_hours"], lc["ramp_hours"], 1.0, lc["min_factor"])
            out_path = os.path.join(out_dir, "png", fault_id, f"{int(r.frame_idx):05d}.png")
            if not os.path.exists(out_path):
                raw = read_raw(r.raw_path).astype(np.float32) * fac
                _write_png(out_path, to_uint8(raw, norm))
            sha = _sha(out_path)
            new_images.append({"png_path": out_path, "dataset": "c2c12_fault_dim", "sequence_id": fault_id,
                               "frame_idx": int(r.frame_idx), "timestamp": r.timestamp})
            post.append({"frame_idx": int(r.frame_idx), "timestamp": r.timestamp,
                         "hours_since_start": float(r.hours_since_start), "image_sha256": sha,
                         "is_modified": True, "severity": float(fac)})
        compose(fault_id, sid, "lamp_dimming", lc["onset_hours"], post)

    os.makedirs(out_dir, exist_ok=True)
    new_df = pd.DataFrame(new_images)
    man_df = pd.DataFrame(manifest)
    new_df.to_csv(os.path.join(out_dir, "fault_frames.csv"), index=False)
    man_df.to_parquet(os.path.join(out_dir, "fault_manifest.parquet"), index=False)
    with open(os.path.join(out_dir, "fault_config.json"), "w") as f:
        json.dump({**cfg, "contamination_sequences": contam_ids, "growth_stall_sequences": stall_ids}, f, indent=2)
    return {"new_images": new_df, "manifest": man_df, "contam_ids": contam_ids, "stall_ids": stall_ids}


_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    global _REPO_ROOT
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--c2c12-dir", required=True, help="--out dir of scripts/fetch_c2c12.py fetch")
    ap.add_argument("--out", required=True)
    ap.add_argument("--sprite-dir", default="data/sprites/bacteria")
    ap.add_argument("--repo-root", default=_REPO_ROOT)
    ap.add_argument("--config", default=None, help="JSON overriding DEFAULTS")
    a = ap.parse_args()
    cfg = None
    if a.config:
        with open(a.config) as f:
            cfg = json.load(f)
    res = build(a.c2c12_dir, a.out, a.sprite_dir, a.repo_root, cfg)
    print(res["manifest"].groupby(["fault_type"]).agg(sequences=("fault_sequence_id", "nunique"),
                                                      rows=("frame_idx", "size"),
                                                      modified=("is_modified", "sum")))
    print(f"{len(res['new_images'])} new images to cache")


if __name__ == "__main__":
    sys.exit(main())
