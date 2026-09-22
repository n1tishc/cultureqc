"""
cultureqc.quality — deterministic image-quality gate (cultureQC_upgrade.md §5.2).

Runs before a visit enters history: focus/blur, exposure, illumination
uniformity. A failing visit gets an immediate REIMAGE decision and reason
codes, and does not enter trend computations — culture/history.py enforces
the "does not enter trend computations" half; this module only decides
pass/fail and why.

Reuses culture.cache.quality_metrics() for the raw numbers (parity with the
compute cache — the same function computes these for every cached image, so
there's exactly one implementation of "what blur/exposure/uniformity mean"
in the codebase, not two that could drift apart).

Thresholds live in configs/quality.yaml, calibrated on data/tiles/'s 1,000
"normal" synthetic tiles (scripts/calibrate_quality_gate.py) — real numbers,
not guessed: at the 1st/99th percentile cut, normal tiles false-positive at
~3.5%, and the (defect-type-mixed) "image_quality" class is caught ~72% of
the time by the union of all three checks. See configs/quality.yaml's own
"calibration" block for the exact run this came from.

Usage:
    from culture.quality import quality_gate
    result = quality_gate(img)  # -> QualityResult
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

import numpy as np
import yaml

_DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "configs", "quality.yaml")

_thresholds = None
_thresholds_path = None


def _load_thresholds(config_path: str = _DEFAULT_CONFIG_PATH) -> dict:
    global _thresholds, _thresholds_path
    if _thresholds is None or _thresholds_path != config_path:
        if not os.path.exists(config_path):
            raise FileNotFoundError(
                f"{config_path} not found — run scripts/calibrate_quality_gate.py "
                "first (needs cache/quality.parquet + data/tiles/manifest.csv)."
            )
        with open(config_path) as f:
            _thresholds = yaml.safe_load(f)
        _thresholds_path = config_path
    return _thresholds


@dataclass
class QualityResult:
    blur: float
    mean_intensity: float
    uniformity: float
    passed: bool
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "blur": self.blur,
            "mean_intensity": self.mean_intensity,
            "uniformity": self.uniformity,
            "pass": self.passed,
            "reasons": self.reasons,
        }


def quality_gate(img: np.ndarray, config_path: str = _DEFAULT_CONFIG_PATH) -> QualityResult:
    """Deterministic pass/fail + reason codes for one FOV image."""
    from culture.cache import quality_metrics

    t = _load_thresholds(config_path)
    m = quality_metrics(img)

    reasons = []
    if m["blur_laplacian_var"] < t["blur_laplacian_var"]["floor"]:
        reasons.append("blur_below_threshold")
    lo, hi = t["exposure_mean"]["low"], t["exposure_mean"]["high"]
    if not (lo <= m["exposure_mean"] <= hi):
        reasons.append("exposure_out_of_range")
    if m["uniformity_block_std"] > t["uniformity_block_std"]["ceiling"]:
        reasons.append("uniformity_above_threshold")

    return QualityResult(
        blur=m["blur_laplacian_var"],
        mean_intensity=m["exposure_mean"],
        uniformity=m["uniformity_block_std"],
        passed=(len(reasons) == 0),
        reasons=reasons,
    )


def config_hash(config_path: str = _DEFAULT_CONFIG_PATH) -> str:
    """SHA-256 of configs/quality.yaml's raw bytes — for visit_summary's
    config_hashes field (§5.1), same hash_file() convention as image_hash
    and model weights."""
    from culture.records import hash_file
    return hash_file(config_path)


if __name__ == "__main__":
    import sys

    import cv2

    if len(sys.argv) < 2:
        print("usage: python -m culture.quality <image_path>")
        raise SystemExit(1)
    img = cv2.imread(sys.argv[1], cv2.IMREAD_GRAYSCALE)
    result = quality_gate(img)
    import json
    print(json.dumps(result.to_dict(), indent=2))
