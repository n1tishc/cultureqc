"""
demo/lab_demo.py — the approved fine-tuned model's demo set, for the Colab-hosted console only.

Off unless CULTUREQC_FINETUNED names a fine-tuned model (configs/finetuned_models.yaml); the Colab launcher
(nb/11_lab_demo.ipynb) sets it and the public console never does. When it is on, the fine-tuned model reads only
the images listed here, each matched by the SHA-256 of the exact file analysed: never an upload, so its reading is
never shown for a lab it was not trained on. The fine-tuned reading is shown beside the shipped one and decides
nothing (culture/finetuned.py).

The four images are test images of the sealed mCellSeg test (results/confluency_mcellseg.md), which the
fine-tuned model never trained on, chosen with the repository owner for the demo: three it reads close to the
experts, and one where it reads high enough to call passage early (results/finetuned_product_readings.jsonl has the
product's readings of all 90). Each is shown with the experts' outline coverage, computed from its own mask.
"""

from __future__ import annotations

import os

import cv2
import numpy as np

from culture.records import hash_file

MODEL_ENV = "CULTUREQC_FINETUNED"
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(REPO, "data", "sources", "mcellseg", "mCellSeg", "labeled")
CREDIT = "mCellSeg (Alam et al. 2026), CC BY 4.0, Zenodo record 20174259"
IMAGES = [  # (file name, SHA-256 of the file, cell line, button label)
    ("HUVEC_Cellsonly_CD7_09_81-0007.tif", "c7c617d655db966b430a00cfca7137545a3f4a8bafd4ed5eb85aa5d1ca215528",
     "HUVEC", "HUVEC · CD7_09"),
    ("HEK_6h_20240306_FumGW_C004T001.tif", "3f95bb7913028eedddf9825b96f6fdcda04dc8995dabc9bf3785e8ec12d1f132",
     "HEK293T", "HEK · FumGW"),
    ("HEK_6h_5A_z1_C004Z005.tif", "f6f013b79d7f4d04447af187e675c915ebe1eed83e0c7650b9f06849a0538571",
     "HEK293T", "HEK · 5A"),
    ("HEK_6h_FumGW_z2_C004Z006.tif", "a69f06cc0925696c8f49d12c5f8f17db607cc4bc40cdaa61c1034e171ae2f42c",
     "HEK293T", "HEK · FumGW z2"),
]
CELL_LINES = sorted({c for _, _, c, _ in IMAGES})


def model_id() -> str | None:
    return os.environ.get(MODEL_ENV) or None


def experts_pct(mask_path: str) -> float:
    m = cv2.imread(mask_path, cv2.IMREAD_UNCHANGED)
    return float((m > 0).mean() * 100)


def available(data: str = DATA) -> list[dict]:
    """The demo images present on disk with the expected bytes; empty when the mode is off."""
    if not model_id():
        return []
    out = []
    for name, sha, line, label in IMAGES:
        path = os.path.join(data, "images", name)
        mask = os.path.join(data, "masks", name[:-4] + "_mask.tif")
        if os.path.exists(path) and os.path.exists(mask) and hash_file(path) == sha:
            out.append({"name": name, "path": path, "sha256": sha, "cell_line": line, "label": label,
                        "experts_pct": experts_pct(mask)})
    return out


def match(path: str | None, images: list[dict]) -> dict | None:
    """The demo image this exact file is, by SHA-256; None for anything else, or when the mode is off."""
    if not model_id() or not path or not os.path.exists(path):
        return None
    sha = hash_file(path)
    return next((i for i in images if i["sha256"] == sha), None)


def preview(path: str, out_dir: str) -> str:
    """A browser-safe PNG of the image (browsers do not render TIFF)."""
    dst = os.path.join(out_dir, "lab_" + os.path.basename(path)[:-4] + ".png")
    if not os.path.exists(dst):
        img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
        cv2.imwrite(dst, img if img is not None else np.zeros((8, 8), np.uint8))
    return dst
