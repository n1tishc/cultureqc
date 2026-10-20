"""Offline spatial coverage tests, not biological detection evidence."""

import numpy as np
import pytest

from culture.cache import qc_tile_from


def test_native_tiles_reach_signal_discarded_by_live_center_crop():
    from culture.anomaly_coverage import native_tiles

    frame = np.zeros((512, 512), dtype=np.uint8)
    frame[10:14, 10:14] = 255
    assert qc_tile_from(frame).max() == 0
    tiles = native_tiles(frame)
    assert max(tile["pixels"].max() for tile in tiles) == 255


@pytest.mark.parametrize("shape", [(224, 224), (225, 447), (512, 512), (1040, 1392)])
def test_tiles_cover_every_pixel_at_native_scale(shape):
    from culture.anomaly_coverage import native_tiles

    frame = np.arange(np.prod(shape), dtype=np.uint32).reshape(shape).astype(np.uint8)
    covered = np.zeros(shape, dtype=bool)
    boxes = []
    for tile in native_tiles(frame):
        left, top, right, bottom = tile["box"]
        boxes.append(tuple(tile["box"]))
        assert tile["pixels"].shape == (224, 224)
        assert np.array_equal(tile["pixels"], frame[top:bottom, left:right])
        covered[top:bottom, left:right] = True
    assert covered.all()
    assert len(boxes) == len(set(boxes))


@pytest.mark.parametrize("frame", [
    np.zeros((100, 512), np.uint8), np.zeros((256, 256), np.uint16),
    np.zeros((256, 256), float), np.zeros((256, 256, 4), np.uint8),
])
def test_unsupported_inputs_do_not_silently_resize_or_rescale(frame):
    from culture.anomaly_coverage import native_tiles

    with pytest.raises(ValueError):
        native_tiles(frame)


def test_tile_budget_is_checked_before_scoring():
    from culture.anomaly_coverage import score_coverage

    calls = []
    with pytest.raises(ValueError, match="tile budget"):
        score_coverage(np.zeros((512, 512), np.uint8),
                       lambda tile: calls.append(tile), max_tiles=2)
    assert calls == []


def test_scores_keep_local_evidence_without_reusing_center_threshold():
    from culture.anomaly_coverage import score_coverage

    frame = np.zeros((512, 512), np.uint8)
    frame[10, 10] = 255
    result = score_coverage(frame, lambda tile: float(tile.max() / 255))
    assert result["score_max"] == 1.0
    assert result["score_median"] == 0.0
    assert result["coverage_fraction"] == 1.0
    assert result["flag"] is None and result["threshold"] is None
    assert result["used_in_decision"] is False
    assert result["status"] == "experimental_uncalibrated"
    assert any(tile["score"] == 1.0 and tile["box"][0] == 0 for tile in result["tiles"])


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -0.1, True, 10**400])
def test_invalid_scorer_results_cannot_look_successful(value):
    from culture.anomaly_coverage import score_coverage

    with pytest.raises(ValueError):
        score_coverage(np.zeros((224, 224), np.uint8), lambda tile: value)


@pytest.mark.parametrize("bank_scale", [1.0, 1e30])
def test_patch_preprocessing_preserves_native_pixels(bank_scale):
    torch = pytest.importorskip("torch")
    from types import SimpleNamespace
    from culture.anomaly_coverage import patch_scorer

    seen = []

    class Inputs(dict):
        def to(self, device):
            return self

    def processor(*, images, return_tensors, do_resize, do_center_crop):
        assert return_tensors == "pt" and do_resize is False and do_center_crop is False
        seen.append(images.copy())
        return Inputs(pixel_values=torch.from_numpy(images.transpose(2, 0, 1)[None].copy()))

    class Model:
        def parameters(self):
            yield torch.zeros(1)

        def __call__(self, **inputs):
            assert tuple(inputs["pixel_values"].shape) == (1, 3, 224, 224)
            return SimpleNamespace(last_hidden_state=torch.ones(1, 257, 4))

    frame = np.zeros((224, 224), np.uint8)
    frame[0, 0] = 255
    scorer = patch_scorer(Model(), processor, np.full((2, 4), bank_scale, np.float32))
    assert scorer(frame) == pytest.approx(0.0, abs=1e-5)
    assert seen[0][0, 0].tolist() == [255, 255, 255]


def test_processor_geometry_change_is_rejected():
    torch = pytest.importorskip("torch")
    from culture.anomaly_coverage import patch_scorer

    scorer = patch_scorer(None, lambda **kwargs: {"pixel_values": torch.zeros(1, 3, 256, 256)},
                          np.ones((2, 4)))
    with pytest.raises(ValueError, match="geometry"):
        scorer(np.zeros((224, 224), np.uint8))


@pytest.mark.parametrize("bank", [np.empty((0, 4)), np.zeros((1, 4)), np.full((1, 4), np.nan)])
def test_invalid_reference_banks_are_rejected(bank):
    from culture.anomaly_coverage import patch_scorer

    with pytest.raises(ValueError, match="reference bank"):
        patch_scorer(None, None, bank)
