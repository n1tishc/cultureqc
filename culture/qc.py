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
from dataclasses import asdict, dataclass

import cv2
import numpy as np

CLASS_NAMES = ["normal", "contamination_suspected", "detachment", "image_quality"]
IMG_SIZE = 256
IMAGENET_MEAN = np.array([0.485, 0.456, 0.406]).reshape(3, 1, 1)
IMAGENET_STD = np.array([0.229, 0.224, 0.225]).reshape(3, 1, 1)

HF_REPO_ID = "LongGrainRice/cultureqc-qc-effnetb0-v1"


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
                    min_area_frac: float = 0.005, max_boxes: int = 8):
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

def qc_classify(img: np.ndarray, run_gradcam: bool = True) -> QCResult:
    """
    Classify a brightfield tile as normal / contamination_suspected /
    detachment / image_quality, with an optional Grad-CAM evidence bbox
    for the predicted class.

    Note: input should be roughly tile-scale (256x256 the model was trained
    on); a full flask image should be tiled by the caller first.
    """
    import torch

    model = _get_model()
    img_tensor = _preprocess(img)

    with torch.no_grad():
        logits = model(img_tensor.unsqueeze(0))
        probs = torch.softmax(logits, dim=1)[0]

    pred_idx = int(probs.argmax())
    per_class = {CLASS_NAMES[i]: round(float(probs[i]), 4) for i in range(len(CLASS_NAMES))}

    bboxes = []
    if run_gradcam:
        try:
            bboxes = _gradcam_bboxes(img_tensor, pred_idx)
        except Exception:
            bboxes = []

    return QCResult(
        flag=CLASS_NAMES[pred_idx],
        confidence=round(float(probs[pred_idx]), 4),
        evidence_bboxes=bboxes,
        per_class_probs=per_class,
        model_version="qc_effnetb0_v1",
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
