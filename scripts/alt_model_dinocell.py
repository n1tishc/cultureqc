"""
Development comparison: DINOCell's cell-probability map on the MSC images (already scored; not held-out).

DINOCell (Stillwagon, VandeLoo, Magondu & Forest 2026, arXiv 2604.10609; code MIT,
github.com/kadenstillwagon/DINOCell; weights on Hugging Face, KadenStillwagon/DINOCell) predicts
Cellpose-style flows and a cell probability (sigmoid) from a DINOv2 encoder; its own foreground is
probability > 0.5. It pins its own torch/numpy/cellpose, so it runs in a separate environment (GPU; its
512 px windows are resized to 896 px, too large for a 16 GB laptop GPU) and only writes maps;
scripts/confluency_finetune.py curves/dev read them.

    virtualenv /content/venv_dino && /content/venv_dino/bin/pip install dinocell==0.74
    /content/venv_dino/bin/python scripts/alt_model_dinocell.py

Maps: cache/probmaps_alt/dinocell/msc/<name>.npz (key `prob`, float16, full size).
"""

import hashlib
import json
import os
import sys

import cv2
import numpy as np
import torch

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(REPO)
OUT = os.path.join("cache", "probmaps_alt", "dinocell", "msc")
MSC = os.path.join("data", "sources", "msc", "images")


def main():
    from huggingface_hub import hf_hub_download
    from dinocell.model import DINOCell
    from dinocell.pipeline import get_pipeline
    weights = hf_hub_download(repo_id="KadenStillwagon/DINOCell", filename="DINOCell_demo_model.pt")
    h = hashlib.sha256(open(weights, "rb").read()).hexdigest()
    os.makedirs(OUT, exist_ok=True)
    json.dump({"weights": "hf:KadenStillwagon/DINOCell/DINOCell_demo_model.pt", "weights_sha256": h},
              open(os.path.join(os.path.dirname(OUT), "manifest.json"), "w"), indent=1)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    # as dinocell.main.segment builds it
    model = DINOCell(dino_model=None, decoder_type="upsample", objective_type="flows", use_dino_weights=False,
                     patch_size=8, feat_size=64, crop_size=512, drop_rate=0.05, dropout_in_encoder=True,
                     finetune_vision=True, finetune_decoder=True, finetune_prediction_head=True)
    model.load_state_dict(torch.load(weights, map_location=torch.device("cpu")))
    model.to(dev)
    pipe = get_pipeline("flows", model, dev, crop_size=512, use_advanced_augmentations=False, overlap_size=512 // 4)
    names = sorted(os.listdir(MSC))
    for k, n in enumerate(names):
        dst = os.path.join(OUT, n + ".npz")
        if os.path.exists(dst):
            continue
        img = cv2.imread(os.path.join(MSC, n), cv2.IMREAD_GRAYSCALE)
        x, _ = pipe._resize(img)
        prob = np.asarray(pipe.predict_on_full_img(x)[2], dtype=np.float32)
        if prob.shape != img.shape:
            prob = cv2.resize(prob, (img.shape[1], img.shape[0]), interpolation=cv2.INTER_LINEAR)
        np.savez_compressed(dst, prob=prob.astype(np.float16))
        if k % 20 == 0:
            print(k, len(names), flush=True)


if __name__ == "__main__":
    sys.exit(main())
