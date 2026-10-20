"""Opt-in CPU parity gate: two local model loads, one image, no downloads.

Run with CULTUREQC_RUN_MODEL_PARITY=1 and pytest -s to retain measurements.
This checks loading/identity, not biological accuracy or deployment capacity.
"""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
IMAGE = ROOT / "test-data/contam_00015.png"


def _worker(mode, destination):
    import gc
    import importlib.metadata
    import resource
    import time

    import cv2
    import torch
    from cellpose import models

    sys.path.insert(0, str(ROOT))
    from culture import seg
    from culture.approvals import require
    from culture.records import hash_file

    torch.set_num_threads(2)
    source = Path(models.MODEL_DIR) / "cpsam_v2"
    started = time.perf_counter()
    approval = require("model", "cpsam_v2", str(source))
    source_hash = hash_file(str(source))
    assert approval.sha256 == source_hash
    frame = cv2.imread(str(IMAGE), cv2.IMREAD_GRAYSCALE)
    assert frame is not None and frame.shape == (256, 256)
    model = (models.CellposeModel(gpu=False, pretrained_model=str(source))
             if mode == "direct" else seg._get_model())
    assert str(model.device) == "cpu"
    load_seconds = time.perf_counter() - started
    snapshot = None
    if mode == "snapshot":
        snapshot = Path(model.pretrained_model)
        assert snapshot != source and snapshot.stat().st_mode & 0o222 == 0
        assert hash_file(str(snapshot)) == model._cultureqc_identity.sha256 == source_hash
    started = time.perf_counter()
    if mode == "direct":
        _, flows, _ = model.eval(frame, diameter=None, channels=[0, 0])
        probability = flows[2]
        foreground = probability > 0
        pct = round(float(foreground.mean() * 100), 2)
        confidence = round(float(np.clip(1 - float((np.abs(probability) < 1).mean()) * 4, 0, 1)), 3)
    else:
        visuals = []
        result = seg.cpsam_confluency(frame, on_visual=lambda probability, foreground: visuals.append(
            (probability, foreground)))
        probability, foreground = visuals[0]
        pct, confidence = result.pct, result.confidence
        assert result.extra["model_check"]["sha256"] == source_hash
        assert result.extra["model_check"]["status"] == "match"
    inference_seconds = time.perf_counter() - started
    assert hash_file(str(source)) == source_hash
    metadata = {
        "mode": mode, "device": str(model.device), "threads": torch.get_num_threads(),
        "input_sha256": hash_file(str(IMAGE)), "weights_sha256": source_hash,
        "approvals_head": approval.approvals_head,
        "load_and_preflight_seconds": load_seconds, "inference_seconds": inference_seconds,
        "peak_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (1 if sys.platform == "darwin" else 1024),
        "snapshot_bytes": snapshot.stat().st_size if snapshot is not None else 0,
        "pct": pct, "confidence": confidence,
        "versions": {name: importlib.metadata.version(name) for name in ("torch", "cellpose", "numpy")},
        "python": sys.version.split()[0],
    }
    np.savez(destination, probability=probability, foreground=foreground)
    seg._cp_model = None
    del model
    gc.collect()
    if snapshot is not None:
        assert not snapshot.exists(), "private snapshot outlived its released model"
    metadata["snapshot_cleanup_verified"] = snapshot is not None
    destination.with_suffix(".json").write_text(json.dumps(metadata, indent=2))


@pytest.mark.skipif(os.environ.get("CULTUREQC_RUN_MODEL_PARITY") != "1",
                    reason="explicit opt-in required: real Cellpose CPU parity check")
def test_private_snapshot_matches_direct_local_weights(tmp_path):
    pytest.importorskip("torch")
    models = pytest.importorskip("cellpose.models")
    source = Path(models.MODEL_DIR) / "cpsam_v2"
    assert source.is_file(), "preprovision approved weights; this check never downloads them"
    assert shutil.disk_usage(tmp_path).free > source.stat().st_size * 2
    metadata = {}
    for mode in ("direct", "snapshot"):
        destination = tmp_path / f"{mode}.npz"
        env = {**os.environ, "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1",
               "CUDA_VISIBLE_DEVICES": "", "CULTUREQC_DEVICE": "cpu",
               "OMP_NUM_THREADS": "2", "MKL_NUM_THREADS": "2"}
        process = subprocess.run([sys.executable, str(Path(__file__).resolve()), mode, str(destination)],
                                 cwd=ROOT, env=env, capture_output=True, text=True, timeout=300)
        assert process.returncode == 0, process.stderr[-4000:]
        metadata[mode] = json.loads(destination.with_suffix(".json").read_text())
    with np.load(tmp_path / "direct.npz") as direct, np.load(tmp_path / "snapshot.npz") as snapshot:
        np.testing.assert_allclose(snapshot["probability"], direct["probability"], rtol=0, atol=1e-5)
        np.testing.assert_array_equal(snapshot["foreground"], direct["foreground"])
        metadata["max_probability_difference"] = float(np.max(np.abs(snapshot["probability"] - direct["probability"])))
    for field in ("pct", "confidence", "input_sha256", "weights_sha256", "approvals_head"):
        assert metadata["snapshot"][field] == metadata["direct"][field]
    assert metadata["snapshot"]["snapshot_cleanup_verified"] is True
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    _worker(sys.argv[1], Path(sys.argv[2]))
