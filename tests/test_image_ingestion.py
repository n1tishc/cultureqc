import hashlib
import io
import json

import cv2
import numpy as np
import pytest
from PIL import Image

import culture.ingestion as ingestion
from culture.ingestion import decode_image, read_image


FORMATS = ["PNG", "JPEG", "TIFF", "BMP", "WEBP"]


def encode(image, image_format, **save_options):
    buffer = io.BytesIO()
    image.save(buffer, format=image_format, **save_options)
    return buffer.getvalue()


@pytest.mark.parametrize("image_format", FORMATS)
@pytest.mark.parametrize("mode", ["L", "RGB"])
def test_valid_single_frame_images_report_provenance_and_opencv_pixels(image_format, mode):
    values = np.arange(8 * 11, dtype=np.uint8).reshape(8, 11)
    if mode == "RGB":
        values = np.stack((values, np.flipud(values), np.fliplr(values)), axis=-1)
    image = Image.fromarray(values, mode=mode)
    raw = encode(image, image_format, quality=100) if image_format in {"JPEG", "WEBP"} else encode(image, image_format)

    result = decode_image(raw)
    expected = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_GRAYSCALE | cv2.IMREAD_IGNORE_ORIENTATION)
    np.testing.assert_array_equal(result.pixels, expected)
    assert result.pixels.dtype == np.uint8
    assert result.image_hash == hashlib.sha256(raw).hexdigest()
    assert result.preprocessing["policy"] == "uint8-single-frame-v1"
    with Image.open(io.BytesIO(raw)) as encoded:
        source_mode = encoded.mode
        source_shape = [encoded.height, encoded.width]
        if source_mode == "RGB":
            source_shape.append(3)
    assert result.preprocessing["source_mode"] == source_mode
    assert result.preprocessing["source_shape"] == source_shape
    assert result.preprocessing["source_dtype"] == "uint8"
    assert result.preprocessing["frame_count"] == 1
    assert result.preprocessing["orientation"] == 1
    assert result.preprocessing["transform"] == ("identity" if source_mode == "L" else "opencv-grayscale")
    assert result.preprocessing["decoder_version"] == cv2.__version__
    assert result.preprocessing["output_shape"] == list(expected.shape)
    assert result.preprocessing["output_dtype"] == "uint8"
    assert result.preprocessing["output_sha256"] == ingestion.pixel_hash(expected)
    assert result.preprocessing["source_format"]
    payload = {key: value for key, value in result.preprocessing.items() if key != "sha256"}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    assert result.preprocessing["sha256"] == hashlib.sha256(canonical.encode()).hexdigest()


def test_read_image_uses_original_file_bytes_without_mutating_them(tmp_path):
    raw = encode(Image.fromarray(np.arange(63, dtype=np.uint8).reshape(7, 9)), "PNG")
    path = tmp_path / "image.png"
    path.write_bytes(raw)

    result = read_image(path)

    assert result.image_hash == hashlib.sha256(raw).hexdigest()
    assert path.read_bytes() == raw
    assert list(tmp_path.iterdir()) == [path]


def test_original_hash_tracks_encoding_while_pixels_track_decoded_content():
    image = Image.fromarray(np.arange(63, dtype=np.uint8).reshape(7, 9))
    png = encode(image, "PNG")
    tiff = encode(image, "TIFF")

    first = decode_image(png)
    second = decode_image(tiff)

    assert first.image_hash != second.image_hash
    np.testing.assert_array_equal(first.pixels, second.pixels)


@pytest.mark.parametrize("image", [
    np.full((8, 9), 65535, dtype=np.uint16),
    np.full((8, 9), 4095, dtype=np.uint16),
])
def test_rejects_uint16_images_without_rescaling(image):
    raw = encode(Image.fromarray(image), "TIFF")
    with pytest.raises(ValueError, match="uint8"):
        decode_image(raw)


def test_rejects_float_tiff_rgba_and_palette_images():
    float_tiff = encode(Image.fromarray(np.ones((8, 9), dtype=np.float32)), "TIFF")
    rgba = encode(Image.fromarray(np.zeros((8, 9, 4), dtype=np.uint8), "RGBA"), "PNG")
    palette_image = Image.fromarray(np.zeros((8, 9), dtype=np.uint8), "P")
    palette = encode(palette_image, "PNG")

    for raw in (float_tiff, rgba, palette):
        with pytest.raises(ValueError):
            decode_image(raw)


def test_rejects_multipage_tiff_and_animated_gif_and_webp():
    first = Image.fromarray(np.zeros((8, 9), dtype=np.uint8))
    second = Image.fromarray(np.full((8, 9), 255, dtype=np.uint8))
    multipage_tiff = encode(first, "TIFF", save_all=True, append_images=[second])
    animated_gif = encode(first, "GIF", save_all=True, append_images=[second], duration=100, loop=0)
    animated_webp = encode(first.convert("RGB"), "WEBP", save_all=True, append_images=[second.convert("RGB")], duration=100, loop=0, lossless=True)
    with Image.open(io.BytesIO(animated_webp)) as encoded_webp:
        if encoded_webp.n_frames < 2:
            pytest.skip("Pillow WebP encoder cannot create animated fixtures in this environment")

    for raw in (multipage_tiff, animated_gif, animated_webp):
        with pytest.raises(ValueError, match="frame|single|animated|multi"):
            decode_image(raw)


@pytest.mark.parametrize("orientation", [2, 6])
def test_rejects_exif_orientation_other_than_one(orientation):
    image = Image.fromarray(np.arange(63, dtype=np.uint8).reshape(7, 9))
    exif = Image.Exif()
    exif[274] = orientation
    raw = encode(image, "JPEG", exif=exif)

    with pytest.raises(ValueError, match="orientation|EXIF"):
        decode_image(raw)


def test_accepts_explicit_exif_orientation_one():
    image = Image.fromarray(np.arange(63, dtype=np.uint8).reshape(7, 9))
    exif = Image.Exif()
    exif[274] = 1
    result = decode_image(encode(image, "JPEG", exif=exif))

    assert result.preprocessing["orientation"] == 1


def test_rejects_png_transparency_chunk():
    image = Image.fromarray(np.zeros((8, 9, 3), dtype=np.uint8), "RGB")
    raw = encode(image, "PNG", transparency=(0, 0, 0))

    with pytest.raises(ValueError, match="transparency"):
        decode_image(raw)


def test_rejects_truncated_encoded_image():
    raw = encode(Image.fromarray(np.arange(63, dtype=np.uint8).reshape(7, 9)), "PNG")

    with pytest.raises(ValueError):
        decode_image(raw[:-12])


def test_rejects_images_over_configured_resource_limits(monkeypatch):
    raw = encode(Image.fromarray(np.zeros((8, 9), dtype=np.uint8)), "PNG")

    monkeypatch.setattr(ingestion, "MAX_BYTES", len(raw) - 1)
    with pytest.raises(ValueError, match="bytes"):
        decode_image(raw)
    monkeypatch.setattr(ingestion, "MAX_BYTES", len(raw) + 1)
    monkeypatch.setattr(ingestion, "MAX_PIXELS", 8 * 9 - 1)
    with pytest.raises(ValueError, match="megapixels"):
        decode_image(raw)
    monkeypatch.setattr(ingestion, "MAX_PIXELS", 8 * 9)
    monkeypatch.setattr(ingestion, "MAX_SIDE", 8)
    with pytest.raises(ValueError, match="per side"):
        decode_image(raw)


@pytest.mark.parametrize("raw", [b"", b"not an image", b"\x89PNG\r\n\x1a\ncorrupt"])
def test_corrupt_image_errors_are_actionable(raw):
    with pytest.raises(ValueError) as error:
        decode_image(raw)
    assert str(error.value).strip()
