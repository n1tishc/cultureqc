"""
cultureqc.qc — Contamination / detachment / image-quality classification.

Classes:
    normal
    contamination_suspected
    detachment
    image_quality

Trained entirely on synthetic data (bacterial sprites composited onto LIVECell
images + mask-erosion detachment). No real contaminated-culture images were
used in training — no open dataset of these exists. See model card for
real-world transfer caveats.

Usage:
    python -m cultureqc.qc path/to/image.tif
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass

import cv2
import numpy as np

CLASS_NAMES = ["normal", "contamination_suspected", "detachment", "image_quality"]
IMG_SIZE = 256
IMAGENET_MEAN = np.array([0.485, 0.456, 0.406]).reshape(3, 1, 1)
IMAGENET_STD = np.array([0.229, 0.224, 0.225]).reshape(3, 1, 1)

HF_REPO_ID = "LongGrainRice/cultureqc-qc-effnetb0-v1"
MODEL_VERSION = "qc_effnetb0_v1"
QC_CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "configs", "qc.yaml")
# Spec v4 §2B.2 wording; configs/qc.yaml's classifier.label overrides it.
DEMOTED_LABEL = ("Trained on synthetic tiles; known not to transfer to this imaging setup "
                 "(see validation report)")


# ---------------------------------------------------------------------------
# Scale matching (spec v3.2 §2B.1, B0; configs/qc.yaml)
# ---------------------------------------------------------------------------

def load_qc_config(path: str = QC_CONFIG_PATH) -> dict:
    import yaml

    with open(path) as f:
        return yaml.safe_load(f)


def rescale_factor(cfg: dict, multiplier: float | None = None, force: bool = False) -> float | None:
    """source_um_per_px / target_um_per_px × multiplier, or None when rescaling
    is off (unless force, which B0 uses to evaluate before it is switched on)."""
    r = cfg["rescale"]
    if not (r.get("enabled") or force):
        return None
    m = r.get("multiplier", 1.0) if multiplier is None else multiplier
    return float(r["source_um_per_px"]) / float(r["target_um_per_px"]) * float(m)


def rescale_frame(img: np.ndarray, factor: float | None) -> np.ndarray:
    """Resize a whole frame by `factor` before the QC tile is cut, so the 256 px
    tile spans the physical area of a training tile. Linear when enlarging,
    area-averaging when shrinking (no aliasing)."""
    if factor is None or factor == 1.0:
        return img
    h, w = img.shape[:2]
    size = (max(1, round(w * factor)), max(1, round(h * factor)))
    return cv2.resize(img, size, interpolation=cv2.INTER_LINEAR if factor > 1 else cv2.INTER_AREA)


def classifier_demoted(path: str = QC_CONFIG_PATH) -> bool:
    """True unless configs/qc.yaml explicitly says `classifier.demoted: false`.
    Fails safe: a missing file or key means demoted (spec v4 §2B.2, B3)."""
    try:
        cfg = load_qc_config(path) or {}
    except FileNotFoundError:
        return True
    return (cfg.get("classifier") or {}).get("demoted", True) is not False


def demoted_label(path: str = QC_CONFIG_PATH) -> str:
    try:
        label = ((load_qc_config(path) or {}).get("classifier") or {}).get("label")
    except FileNotFoundError:
        label = None
    return label or DEMOTED_LABEL


def rescaled_model_version(factor: float) -> str:
    """Logits from rescaled input are a different input distribution: never
    mix them with MODEL_VERSION rows (trend windows, calibration)."""
    return f"{MODEL_VERSION}+rescale{factor:.3f}"


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class QCResult:
    flag: str
    confidence: float
    evidence_bboxes: list          # list of (x, y, w, h), can be empty
    per_class_probs: dict
    model_version: str
    calibrated: bool = False       # temperature-scaled (configs/calibration.yaml)?

    # Keep backward compat: single bbox returns the largest, or None
    @property
    def evidence_bbox(self):
        return self.evidence_bboxes[0] if self.evidence_bboxes else None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["evidence_bboxes"] = [list(b) for b in self.evidence_bboxes]
        d["evidence_bbox"] = list(self.evidence_bboxes[0]) if self.evidence_bboxes else None
        return d

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

# ---------------------------------------------------------------------------
# Model (lazy-loaded singleton)
# ---------------------------------------------------------------------------

_model = None
_cam = None
_calibration = None
_calibration_loaded = False


def _get_calibration():
    """configs/calibration.yaml, loaded once (None if absent)."""
    global _calibration, _calibration_loaded
    if not _calibration_loaded:
        from culture.calibration import load_calibration
        _calibration, _calibration_loaded = load_calibration(), True
    return _calibration


def _get_model():
    global _model
    if _model is None:
        import timm
        import torch
        from huggingface_hub import hf_hub_download

        ckpt_path = hf_hub_download(HF_REPO_ID, "best.pt")
        ckpt = torch.load(ckpt_path, map_location="cpu")

        _model = timm.create_model("efficientnet_b0", pretrained=False, num_classes=len(CLASS_NAMES))
        _model.load_state_dict(ckpt["model_state"])
        _model.eval()
        # Same device-selection idiom culture/seg.py uses for Cellpose-SAM: True
        # on real GPU hardware, and — inside an @spaces.GPU call on a ZeroGPU
        # Space — also True there, since `import spaces` makes that check succeed
        # for the duration of the call. False (CPU) everywhere else.
        _model = _model.to(torch.device("cuda" if torch.cuda.is_available() else "cpu"))
    return _model


def _get_cam():
    global _cam
    if _cam is None:
        from pytorch_grad_cam import GradCAM

        model = _get_model()
        _cam = GradCAM(model=model, target_layers=[model.conv_head])
    return _cam


def _preprocess(img: np.ndarray) -> "torch.Tensor":
    import torch

    if img.ndim == 3:
        img = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    img = cv2.resize(img, (IMG_SIZE, IMG_SIZE))
    img = img.astype(np.float32) / 255.0
    img3 = np.stack([img, img, img], axis=0)
    img3 = (img3 - IMAGENET_MEAN) / IMAGENET_STD
    return torch.tensor(img3, dtype=torch.float32)

def _gradcam_bboxes(img_tensor, target_class: int, threshold: float = 0.3,
                    min_area_frac: float = 0.005, max_boxes: int = 8, on_visual=None):
    """
    Multiple bounding boxes from Grad-CAM, one per activated region.
    Like object detection: each distinct hot spot gets its own box.

    Args:
        threshold:      CAM activation cutoff (lower = more sensitive)
        min_area_frac:  ignore components smaller than this fraction of the tile
        max_boxes:      cap on number of boxes returned

    Returns list of (x, y, w, h) tuples, largest first. Empty list if nothing found.
    """
    from pytorch_grad_cam.utils.model_targets import ClassifierOutputTarget

    cam_obj = _get_cam()
    targets = [ClassifierOutputTarget(target_class)]
    grayscale_cam = cam_obj(input_tensor=img_tensor.unsqueeze(0), targets=targets)[0]

    if on_visual is not None:
        on_visual(grayscale_cam)

    binary = (grayscale_cam > threshold).astype(np.uint8)
    tile_area = binary.shape[0] * binary.shape[1]
    min_area = int(tile_area * min_area_frac)

    n_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)

    boxes = []
    for i in range(1, n_labels):  # skip background
        area = stats[i, cv2.CC_STAT_AREA]
        if area < min_area:
            continue
        x = int(stats[i, cv2.CC_STAT_LEFT])
        y = int(stats[i, cv2.CC_STAT_TOP])
        w = int(stats[i, cv2.CC_STAT_WIDTH])
        h = int(stats[i, cv2.CC_STAT_HEIGHT])
        boxes.append((x, y, w, h, area))

    # Sort by area descending, cap at max_boxes
    boxes.sort(key=lambda b: b[4], reverse=True)
    return [(x, y, w, h) for x, y, w, h, _ in boxes[:max_boxes]]

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def qc_classify(img: np.ndarray, run_gradcam: bool = True, on_visual=None) -> QCResult:
    """
    Classify a brightfield tile as normal / contamination_suspected /
    detachment / image_quality, with an optional Grad-CAM evidence bbox
    for the predicted class.

    Note: input should be roughly tile-scale (256x256 the model was trained
    on); a full flask image should be tiled by the caller first.

    Probabilities are temperature-scaled with configs/calibration.yaml when
    it was fit for MODEL_VERSION (`calibrated` says whether). That fit is on
    synthetic val tiles (V8), so it says nothing about calibration on real
    images. Scaling doesn't change the arg-max, so the flag and the
    Grad-CAM target are the same either way.
    """
    import torch

    from culture.calibration import calibrated_probs

    model = _get_model()
    img_tensor = _preprocess(img).to(next(model.parameters()).device)

    with torch.no_grad():
        logits = model(img_tensor.unsqueeze(0))[0].cpu().numpy()
    probs, calibrated = calibrated_probs(logits, _get_calibration(), MODEL_VERSION)

    pred_idx = int(probs.argmax())
    per_class = {CLASS_NAMES[i]: round(float(probs[i]), 4) for i in range(len(CLASS_NAMES))}

    bboxes = []
    if run_gradcam:
        try:
            bboxes = _gradcam_bboxes(img_tensor, pred_idx, on_visual=on_visual)
        except Exception:
            bboxes = []

    return QCResult(
        flag=CLASS_NAMES[pred_idx],
        confidence=round(float(probs[pred_idx]), 4),
        evidence_bboxes=bboxes,
        per_class_probs=per_class,
        model_version=MODEL_VERSION,
        calibrated=calibrated,
    )
# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Classify a brightfield tile for QC flags.")
    parser.add_argument("image", help="Path to a .tif or .png tile")
    parser.add_argument("--no-gradcam", action="store_true", help="Skip Grad-CAM (faster)")
    args = parser.parse_args()

    img = cv2.imread(args.image, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise FileNotFoundError(f"Could not read image: {args.image}")

    result = qc_classify(img, run_gradcam=not args.no_gradcam)
    print(result.to_json())


if __name__ == "__main__":
    main()
