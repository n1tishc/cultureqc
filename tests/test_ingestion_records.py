"""Both live paths bind the same decoding provenance before model inference."""

from copy import deepcopy
import hashlib
import io

import cv2
import jsonschema
import numpy as np
from PIL import Image
import pytest

from culture.ingestion import read_image, pixel_hash
from culture.records import RecordWriter
from test_decision_provenance import runtime


def test_library_and_console_record_identical_preprocessing(runtime):
    library, console = runtime.library(), runtime.console()
    assert library["schema_version"] == console["schema_version"] == "0.8"
    assert library["preprocessing"] == console["preprocessing"]
    assert library["image_hash"] == library["preprocessing"]["source_sha256"]
    assert library["preprocessing"]["output_sha256"] == pixel_hash(runtime.image)


@pytest.mark.parametrize("surface", ["library", "console"])
@pytest.mark.parametrize("maximum", [4095, 65535])
def test_high_bit_depth_refused_before_inference(runtime, surface, maximum):
    buffer = io.BytesIO()
    Image.fromarray(np.full((32, 32), maximum, np.uint16)).save(buffer, format="TIFF")
    runtime.path.write_bytes(buffer.getvalue())
    calls = []
    runtime.during_segment = lambda: calls.append(True)
    with pytest.raises(ValueError, match="uint8"):
        getattr(runtime, surface)()
    assert not calls
    assert not (runtime.path.parent / f"{surface}.jsonl").exists()


@pytest.mark.parametrize("surface", ["library", "console"])
def test_preprocessing_retains_original_source_when_path_changes(runtime, surface):
    original = read_image(runtime.path)
    runtime.during_segment = lambda: runtime.path.write_bytes(b"replaced during inference")
    record = getattr(runtime, surface)()
    assert record["image_hash"] == original.image_hash
    assert record["preprocessing"] == original.preprocessing


def test_read_and_decode_use_one_byte_snapshot(tmp_path, monkeypatch):
    path = tmp_path / "input.png"
    pixels = np.full((8, 8), 65, np.uint8)
    cv2.imwrite(str(path), pixels)
    original = path.read_bytes()
    real_decode = cv2.imdecode

    def replace_then_decode(*args):
        path.write_bytes(b"changed after read, before hash")
        return real_decode(*args)

    monkeypatch.setattr(cv2, "imdecode", replace_then_decode)
    result = read_image(path)
    assert result.image_hash == hashlib.sha256(original).hexdigest()
    np.testing.assert_array_equal(result.pixels, pixels)


def test_rgb_uint16_cannot_hide_behind_pillow_rgb_mode(tmp_path):
    path = tmp_path / "rgb16.tif"
    cv2.imwrite(str(path), np.full((8, 8, 3), 4095, np.uint16))
    with Image.open(path) as metadata:
        assert metadata.mode == "RGB"
    with pytest.raises(ValueError, match="bit-depth"):
        read_image(path)


def test_damaged_tiff_directory_is_an_actionable_rejection(tmp_path):
    path = tmp_path / "damaged.tif"
    cv2.imwrite(str(path), np.full((32, 32), 100, np.uint8))
    damaged = bytearray(path.read_bytes())
    damaged[-1] ^= 1
    path.write_bytes(damaged)
    with pytest.raises(ValueError, match="decode"):
        read_image(path)


@pytest.mark.parametrize("change", ["missing", "identity", "source_hash", "source_shape", "transform"])
def test_invalid_preprocessing_refused_before_file_creation(runtime, tmp_path, change):
    from culture.ingestion import _digest
    record = runtime.library()
    if change == "missing":
        record.pop("preprocessing")
    elif change == "identity":
        record["preprocessing"]["sha256"] = "0" * 64
    else:
        field, value = {"source_hash": ("source_sha256", "0" * 64),
                        "source_shape": ("source_shape", [1, 1]),
                        "transform": ("transform", "opencv-grayscale")}[change]
        record["preprocessing"][field] = value
        payload = {name: value for name, value in record["preprocessing"].items() if name != "sha256"}
        record["preprocessing"]["sha256"] = _digest(payload)
    path = tmp_path / "rejected.jsonl"
    with pytest.raises((ValueError, jsonschema.ValidationError)):
        RecordWriter(str(path)).append(record)
    assert not path.exists()


def test_schema_07_needs_no_invented_preprocessing(runtime, tmp_path):
    record = deepcopy(runtime.library())
    record["schema_version"] = "0.7"
    record.pop("preprocessing")
    stored = RecordWriter(str(tmp_path / "historical.jsonl")).append(record)
    assert "preprocessing" not in stored


def test_console_rejects_unsupported_upload_without_analysis_or_record(tmp_path, monkeypatch):
    pytest.importorskip("gradio")
    from demo import app
    path = tmp_path / "input.tif"
    Image.fromarray(np.full((16, 16), 4095, np.uint16)).save(path)
    calls = []
    monkeypatch.setattr(app, "analyze_image", lambda *args, **kwargs: calls.append(True))
    before = app.writer.record_count
    out = app.analyze_or_explain(str(path), "unknown", 80, "uncalibrated")
    assert "uint8" in out[2] and "no record was written" in out[2]
    assert not calls and app.writer.record_count == before
    upload = app.on_upload(str(path))
    assert "uint8" in upload[1]
    assert upload[2] is None and upload[4] is None


def test_gradio_transport_preserves_original_depth_and_bytes(tmp_path, monkeypatch):
    pytest.importorskip("gradio")
    import asyncio
    from demo import app
    from demo.uploads import image_upload_path

    path = tmp_path / "original.tif"
    Image.fromarray(np.full((16, 16), 4095, np.uint16)).save(path)
    original = path.read_bytes()
    upload_fn = next(function for function in app.demo.fns.values() if function.fn is app.on_upload)
    assert upload_fn.preprocess is False
    from gradio.components.image import ImageData
    assert app.image_view.preprocess(ImageData(path=str(path), orig_name=path.name)) == str(path)
    payload = {"path": str(path), "orig_name": path.name, "meta": {"_type": "gradio.FileData"}}
    moved = asyncio.run(app.demo.preprocess_data(upload_fn, [payload], None, explicit_call=True))[0]
    cached = image_upload_path(moved)
    from pathlib import Path
    assert Path(cached).read_bytes() == original
    assert "uint8" in app.on_upload(moved)[1]
    outside = {"path": str(path), "orig_name": path.name, "meta": {"_type": "gradio.FileData"}}
    from gradio.context import LocalContext
    token = LocalContext.blocks.set(app.demo)
    monkeypatch.setattr(app.demo, "has_launched", True)
    try:
        with pytest.raises(Exception, match="upload"):
            asyncio.run(app.demo.preprocess_data(upload_fn, [outside], None))
    finally:
        LocalContext.blocks.reset(token)


def test_inline_upload_data_cannot_trigger_gradio_conversion():
    from demo.uploads import image_upload_path
    with pytest.raises(ValueError, match="original image file"):
        image_upload_path({"path": "irrelevant", "url": "data:image/png;base64,irrelevant"})


def test_raw_demo_keeps_file_input_and_refuses_high_depth(tmp_path, monkeypatch):
    pytest.importorskip("gradio")
    import importlib.util
    from pathlib import Path
    import sys
    import types
    from culture import qc, seg

    monkeypatch.setitem(sys.modules, "spaces", types.SimpleNamespace(GPU=lambda **kwargs: lambda function: function))
    monkeypatch.setattr(qc, "_get_model", lambda: None)
    monkeypatch.setattr(seg, "_get_model", lambda: None)
    source = Path(__file__).resolve().parents[1] / "deploy/hf-space-demo/app.py"
    spec = importlib.util.spec_from_file_location("raw_ingestion_test", source)
    raw_demo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(raw_demo)
    function = next(function for function in raw_demo.demo.fns.values() if function.fn is raw_demo.infer)
    assert not function.preprocess and raw_demo.image_in.type == "filepath"
    calls = []
    monkeypatch.setattr(raw_demo, "_run_analysis", lambda *args: calls.append(args))
    path = tmp_path / "raw16.tif"
    Image.fromarray(np.full((16, 16), 4095, np.uint16)).save(path)
    with pytest.raises(ValueError, match="uint8"):
        raw_demo.infer({"path": str(path)}, "unknown", 80)
    assert not calls
