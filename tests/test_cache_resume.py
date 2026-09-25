"""
Cache.build() periodic flushing (spec v3.1 §2A.0, A0.2).

A build() killed partway must keep every table row computed up to its last
periodic flush, and a rerun must finish the job without recomputing the
flushed rows or writing duplicates.

The kill is simulated with an exception raised from inside the per-image
loop. No finally-flush exists in build(), on purpose: a real Colab
disconnect gives no chance to run cleanup code, so the only thing that can
save rows is a flush that already happened. The assertions on the on-disk
state right after the kill are the ones that fail without periodic flushing;
the rerun assertions alone would pass either way (a rerun recomputes
whatever was lost).

Uses only the "quality" model (no weights, no GPU) on generated images.
"""

from __future__ import annotations

import json
import os

import cv2
import numpy as np
import pandas as pd
import pytest

import culture.cache as cache_mod
from culture.cache import Cache, ImageRecord

N_IMAGES = 12
FLUSH_EVERY = 4
KILL_AT_CALL = 7  # 1-based: calls 1-4 are flushed at record 4, calls 5-6 are in memory


class _Killed(RuntimeError):
    pass


def _make_images(root: str, n: int) -> list[ImageRecord]:
    rng = np.random.default_rng(0)
    records = []
    for i in range(n):
        path = os.path.join(root, f"img_{i:02d}.png")
        cv2.imwrite(path, rng.integers(0, 256, size=(64, 64), dtype=np.uint8))
        records.append(ImageRecord(path=path, dataset="resume_test", source_path=path))
    return records


def _counting_quality_metrics(kill_at: int | None):
    real = cache_mod.quality_metrics
    calls = {"n": 0}

    def wrapped(img):
        calls["n"] += 1
        if kill_at is not None and calls["n"] == kill_at:
            raise _Killed(f"simulated kill at quality call {kill_at}")
        return real(img)

    return wrapped, calls


def _read(cache_dir: str, name: str) -> pd.DataFrame:
    return pd.read_parquet(os.path.join(cache_dir, name))


def test_killed_build_keeps_flushed_rows_and_rerun_completes(tmp_path, monkeypatch):
    records = _make_images(str(tmp_path), N_IMAGES)
    cache_dir = str(tmp_path / "cache")
    cache = Cache(cache_dir)

    killing, _ = _counting_quality_metrics(kill_at=KILL_AT_CALL)
    monkeypatch.setattr(cache_mod, "quality_metrics", killing)
    with pytest.raises(_Killed):
        cache.build(records, models=("quality",), crop_fracs=(), crops_per_frac=0,
                    progress=False, flush_every=FLUSH_EVERY)

    # The discriminating check: the first FLUSH_EVERY records are already on
    # disk even though build() never reached its final flush.
    n_flushed = FLUSH_EVERY * ((KILL_AT_CALL - 1) // FLUSH_EVERY)
    quality_after_kill = _read(cache_dir, "quality.parquet")
    images_after_kill = _read(cache_dir, "images.parquet")
    assert len(quality_after_kill) == n_flushed
    assert len(images_after_kill) == n_flushed
    flushed_shas = set(quality_after_kill.image_sha256)
    assert flushed_shas == set(images_after_kill.image_sha256)

    # Rerun (no kill): computes only the images not yet flushed.
    counting, calls = _counting_quality_metrics(kill_at=None)
    monkeypatch.setattr(cache_mod, "quality_metrics", counting)
    cache.build(records, models=("quality",), crop_fracs=(), crops_per_frac=0,
                progress=False, flush_every=FLUSH_EVERY)
    assert calls["n"] == N_IMAGES - n_flushed, "rerun recomputed rows that were already flushed"

    quality = _read(cache_dir, "quality.parquet")
    images = _read(cache_dir, "images.parquet")
    assert len(quality) == N_IMAGES
    assert len(images) == N_IMAGES
    assert not quality.duplicated(["image_sha256", "model_name", "model_version"]).any()
    assert not images.image_sha256.duplicated().any()

    # Flushed rows survive the rerun unchanged.
    before = quality_after_kill.set_index("image_sha256").sort_index()
    after = quality.set_index("image_sha256").loc[sorted(flushed_shas)]
    pd.testing.assert_frame_equal(before, after)


def test_rerun_after_kill_matches_uninterrupted_build(tmp_path, monkeypatch):
    records = _make_images(str(tmp_path), N_IMAGES)

    clean_dir = str(tmp_path / "clean")
    Cache(clean_dir).build(records, models=("quality",), crop_fracs=(), crops_per_frac=0,
                           progress=False, flush_every=FLUSH_EVERY)

    killed_dir = str(tmp_path / "killed")
    killed = Cache(killed_dir)
    killing, _ = _counting_quality_metrics(kill_at=KILL_AT_CALL)
    monkeypatch.setattr(cache_mod, "quality_metrics", killing)
    with pytest.raises(_Killed):
        killed.build(records, models=("quality",), crop_fracs=(), crops_per_frac=0,
                     progress=False, flush_every=FLUSH_EVERY)
    monkeypatch.undo()
    killed.build(records, models=("quality",), crop_fracs=(), crops_per_frac=0,
                 progress=False, flush_every=FLUSH_EVERY)

    for name, key in [("quality.parquet", "image_sha256"), ("images.parquet", "image_sha256")]:
        a = _read(clean_dir, name).set_index(key).sort_index()
        b = _read(killed_dir, name).set_index(key).sort_index()
        pd.testing.assert_frame_equal(a, b)

    with open(os.path.join(killed_dir, "MANIFEST.json")) as f:
        manifest_rows = json.load(f)["row_counts"]
    assert manifest_rows["quality.parquet"] == N_IMAGES


def test_flush_every_must_be_positive(tmp_path):
    with pytest.raises(ValueError):
        Cache(str(tmp_path / "c")).build([], models=("quality",), flush_every=0, progress=False)
