import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

from classifier_scale_test import choose, criteria_met, select_frames, summarize  # noqa: E402
from culture.qc import (CLASS_NAMES, MODEL_VERSION, load_qc_config, rescale_factor,  # noqa: E402
                        rescale_frame, rescaled_model_version)


def test_config_is_off_and_factor_from_pixel_sizes():
    cfg = load_qc_config()
    assert rescale_factor(cfg) is None                      # live path unchanged until B0 passes
    f = rescale_factor(cfg, multiplier=1.0, force=True)
    assert f == pytest.approx(1.3 / 1.243)
    assert rescale_factor(cfg, multiplier=1.25, force=True) == pytest.approx(f * 1.25)


def test_rescale_frame():
    img = np.random.default_rng(0).integers(0, 255, (1040, 1392), dtype=np.uint8)
    assert rescale_frame(img, None) is img
    assert rescale_frame(img, 1.0) is img
    assert rescale_frame(img, 1.25).shape == (1300, 1740)
    assert rescale_frame(img, 0.5).shape == (520, 696)
    assert rescaled_model_version(1.046) == "qc_effnetb0_v1+rescale1.046" != MODEL_VERSION


def _fixture():
    split = pd.DataFrame([
        ("A", "base", "A", "none", "tuning"), ("B", "base", "B", "none", "heldout"),
        ("B__fault_dim", "fault", "B", "lamp_dimming", "heldout"),
        ("A__fault_contam", "fault", "A", "contamination_onset", "tuning"),
    ], columns=["sequence_id", "kind", "base_sequence_id", "fault_type", "split"])
    frames = pd.DataFrame({"sequence_id": ["A", "A", "B", "B"], "frame_idx": [1, 2, 1, 2],
                           "png_path": ["a1", "a2", "b1", "b2"]})
    fault_frames = pd.DataFrame({"png_path": ["bd2", "bd3", "ac2"],
                                 "sequence_id": ["B__fault_dim", "B__fault_dim", "A__fault_contam"],
                                 "frame_idx": [2, 3, 2]})
    manifest = pd.DataFrame({
        "fault_sequence_id": ["B__fault_dim"] * 3 + ["A__fault_contam"] * 2,
        "fault_type": ["lamp_dimming"] * 3 + ["contamination_onset"] * 2,
        "frame_idx": [1, 2, 3, 1, 2],
        # onset frame 2 is byte-identical to base frame b2 (pre-3d0c140 manifests mark it modified)
        "image_sha256": ["s_b1", "s_b2", "s_bd3", "s_a1", "s_ac2"],
        "is_modified": [False, True, True, False, True],
    })
    shas = {"a1": "s_a1", "a2": "s_a2", "b1": "s_b1", "b2": "s_b2", "bd2": "s_b2", "bd3": "s_bd3", "ac2": "s_ac2"}
    return frames, fault_frames, manifest, split, shas


def test_select_frames_drops_unmodified_onset_and_splits():
    frames, ff, man, split, shas = _fixture()
    out = select_frames(frames, ff, man, split, sha_of=shas.__getitem__)
    got = {(r.image_sha256, r.group, r.split) for r in out.itertuples()}
    assert got == {("s_a1", "normal", "tuning"), ("s_a2", "normal", "tuning"),
                   ("s_b1", "normal", "heldout"), ("s_b2", "normal", "heldout"),
                   ("s_bd3", "lamp_dimming", "heldout"), ("s_ac2", "contamination_onset", "tuning")}


def test_select_frames_rejects_file_manifest_mismatch():
    frames, ff, man, split, shas = _fixture()
    shas["bd3"] = "something_else"
    with pytest.raises(ValueError, match="differ from the manifest"):
        select_frames(frames, ff, man, split, sha_of=shas.__getitem__)


def test_summarize_and_choose():
    n, c, iq = (CLASS_NAMES.index(k) for k in ("normal", "contamination_suspected", "image_quality"))
    groups = np.array(["normal"] * 10 + ["contamination_onset"] * 4 + ["lamp_dimming"] * 2)
    calls = np.array([n] * 9 + [c] + [c] * 4 + [c, iq])
    s = summarize(calls, groups)
    assert s == {"normal_called_normal": 90.0, "contamination_recall": 100.0,
                 "normal_called_contamination": 10.0, "dimmed_called_contamination": 50.0}
    assert criteria_met(s) == {"normal_called_normal": True, "contamination_recall": True,
                               "normal_called_contamination": False}
    base = {"normal_called_normal": 10.0, "contamination_recall": 90.0, "normal_called_contamination": 20.0}
    # most criteria met wins over a higher normal rate
    assert choose({0.75: dict(base, normal_called_normal=70.0), 1.0: base,
                   1.25: dict(base, normal_called_contamination=4.0)}) == 1.25
    # tie on criteria -> higher normal-called-normal
    assert choose({0.75: base, 1.0: dict(base, normal_called_normal=12.0), 1.25: base}) == 1.0
    # full tie -> closest to 1
    assert choose({0.75: base, 1.0: base, 1.25: base}) == 1.0
