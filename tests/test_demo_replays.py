"""B1 (cultureQC_upgrade_specv4.md §2B.3): the Flask Timeline's precomputed
replays. The committed JSONs must hold the spec's invariants and render with
no cache; with the cache present, a re-export must reproduce them exactly."""

import filecmp
import glob
import json
import os
import subprocess
import sys

import pytest
from conftest import require_module

require_module("gradio")
from demo import replay_timeline  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPLAYS = replay_timeline.load_replays()


def test_all_five_scenarios_are_committed():
    assert list(REPLAYS) == ["normal_1", "normal_2", "contamination", "stall", "dimming"]
    kinds = {k: (d["fault"] or {}).get("type") for k, d in REPLAYS.items()}
    assert kinds == {"normal_1": None, "normal_2": None, "contamination": "contamination_onset",
                     "stall": "growth_stall", "dimming": "lamp_dimming"}


@pytest.mark.parametrize("name", list(REPLAYS))
def test_replay_invariants(name):
    d = REPLAYS[name]
    assert d["split"] == "heldout"
    assert d["banner"] == "Replay of recorded time-lapse (simulated visits and faults)"
    assert "Ker" in d["credit"] and "CC BY 4.0" in d["credit"]
    assert d["replay_params"] == {"mean_interval_hours": 6.0, "jitter_hours": 1.5, "n_fov": 3, "crop_frac": 0.25,
                                  "seed": 0}
    raw = json.dumps(d)
    assert "class_probs" not in raw and "class_pred" not in raw       # classifier demoted
    hours = [v["hours"] for v in d["visits"]]
    assert hours == sorted(hours) and hours[0] == 0
    for v in d["visits"]:
        assert v["reimage"] is (not v["quality_pass"])
        assert v["noise_se"] > 0
    fc = d["forecast"]
    assert fc["backtest"]["n_sequences"] == 5 and fc["target_pct"] == 50 and fc["cut_pct"] == 40
    if fc["status"] == "predicted":
        at = d["visits"][fc["made_at_visit"]]
        assert at["quality_pass"] and at["confluency_mean"] >= fc["cut_pct"]
        assert all(v["confluency_mean"] < fc["cut_pct"] for v in d["visits"][:fc["made_at_visit"]]
                   if v["quality_pass"])                               # made once, at the cut
    if "contamination" in name:
        assert "16.5×" in d["caption"] and "stress test" in d["caption"]
    if d.get("fault"):
        assert all(v["post_onset"] == (v["hours"] > d["fault"]["onset_hours"]) for v in d["visits"])


def test_normal_forecast_matches_the_backtest():
    parity = REPLAYS["normal_1"]["forecast"]["backtest_parity"]
    assert parity["unfiltered_matches_backtest"]


@pytest.mark.parametrize("name", list(REPLAYS))
def test_tab_renders_without_cache(name):
    fig, md, table = replay_timeline.render(name, REPLAYS)
    assert fig.axes and table.count("<tr>") == len(REPLAYS[name]["visits"]) + 1
    assert "n = 5 sequences" in md


@pytest.mark.skipif(not os.path.exists(os.path.join(REPO, "cache", "anomaly", "scores.parquet")),
                    reason="needs the local compute cache")
def test_reexport_is_byte_identical(tmp_path):
    subprocess.run([sys.executable, os.path.join(REPO, "scripts", "export_demo_replays.py"), "--cache-dir",
                    os.path.join(REPO, "cache"), "--out-dir", str(tmp_path)], check=True, capture_output=True)
    committed = sorted(os.path.basename(p) for p in glob.glob(os.path.join(REPO, "demo", "replays", "*.json")))
    assert sorted(os.listdir(tmp_path)) == committed
    for name in committed:
        assert filecmp.cmp(tmp_path / name, os.path.join(REPO, "demo", "replays", name), shallow=False), name


def test_forecast_on_a_flagged_visit_says_the_passage_is_held():
    for name, doc in REPLAYS.items():
        fc = doc["forecast"]
        text = replay_timeline.forecast_text(doc)
        flagged = fc["status"] in ("predicted", "suppressed_fault") and any(
            v["visit"] == fc["made_at_visit"] and v.get("anomaly_flag") for v in doc["visits"])
        assert ("Passage held" in text) == flagged, name
    assert "Passage held" in replay_timeline.forecast_text(REPLAYS["contamination"])


def test_suppressed_forecast_shows_its_reason_not_a_crossing_time():
    doc = REPLAYS["contamination"]
    text = replay_timeline.forecast_text(doc)
    assert doc["forecast"]["suppressed_reason"] in text and "reaches 50% at" not in text
    fig, _, _ = replay_timeline.render("contamination", REPLAYS)
    assert not any("Growth fit" in t.get_text() for t in fig.axes[0].get_legend().get_texts())
