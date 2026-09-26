"""
scripts/make_fault_set.py lamp dimming, on a tiny synthetic 16-bit sequence.

The dimming ramp starts at exactly 1.0, so the onset frame is the original
byte for byte. It must not be labelled as a modified fault frame.
"""

from __future__ import annotations

import importlib.util
import json
import os
from datetime import datetime, timedelta

import cv2
import numpy as np
import pandas as pd

REPO = os.path.join(os.path.dirname(__file__), "..")
_SPEC = importlib.util.spec_from_file_location("make_fault_set", os.path.join(REPO, "scripts", "make_fault_set.py"))
mfs = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(mfs)
_FSPEC = importlib.util.spec_from_file_location("fetch_c2c12", os.path.join(REPO, "scripts", "fetch_c2c12.py"))
fc = importlib.util.module_from_spec(_FSPEC)
_FSPEC.loader.exec_module(fc)


def _fixture(tmp_path, hours=46):
    c2c12, sprites = tmp_path / "c2c12", tmp_path / "sprites"
    sprites.mkdir()
    cv2.imwrite(str(sprites / "s.png"), np.full((3, 3, 4), 200, np.uint8))
    norm = {"lo": 0.0, "hi": 4000.0}
    c2c12.mkdir()
    (c2c12 / "c2c12_normalization.json").write_text(json.dumps(norm))
    rng = np.random.default_rng(0)
    t0 = datetime(2009, 3, 3)
    rows = []
    for h in range(hours):
        fidx = 1 + 12 * h
        raw = rng.integers(1000, 3000, size=(32, 32)).astype(np.uint16)
        raw_path, png_path = c2c12 / "raw" / f"{fidx:05d}.tif", c2c12 / "png" / f"{fidx:05d}.png"
        raw_path.parent.mkdir(exist_ok=True)
        png_path.parent.mkdir(exist_ok=True)
        cv2.imwrite(str(raw_path), raw)
        cv2.imwrite(str(png_path), fc.to_uint8(raw, norm))
        rows.append({"sequence_id": "seqA", "experiment": "090303", "condition": "unknown", "frame_idx": fidx,
                     "timestamp": (t0 + timedelta(hours=h)).isoformat(), "hours_since_start": float(h),
                     "png_path": str(png_path), "raw_path": str(raw_path)})
    pd.DataFrame(rows).to_csv(c2c12 / "c2c12_frames.csv", index=False)
    pd.DataFrame([{"sequence_id": "seqA"}]).to_csv(c2c12 / "c2c12_sequences.csv", index=False)
    return str(c2c12), str(sprites)


def test_lamp_dimming_onset_frame_is_not_a_modified_fault_frame(tmp_path):
    c2c12, sprites = _fixture(tmp_path)
    out = str(tmp_path / "faults")
    cfg = json.loads(json.dumps(mfs.DEFAULTS))
    cfg["contamination"]["n_sequences"] = 0
    cfg["growth_stall"]["n_sequences"] = 0
    mfs.build(c2c12, out, sprites, REPO, cfg)

    man = pd.read_parquet(os.path.join(out, "fault_manifest.parquet"))
    new = pd.read_csv(os.path.join(out, "fault_frames.csv"))
    frames = pd.read_csv(os.path.join(c2c12, "c2c12_frames.csv"))
    onset = man[man.hours_since_start == 40.0].iloc[0]
    original = frames[frames.hours_since_start == 40.0].iloc[0]

    assert not onset.is_modified and onset.severity == 1.0
    assert onset.image_sha256 == mfs._sha(original.png_path)
    assert onset.frame_idx not in set(new.frame_idx)  # nothing new to cache for it
    after = man[man.hours_since_start > 40.0]
    assert len(after) and after.is_modified.all() and (after.severity < 1.0).all()
    assert set(new.frame_idx) == set(after.frame_idx)
