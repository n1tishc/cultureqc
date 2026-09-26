"""
scripts/replay_fleet.py on a tiny fixture cache: 5 base sequences plus a
contamination and a lamp-dimming twin of one of them.

Checks the split file (twins follow their base), every stream x cadence x
FOV cell, the pre-onset pairing check, and that a rerun is byte-identical.
"""

from __future__ import annotations

import filecmp
import importlib.util
import json
import os
import sys

import pandas as pd

from test_replay import _build_fixture_cache, _fake_sha

_SPEC = importlib.util.spec_from_file_location(
    "replay_fleet", os.path.join(os.path.dirname(__file__), "..", "scripts", "replay_fleet.py"))
rf = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(rf)

_N, _H = 40, 2.0  # frames per sequence, hours apart (78 h span)
_ONSET = 40.0


def _fleet_cache(tmp_path):
    d = tmp_path / "cache"
    (d / "sidecars").mkdir(parents=True)
    ids = [f"c2c12_s{k}" for k in range(5)]
    for k, sid in enumerate(ids):
        _build_fixture_cache(str(d), sid, _N, hours_apart=_H, start="2009-03-03T00:00:00",
                             shas=[_fake_sha(1000 * k + i) for i in range(_N)], dataset="c2c12")
    pd.DataFrame({"sequence_id": ids, "experiment": [90303] * 5}).to_csv(d / "sidecars" / "c2c12_sequences.csv")

    base = pd.Timestamp("2009-03-03T00:00:00")
    n_mod = _N - int(_ONSET / _H) - 1
    rows = []
    for ftype, fid, tag in [("contamination_onset", "c2c12_s0__fault_contam", 7000),
                            ("lamp_dimming", "c2c12_s0__fault_dim", 8000)]:
        mod = [_fake_sha(tag + i) for i in range(n_mod)]
        _build_fixture_cache(str(d), fid, n_mod, hours_apart=_H, start="2009-03-04T18:00:00", shas=mod,
                             dataset="c2c12_fault")
        for i in range(_N):
            h = _H * i
            after = h > _ONSET
            rows.append({"fault_sequence_id": fid, "base_sequence_id": "c2c12_s0", "fault_type": ftype,
                         "onset_hours": _ONSET, "frame_idx": i, "timestamp": (base + pd.Timedelta(hours=h)).isoformat(),
                         "hours_since_start": h, "image_sha256": mod[i - _N + n_mod] if after else _fake_sha(i),
                         "is_modified": after, "severity": 0.5 if after else 0.0, "provenance": "simulated"})
    pd.DataFrame(rows).to_parquet(d / "sidecars" / "fault_manifest.parquet")
    return str(d)


def _run(monkeypatch, cache, out, visits):
    monkeypatch.setattr(sys, "argv", ["replay_fleet.py", "--cache-dir", cache, "--out", out, "--visits-out", visits])
    rf.main()


def test_fleet_run(tmp_path, monkeypatch):
    cache, out, visits = _fleet_cache(tmp_path), str(tmp_path / "results"), str(tmp_path / "visits")
    _run(monkeypatch, cache, out, visits)

    split = pd.read_csv(os.path.join(out, "replay_fleet_split.csv")).set_index("sequence_id").split
    assert set(split.index) == {f"c2c12_s{k}" for k in range(5)} | {"c2c12_s0__fault_contam", "c2c12_s0__fault_dim"}
    assert split["c2c12_s0__fault_contam"] == split["c2c12_s0__fault_dim"] == split["c2c12_s0"]

    streams = pd.read_csv(os.path.join(out, "replay_fleet_streams.csv"))
    assert len(streams) == 7 * len(rf.CADENCES) * len(rf.N_FOVS)
    assert (streams.n_visits >= rf.MIN_GROWTH_VISITS).all()
    assert set(streams.source_dataset) == {"c2c12"}

    rows = [json.loads(line) for line in open(os.path.join(visits, "visits_6h_fov3.jsonl"))]
    assert all(r["n_fov"] == 3 and all(s.startswith("crop_f0.25_") for s in r["crop_specs"]) for r in rows)
    assert all(r["fleet_split"] == split[r["source_sequence_id"]] for r in rows)

    summary = open(os.path.join(out, "replay_fleet_summary.md")).read()
    assert "| contamination_onset | 4/4 |" in summary and "| lamp_dimming | 4/4 |" in summary

    first = str(tmp_path / "visits_first")
    os.rename(visits, first)
    _run(monkeypatch, cache, out, visits)
    for name in os.listdir(first):
        assert filecmp.cmp(os.path.join(first, name), os.path.join(visits, name), shallow=False)
