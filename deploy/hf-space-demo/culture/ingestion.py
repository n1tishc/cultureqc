"""Single-frame uint8 ingestion with source-byte and decoded-pixel provenance."""

from dataclasses import dataclass
import hashlib
import io
import json
import struct
import warnings

import cv2
import numpy as np
from PIL import Image, UnidentifiedImageError

POLICY = "uint8-single-frame-v1"
MAX_BYTES = 64 * 1024 * 1024
MAX_PIXELS = 16 * 1024 * 1024
MAX_SIDE = 8192
FORMATS = ("PNG", "JPEG", "TIFF", "BMP", "WEBP")


@dataclass(frozen=True)
class ImageInput:
    pixels: np.ndarray
    image_hash: str
    preprocessing: dict


def _digest(value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    return hashlib.sha256(raw.encode()).hexdigest()


def pixel_hash(pixels):
    header = json.dumps({"dtype": str(pixels.dtype), "shape": list(pixels.shape)},
                        sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(header.encode() + b"\0" + pixels.tobytes(order="C")).hexdigest()


def read_image(path):
    with open(path, "rb") as stream:
        return decode_image(stream.read(MAX_BYTES + 1))


def decode_image(raw):
    """Reject unsupported encodings; never infer bit depth from a frame's maximum."""
    if not isinstance(raw, bytes) or not raw or len(raw) > MAX_BYTES:
        raise ValueError("Image must contain 1 byte to 64 MiB of immutable encoded bytes")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            warnings.filterwarnings("error", category=UserWarning, module=r"PIL(\..*)?")
            with Image.open(io.BytesIO(raw)) as source:
                source_format, source_mode = source.format, source.mode
                width, height = source.size
                if width * height > MAX_PIXELS or max(width, height) > MAX_SIDE:
                    raise ValueError("Image exceeds 16 megapixels or 8192 pixels per side; use a validated acquisition/export size")
                if getattr(source, "n_frames", 1) != 1:
                    raise ValueError("Multi-frame images are unsupported; export one explicitly selected frame")
                if source_format == "TIFF" and source.tag_v2.get(330):
                    raise ValueError("TIFF subimages are unsupported; export one explicitly selected frame")
                if source_format not in FORMATS:
                    raise ValueError("Unsupported image format; use single-frame PNG, JPEG, TIFF, BMP or WebP")
                orientation = source.getexif().get(274, 1)
                if orientation != 1:
                    raise ValueError("Non-default EXIF orientation is unsupported; export pixels in the intended orientation")
                if source_mode not in ("L", "RGB"):
                    raise ValueError("Only uint8 grayscale or RGB images are supported; export using a fixed, setup-validated conversion (no per-image auto-contrast)")
                if "transparency" in source.info:
                    raise ValueError("Image transparency is unsupported; export uint8 grayscale or RGB without alpha/transparency")
                source.load()
        encoded = np.frombuffer(raw, dtype=np.uint8)
        native = cv2.imdecode(encoded, cv2.IMREAD_UNCHANGED)
        expected = (height, width) if source_mode == "L" else (height, width, 3)
        if native is None:
            raise ValueError("Could not decode image; provide a complete, supported image file")
        if native.dtype != np.uint8:
            raise ValueError("High-bit-depth or floating-point images are unsupported; export uint8 using a fixed, setup-validated mapping, not auto-contrast")
        if native.shape != expected:
            raise ValueError("Image channels or dimensions disagree with metadata; export uint8 grayscale or RGB without alpha")
        pixels = cv2.imdecode(encoded, cv2.IMREAD_GRAYSCALE | cv2.IMREAD_IGNORE_ORIENTATION)
        if pixels is None or pixels.dtype != np.uint8 or pixels.shape != (height, width):
            raise ValueError("Could not decode image consistently as uint8 grayscale")
    except (UnidentifiedImageError, OSError, SyntaxError, TypeError, KeyError, IndexError,
            OverflowError, EOFError, struct.error,
            cv2.error, Image.DecompressionBombError, UserWarning) as exc:
        raise ValueError("Could not decode image safely; provide a complete single-frame uint8 image") from exc
    image_hash = hashlib.sha256(raw).hexdigest()
    preprocessing = {
        "policy": POLICY, "source_format": source_format, "source_mode": source_mode,
        "source_dtype": "uint8", "source_shape": list(native.shape), "source_sha256": image_hash,
        "frame_count": 1, "orientation": 1,
        "transform": "identity" if source_mode == "L" else "opencv-grayscale",
        "decoder_version": cv2.__version__, "output_dtype": "uint8",
        "output_shape": list(pixels.shape), "output_sha256": pixel_hash(pixels),
    }
    preprocessing["sha256"] = _digest(preprocessing)
    return ImageInput(pixels, image_hash, preprocessing)


def validate_preprocessing(record):
    """Validate recorded provenance without reading mutable source files."""
    provenance = record["preprocessing"]
    payload = {name: value for name, value in provenance.items() if name != "sha256"}
    if provenance["sha256"] != _digest(payload):
        raise ValueError("Preprocessing identity mismatch")
    if provenance["source_sha256"] != record["image_hash"]:
        raise ValueError("Preprocessing source differs from image hash")
    expected = provenance["output_shape"] + ([3] if provenance["source_mode"] == "RGB" else [])
    height, width = provenance["output_shape"]
    if height * width > MAX_PIXELS:
        raise ValueError("Preprocessing dimensions exceed the decoding limit")
    if provenance["source_shape"] != expected:
        raise ValueError("Preprocessing source/output dimensions disagree")
    transform = "identity" if provenance["source_mode"] == "L" else "opencv-grayscale"
    if provenance["transform"] != transform:
        raise ValueError("Preprocessing mode/transform disagree")
