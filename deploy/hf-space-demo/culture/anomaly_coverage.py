"""Experimental full-frame native-scale anomaly signals; never decision flags."""

import math

import numpy as np

TILE_SIZE = 224
METHOD = "native224-grid-max-v1"


def _origins(length):
    positions = list(range(0, length - TILE_SIZE + 1, TILE_SIZE))
    if positions[-1] != length - TILE_SIZE:
        positions.append(length - TILE_SIZE)
    return positions


def native_tiles(frame, *, max_tiles=64):
    """Cover an 8-bit frame without resizing; edge windows overlap if necessary."""
    if (not isinstance(frame, np.ndarray) or frame.dtype != np.uint8
            or frame.ndim not in (2, 3)
            or (frame.ndim == 3 and frame.shape[2] != 3)):
        raise ValueError("expected an explicitly normalized uint8 grayscale or RGB frame")
    if min(frame.shape[:2]) < TILE_SIZE:
        raise ValueError("frame must be at least 224 pixels on both axes; resizing is not allowed")
    if type(max_tiles) is not int or max_tiles < 1:
        raise ValueError("tile budget must be a positive integer")
    height, width = frame.shape[:2]
    rows, columns = _origins(height), _origins(width)
    if len(rows) * len(columns) > max_tiles:
        raise ValueError(f"tile budget exceeded: need {len(rows) * len(columns)}, allowed {max_tiles}")
    return [
        {"box": [left, top, left + TILE_SIZE, top + TILE_SIZE],
         "pixels": frame[top:top + TILE_SIZE, left:left + TILE_SIZE]}
        for top in rows for left in columns
    ]


def coverage_plan(frame, *, max_tiles=64):
    tiles = native_tiles(frame, max_tiles=max_tiles)
    return {
        "method": METHOD, "image_shape": list(frame.shape), "tile_size_px": TILE_SIZE,
        "tile_count": len(tiles), "coverage_fraction": 1.0,
        "resized": False, "boxes": [tile["box"] for tile in tiles],
    }


def score_coverage(frame, scorer, *, max_tiles=64):
    """Keep per-tile signals and their maximum; this aggregation needs new calibration."""
    tiles = native_tiles(frame, max_tiles=max_tiles)
    evidence = []
    for tile in tiles:
        value = scorer(tile["pixels"])
        if (isinstance(value, (bool, np.bool_)) or not np.isscalar(value)
                or not isinstance(value, (int, float, np.integer, np.floating))):
            raise ValueError("tile scorer must return a finite nonnegative numeric score")
        try:
            value = float(value)
        except OverflowError as error:
            raise ValueError("tile score exceeds finite numeric range") from error
        if not math.isfinite(value) or value < 0:
            raise ValueError("tile scorer must return a finite nonnegative numeric score")
        evidence.append({"box": tile["box"], "score": float(value)})
    scores = [tile["score"] for tile in evidence]
    return {
        **coverage_plan(frame, max_tiles=max_tiles),
        "status": "experimental_uncalibrated", "score_max": max(scores),
        "score_median": float(np.median(scores)), "tiles": evidence,
        "flag": None, "threshold": None, "used_in_decision": False,
        "limitations": [
            "Spatial coverage does not establish bacterial sensitivity or optical resolution.",
            "Frame maxima depend on tile count; center-tile thresholds are not transferable.",
            "Reference banks need target-setup and spatially representative validation.",
        ],
    }


def patch_scorer(model, processor, bank, *, top_frac=0.01):
    """Use caller-supplied DINO weights/bank without loading models or downloading files."""
    from culture.anomaly import EPS, image_score, nn_distance

    reference = np.asarray(bank, dtype=np.float32)
    if reference.ndim != 2 or not all(reference.shape) or not np.isfinite(reference).all():
        raise ValueError("reference bank must contain finite nonzero patch vectors")
    norms = np.linalg.norm(reference.astype(np.float64), axis=1, keepdims=True)
    if not np.isfinite(norms).all() or (norms == 0).any():
        raise ValueError("reference bank must contain finite nonzero patch vectors")
    if type(top_frac) not in (float, int) or not 0 < top_frac <= 1:
        raise ValueError("top_frac must be in (0, 1]")
    reference = (reference / norms).astype(np.float32)

    def score(tile):
        import torch

        if tile.shape[:2] != (TILE_SIZE, TILE_SIZE):
            raise ValueError("native patch scorer requires 224 by 224 pixels")
        rgb = np.repeat(tile[..., None], 3, axis=2) if tile.ndim == 2 else tile
        inputs = processor(images=rgb, return_tensors="pt", do_resize=False, do_center_crop=False)
        if tuple(inputs["pixel_values"].shape) != (1, 3, TILE_SIZE, TILE_SIZE):
            raise ValueError("processor changed the native tile geometry")
        inputs = inputs.to(next(model.parameters()).device)
        with torch.no_grad():
            patches = model(**inputs).last_hidden_state[0, 1:].cpu().numpy()
        if patches.shape != (256, reference.shape[1]) or not np.isfinite(patches).all():
            raise ValueError("unexpected or nonfinite DINO patch embeddings")
        patches = patches.astype(np.float16).astype(np.float32)
        if not np.isfinite(patches).all():
            raise ValueError("DINO embeddings exceed the retained float16 range")
        patches = patches / (np.linalg.norm(patches, axis=1, keepdims=True) + EPS)
        return image_score(nn_distance(patches, reference), top_frac)

    return score
