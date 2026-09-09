"""
cultureqc.seg — Confluency estimation from brightfield / phase-contrast images.

Methods:
    threshold:  Local-variance Otsu (classical baseline)
    probmap:    Cellpose-SAM cpsam_v2 cell-probability map (default, recommended)
    instance:   Cellpose-SAM cpsam_v2 instance masks (kept for comparison)

Usage:
    python -m cultureqc.seg path/to/image.tif
    python -m cultureqc.seg path/to/image.tif --method instance
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass
from typing import Literal

import cv2
import numpy as np
from skimage.filters import threshold_otsu

# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class ConfluencyResult:
    pct: float                                              # confluency percentage (0–100)
    confidence: float                                       # 0.0 = uncertain, 1.0 = certain
    method: str                                             # "threshold" | "probmap" | "instance"
    model_version: str                                      # e.g. "cpsam_v2" or "threshold_v1"
    extra: dict                                             # anything method-specific

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


# ---------------------------------------------------------------------------
# Threshold baseline
# ---------------------------------------------------------------------------

def threshold_confluency(img: np.ndarray) -> ConfluencyResult:
    """
    Local-variance thresholding on phase contrast.

    Phase-contrast cells are texture (high local variance), background is flat
    (low local variance). Fairer than plain intensity Otsu.
    """
    if img.ndim == 3:
        img = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

    g = cv2.GaussianBlur(img.astype(np.float32), (5, 5), 0)

    ksize = (15, 15)
    mean = cv2.blur(g, ksize)
    sq_mean = cv2.blur(g ** 2, ksize)
    local_var = np.clip(sq_mean - mean ** 2, 0, None)

    t = threshold_otsu(local_var)
    mask = local_var > t

    kernel_close = np.ones((7, 7), np.uint8)
    kernel_open = np.ones((3, 3), np.uint8)
    mask = cv2.morphologyEx(mask.astype(np.uint8), cv2.MORPH_CLOSE, kernel_close)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel_open)

    pct = float(mask.mean() * 100)

    return ConfluencyResult(
        pct=round(pct, 2),
        confidence=0.5,                                     # no calibrated confidence for threshold
        method="threshold",
        model_version="threshold_v1",
        extra={"otsu_threshold": float(t)},
    )


# ---------------------------------------------------------------------------
# Cellpose-SAM (lazy-loaded singleton)
# ---------------------------------------------------------------------------

_cp_model = None


def _get_model():
    global _cp_model
    if _cp_model is None:
        import torch
        from cellpose import models
        # Device selection, not analysis logic: the deployment target is a CPU-only
        # container, where a hard gpu=True asks cellpose for a device that is not
        # there. Segmentation behaviour and the reported confluency are unchanged.
        _cp_model = models.CellposeModel(gpu=torch.cuda.is_available())
    return _cp_model


def cpsam_confluency(
    img: np.ndarray,
    method: Literal["probmap", "instance"] = "probmap",
    thr: float = 0.0,
    band: float = 1.0,
) -> ConfluencyResult:
    """
    Confluency from Cellpose-SAM cpsam_v2.

    method="probmap" (default):
        Uses the raw cell-probability map. Skips flow-based instance
        reconstruction, which drops thin processes (neuronal, fibroblast
        periphery). Confluency is an area measurement, so instances aren't
        needed. This is the recommended method.

    method="instance":
        Uses the union of instance masks. Kept for comparison; known to
        under-segment spread / thin-process lines by 4–9 pp.

    Confidence (probmap only):
        Fraction of pixels within ±band of the cutoff. Many borderline
        pixels → low confidence.
    """
    model = _get_model()
    masks, flows, styles = model.eval(img, diameter=None, channels=[0, 0])

    if method == "probmap":
        prob = flows[2]
        fg = prob > thr
        pct = float(fg.mean() * 100)

        borderline_frac = float((np.abs(prob - thr) < band).mean())
        confidence = float(np.clip(1.0 - borderline_frac * 4, 0, 1))

        extra = {
            "cellprob_threshold": thr,
            "confidence_band": band,
            "borderline_fraction": round(borderline_frac, 4),
            "instance_pct": round(float((masks > 0).mean() * 100), 2),
        }
    else:
        fg = masks > 0
        pct = float(fg.mean() * 100)
        confidence = 0.7                                     # no calibrated confidence for instance
        extra = {"n_instances": int(masks.max())}

    return ConfluencyResult(
        pct=round(pct, 2),
        confidence=round(confidence, 3),
        method=method,
        model_version="cpsam_v2",
        extra=extra,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Estimate confluency from a brightfield image.")
    parser.add_argument("image", help="Path to a .tif or .png image")
    parser.add_argument(
        "--method",
        choices=["threshold", "probmap", "instance"],
        default="probmap",
        help="Estimation method (default: probmap)",
    )
    args = parser.parse_args()

    from cellpose import io
    img = io.imread(args.image)

    if args.method == "threshold":
        result = threshold_confluency(img)
    else:
        result = cpsam_confluency(img, method=args.method)

    print(result.to_json())


if __name__ == "__main__":
    main()
