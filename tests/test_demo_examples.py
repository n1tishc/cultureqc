"""B8 (cultureQC_upgrade_specv4.md §2B.7 item 2): the Analyze tab's precomputed
examples (demo/examples/, scripts/export_demo_examples.py).

- Each example is self-consistent: image hash, record fields, flag vs
  threshold, action vs the rules on the stored numbers, and the confluency
  profile it was read with is the one in configs/confluency_profiles.yaml.
- C2C12 examples agree with the compute cache (GPU) for the same image, at
  the cutoff the cache uses (0.0, `pct_default_cutoff`).
- Showing one needs no model and never touches the session's audit chain.
- The 3D view's map is the one the record hashes (confluency_map_hash).
"""

import json
import math
import os

import numpy as np
import pytest
from conftest import requires

from culture.cache import PROBMAP_DOWNSAMPLE, downsample_probmap, probmap_sha256
from culture.profiles import UNCALIBRATED, get_profile
from culture.records import GENESIS_HASH, hash_file
from culture.rules import RULES_VERSION, LineConfig, decide
from demo import precomputed
from demo.analysis import DEFAULT_HOURS_SINCE_FEED, DEFAULT_HOURS_SINCE_PASSAGE

EXAMPLES = precomputed.load()


def test_examples_exist():
    ids = [e["id"] for e in EXAMPLES]
    assert 6 <= len(ids) <= 8 and len(set(ids)) == len(ids)
    kinds = {e["kind"] for e in EXAMPLES}
    assert kinds == {"c2c12_normal", "c2c12_contamination", "c2c12_contamination_real", "evican"}


@pytest.mark.skipif(not os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                                    "results", "contamination_scale.csv")), reason="no scale results")
def test_real_size_example_matches_the_scale_run():
    """The real-size example is the same frame, variant and models as results/contamination_scale.csv."""
    import pandas as pd
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sc = pd.read_csv(os.path.join(repo, "results", "contamination_scale.csv"))
    (ex,) = [e for e in EXAMPLES if e["kind"] == "c2c12_contamination_real"]
    row = sc[(sc.variant == "scale0.060769_haze") & (sc.image_sha256 == ex["image_sha256"])].iloc[0]
    assert ex["confluency"]["extra"]["pct_default_cutoff"] == pytest.approx(row.pct, abs=0.01)
    assert ex["anomaly"]["score"] == pytest.approx(row.score, abs=1e-4)
    assert ex["anomaly"]["flag"] == row.flag
    assert "at chance" in ex["caption"] and "16.5" not in ex["caption"]


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
    # read with the setup's current profile, and binned for the anomaly check at cutoff 0.0
    prof = get_profile(ex["profile_id"])
    assert prof.id == ex["profile_id"] and rec["confluency_profile"] == prof.record_fields()
    assert rec["confluency_interval"] == prof.interval(rec["confluency_pct"])
    assert rec["anomaly_bin_confluency_pct"] == ex["confluency"]["extra"]["pct_default_cutoff"]
    if prof.cutoff == 0.0:
        assert ex["confluency"]["pct"] == pytest.approx(ex["confluency"]["extra"]["pct_default_cutoff"], abs=1e-6)
    # the action follows from the stored numbers alone (classifier demoted)
    assert ex["demoted"]
    gate = rec.get("quality_gate") or {}
    action, _ = decide(confluency_pct=ex["confluency"]["pct"], confluency_confidence=ex["confluency"]["confidence"],
                       qc_flag=None, qc_confidence=None,
                       line_config=LineConfig(cell_line=ex["cell_line"], target_confluency=ex["target_confluency"]),
                       hours_since_passage=DEFAULT_HOURS_SINCE_PASSAGE, hours_since_feed=DEFAULT_HOURS_SINCE_FEED,
                       anomaly_flag=a["flag"] if a["status"] == "ok" else None, band_pp=prof.band_pp,
                       quality_passed=gate.get("passed"), quality_reasons=gate.get("reasons"))
    assert action == ex["action"]
    for key in ("caption", "credit", "generated_at", "device", "timings_s"):
        assert ex[key], key


@pytest.mark.parametrize("ex", EXAMPLES, ids=lambda e: e["id"])
def test_stored_record_matches_the_schema(ex):
    jsonschema = pytest.importorskip("jsonschema")
    with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "culture", "schema.json")) as f:
        jsonschema.validate(ex["record"], json.load(f))


def test_stored_chain_starts_with_the_approved_profile_changes():
    """Every validated profile went live through a change record that replaces
    `uncalibrated` with it, by SHA-256, at the chain's start, whether or not an
    example reads with it (msc_phase has no example image). A named setup without
    a calibration (c2c12_ker2018) reads like `uncalibrated`, so it has none."""
    from culture.profiles import load_profiles
    with open(precomputed.EXAMPLES_JSON) as f:
        changes = json.load(f).get("changes") or []
    validated = {p for p, prof in load_profiles().items() if prof.status == "validated"}
    after = {c["after"]["id"]: c for c in changes}
    assert len(after) == len(changes) and set(after) == validated
    for pid in {e["profile_id"] for e in EXAMPLES} - validated:
        assert get_profile(pid).status == "uncalibrated" and get_profile(pid).band_pp is None, pid
    for pid in validated:
        c, prof = after[pid], get_profile(pid)
        assert c["record_type"] == "change" and c["subject"] == "confluency_profile"
        assert c["before"] == {"id": UNCALIBRATED, "sha256": get_profile(UNCALIBRATED).sha256}
        assert c["after"] == {"id": pid, "sha256": prof.sha256}
    # one chain: the changes first, then the examples
    chain = changes + [e["record"] for e in EXAMPLES]
    assert chain[0]["prev_record_hash"] == GENESIS_HASH
    for prev, rec in zip(chain, chain[1:]):
        assert rec["prev_record_hash"] == prev["record_hash"]


@pytest.mark.parametrize("ex", [e for e in EXAMPLES if "cache" in e], ids=lambda e: e["id"])
def test_c2c12_examples_match_the_cache(ex):
    """Cache: Colab GPU (nb/03), cutoff 0.0. Examples: this machine's run of the same code."""
    c = ex["cache"]
    assert ex["anomaly"]["bin_label"] == c["anomaly_bin"]
    assert ex["confluency"]["extra"]["pct_default_cutoff"] == pytest.approx(c["confluency_pct"], abs=0.5)
    assert ex["anomaly"]["score"] == pytest.approx(c["anomaly_score"], abs=0.01)
    assert ex["anomaly"]["flag"] == c["anomaly_flag"]


@requires("gradio")
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
    cut = ex["record"]["confluency_profile"]["cutoff"]
    # observed on the 7 examples: max 0.15 pp and 0.0014 (1/4-resolution sampling)
    assert (m > round(cut * 1000)).mean() * 100 == pytest.approx(c["pct"], abs=0.5)
    assert (m > 0).mean() * 100 == pytest.approx(c["extra"]["pct_default_cutoff"], abs=0.5)
    # borderline: within ±1 logit of the cutoff the reading was counted at (culture/seg.py)
    assert (np.abs(m.astype(np.int32) - round(cut * 1000)) < 1000).mean() == pytest.approx(
        c["extra"]["borderline_fraction"], abs=0.005)


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


@requires("gradio")
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


def test_cutoff_study_is_the_live_evican_profile():
    """demo/examples/cutoff_calibrated.json is exactly what scripts/export_cutoff_examples.py
    derives from results/confluency_cutoff.csv, is marked superseded, and its calibrated
    cutoff is the one the EVICAN examples are read with (profile evican_mixed), so the site's
    not-fully-blind disclosure is about the cutoff that is live."""
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    csv = os.path.join(repo, "results", "confluency_cutoff.csv")
    doc = precomputed.cutoff_calibrated()
    if not os.path.exists(csv):
        pytest.skip("no cutoff study results")
    import sys
    sys.path.insert(0, os.path.join(repo, "scripts"))
    from export_cutoff_examples import build
    assert doc == build(csv)
    assert doc["status"].startswith("superseded") and "evican_mixed" in doc["status"]
    assert doc["disclosure"]["text"].startswith("Not fully blind")
    evican = [e for e in EXAMPLES if e["kind"] == "evican"]
    assert evican
    for ex in evican:
        assert ex["profile_id"] == "evican_mixed"
        assert ex["record"]["confluency_profile"]["cutoff"] == doc["cutoff"]["calibrated"]
        # the study's reading at the pick is the card's, as displayed
        assert f'{doc["examples"][ex["id"]]["calibrated"]["pct"]:.1f}' == f'{ex["confluency"]["pct"]:.1f}', ex["id"]
