"""
demo/precomputed.py — the Analyze tab's precomputed examples
(demo/examples/examples.json, written by scripts/export_demo_examples.py).
Loading and showing one needs no model; the app labels it as precomputed.
"""

from __future__ import annotations

import json
import os

import cv2
import numpy as np

from culture.anomaly import AnomalyResult
from culture.records import hash_file

EXAMPLES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "examples")
EXAMPLES_JSON = os.path.join(EXAMPLES_DIR, "examples.json")


def load(path: str = EXAMPLES_JSON) -> list[dict]:
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return json.load(f)["examples"]


def image_path(ex: dict) -> str:
    return os.path.join(EXAMPLES_DIR, ex["image"])


def overlay_path(ex: dict) -> str:
    return os.path.join(EXAMPLES_DIR, ex["overlay"])


def match(path: str, examples: list[dict]) -> dict | None:
    """The example this file shows. Gradio copies example files and re-saves
    PNGs (8-bit grey becomes RGB), so a byte hash matches only the JPEGs; the
    fallback compares the decoded grey pixels with each same-sized example."""
    if not path or not os.path.exists(path):
        return None
    sha = hash_file(path)
    ex = next((e for e in examples if e["image_sha256"] == sha), None)
    if ex is not None:
        return ex
    img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        return None
    for e in examples:
        if (e["height"], e["width"]) == img.shape and np.array_equal(
                cv2.imread(image_path(e), cv2.IMREAD_GRAYSCALE), img):
            return e
    return None


def anomaly_result(ex: dict) -> AnomalyResult:
    a = dict(ex["anomaly"])
    a["top_patches"] = [tuple(p) for p in a.get("top_patches") or []]
    return AnomalyResult(**a)
