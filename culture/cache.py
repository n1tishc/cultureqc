"""
culture.cache — the Slice 1b compute cache (cultureQC_upgrade.md §4A).

One batched pass runs every expensive model over every image the project
needs, once, and stores raw outputs. Everything downstream — thresholds,
calibration, binning, crop choices, FOV-noise fitting — reads through this
module instead of re-running inference. Rule 10: no new GPU passes after
this slice except where a later slice explicitly calls for one.

Storage layout under `cache_dir`:
    images.parquet          one row per image_sha256: dataset, source_path,
                             sequence_id, frame_idx, timestamp, height, width,
                             bit_depth, normalization
    confluency.parquet      one row per (image_sha256, crop_spec, model_name,
                             model_version): pct, confidence, extra (json str)
    probmaps/<sha256>.npz   downsampled uint8 cell-probability map, full-frame
                             crop_spec only — the raw signal thresholds derive from
    logits.parquet          one row per (image_sha256, crop_spec, model_name,
                             model_version): raw per-class logits (pre-softmax),
                             on the exact tile the live app would classify
    quality.parquet         blur / exposure / uniformity, one row per image_sha256
    embeddings/<sha256>_<crop_spec>.npy   DINOv2 patch embeddings, float16
    embeddings_cls.parquet  CLS token only, for rows not kept as full patch
                             embeddings (export_slim keeps only this + the
                             bank-source/eval/replay subset's full patches)
    MANIFEST.json           row counts, model versions + weight hashes, config
                             hash, SHA-256 per shard file

Every row is keyed by (image_sha256, crop_spec, model_name, model_version).
crop_spec is "full" for the whole image, or "crop_f<frac>_s<seed>_k<index>"
for one of the K deterministic FOV-noise sub-crops (§4.3).

Resumable + idempotent by design: `build()` reads the existing index for each
output table before computing anything, and skips keys already present. Each
shard is written to a temp path and atomically renamed into place, so a run
killed mid-shard (Colab disconnect) leaves no partial/corrupt file — the
worst case is redoing the one shard in flight, not the whole run.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from typing import Iterable, Literal

import numpy as np
import pandas as pd

CACHE_VERSION = "1"  # bump if the storage layout changes incompatibly

QUALITY_MODEL_VERSION = "quality_v1"
DINO_MODEL_NAME = "dinov2"
DINO_MODEL_VERSION = "facebook/dinov2-small"
PROBMAP_DOWNSAMPLE = 4  # store the cell-probability map at 1/4 resolution


# ---------------------------------------------------------------------------
# Keys and specs
# ---------------------------------------------------------------------------

def image_sha256(path: str) -> str:
    """Same hashing as culture/records.py::hash_file — one identity for an
    image whether it's referenced by the live pipeline or the cache."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def fov_crop_specs(image_sha: str, fracs=(0.25, 0.5), k: int = 8) -> list[dict]:
    """
    Deterministic sub-crop specs for the FOV-noise model (§4.3). Seeded off
    the image's own hash so specs are reproducible per-image without a
    shared global counter (order-independent — safe to compute in any order
    or resume mid-way).
    """
    specs = []
    for frac in fracs:
        seed = int(image_sha[:8], 16)
        rng = np.random.default_rng(seed ^ int(round(frac * 1000)))
        for i in range(k):
            oy, ox = float(rng.uniform(0, 1)), float(rng.uniform(0, 1))
            specs.append({
                "crop_spec": f"crop_f{frac}_s{seed}_k{i}",
                "frac": frac,
                "offset_y": oy,
                "offset_x": ox,
            })
    return specs


def crop_from_spec(img: np.ndarray, spec: dict) -> np.ndarray:
    h, w = img.shape[:2]
    ch, cw = int(h * spec["frac"]), int(w * spec["frac"])
    ch, cw = max(ch, 1), max(cw, 1)
    y0 = int(spec["offset_y"] * max(h - ch, 0))
    x0 = int(spec["offset_x"] * max(w - cw, 0))
    return img[y0 : y0 + ch, x0 : x0 + cw]


def qc_tile_from(img: np.ndarray, tile_size: int = 256) -> np.ndarray:
    """The exact crop-or-resize culture/pipeline.py::analyze() feeds qc_classify.
    Cache logits must be computed on this same input or the parity test fails."""
    import cv2

    h, w = img.shape[:2]
    if h >= tile_size and w >= tile_size:
        cy, cx = h // 2, w // 2
        return img[cy - tile_size // 2 : cy + tile_size // 2,
                    cx - tile_size // 2 : cx + tile_size // 2]
    return cv2.resize(img, (tile_size, tile_size))


# ---------------------------------------------------------------------------
# Shard store: parquet tables with an on-disk existing-key index
# ---------------------------------------------------------------------------

class _Table:
    """One append-only parquet table under cache_dir, keyed by `key_cols`.
    Reads the existing file (if any) once, holds new rows in memory, and
    flushes atomically. Not for concurrent writers — build() runs single-
    process, shard by shard."""

    def __init__(self, path: str, key_cols: list[str]):
        self.path = path
        self.key_cols = key_cols
        self._existing_keys: set[tuple] = set()
        self._new_rows: list[dict] = []
        if os.path.exists(path):
            existing = pd.read_parquet(path)
            self._existing_keys = set(
                tuple(row) for row in existing[key_cols].itertuples(index=False, name=None)
            )
            self._existing_df = existing
        else:
            self._existing_df = None

    def has(self, key: tuple) -> bool:
        return key in self._existing_keys

    def add(self, row: dict):
        key = tuple(row[c] for c in self.key_cols)
        if key in self._existing_keys:
            return
        self._existing_keys.add(key)
        self._new_rows.append(row)

    def flush(self) -> str | None:
        """Atomically merge new rows into the parquet file. Returns the
        shard's SHA-256 if anything was written, else None."""
        if not self._new_rows:
            return None
        new_df = pd.DataFrame(self._new_rows)
        out = pd.concat([self._existing_df, new_df], ignore_index=True) if self._existing_df is not None else new_df
        tmp = self.path + ".tmp"
        out.to_parquet(tmp, index=False)
        os.replace(tmp, self.path)  # atomic on the same filesystem
        self._existing_df = out
        self._new_rows = []
        h = hashlib.sha256()
        with open(self.path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 16), b""):
                h.update(chunk)
        return h.hexdigest()


def _atomic_write_bytes(path: str, write_fn):
    """write_fn(fileobj) writes into an open binary file; renamed into place
    only on success. Takes a file object, not a path string — np.save /
    np.savez_compressed silently APPEND their extension onto a bare path
    that doesn't already end with it (so a ".tmp" path becomes
    ".tmp.npz" on disk, and the rename below would then look for a file
    that was never created); passing a file object bypasses that."""
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        write_fn(f)
    os.replace(tmp, path)


# ---------------------------------------------------------------------------
# Quality metrics (cheap, no model — §4A.2)
# ---------------------------------------------------------------------------

def quality_metrics(img: np.ndarray) -> dict:
    """Blur (variance of Laplacian, higher = sharper), exposure (mean
    intensity, 0-255), uniformity (std of block means — low = evenly lit).
    Simplified proxies, not a validated quality model; the quality gate
    (Slice 2) tunes thresholds against these offline, without recompute."""
    import cv2

    g = img if img.ndim == 2 else cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    lap = cv2.Laplacian(g.astype(np.float32), cv2.CV_32F)
    blur = float(lap.var())
    exposure = float(g.mean())
    bs = 32
    h, w = g.shape[:2]
    block_means = [
        g[y:y+bs, x:x+bs].mean()
        for y in range(0, h - bs + 1, bs)
        for x in range(0, w - bs + 1, bs)
    ]
    uniformity = float(np.std(block_means)) if block_means else 0.0
    return {"blur_laplacian_var": blur, "exposure_mean": exposure, "uniformity_block_std": uniformity}


# ---------------------------------------------------------------------------
# DINOv2 (lazy-loaded singleton, same idiom as culture/seg.py, culture/qc.py)
# ---------------------------------------------------------------------------

_dino_model = None
_dino_processor = None


def _get_dino():
    global _dino_model, _dino_processor
    if _dino_model is None:
        import torch
        from transformers import AutoImageProcessor, AutoModel

        _dino_processor = AutoImageProcessor.from_pretrained(f"facebook/{DINO_MODEL_VERSION.split('/')[-1]}")
        _dino_model = AutoModel.from_pretrained(f"facebook/{DINO_MODEL_VERSION.split('/')[-1]}")
        _dino_model.eval()
        _dino_model = _dino_model.to(torch.device("cuda" if torch.cuda.is_available() else "cpu"))
    return _dino_model, _dino_processor


def dino_embed(img: np.ndarray) -> dict:
    """Returns {'cls': float16[D], 'patches': float16[N, D]}."""
    import cv2
    import torch

    model, processor = _get_dino()
    rgb = img if img.ndim == 3 else cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
    inputs = processor(images=rgb, return_tensors="pt").to(next(model.parameters()).device)
    with torch.no_grad():
        out = model(**inputs)
    last_hidden = out.last_hidden_state[0]  # [1 + n_patches, D]
    cls = last_hidden[0].cpu().numpy().astype(np.float16)
    patches = last_hidden[1:].cpu().numpy().astype(np.float16)
    return {"cls": cls, "patches": patches}


# ---------------------------------------------------------------------------
# The cache
# ---------------------------------------------------------------------------

@dataclass
class ImageRecord:
    path: str
    dataset: str
    source_path: str
    sequence_id: str = ""
    frame_idx: int = -1
    timestamp: str = ""


class Cache:
    def __init__(self, cache_dir: str):
        self.dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        os.makedirs(os.path.join(cache_dir, "probmaps"), exist_ok=True)
        os.makedirs(os.path.join(cache_dir, "embeddings"), exist_ok=True)

    def _path(self, name: str) -> str:
        return os.path.join(self.dir, name)

    # -- build --------------------------------------------------------

    def build(
        self,
        records: Iterable[ImageRecord],
        models: tuple[str, ...] = ("seg", "qc", "quality", "dino"),
        crop_fracs=(0.25, 0.5),
        crops_per_frac: int = 8,
        keep_full_patches_for: set[str] | None = None,
        progress: bool = True,
    ) -> dict:
        """
        Process `records`, skipping any (image_sha256, crop_spec, model_name,
        model_version) already in the relevant table. Returns a summary dict
        (counts processed/skipped, wall time, per-model seconds).

        `keep_full_patches_for`: set of image_sha256 to store full DINOv2
        patch embeddings for (bank-source normals, eval sets, replay frames).
        Every other image gets CLS-only, per §4A.3's storage budget.
        """
        import cv2

        keep_full_patches_for = keep_full_patches_for or set()

        images_tbl = _Table(self._path("images.parquet"), ["image_sha256"])
        conf_tbl = _Table(self._path("confluency.parquet"), ["image_sha256", "crop_spec", "model_name", "model_version"])
        logits_tbl = _Table(self._path("logits.parquet"), ["image_sha256", "crop_spec", "model_name", "model_version"])
        quality_tbl = _Table(self._path("quality.parquet"), ["image_sha256", "model_name", "model_version"])
        cls_tbl = _Table(self._path("embeddings_cls.parquet"), ["image_sha256", "crop_spec", "model_name", "model_version"])

        timings = {m: 0.0 for m in models}
        n_processed, n_skipped_images = 0, 0
        records = list(records)
        it = records
        if progress:
            from tqdm import tqdm
            it = tqdm(records, desc="cache build")

        for rec in it:
            sha = image_sha256(rec.path)
            img = cv2.imread(rec.path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                continue
            h, w = img.shape[:2]

            if not images_tbl.has((sha,)):
                images_tbl.add({
                    "image_sha256": sha, "dataset": rec.dataset, "source_path": rec.source_path,
                    "sequence_id": rec.sequence_id, "frame_idx": rec.frame_idx,
                    "timestamp": rec.timestamp, "height": h, "width": w, "bit_depth": str(img.dtype),
                    "normalization": "grayscale_imread",
                })

            crop_specs = [{"crop_spec": "full", "frac": 1.0, "offset_y": 0.0, "offset_x": 0.0}]
            crop_specs += fov_crop_specs(sha, crop_fracs, crops_per_frac)

            if "seg" in models:
                t0 = time.time()
                self._build_seg(sha, img, crop_specs, conf_tbl)
                timings["seg"] += time.time() - t0

            if "qc" in models:
                t0 = time.time()
                self._build_qc(sha, img, crop_specs, logits_tbl)
                timings["qc"] += time.time() - t0

            if "quality" in models and not quality_tbl.has((sha, "quality", QUALITY_MODEL_VERSION)):
                t0 = time.time()
                q = quality_metrics(img)
                q.update({"image_sha256": sha, "model_name": "quality", "model_version": QUALITY_MODEL_VERSION})
                quality_tbl.add(q)
                timings["quality"] += time.time() - t0

            if "dino" in models:
                t0 = time.time()
                self._build_dino(sha, img, keep_full_patches_for, cls_tbl)
                timings["dino"] += time.time() - t0

            n_processed += 1

        shard_hashes = {}
        for name, tbl in [("images.parquet", images_tbl), ("confluency.parquet", conf_tbl),
                           ("logits.parquet", logits_tbl), ("quality.parquet", quality_tbl),
                           ("embeddings_cls.parquet", cls_tbl)]:
            h = tbl.flush()
            if h:
                shard_hashes[name] = h

        self._write_manifest(shard_hashes)

        return {
            "n_images": n_processed,
            "timings_s": timings,
            "per_image_s": {k: (v / n_processed if n_processed else 0.0) for k, v in timings.items()},
        }

    def _build_seg(self, sha, img, crop_specs, conf_tbl):
        from culture.seg import cpsam_confluency

        # Full-frame: store the downsampled prob map (the raw signal) plus
        # the confluency-at-default-threshold convenience row.
        full_key = (sha, "full", "seg", "cpsam_v2")
        need_full = not conf_tbl.has(full_key)
        probmap_path = os.path.join(self.dir, "probmaps", f"{sha}.npz")
        need_probmap = not os.path.exists(probmap_path)
        if need_full or need_probmap:
            captured = {}
            result = cpsam_confluency(img, method="probmap", on_visual=lambda prob, fg: captured.update(prob=prob))
            if need_full:
                conf_tbl.add({
                    "image_sha256": sha, "crop_spec": "full", "model_name": "seg", "model_version": "cpsam_v2",
                    "pct": result.pct, "confidence": result.confidence, "extra": json.dumps(result.extra),
                })
            if need_probmap and "prob" in captured:
                prob = captured["prob"]
                small = prob[::PROBMAP_DOWNSAMPLE, ::PROBMAP_DOWNSAMPLE]
                # Raw prob values are unbounded logits in practice small (~[-10,10]);
                # store as int16 scaled by 1000 rather than lossy uint8, so any
                # threshold in a sane range is exactly recoverable.
                scaled = np.clip(small * 1000, -32000, 32000).astype(np.int16)
                _atomic_write_bytes(probmap_path, lambda f: np.savez_compressed(f, prob_x1000=scaled))

        # Crop confluency rows for the FOV-noise model, computed from the
        # already-loaded full prob map when we have it this call, else by
        # re-running seg on the crop (still resumable/skippable per-row).
        for spec in crop_specs[1:]:
            key = (sha, spec["crop_spec"], "seg", "cpsam_v2")
            if conf_tbl.has(key):
                continue
            crop_img = crop_from_spec(img, spec)
            r = cpsam_confluency(crop_img, method="probmap")
            conf_tbl.add({
                "image_sha256": sha, "crop_spec": spec["crop_spec"], "model_name": "seg", "model_version": "cpsam_v2",
                "pct": r.pct, "confidence": r.confidence, "extra": json.dumps({**r.extra, **spec}),
            })

    def _build_qc(self, sha, img, crop_specs, logits_tbl):
        import torch
        from culture.qc import _get_model, _preprocess

        # Only "full" is meaningful for QC (it's always a 256x256-tile
        # classifier fed the same center-crop-or-resize regardless of the
        # source image's size) — matches culture/pipeline.py exactly.
        key = (sha, "full", "qc", "qc_effnetb0_v1")
        if logits_tbl.has(key):
            return
        model = _get_model()
        tile = qc_tile_from(img)
        img_tensor = _preprocess(tile).to(next(model.parameters()).device)
        with torch.no_grad():
            logits = model(img_tensor.unsqueeze(0))[0].cpu().numpy().astype(np.float32)
        logits_tbl.add({
            "image_sha256": sha, "crop_spec": "full", "model_name": "qc", "model_version": "qc_effnetb0_v1",
            "logits": json.dumps(logits.tolist()),
        })

    def _build_dino(self, sha, img, keep_full_patches_for, cls_tbl):
        key = (sha, "full", DINO_MODEL_NAME, DINO_MODEL_VERSION)
        if cls_tbl.has(key):
            return
        emb = dino_embed(img)
        cls_tbl.add({
            "image_sha256": sha, "crop_spec": "full", "model_name": DINO_MODEL_NAME, "model_version": DINO_MODEL_VERSION,
            "cls": emb["cls"].tobytes(), "cls_dtype": "float16", "cls_dim": emb["cls"].shape[0],
        })
        if sha in keep_full_patches_for:
            patch_path = os.path.join(self.dir, "embeddings", f"{sha}_full.npy")
            if not os.path.exists(patch_path):
                _atomic_write_bytes(patch_path, lambda f: np.save(f, emb["patches"]))

    def _write_manifest(self, shard_hashes: dict):
        manifest = {
            "cache_version": CACHE_VERSION,
            "written_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "row_counts": {},
            "model_versions": {
                "seg": "cpsam_v2", "qc": "qc_effnetb0_v1",
                "quality": QUALITY_MODEL_VERSION, "dino": DINO_MODEL_VERSION,
            },
            "shard_sha256": shard_hashes,
        }
        for name in ["images.parquet", "confluency.parquet", "logits.parquet", "quality.parquet", "embeddings_cls.parquet"]:
            p = self._path(name)
            if os.path.exists(p):
                manifest["row_counts"][name] = len(pd.read_parquet(p, columns=[]))
        manifest_path = self._path("MANIFEST.json")
        _atomic_write_bytes(manifest_path, lambda f: f.write(json.dumps(manifest, indent=2).encode("utf-8")))

    # -- load -----------------------------------------------------------

    def load_confluency(self, crop_spec: str | None = None) -> pd.DataFrame:
        df = pd.read_parquet(self._path("confluency.parquet"))
        return df[df.crop_spec == crop_spec] if crop_spec else df

    def load_probmap(self, image_sha256: str) -> np.ndarray:
        """Returns the downsampled prob map as float32 (unscaled)."""
        npz = np.load(os.path.join(self.dir, "probmaps", f"{image_sha256}.npz"))
        return npz["prob_x1000"].astype(np.float32) / 1000.0

    def load_logits(self) -> pd.DataFrame:
        df = pd.read_parquet(self._path("logits.parquet"))
        df["logits"] = df["logits"].apply(json.loads)
        return df

    def load_quality(self) -> pd.DataFrame:
        return pd.read_parquet(self._path("quality.parquet"))

    def load_embeddings(self, image_sha256: str, crop_spec: str = "full") -> dict:
        """CLS always available; patches only for images kept full (see build()'s
        keep_full_patches_for)."""
        cls_df = pd.read_parquet(self._path("embeddings_cls.parquet"))
        row = cls_df[(cls_df.image_sha256 == image_sha256) & (cls_df.crop_spec == crop_spec)]
        out = {}
        if len(row):
            r = row.iloc[0]
            out["cls"] = np.frombuffer(r["cls"], dtype=r["cls_dtype"]).reshape(r["cls_dim"])
        patch_path = os.path.join(self.dir, "embeddings", f"{image_sha256}_{crop_spec}.npy")
        if os.path.exists(patch_path):
            out["patches"] = np.load(patch_path)
        return out

    # -- slim export ------------------------------------------------------

    def export_slim(self, out_dir: str):
        """A Mac-sized copy: everything except the full patch-embedding .npy
        files (kept: CLS-only table, which every image has)."""
        import shutil

        os.makedirs(out_dir, exist_ok=True)
        for name in ["images.parquet", "confluency.parquet", "logits.parquet",
                     "quality.parquet", "embeddings_cls.parquet", "MANIFEST.json"]:
            src = self._path(name)
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(out_dir, name))
        src_probmaps = os.path.join(self.dir, "probmaps")
        if os.path.exists(src_probmaps):
            shutil.copytree(src_probmaps, os.path.join(out_dir, "probmaps"), dirs_exist_ok=True)
        # embeddings/ (full patches) intentionally omitted from the slim export.
