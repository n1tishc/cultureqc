#!/usr/bin/env python3
"""
scripts/cache_tile_embeddings.py — DINOv2 embeddings of the QC tile, added to an
existing culture.cache under crop_spec="qctile".

Why: culture.cache.dino_embed() on a *full* frame goes through DINOv2's processor
(resize shortest side -> 256, centre-crop 224). For a 1392x1040 C2C12 frame that is
a ~4-5x downscale: 2-5 px bacterial sprites become sub-pixel, so a patch-kNN anomaly
score computed on full-frame embeddings can't see them — and those embeddings sit at
a different scale from a memory bank built on 256 px synthetic tiles (where "full"
already *is* a tile). Embedding the same 256 px centre tile the QC classifier sees
(culture.cache.qc_tile_from) keeps bank and query at one scale, at native resolution.

Storage follows culture.cache's existing conventions, so the existing loader works:
    Cache(dir).load_embeddings(sha, crop_spec="qctile")  -> {"cls", "patches"}
  - CLS row in embeddings_cls.parquet with crop_spec="qctile"
  - patches in embeddings/<sha>_qctile.npy (float16)

Resumable: skips (sha, "qctile", model) keys already present; flushes every chunk.
"""

from __future__ import annotations

import argparse
import os
import sys

import numpy as np


def build_qctile_embeddings(cache_dir: str, paths: list[str], chunk: int = 200, progress: bool = True) -> int:
    import cv2
    from culture.cache import (DINO_MODEL_NAME, DINO_MODEL_VERSION, Cache, _atomic_write_bytes, _Table,
                               dino_embed, image_sha256, qc_tile_from)

    n_new = 0
    for i in range(0, len(paths), chunk):
        cls_tbl = _Table(os.path.join(cache_dir, "embeddings_cls.parquet"),
                         ["image_sha256", "crop_spec", "model_name", "model_version"])
        for p in paths[i:i + chunk]:
            sha = image_sha256(p)
            if cls_tbl.has((sha, "qctile", DINO_MODEL_NAME, DINO_MODEL_VERSION)):
                continue
            img = cv2.imread(p, cv2.IMREAD_GRAYSCALE)
            if img is None:
                continue
            emb = dino_embed(qc_tile_from(img))
            cls_tbl.add({"image_sha256": sha, "crop_spec": "qctile", "model_name": DINO_MODEL_NAME,
                         "model_version": DINO_MODEL_VERSION, "cls": emb["cls"].tobytes(),
                         "cls_dtype": "float16", "cls_dim": int(emb["cls"].shape[0])})
            patch_path = os.path.join(cache_dir, "embeddings", f"{sha}_qctile.npy")
            if not os.path.exists(patch_path):
                _atomic_write_bytes(patch_path, lambda f, a=emb["patches"]: np.save(f, a))
            n_new += 1
        cls_tbl.flush()
        if progress:
            print(f"qctile embeddings: {min(i + chunk, len(paths))}/{len(paths)}  (+{n_new} new)", flush=True)
    Cache(cache_dir)._write_manifest()
    return n_new


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cache-dir", required=True)
    ap.add_argument("--paths-file", required=True, help="text file, one image path per line")
    a = ap.parse_args()
    with open(a.paths_file) as f:
        paths = [ln.strip() for ln in f if ln.strip()]
    print(build_qctile_embeddings(a.cache_dir, paths), "new qctile embeddings")


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.exit(main())
