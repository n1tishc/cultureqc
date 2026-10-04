"""What the replays and the site tell a viewer beside the numbers
(scripts/export_demo_replays.py, site/assets/build_data.py). Wherever the
quality gate fires with no fault present, the note shows this replay's rate next
to the gate's rate on all held-out normal frames, so a replay picked before the
gate was calibrated can't read as typical (the replays themselves are not
swapped). A forecast driven by pasted bacteria shows its reason, not a crossing
time. The demoted classifier is off the site's cards, and the console's heading
for it carries the measured rate."""

import ast
import glob
import json
import os
import re

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_gate_notes_show_the_replay_rate_and_the_overall_rate():
    with open(os.path.join(REPO, "results", "quality_gate_c2c12.md")) as f:
        overall = re.search(r"^\| held-out normal \| \d+ \| \d+ \| \d+ \(([\d.]+)%\)", f.read(), re.M).group(1)
    checked = 0
    for path in sorted(glob.glob(os.path.join(REPO, "demo", "replays", "*.json"))):
        with open(path) as f:
            doc = json.load(f)
        k = doc["summary"]["reimage_before_onset"]
        gate_notes = [n for n in doc["notes"] if "fail the quality gate" in n]
        if not k:
            assert not gate_notes, path
            continue
        (note,) = gate_notes
        assert note.startswith(f"{k} of ") and f"{overall}%" in note and "per-instrument calibration" in note, path
        checked += 1
    assert checked >= 1


def _replays():
    out = {}
    for path in sorted(glob.glob(os.path.join(REPO, "demo", "replays", "*.json"))):
        with open(path) as f:
            out[os.path.basename(path)[:-5]] = json.load(f)
    return out


def test_contamination_forecast_is_suppressed_with_its_reason():
    replays = _replays()
    for name, doc in replays.items():
        fc = doc["forecast"]
        after_onset = (doc.get("fault") or {}).get("type") == "contamination_onset" and fc.get("made_at_hours") and \
            fc["made_at_hours"] > doc["fault"]["onset_hours"]
        assert (fc["status"] == "suppressed_fault") == bool(after_onset), name
    fc = replays["contamination"]["forecast"]
    assert fc["status"] == "suppressed_fault"
    assert fc["suppressed_reason"] == "driven by pasted bacteria raising measured confluency, not by growth"
    with open(os.path.join(REPO, "site", "src", "data.json")) as f:
        site = {r["scenario"]: r for r in json.load(f)["replays"]}
    shown = site["contamination"]["forecast"]
    assert shown["t_star"] is None and shown["interval"] is None and not shown["curve"]
    assert shown["suppressed_reason"] == fc["suppressed_reason"]


def test_target_note_matches_its_sources():
    with open(os.path.join(REPO, "results", "review_rate.md")) as f:
        top = re.search(r"Highest held-out C2C12 confluency: ([\d.]+)%", f.read()).group(1)
    with open(os.path.join(REPO, "demo", "examples", "examples.json")) as f:
        targets = {e["target_confluency"] for e in json.load(f)["examples"]}
    assert targets == {80.0}
    for name, doc in _replays().items():
        note = doc["target_note"]
        assert f"Passage target {doc['forecast']['target_pct']:.0f}%" in note, name
        assert f"never pass {top}%" in note and "Analyze examples use 80%" in note, name


def test_classifier_is_off_the_site_cards_and_its_console_heading_is_sourced():
    with open(os.path.join(REPO, "site", "src", "data.json")) as f:
        items = json.load(f)["examples"]["items"]
    assert items and not any("classifier" in e for e in items)
    with open(os.path.join(REPO, "site", "src", "components", "Stage.jsx")) as f:
        assert "classifier" not in f.read()
    with open(os.path.join(REPO, "results", "classifier_c2c12.md")) as f:
        rate = re.search(r"^\| normal \(held-out base frames\) \| \d+ \| ([\d.]+%)", f.read(), re.M).group(1)
    from culture.claims import python_strings
    strings = python_strings(os.path.join(REPO, "demo", "app.py"))
    assert f"Demoted — known wrong on real frames ({rate} of normal frames called normal); " in strings


def _constant(path, name):
    with open(os.path.join(REPO, path)) as f:
        tree = ast.parse(f.read())
    (value,) = [n.value.value for n in tree.body if isinstance(n, ast.Assign)
                and any(getattr(t, "id", None) == name for t in n.targets)]
    return value


def test_site_reads_the_replays_with_the_console_setup():
    """build_data.py keeps its own copy of the replays' imaging setup: importing it from
    demo/replay_timeline.py would need matplotlib, which the site job does not install."""
    assert _constant("site/assets/build_data.py", "REPLAY_PROFILE") == \
        _constant("demo/replay_timeline.py", "SETUP_PROFILE") == "c2c12_ker2018"
