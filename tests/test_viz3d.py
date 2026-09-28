"""The 3D views' motion contract (demo/viz3d.py): what the figures must carry
for the page script to turn the camera and build the timeline up, and that the
figures stay complete without it. The motion itself is checked in a browser
(the console's 3D check), not here."""

import os

from demo import confluency_3d, precomputed, replay_3d, replay_timeline, viz3d

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXAMPLES = precomputed.load()


def test_every_example_has_an_opening_camera():
    assert set(confluency_3d.CAMERA_PRESETS) == {e["id"] for e in EXAMPLES}


def test_landscape_carries_a_fresh_nonce_and_the_preset():
    ex = next(e for e in EXAMPLES if e.get("probmap"))
    m = precomputed.probmap(ex)
    a = confluency_3d.landscape_figure(m, example_id=ex["id"])
    b = confluency_3d.landscape_figure(m, example_id=ex["id"])
    assert a.layout.meta["cqc3d"] == "landscape" and a.layout.meta["nonce"] != b.layout.meta["nonce"]
    eye = a.layout.scene.camera.eye
    assert (eye.x, eye.y, eye.z) == tuple(confluency_3d.CAMERA_PRESETS[ex["id"]].values())
    eye = confluency_3d.landscape_figure(m).layout.scene.camera.eye
    assert (eye.x, eye.y, eye.z) == tuple(confluency_3d.DEFAULT_EYE.values())


def test_timeline_is_complete_as_drawn_and_tagged_per_visit():
    replays = replay_timeline.load_replays()
    name = next(n for n in replays if replay_3d.available(n))
    fig = replay_3d.figure(name, replays[name])
    layers = replay_3d.load_index()["replays"][name]["layers"]
    assert fig.layout.meta["cqc3d"] == "timeline" and fig.layout.meta["build_step_ms"] > 0
    assert all(t.visible in (None, True) for t in fig.data)          # nothing hidden without the script
    hours = [t.meta["hours"] for t in fig.data if t.meta and "hours" in t.meta]
    assert len(hours) >= 4 * len(layers)                              # cells, outline, FOVs, hover per visit
    assert {L["hours"] for L in layers} <= set(hours)
    shown = [t.legendgroup for t in fig.data if t.showlegend]
    assert len(shown) == len(set(shown))                              # one legend entry per group
    scene = fig.layout.scene                                          # fixed ranges: no jump while building
    assert scene.xaxis.range and scene.yaxis.range and scene.zaxis.range


def test_page_script_is_wired_into_both_launches():
    assert viz3d.HEAD.startswith("<script>(") and "window.__cqc3d = true" in viz3d.HEAD
    assert "prefers-reduced-motion" in viz3d.JS
    with open(os.path.join(REPO, "deploy", "hf-space-demo", "console.py")) as f:
        assert "head=HEAD" in f.read()
    with open(os.path.join(REPO, "demo", "app.py")) as f:
        assert "head=viz3d.HEAD" in f.read()
