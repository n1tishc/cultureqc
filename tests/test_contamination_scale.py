"""scripts/contamination_scale.py: at scale 1 with haze its injector is the
original fault builder's, byte for byte; shrinking keeps each bacterium's
coverage and brightness; the haze switch changes only the haze."""

import os
import sys

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))

import contamination_scale as cs  # noqa: E402
import make_fault_set as mfs  # noqa: E402


def _sprites(n=12, seed=0):
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n):
        h, w = int(rng.integers(8, 20)), int(rng.integers(30, 70))
        s = np.zeros((h, w, 4), np.uint8)
        s[2:-2, 3:-3, :3] = rng.integers(60, 120)
        s[2:-2, 3:-3, 3] = 255
        out.append(s)
    return out


def _frame(seed=1):
    rng = np.random.default_rng(seed)
    img = np.full((300, 400), 140, np.uint8)
    for _ in range(12):                                          # a few dark "cells"
        y, x = rng.integers(20, 280), rng.integers(20, 380)
        img[y - 15:y + 15, x - 15:x + 15] = 70
    return img


def test_scale_one_is_the_original_injector():
    synth = mfs._load_synth(REPO)
    sprites, img = _sprites(), _frame()
    ref = mfs.inject_bacteria_frame(img, sprites, 300.0, synth, np.random.default_rng(7))
    out, target, placed = cs.inject(img, cs.scale_sprites(sprites, 1.0), 300.0, synth,
                                    np.random.default_rng(7), haze=True)
    assert np.array_equal(ref, out) and 0 < placed <= target


def test_shrinking_keeps_coverage_and_brightness():
    s = _sprites(1)[0]
    (small,) = cs.scale_sprites([s], cs.REALISTIC)
    f = cs.REALISTIC
    area_in = (s[..., 3] / 255.0).sum() * f * f
    area_out = (small[..., 3] / 255.0).sum()
    assert abs(area_out - area_in) / area_in < 0.25
    assert max(small.shape[:2]) <= int(np.ceil(np.hypot(*s.shape[:2]) * f)) + 1
    covered = small[..., 3] > 0
    assert abs(float(small[..., 0][covered].mean()) - float(s[2:-2, 3:-3, 0].mean())) < 2


def test_haze_switch_changes_only_the_haze():
    synth = mfs._load_synth(REPO)
    sprites, img = cs.scale_sprites(_sprites(), cs.REALISTIC), _frame()
    a, _, pa = cs.inject(img, sprites, 400.0, synth, np.random.default_rng(3), haze=True)
    b, _, pb = cs.inject(img, sprites, 400.0, synth, np.random.default_rng(3), haze=False)
    assert pa == pb and not np.array_equal(a, b)
    rng_a, rng_b = np.random.default_rng(3), np.random.default_rng(3)
    cs.inject(img, sprites, 400.0, synth, rng_a, haze=True)
    cs.inject(img, sprites, 400.0, synth, rng_b, haze=False)
    assert rng_a.random() == rng_b.random()                     # same stream afterwards: same next frame
