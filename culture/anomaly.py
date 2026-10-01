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


# ---------------------------------------------------------------------------
# Live per-image scoring (cultureQC_upgrade_specv4.md §2B.4, B2)
# ---------------------------------------------------------------------------
# Same scorer as scripts/eval_anomaly.py, on one image: DINOv2-small patches of
# the 256 px centre tile (culture.cache.qc_tile_from + dino_embed, stored as
# float16 exactly as the cache does), bin from the frame's full-frame
# Cellpose-SAM confluency, nearest-patch cosine distance against that bin's
# bank, image score = mean of the top 1% patch distances, flag = score above
# the bin's threshold (5% FPR on tuning normals, configs/anomaly.yaml).
# The banks (cache/anomaly/banks.npz, 67 MB) are verified against the SHA-256
# in configs/anomaly.yaml before use; a missing or mismatched file gives
# status "unavailable", never a score against unverified banks.

import os as _os
from dataclasses import dataclass, field

_REPO = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
ANOMALY_CONFIG_PATH = _os.path.join(_REPO, "configs", "anomaly.yaml")
DEFAULT_BANKS_PATH = _os.path.join(_REPO, "cache", "anomaly", "banks.npz")
TILE_PX = 256            # culture.cache.qc_tile_from
CROP_PX = 224            # DINOv2 processor: shortest edge 256, centre crop 224
PATCH_PX = 14
GRID = CROP_PX // PATCH_PX
TOP_PATCHES = 3          # ceil(1% of 256): the patches that set the image score

# Known limits for the app caption. Numbers copied from
# results/anomaly_summary.md (tests/test_anomaly_live.py checks they are still
# there).
LIVE_LIMITS = [
    "Banks and thresholds come from normal C2C12 frames only (5× objective, 1.3 µm/px); on images from "
    "other instruments or cell types the flag is uncalibrated (site calibration: scripts/site_calibrate.py).",
    "Held-out normal C2C12 frames are flagged 10.0% of the time against a 5% target, and calibration does "
    "not transfer across experiments: one 090318 sequence was flagged on 69% of its frames.",
    "Simulated contamination is flagged at every severity (V5(b), n = 2 sequences, with bacteria pasted at "
    "16.5× their real size). The pasted bacteria shift measured confluency by a median +59.4 pp, so 88% of "
    "those frames land in a different bin.",
    "At their real size, up to 400 per 256 px tile area, the same simulated bacteria are not caught: flagged "
    "on 1 of 97 frames, against 4 of 97 for the same frames without them, and confluency reads a median "
    "4.3 pp lower (results/contamination_scale.md). Heavier contamination is not tested. Confirm "
    "contamination by culture, Gram stain or PCR.",
    "Simulated lamp dimming is not caught by this flag (AUROC 0.47 at intensity ≤ 0.7).",
    "A flag holds a passage for human review (a flagged flask is not passaged automatically); it does not change continue or feed. On cell types other than C2C12 the flag is uncalibrated, so it can hold a passage on a healthy flask.",
]


@dataclass
class AnomalyResult:
    status: str                              # "ok" | "unavailable"
    reason: str | None = None
    score: float | None = None
    z: float | None = None
    bin_label: str | None = None
    threshold: float | None = None
    flag: bool | None = None
    patch_distances: list | None = None      # GRID x GRID, row-major over the 224 px crop
    top_patches: list = field(default_factory=list)   # [(row, col)] of the TOP_PATCHES highest
    bank_sha256: str | None = None
    model_version: str = "facebook/dinov2-small"

    def record_fields(self) -> dict:
        return {"anomaly_status": self.status, "anomaly_score": self.score, "anomaly_z": self.z,
                "anomaly_bin": self.bin_label, "anomaly_threshold": self.threshold, "anomaly_flag": self.flag,
                "anomaly_bank_sha256": self.bank_sha256,
                # An input to the rules (v0.3, rule 3) whenever the check ran.
                "anomaly_used_in_decision": self.status == "ok" and self.flag is not None}


def load_anomaly_config(path: str | None = None) -> dict | None:
    """configs/anomaly.yaml, or a site calibration's (CULTUREQC_ANOMALY_CONFIG)."""
    import yaml

    path = path or _os.environ.get("CULTUREQC_ANOMALY_CONFIG", ANOMALY_CONFIG_PATH)
    if not _os.path.exists(path):
        return None
    with open(path) as f:
        return yaml.safe_load(f)


_banks_cache: dict = {}


def load_banks(cfg: dict, path: str | None = None) -> tuple[dict | None, str | None]:
    """(banks, None) if the file's hash matches cfg['bank']['sha256'], else
    (None, reason). Cached per path."""
    path = path or _os.environ.get("CULTUREQC_ANOMALY_BANKS", DEFAULT_BANKS_PATH)
    if path in _banks_cache:
        return _banks_cache[path]
    if not _os.path.exists(path):
        out = (None, f"anomaly banks not found ({_os.path.basename(path)})")
    else:
        z = np.load(path)
        banks = {k: z[k] for k in z.files}
        h = bank_hash([banks[k] for k in sorted(banks)])
        out = (banks, None) if h == cfg["bank"]["sha256"] else (None, "anomaly banks do not match configs/anomaly.yaml")
    _banks_cache[path] = out
    return out


def score_patches(patches: np.ndarray, confluency_pct: float, cfg: dict, banks: dict) -> AnomalyResult:
    """Score one tile's (GRID*GRID, dim) patch embeddings. Pure: no model."""
    if len(patches) != GRID * GRID:
        raise ValueError(f"expected {GRID * GRID} patches, got {len(patches)}")
    x = patches.astype(np.float16).astype(np.float32)          # the cache stores float16
    x = x / (np.linalg.norm(x, axis=1, keepdims=True) + EPS)
    edges = cfg["bins"]["edges"]
    label = bin_label(bin_index(confluency_pct, edges), edges)
    cal = cfg["calibration"]["bins"][label]
    d = nn_distance(x, banks[f"bin_{label}"])
    score = image_score(d, cfg["method"]["top_frac"])
    top = np.argsort(d)[-TOP_PATCHES:][::-1]
    return AnomalyResult(
        status="ok", score=round(score, 6), z=round((score - cal["mean"]) / cal["sd"], 4), bin_label=label,
        threshold=cal["threshold"], flag=bool(score > cal["threshold"]),
        patch_distances=d.reshape(GRID, GRID).round(5).tolist(),
        top_patches=[(int(i // GRID), int(i % GRID)) for i in top], bank_sha256=cfg["bank"]["sha256"],
        model_version=cfg["method"]["backbone"])


def score_frame(img: np.ndarray, confluency_pct: float, cfg: dict | None = None,
                banks_path: str | None = None) -> AnomalyResult:
    """Live path: embed the frame's 256 px centre tile and score it."""
    cfg = load_anomaly_config() if cfg is None else cfg
    if cfg is None:
        return AnomalyResult(status="unavailable", reason="configs/anomaly.yaml not found")
    banks, reason = load_banks(cfg, banks_path)
    if banks is None:
        return AnomalyResult(status="unavailable", reason=reason, model_version=cfg["method"]["backbone"])
    from culture.cache import dino_embed, qc_tile_from

    return score_patches(dino_embed(qc_tile_from(img))["patches"], confluency_pct, cfg, banks)


def tile_box(h: int, w: int) -> tuple[int, int, float, float]:
    """(x0, y0, sx, sy): frame pixel = (x0 + sx * tile_x, y0 + sy * tile_y) for
    the 256 px QC tile. A frame of at least 256 px is centre-cropped (offset
    only, scale 1); a smaller one was resized whole (qc_tile_from), so scale."""
    if h >= TILE_PX and w >= TILE_PX:
        return w // 2 - TILE_PX // 2, h // 2 - TILE_PX // 2, 1.0, 1.0
    return 0, 0, w / TILE_PX, h / TILE_PX
