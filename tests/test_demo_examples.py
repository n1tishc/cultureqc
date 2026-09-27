"""B8 (cultureQC_upgrade_specv4.md §2B.7 item 2): the Analyze tab's precomputed
examples (demo/examples/, scripts/export_demo_examples.py).

- Each example is self-consistent: image hash, record fields, flag vs
  threshold, action vs the rules on the stored numbers.
- C2C12 examples agree with the compute cache (GPU) for the same image.
- Showing one needs no model and never touches the session's audit chain.
"""

import os

import pytest

from culture.records import hash_file
from culture.rules import LineConfig, decide
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
    assert rec["anomaly_used_in_decision"] is False
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
                       hours_since_passage=DEFAULT_HOURS_SINCE_PASSAGE, hours_since_feed=DEFAULT_HOURS_SINCE_FEED)
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
