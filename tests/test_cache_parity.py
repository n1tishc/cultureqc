"""
Slice 1b pre-Colab checks (cultureQC_upgrade.md §4A.3). All three run on a
small local sample, on CPU, before any Colab time is spent — because rule 10
forbids a second GPU pass, so these have to be proven correct in advance:

1. Parity: live culture.pipeline path == cache path, same image, same numbers.
2. Downsample fidelity: confluency from the stored 1/4-res int16 prob map
   matches full-res confluency closely enough that no threshold decision
   would flip.
3. Resume/idempotency: a build() that stops partway and restarts doesn't
   recompute finished work and doesn't corrupt the shard.

Real models, no stubs — deliberately slow (~1-2 min/image on CPU), not part
of the fast CI job. Run explicitly:
    .venv/bin/python -m pytest tests/test_cache_parity.py -v -s
"""

from __future__ import annotations

import glob
import os
import shutil

import numpy as np
import pytest

from culture.cache import Cache, ImageRecord, image_sha256

N_IMAGES = 2  # kept small deliberately; see module docstring

EVICAN_DIR = "data/sources/evican/eval2019_images"


def _sample_images():
    paths = sorted(glob.glob(os.path.join(EVICAN_DIR, "*.jpg")))[:N_IMAGES]
    if len(paths) < N_IMAGES:
        pytest.skip(f"need {N_IMAGES} EVICAN images in {EVICAN_DIR}, found {len(paths)}")
    return paths


@pytest.fixture(scope="module")
def cache_dir(tmp_path_factory):
    return str(tmp_path_factory.mktemp("cache_parity"))


@pytest.fixture(scope="module")
def built_cache(cache_dir):
    paths = _sample_images()
    records = [ImageRecord(path=p, dataset="evican_parity_test", source_path=p) for p in paths]
    cache = Cache(cache_dir)
    summary = cache.build(records, models=("seg", "qc", "quality"), crop_fracs=(), crops_per_frac=0)
    return cache, paths, summary


def test_parity_confluency(built_cache):
    """Cache's full-frame confluency must equal the live pipeline's, same image."""
    import cv2
    from culture.seg import cpsam_confluency

    cache, paths, _ = built_cache
    conf = cache.load_confluency(crop_spec="full")

    for path in paths:
        sha = image_sha256(path)
        img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        live = cpsam_confluency(img, method="probmap")

        row = conf[(conf.image_sha256 == sha) & (conf.model_name == "seg")]
        assert len(row) == 1, f"missing cache row for {path}"
        cached_pct = float(row.iloc[0]["pct"])

        assert cached_pct == pytest.approx(live.pct, abs=1e-6), (
            f"{path}: cache={cached_pct} live={live.pct} — "
            "cache and live pipeline diverged on the same image"
        )


def test_parity_qc_logits(built_cache):
    """Cache's QC logits (on the same center-crop-or-resize tile the live
    pipeline feeds the classifier) must match the live path's logits."""
    import cv2
    import torch
    from culture.qc import _get_model, _preprocess
    from culture.cache import qc_tile_from

    cache, paths, _ = built_cache
    logits_df = cache.load_logits()
    model = _get_model()

    for path in paths:
        sha = image_sha256(path)
        img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        tile = qc_tile_from(img)
        img_tensor = _preprocess(tile).to(next(model.parameters()).device)
        with torch.no_grad():
            live_logits = model(img_tensor.unsqueeze(0))[0].cpu().numpy()

        row = logits_df[(logits_df.image_sha256 == sha) & (logits_df.model_name == "qc")]
        assert len(row) == 1, f"missing cache logits for {path}"
        cached_logits = np.array(row.iloc[0]["logits"], dtype=np.float32)

        assert np.allclose(cached_logits, live_logits, atol=1e-4), (
            f"{path}: cache and live QC logits diverged beyond float tolerance"
        )


def test_downsample_fidelity(built_cache):
    """Confluency recomputed from the stored 1/4-res int16 prob map, at the
    default threshold, must be close enough to the true full-res confluency
    that no realistic threshold-tuning decision would flip based on the
    stored (lossy) version instead of the original."""
    cache, paths, _ = built_cache
    conf = cache.load_confluency(crop_spec="full")

    max_delta = 0.0
    for path in paths:
        sha = image_sha256(path)
        row = conf[(conf.image_sha256 == sha) & (conf.model_name == "seg")]
        full_res_pct = float(row.iloc[0]["pct"])

        prob = cache.load_probmap(sha)  # 1/4-res, unscaled from int16
        pct_from_stored = float((prob > 0.0).mean() * 100)

        delta = abs(pct_from_stored - full_res_pct)
        max_delta = max(max_delta, delta)

    # Downsampling by 4x changes pixel-count denominators and can shift a
    # count-based percentage by a small amount even with no information
    # loss in the threshold decision itself. 2pp is the bar: comfortably
    # inside cultureQC's own real-data MAE (8.35pp, see results/), so a
    # threshold refit against the stored map would not be misled by this.
    assert max_delta < 2.0, (
        f"stored 1/4-res prob map diverges from full-res by {max_delta:.2f}pp "
        "— raise PROBMAP_DOWNSAMPLE resolution before trusting the cache for "
        "threshold refitting"
    )


def test_resume_skips_completed_work(cache_dir):
    """A second build() call over the same images must add zero new rows —
    proving idempotency/resume before this ever runs somewhere that can
    disconnect mid-shard (Colab)."""
    import pandas as pd

    paths = _sample_images()
    records = [ImageRecord(path=p, dataset="evican_parity_test", source_path=p) for p in paths]

    resume_dir = cache_dir + "_resume"
    cache = Cache(resume_dir)
    first = cache.build(records, models=("quality",), crop_fracs=(), crops_per_frac=0)
    assert first["n_images"] == len(paths)

    before = pd.read_parquet(os.path.join(resume_dir, "quality.parquet"))

    second = cache.build(records, models=("quality",), crop_fracs=(), crops_per_frac=0)
    after = pd.read_parquet(os.path.join(resume_dir, "quality.parquet"))

    assert len(after) == len(before), "resume run added duplicate rows instead of skipping completed keys"
    assert second["timings_s"]["quality"] == pytest.approx(0.0, abs=0.05), (
        "resume run recomputed quality metrics instead of skipping — "
        f"spent {second['timings_s']['quality']:.3f}s on work that should have been skipped"
    )

    shutil.rmtree(resume_dir, ignore_errors=True)
