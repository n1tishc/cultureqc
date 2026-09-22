"""
culture/history.py tests (cultureQC_upgrade.md §5.3, §5.5 acceptance:
"history append-only with hash chain verified in tests"). Pure Python, no
GPU, no cache dependency.
"""

from __future__ import annotations

import json

import pytest

from culture.history import History, ModelVersionChange

MODEL_VERSIONS_V1 = {
    "seg": {"version": "cpsam_v2", "weights_sha256": "a" * 64},
    "qc": {"version": "qc_effnetb0_v1", "weights_sha256": "b" * 64},
}
MODEL_VERSIONS_V2 = {
    "seg": {"version": "cpsam_v2", "weights_sha256": "c" * 64},  # same name, different weights
    "qc": {"version": "qc_effnetb0_v1", "weights_sha256": "b" * 64},
}


def make_visit(lineage_id, segment_id, visit_id, timestamp, confluency=30.0,
                model_versions=None, quality_pass=True):
    return {
        "visit_id": visit_id,
        "lineage_id": lineage_id,
        "segment_id": segment_id,
        "flask_id": "flask-1",
        "timestamp": timestamp,
        "image_sha256": ["d" * 64],
        "fov_confluency": [confluency],
        "confluency_mean": confluency,
        "confluency_sd": 0.0,
        "n_fov": 1,
        "class_probs": {"normal": 0.9, "contamination_suspected": 0.1},
        "class_pred": "normal",
        "calibrated": False,
        "anomaly_score": None,
        "anomaly_score_density_bin": None,
        "quality": {
            "blur": 500.0, "mean_intensity": 128.0, "uniformity": 0.3,
            "pass": quality_pass,
            "reasons": [] if quality_pass else ["blur_below_threshold"],
        },
        "model_versions": model_versions or MODEL_VERSIONS_V1,
        "config_hashes": {"quality.yaml": "e" * 64},
    }


def test_append_visit_validates_schema(tmp_path):
    h = History(str(tmp_path))
    bad_visit = make_visit("L1", "S1", "v1", "2026-01-01T00:00:00Z")
    del bad_visit["confluency_mean"]
    import jsonschema
    with pytest.raises(jsonschema.ValidationError):
        h.append_visit(bad_visit)


def test_append_visit_and_get_lineage(tmp_path):
    h = History(str(tmp_path))
    h.append_visit(make_visit("L1", "S1", "v1", "2026-01-01T00:00:00Z"))
    h.append_visit(make_visit("L1", "S1", "v2", "2026-01-02T00:00:00Z"))

    rows = h.get_lineage("L1")
    assert len(rows) == 2
    assert [r["visit_id"] for r in rows] == ["v1", "v2"]
    # RecordWriter's chain fields are present on the stored rows
    assert rows[0]["prev_record_hash"] == "0" * 64
    assert rows[1]["prev_record_hash"] == rows[0]["record_hash"]


def test_get_lineage_unknown_returns_empty(tmp_path):
    h = History(str(tmp_path))
    assert h.get_lineage("nonexistent") == []


def test_hash_chain_is_append_only_and_verifiable(tmp_path):
    h = History(str(tmp_path))
    for i in range(5):
        h.append_visit(make_visit("L1", "S1", f"v{i}", f"2026-01-0{i+1}T00:00:00Z"))

    ok, bad_line = h.verify_lineage("L1")
    assert ok and bad_line is None


def test_hash_chain_detects_tampering(tmp_path):
    h = History(str(tmp_path))
    h.append_visit(make_visit("L1", "S1", "v1", "2026-01-01T00:00:00Z"))
    h.append_visit(make_visit("L1", "S1", "v2", "2026-01-02T00:00:00Z"))

    # Tamper with the first line's confluency_mean directly on disk.
    path = tmp_path / "L1.jsonl"
    lines = path.read_text().splitlines()
    row = json.loads(lines[0])
    row["confluency_mean"] = 999.0
    lines[0] = json.dumps(row)
    path.write_text("\n".join(lines) + "\n")

    ok, bad_line = h.verify_lineage("L1")
    assert not ok
    assert bad_line == 1


def test_append_event_and_get_segment(tmp_path):
    h = History(str(tmp_path))
    h.append_event(lineage_id="L1", segment_id="S1", event_type="SEEDED", seeding_density=5000)
    h.append_visit(make_visit("L1", "S1", "v1", "2026-01-01T00:00:00Z"))
    h.append_event(lineage_id="L1", segment_id="S1", event_type="PASSAGED",
                    split_ratio=0.2, child_segment_ids=["S2"])
    h.append_visit(make_visit("L1", "S2", "v2", "2026-01-02T00:00:00Z"))

    s1 = h.get_segment("S1")
    assert [r.get("row_type") for r in s1] == ["event", "visit", "event"]
    assert s1[0]["event_type"] == "SEEDED"
    assert s1[0]["seeding_density"] == 5000

    s2 = h.get_segment("S2")
    assert len(s2) == 1
    assert s2[0]["visit_id"] == "v2"


def test_append_event_rejects_unknown_type(tmp_path):
    h = History(str(tmp_path))
    with pytest.raises(ValueError):
        h.append_event(lineage_id="L1", segment_id="S1", event_type="BOGUS")


def test_trend_windows_excludes_quality_failures(tmp_path):
    h = History(str(tmp_path))
    h.append_visit(make_visit("L1", "S1", "v1", "2026-01-01T00:00:00Z", quality_pass=True))
    h.append_visit(make_visit("L1", "S1", "v2", "2026-01-02T00:00:00Z", quality_pass=False))
    h.append_visit(make_visit("L1", "S1", "v3", "2026-01-03T00:00:00Z", quality_pass=True))

    windows = h.trend_windows("S1")
    assert len(windows) == 1
    assert [v["visit_id"] for v in windows[0]] == ["v1", "v3"]

    # get_lineage(trend_only=True) applies the same filter, but keeps events
    h.append_event(lineage_id="L1", segment_id="S1", event_type="NOTE", note="check")
    trend_rows = h.get_lineage("L1", trend_only=True)
    assert [r.get("visit_id", r.get("event_type")) for r in trend_rows] == ["v1", "v3", "NOTE"]


def test_trend_windows_splits_on_model_version_change(tmp_path):
    h = History(str(tmp_path))
    h.append_visit(make_visit("L1", "S1", "v1", "2026-01-01T00:00:00Z", model_versions=MODEL_VERSIONS_V1))
    h.append_visit(make_visit("L1", "S1", "v2", "2026-01-02T00:00:00Z", model_versions=MODEL_VERSIONS_V1))
    h.append_visit(make_visit("L1", "S1", "v3", "2026-01-03T00:00:00Z", model_versions=MODEL_VERSIONS_V2))
    h.append_visit(make_visit("L1", "S1", "v4", "2026-01-04T00:00:00Z", model_versions=MODEL_VERSIONS_V2))

    windows = h.trend_windows("S1")
    assert len(windows) == 2
    assert [v["visit_id"] for v in windows[0]] == ["v1", "v2"]
    assert [v["visit_id"] for v in windows[1]] == ["v3", "v4"]


def test_require_single_window_raises_on_version_change(tmp_path):
    h = History(str(tmp_path))
    h.append_visit(make_visit("L1", "S1", "v1", "2026-01-01T00:00:00Z", model_versions=MODEL_VERSIONS_V1))
    h.append_visit(make_visit("L1", "S1", "v2", "2026-01-02T00:00:00Z", model_versions=MODEL_VERSIONS_V2))

    with pytest.raises(ModelVersionChange):
        h.require_single_window("S1")


def test_require_single_window_passes_when_consistent(tmp_path):
    h = History(str(tmp_path))
    h.append_visit(make_visit("L1", "S1", "v1", "2026-01-01T00:00:00Z"))
    h.append_visit(make_visit("L1", "S1", "v2", "2026-01-02T00:00:00Z"))

    visits = h.require_single_window("S1")
    assert len(visits) == 2


def test_different_lineages_chain_independently(tmp_path):
    h = History(str(tmp_path))
    h.append_visit(make_visit("L1", "S1", "v1", "2026-01-01T00:00:00Z"))
    h.append_visit(make_visit("L2", "S2", "v2", "2026-01-01T00:00:00Z"))

    # Both are the first row in their own lineage -> both chain to genesis,
    # not to each other, even though L2's write happened second overall.
    l1 = h.get_lineage("L1")
    l2 = h.get_lineage("L2")
    assert l1[0]["prev_record_hash"] == "0" * 64
    assert l2[0]["prev_record_hash"] == "0" * 64
