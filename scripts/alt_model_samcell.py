"""
Development comparison: SAMCell-Generalist's distance map on the MSC images (already scored; not held-out).

SAMCell (Malta, Sanganeriya et al., PLOS ONE 2025; code and weights MIT, github.com/saahilsanganeriya/SAMCell
release v1) regresses each pixel's distance to the cell boundary; its own foreground is distance > 0.09
(`cell_fill`). It needs its own environment (transformers, the `samcell` package), so it runs outside the
project venv and only writes maps; scripts/confluency_finetune.py dev reads them.

    python3.12 -m venv /tmp/venv_samcell && /tmp/venv_samcell/bin/pip install samcell==1.2.0
    curl -L -o cache/alt_models/samcell-generalist.pt \\
        https://github.com/saahilsanganeriya/SAMCell/releases/download/v1/samcell-generalist.pt
    /tmp/venv_samcell/bin/python scripts/alt_model_samcell.py

Maps: cache/probmaps_alt/samcell/msc/<name>.npz (key `dist`, float16, full size).
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
WEIGHTS = os.path.join("cache", "alt_models", "samcell-generalist.pt")
OUT = os.path.join("cache", "probmaps_alt", "samcell", "msc")
MSC = os.path.join("data", "sources", "msc", "images")


def main():
    import samcell
    h = hashlib.sha256(open(WEIGHTS, "rb").read()).hexdigest()
    os.makedirs(OUT, exist_ok=True)
    json.dump({"weights": WEIGHTS, "weights_sha256": h, "samcell": getattr(samcell, "__version__", "?")},
              open(os.path.join(os.path.dirname(OUT), "manifest.json"), "w"), indent=1)
    dev = torch.device("cuda") if torch.cuda.is_available() else torch.device("mps") if torch.backends.mps.is_available() else torch.device("cpu")
    model = samcell.FinetunedSAM("facebook/sam-vit-base")
    model.load_weights(WEIGHTS, map_location=torch.device("cpu"))
    pipe = samcell.SAMCellPipeline(model, device=dev)
    names = sorted(os.listdir(MSC))
    for k, n in enumerate(names):
        dst = os.path.join(OUT, n + ".npz")
        if os.path.exists(dst):
            continue
        img = cv2.imread(os.path.join(MSC, n), cv2.IMREAD_GRAYSCALE)
        dist = pipe.predict_on_full_img(img)
        np.savez_compressed(dst, dist=np.asarray(dist, dtype=np.float16))
        if k % 20 == 0:
            print(k, len(names), flush=True)


if __name__ == "__main__":
    sys.exit(main())
