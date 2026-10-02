"""
cultureqc.weights — SHA-256 of each model's weights file, for model_weights_hash.

Keyed like the record's model_versions (seg, dino, qc). A file that isn't on
this machine gives null, never a guessed hash. Each file is hashed once per
process (the Cellpose-SAM file is about 1.2 GB) and re-hashed if its size or
modification time changes.
"""

from __future__ import annotations

import os

_memo: dict[tuple[str, int, float], str] = {}


def _sha(path: str | None) -> str | None:
    if not path or not os.path.exists(path):
        return None
    st = os.stat(path)
    key = (os.path.realpath(path), st.st_size, st.st_mtime)
    if key not in _memo:
        from culture.records import hash_file
        _memo[key] = hash_file(path)
    return _memo[key]


def _cellpose_path() -> str | None:
    try:
        from cellpose import models
        return os.path.join(str(models.MODEL_DIR), "cpsam_v2")
    except Exception:
        return None


def _hf_cached(repo: str, filename: str) -> str | None:
    try:
        from huggingface_hub import try_to_load_from_cache
        p = try_to_load_from_cache(repo, filename)
        return p if isinstance(p, str) else None
    except Exception:
        return None


def weights_hashes() -> dict:
    from culture.cache import DINO_MODEL_VERSION
    from culture.qc import HF_REPO_ID
    dino_repo = f"facebook/{DINO_MODEL_VERSION.split('/')[-1]}"
    return {
        "seg": _sha(_cellpose_path()),
        "dino": _sha(_hf_cached(dino_repo, "model.safetensors") or _hf_cached(dino_repo, "pytorch_model.bin")),
        "qc": _sha(_hf_cached(HF_REPO_ID, "best.pt")),
    }
