"""
scripts/fov_noise.py writing configs/noise.yaml, on a tiny hand-built cache.

--entry adds a separately measured fit under entries.<name> without touching
the top-level crop_fracs that culture/growth.py reads; a default run replaces
the top level but keeps entries, and never fits simulated fault frames.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys

import numpy as np
import pandas as pd
import yaml

_SPEC = importlib.util.spec_from_file_location(
    "fov_noise", os.path.join(os.path.dirname(__file__), "..", "scripts", "fov_noise.py"))
fn = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(fn)


def _cache(tmp_path):
    rng = np.random.default_rng(0)
    images, conf = [], []
    for dataset, n in [("c2c12", 6), ("evican_eval2019", 6), ("c2c12_fault_dim", 6)]:
        for i in range(n):
            sha = f"{dataset}_{i}"
            images.append({"image_sha256": sha, "dataset": dataset, "sequence_id": f"{dataset}_s{i % 2}"})
            for frac in (0.25, 0.5):
                for k in range(4):
                    conf.append({"image_sha256": sha, "crop_spec": f"crop_f{frac}_s0_k{k}", "model_name": "seg",
                                 "model_version": "cpsam_v2", "pct": float(rng.uniform(5 * i, 5 * i + 10)),
                                 "confidence": 1.0, "extra": json.dumps({"frac": frac})})
    d = tmp_path / "cache"
    d.mkdir()
    pd.DataFrame(images).to_parquet(d / "images.parquet")
    pd.DataFrame(conf).to_parquet(d / "confluency.parquet")
    return str(d)


def _run(monkeypatch, *args):
    monkeypatch.setattr(sys, "argv", ["fov_noise.py", *args])
    fn.main()


def test_entry_is_separate_and_default_run_keeps_it(tmp_path, monkeypatch):
    cache, cfg, out = _cache(tmp_path), tmp_path / "configs", tmp_path / "results"
    cfg.mkdir()
    top = {"model": "m", "crop_fracs": {"0.25": {"slope": 1.0, "intercept": 0.5}}}
    (cfg / "noise.yaml").write_text(yaml.safe_dump(top))

    _run(monkeypatch, "--cache-dir", cache, "--datasets", "c2c12", "--entry", "c2c12",
         "--out", str(out), "--configs-out", str(cfg))
    y = yaml.safe_load((cfg / "noise.yaml").read_text())
    assert y["crop_fracs"] == top["crop_fracs"]
    e = y["entries"]["c2c12"]
    assert e["datasets"] == ["c2c12"] and e["n_images"] == 6 and e["n_sequences"] == 2
    assert set(e["crop_fracs"]) == {"0.25", "0.5"}
    assert (out / "fov_noise_c2c12.csv").exists() and not (out / "fov_noise.csv").exists()

    _run(monkeypatch, "--cache-dir", cache, "--out", str(out), "--configs-out", str(cfg))
    y = yaml.safe_load((cfg / "noise.yaml").read_text())
    assert y["entries"]["c2c12"] == e
    assert y["datasets"] == ["c2c12", "evican_eval2019"]  # fault frames are simulated, not repositioning noise
