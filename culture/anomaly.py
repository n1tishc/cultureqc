"""
cultureqc.anomaly — density-conditioned patch-kNN anomaly scoring (A4 minimal;
cultureQC_upgrade_spec.md §2A.5, §7).

Training-free, from cached DINOv2 patch embeddings (crop_spec "qctile": the
256 px centre tile of a frame at native resolution, 16x16 patches x 384):

- Patch distance = cosine distance to the nearest patch in a memory bank of
  normal patches (AnomalyDINO, Damm et al., WACV 2025).
- Image score = mean of the top `top_frac` (1%) patch distances (same paper).
- Banks per confluency bin (§7.1: morphology changes with density, so a
  single bank makes normal growth look anomalous), each a greedy k-center
  coreset (PatchCore, Roth et al., CVPR 2022) of the bin's normal patches,
  selected on a seeded random projection. Bin = the frame's full-frame
  Cellpose-SAM confluency. Bins with too few bank sequences merge into a
  neighbour (merge_bins()).
- Per-bin mean/SD of normal scores give the residual z = (score − mean)/SD
  that SPC trends; per-bin threshold = the (1 − fpr) quantile of normal scores.

No model runs here; everything reads cache/embeddings/<sha>_<crop_spec>.npy.
scripts/eval_anomaly.py builds the banks, scores the C2C12 fleet and writes
configs/anomaly.yaml.
"""

from __future__ import annotations

import hashlib
import math
import os

import numpy as np

EPS = 1e-8


def load_patches(cache_dir: str, image_sha256: str, crop_spec: str = "qctile") -> np.ndarray:
    """(n_patches, dim) float32, rows L2-normalised (cosine distance = 1 − dot)."""
    x = np.load(os.path.join(cache_dir, "embeddings", f"{image_sha256}_{crop_spec}.npy")).astype(np.float32)
    return x / (np.linalg.norm(x, axis=1, keepdims=True) + EPS)


def greedy_coreset(x: np.ndarray, n: int, seed: int = 0, proj_dim: int = 128) -> np.ndarray:
    """Indices of a greedy k-center coreset of `x` (PatchCore): start from a
    seeded random row, repeatedly add the row farthest from everything chosen.
    Distances on a seeded Gaussian projection to `proj_dim` dims (PatchCore's
    speed-up). Deterministic given `seed`."""
    import torch

    n_rows = len(x)
    if n >= n_rows:
        return np.arange(n_rows)
    rng = np.random.default_rng(seed)
    proj = rng.standard_normal((x.shape[1], proj_dim)).astype(np.float32) / math.sqrt(proj_dim)
    with torch.no_grad():
        z = torch.from_numpy(x @ proj)
        chosen = np.empty(n, dtype=np.int64)
        chosen[0] = int(rng.integers(n_rows))
        min_d = torch.sum((z - z[chosen[0]]) ** 2, dim=1)
        for i in range(1, n):
            j = int(torch.argmax(min_d))
            chosen[i] = j
            min_d = torch.minimum(min_d, torch.sum((z - z[j]) ** 2, dim=1))
    return chosen


def nn_distance(q: np.ndarray, bank: np.ndarray, chunk: int = 8192) -> np.ndarray:
    """Cosine distance from each row of `q` to its nearest row of `bank` (both L2-normalised)."""
    import torch

    out = np.empty(len(q), dtype=np.float32)
    b = torch.from_numpy(np.ascontiguousarray(bank)).T
    with torch.no_grad():
        for s in range(0, len(q), chunk):
            sim = torch.from_numpy(np.ascontiguousarray(q[s:s + chunk])) @ b
            out[s:s + chunk] = (1.0 - sim.max(dim=1).values).numpy()
    return np.clip(out, 0.0, 2.0)


def image_score(patch_d: np.ndarray, top_frac: float = 0.01) -> float:
    """Mean of the top ceil(top_frac * n) patch distances."""
    k = max(1, int(math.ceil(top_frac * len(patch_d))))
    return float(np.sort(patch_d)[-k:].mean())


def merge_bins(edges: list[float], seqs_per_bin: list[int], min_sequences: int) -> list[float]:
    """Drop inner edges until every bin has >= min_sequences bank sequences.
    A short bin merges into its lower neighbour (the top bin into the one
    below it; the bottom bin into the one above). `seqs_per_bin` counts, per
    original bin, the distinct sequences with a normal frame in it; merged
    counts are approximated by the sum (a sequence can span both), so a
    merged bin may hold fewer distinct sequences — callers recheck."""
    edges, counts = list(edges), list(seqs_per_bin)
    while len(counts) > 1 and min(counts) < min_sequences:
        i = int(np.argmin(counts))
        j = i - 1 if i > 0 else 1  # neighbour to merge with
        lo, hi = min(i, j), max(i, j)
        counts[lo:hi + 1] = [counts[lo] + counts[hi]]
        del edges[hi]
    return edges


def bin_index(pct: float, edges: list[float]) -> int:
    """Index of the bin [edges[i], edges[i+1]) holding pct; the last bin is closed at 100."""
    i = int(np.searchsorted(edges, pct, side="right")) - 1
    return min(max(i, 0), len(edges) - 2)


def bin_label(i: int, edges: list[float]) -> str:
    return f"{edges[i]:g}-{edges[i + 1]:g}"


def bank_hash(arrays: list[np.ndarray]) -> str:
    h = hashlib.sha256()
    for a in arrays:
        h.update(np.ascontiguousarray(a).tobytes())
    return h.hexdigest()
