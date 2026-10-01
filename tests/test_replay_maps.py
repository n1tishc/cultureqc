"""The Flask Timeline's 3D space x time view (demo/replay_3d.py,
scripts/export_replay_maps.py): the layer maps are the compute cache's own
maps for the frames each replay visit imaged, each one hashes to its index
entry, and the FOV boxes are the crops the visit's number came from."""

import os

import numpy as np
import pytest
from conftest import require_module

require_module("gradio")
from culture.cache import probmap_sha256  # noqa: E402
from demo import replay_3d, replay_timeline  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPLAYS = replay_timeline.load_replays()
INDEX = replay_3d.load_index()


def test_every_replay_has_maps():
    assert INDEX is not None and set(INDEX["replays"]) == set(REPLAYS)


@pytest.mark.parametrize("name", sorted(REPLAYS))
def test_layers_follow_the_replay(name):
    layers, visits = INDEX["replays"][name]["layers"], REPLAYS[name]["visits"]
    maps = replay_3d.load_maps(name)
    assert len(layers) == len(visits) == len(maps)
    fh, fw = INDEX["frame_hw"]
    for L, v, m in zip(layers, visits, maps):
        assert (L["visit"], L["hours"], L["image_sha256"]) == (v["visit"], v["hours"], v["image_sha256"])
        assert L["fov_pct_recorded"] == v["fov_confluency"] and L["fov_mean_recorded"] == v["confluency_mean"]
        assert L["quality_pass"] == v["quality_pass"]
        assert probmap_sha256(m) == L["map_sha256"]
        # the 1/4-resolution map reproduces the cache's full-frame number (observed max 0.12 pp)
        assert (m > 0).mean() * 100 == pytest.approx(L["frame_pct_recorded"], abs=0.5)
        assert len(L["fov_boxes"]) == len(v["fov_confluency"])
        for y0, x0, h, w in L["fov_boxes"]:
            assert (h, w) == (int(fh * 0.25), int(fw * 0.25))
            assert 0 <= y0 <= fh - h and 0 <= x0 <= fw - w
    assert replay_3d.verified_layers(name) == (len(layers), len(layers))


@pytest.mark.skipif(not os.path.isdir(os.path.join(REPO, "cache", "probmaps")), reason="needs the compute cache")
@pytest.mark.parametrize("name", sorted(REPLAYS))
def test_maps_are_the_cache_maps(name):
    for L, m in zip(INDEX["replays"][name]["layers"], replay_3d.load_maps(name)):
        with np.load(os.path.join(REPO, "cache", "probmaps", f"{L['image_sha256']}.npz")) as npz:
            assert np.array_equal(npz["prob_x1000"], m)


def test_timeline_3d_renders():
    from demo import app

    for name in REPLAYS:
        curve, _, _, plot3d, note = app.on_timeline(name, "3D: space × time", REPLAYS)
        assert curve["visible"] is False and plot3d["visible"] is True
        assert "match their SHA-256" in note["value"]
    curve, _, _, plot3d, _ = app.on_timeline(name, "Curve", REPLAYS)
    assert curve["visible"] is True and plot3d["visible"] is False
