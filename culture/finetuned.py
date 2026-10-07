"""
cultureqc.finetuned — a fine-tuned model's reading, shown beside the shipped one.

A fine-tuned model (configs/finetuned_models.yaml) reads the same image as the
shipped Cellpose-SAM model. Its reading goes into the record's
`finetuned_reading` and decides nothing: the rules, the anomaly check and the
rationale use the shipped reading only.

Before the model loads, its weights are checked against the latest approved
change record for its id (culture/approvals.py). A mismatch, a missing file or
no approval gives a refusal: `confluency_pct` null and the check's status and
reason, written into the reading's record like any other field.

    from culture.finetuned import read
    read(img, "mcellseg_ftF_r2")   # -> {"id", "status", "check", "confluency_pct", ...}
"""

from __future__ import annotations

import os

import numpy as np
import yaml

from culture.approvals import REPO, check

CONFIG_PATH = os.path.join(REPO, "configs", "finetuned_models.yaml")

_models: dict[str, object] = {}       # weights SHA-256 -> loaded model


def load_config(path: str = CONFIG_PATH) -> dict:
    with open(path) as f:
        return (yaml.safe_load(f) or {}).get("models") or {}


def weights_file(entry: dict) -> str:
    d = os.environ.get("CULTUREQC_WEIGHTS_DIR")
    if d:
        p = os.path.join(d, os.path.basename(entry["path"]))
        if os.path.exists(p):
            return p
    return os.path.join(REPO, entry["path"])


def _model(path: str, sha: str):
    if sha not in _models:
        from culture.seg import _new_model
        _models.clear()                                    # one fine-tuned model in memory at a time
        _models[sha] = _new_model(pretrained_model=path)
    return _models[sha]


def read(img: np.ndarray, model_id: str, config_path: str = CONFIG_PATH) -> dict:
    """The fine-tuned model's reading of img, or a refusal; never used in a decision."""
    entry = load_config(config_path).get(model_id)
    if entry is None:
        raise KeyError(f"no fine-tuned model {model_id!r} in {config_path}")
    path = weights_file(entry)
    c = check("model", model_id, path)
    out = {"id": model_id, "base": entry["base"], "status": entry["status"], "cutoff": float(entry["cutoff"]),
           "band_pp": None, "check": c.record_fields(), "reason": c.reason, "confluency_pct": None,
           "used_in_decision": False}
    if not c.ok:
        return out
    model = _model(path, c.sha256)
    _, flows, _ = model.eval(img, diameter=None, channels=[0, 0], compute_masks=False)
    out["confluency_pct"] = round(float((flows[2] > out["cutoff"]).mean() * 100), 2)
    return out
