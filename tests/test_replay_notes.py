"""The replays' quality-gate notes (scripts/export_demo_replays.py). Wherever the
gate fires with no fault present, the note shows this replay's rate next to the
gate's rate on all held-out normal frames, so a replay picked before the gate
was calibrated can't read as typical (the replays themselves are not swapped)."""

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
