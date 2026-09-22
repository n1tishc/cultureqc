"""
cultureqc.model_versions — resolve each model's weights SHA-256, for real.

Slice 2 (cultureQC_upgrade.md §5.1) requires visit_summary's model_versions
field to carry a weights SHA-256 per model, not just a version string — so
that Slice 2's trend functions can tell "same model" from "silently
different weights, same name" (culture/history.py's MODEL_VERSION_CHANGE
check depends on this being trustworthy, not guessed).

Each model's checkpoint is a real, locally-cached file (Cellpose-SAM under
~/.cellpose/models/, the HF Hub models under ~/.cache/huggingface/hub/) —
this module resolves the actual path via each library's own API (never by
guessing the cache layout) and hashes it with records.hash_file(), the same
SHA-256-of-raw-bytes convention already used for image_hash.

Usage:
    from culture.model_versions import get_model_versions
    get_model_versions()  # -> {"seg": {"version": "cpsam_v2", "weights_sha256": "..."}, ...}

A model that hasn't been loaded/downloaded yet on this machine gets
weights_sha256: None with a "note" explaining why — never a fabricated
placeholder hash.
"""

from __future__ import annotations

import functools

from culture.records import hash_file

SEG_MODEL_VERSION = "cpsam_v2"
QC_MODEL_VERSION = "qc_effnetb0_v1"
QC_HF_REPO_ID = "LongGrainRice/cultureqc-qc-effnetb0-v1"
QC_HF_FILENAME = "best.pt"
QUALITY_MODEL_VERSION = "quality_v1"  # deterministic CV, no weights to hash
DINO_MODEL_VERSION = "facebook/dinov2-small"


def _seg_weights_hash() -> tuple[str | None, str | None]:
    try:
        from culture.seg import _get_model as _get_seg_model
        model = _get_seg_model()
        path = getattr(model, "pretrained_model", None)
        # cellpose>=4 sometimes returns a list of per-stage paths.
        if isinstance(path, (list, tuple)):
            path = path[0] if path else None
        if not path:
            return None, "CellposeModel has no resolved pretrained_model path"
        return hash_file(path), None
    except Exception as e:  # model not loadable/downloadable right now
        return None, f"seg model unavailable: {e}"


def _qc_weights_hash() -> tuple[str | None, str | None]:
    try:
        from huggingface_hub import hf_hub_download
        # Cached no-op if already local; resolves the real path via the
        # library's own cache API rather than assuming its layout.
        path = hf_hub_download(QC_HF_REPO_ID, QC_HF_FILENAME)
        return hash_file(path), None
    except Exception as e:
        return None, f"qc weights unavailable: {e}"


def _dino_weights_hash() -> tuple[str | None, str | None]:
    try:
        from huggingface_hub import hf_hub_download, list_repo_files
        candidates = ["model.safetensors", "pytorch_model.bin"]
        try:
            real_files = set(list_repo_files(DINO_MODEL_VERSION))
            candidates = [c for c in candidates if c in real_files] or candidates
        except Exception:
            pass  # offline / rate-limited: fall back to trying both by name
        last_err = None
        for fname in candidates:
            try:
                path = hf_hub_download(DINO_MODEL_VERSION, fname)
                return hash_file(path), None
            except Exception as e:
                last_err = e
        return None, f"dino weights unavailable: {last_err}"
    except Exception as e:
        return None, f"dino weights unavailable: {e}"


@functools.lru_cache(maxsize=1)
def get_model_versions() -> dict:
    """One resolution per process (weights don't change mid-run); wall time
    is dominated by loading models that aren't already resident, same cost
    the live pipeline pays anyway the first time it touches each model."""
    seg_hash, seg_note = _seg_weights_hash()
    qc_hash, qc_note = _qc_weights_hash()
    dino_hash, dino_note = _dino_weights_hash()

    out = {
        "seg": {"version": SEG_MODEL_VERSION, "weights_sha256": seg_hash},
        "qc": {"version": QC_MODEL_VERSION, "weights_sha256": qc_hash},
        "quality": {"version": QUALITY_MODEL_VERSION, "weights_sha256": None},
        "dino": {"version": DINO_MODEL_VERSION, "weights_sha256": dino_hash},
    }
    for name, note in [("seg", seg_note), ("qc", qc_note), ("dino", dino_note)]:
        if note:
            out[name]["note"] = note
    out["quality"]["note"] = "deterministic CV (blur/exposure/uniformity) — no weights to hash"
    return out


if __name__ == "__main__":
    import json
    print(json.dumps(get_model_versions(), indent=2))
