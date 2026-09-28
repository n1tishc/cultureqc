"""B8 (cultureQC_upgrade_specv4.md §2B.7 item 2): the Analyze tab's precomputed
examples (demo/examples/, scripts/export_demo_examples.py).

- Each example is self-consistent: image hash, record fields, flag vs
  threshold, action vs the rules on the stored numbers.
- C2C12 examples agree with the compute cache (GPU) for the same image.
- Showing one needs no model and never touches the session's audit chain.
- The 3D view's map is the one the record hashes (confluency_map_hash).
"""

import math
import os

import numpy as np
import pytest

from culture.cache import PROBMAP_DOWNSAMPLE, downsample_probmap, probmap_sha256
from culture.records import hash_file
from culture.rules import RULES_VERSION, LineConfig, decide
from demo import precomputed
from demo.analysis import DEFAULT_HOURS_SINCE_FEED, DEFAULT_HOURS_SINCE_PASSAGE

EXAMPLES = precomputed.load()


def test_examples_exist():
    ids = [e["id"] for e in EXAMPLES]
    assert 6 <= len(ids) <= 8 and len(set(ids)) == len(ids)
    kinds = {e["kind"] for e in EXAMPLES}
    assert kinds == {"c2c12_normal", "c2c12_contamination", "evican"}


@pytest.mark.parametrize("ex", EXAMPLES, ids=lambda e: e["id"])
def test_example_is_self_consistent(ex):
    assert hash_file(precomputed.image_path(ex)) == ex["image_sha256"] == ex["record"]["image_hash"]
    assert os.path.exists(precomputed.overlay_path(ex))
    rec = ex["record"]
    assert rec["confluency_pct"] == ex["confluency"]["pct"]
    assert rec["anomaly_used_in_decision"] is (ex["anomaly"]["status"] == "ok")
    assert rec["decided_by"] == RULES_VERSION
    assert rec["qc_used_in_decision"] is (not ex["demoted"])
    assert rec["recommended_action"] == ex["action"]
    a = ex["anomaly"]
    if a["status"] == "ok":
        assert a["flag"] == (a["score"] > a["threshold"]) == rec["anomaly_flag"]
    # the action follows from the stored numbers alone (classifier demoted)
    assert ex["demoted"]
    action, _ = decide(confluency_pct=ex["confluency"]["pct"], confluency_confidence=ex["confluency"]["confidence"],
                       qc_flag=None, qc_confidence=None,
                       line_config=LineConfig(cell_line=ex["cell_line"], target_confluency=ex["target_confluency"]),
                       hours_since_passage=DEFAULT_HOURS_SINCE_PASSAGE, hours_since_feed=DEFAULT_HOURS_SINCE_FEED,
                       anomaly_flag=a["flag"] if a["status"] == "ok" else None)
    assert action == ex["action"]
    for key in ("caption", "credit", "generated_at", "device", "timings_s"):
        assert ex[key], key


@pytest.mark.parametrize("ex", [e for e in EXAMPLES if "cache" in e], ids=lambda e: e["id"])
def test_c2c12_examples_match_the_cache(ex):
    """Cache: Colab GPU (nb/03). Examples: this machine's run of the same code."""
    c = ex["cache"]
    assert ex["anomaly"]["bin_label"] == c["anomaly_bin"]
    assert ex["confluency"]["pct"] == pytest.approx(c["confluency_pct"], abs=0.5)
    assert ex["anomaly"]["score"] == pytest.approx(c["anomaly_score"], abs=0.01)
    assert ex["anomaly"]["flag"] == c["anomaly_flag"]


def test_showing_an_example_runs_no_model(monkeypatch):
    import culture.qc
    import culture.seg

    def boom(*a, **k):
        raise AssertionError("a model was loaded to show a precomputed example")

    monkeypatch.setattr(culture.seg, "_get_model", boom)
    monkeypatch.setattr(culture.qc, "_get_model", boom)
    from demo import app

    before = app.writer.record_count
    for ex in EXAMPLES:
        out = app.on_example(precomputed.image_path(ex))
        html = out[2]
        assert "Precomputed example" in html and "not part of this session" in html
        assert ex["caption"].split(";")[0] in html.replace("&#x27;", "'")
        assert out[0] == precomputed.overlay_path(ex)
        image, plot, note = app.switch_view("3D", None, None, out[7])
        assert image["visible"] is False and plot["visible"] is True
        assert "matches the record" in note["value"] and "NOT" not in note["value"]
    assert app.writer.record_count == before


@pytest.mark.parametrize("ex", EXAMPLES, ids=lambda e: e["id"])
def test_example_matches_after_gradio_resave(ex, tmp_path):
    """Gradio hands the click handler a re-saved copy (grey PNG becomes RGB)."""
    from PIL import Image

    copy = tmp_path / os.path.basename(precomputed.image_path(ex))
    Image.open(precomputed.image_path(ex)).convert("RGB").save(copy)
    if copy.suffix == ".png":
        assert hash_file(str(copy)) != ex["image_sha256"]
        assert precomputed.match(str(copy), EXAMPLES) is ex


@pytest.mark.parametrize("ex", EXAMPLES, ids=lambda e: e["id"])
def test_3d_map_is_the_recorded_one(ex):
    """The stored map hashes to the record's confluency_map_hash, has the
    cache's stored shape, and reproduces the full-resolution numbers."""
    m = precomputed.probmap(ex)
    assert m is not None and m.dtype == np.int16
    assert m.shape == (math.ceil(ex["height"] / PROBMAP_DOWNSAMPLE), math.ceil(ex["width"] / PROBMAP_DOWNSAMPLE))
    assert probmap_sha256(m) == ex["record"]["confluency_map_hash"]
    c = ex["confluency"]
    # observed on the 7 examples: max 0.15 pp and 0.0014 (1/4-resolution sampling)
    assert (m > 0).mean() * 100 == pytest.approx(c["pct"], abs=0.5)
    assert (np.abs(m) < 1000).mean() == pytest.approx(c["extra"]["borderline_fraction"], abs=0.005)


@pytest.mark.parametrize("ex", [e for e in EXAMPLES if "cache" in e], ids=lambda e: e["id"])
def test_3d_map_agrees_with_the_cache(ex):
    """CPU map (this export) vs the Colab GPU cache's map of the same frame:
    share of map points on the other side of the cutoff."""
    assert ex["cache"]["probmap_sign_disagree_pct"] < 1.0      # observed max 0.244%


def test_map_hash_is_canonical():
    prob = np.random.default_rng(0).normal(0, 4, (1040, 1392)).astype(np.float32)
    m = downsample_probmap(prob)
    assert m.shape == (260, 348) and m.dtype == np.int16
    assert probmap_sha256(m) == probmap_sha256(m.astype(">i2")) == probmap_sha256(np.asfortranarray(m))
    assert probmap_sha256(m) != probmap_sha256(m.reshape(348, 260))
    changed = m.copy()
    changed[0, 0] += 1
    assert probmap_sha256(changed) != probmap_sha256(m)


def test_3d_note_flags_a_map_that_does_not_match():
    from demo import confluency_3d

    ex = next(e for e in EXAMPLES if e.get("probmap"))
    m = precomputed.probmap(ex).copy()
    m[0, 0] += 1
    note = confluency_3d.landscape_note(m, ex["confluency"], ex["record"]["confluency_map_hash"], True)
    assert "does NOT match" in note


def test_examples_are_not_cached_on_spaces():
    """Hugging Face Spaces set GRADIO_CACHE_EXAMPLES=true; caching the examples
    failed at startup on the Space (the stored maps exceed Gradio's CSV field
    limit), so the app must opt out whatever the environment says."""
    import subprocess
    import sys

    code = "from demo import app; assert app.EXAMPLES_UI.cache_examples is False"
    env = {**os.environ, "GRADIO_CACHE_EXAMPLES": "true"}
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    r = subprocess.run([sys.executable, "-c", code], cwd=repo, env=env, capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stderr[-2000:]
