"""
culture/replay.py tests (cultureQC_upgrade.md §5.4, §5.5 acceptance: "Replay
produces irregular, repositioned, lineage-aware visit streams; deterministic
given a seed").

Builds a fully synthetic fixture cache directly (fabricated sha256 strings,
constructed parquet rows) rather than depending on cache/ (gitignored, real
Colab output, not present in a fresh clone/CI) or on downloading real image
sources — culture/replay.py only ever reads parquet tables, never touches
pixels or calls load_probmap(), so a synthetic cache exercises the real code
path exactly as the real cache would. Manually verified once against the
real production cache during development (see the branch's commit history)
to confirm this isn't just testing itself in a vacuum.
"""

from __future__ import annotations

import hashlib
import json
import os

import jsonschema
import numpy as np
import pandas as pd
import pytest

from culture.replay import build_replay_lineage_with_passage, build_replay_visits


def _fake_sha(i: int) -> str:
    return hashlib.sha256(f"fixture-image-{i}".encode()).hexdigest()


class _FakeCache:
    """Not culture.cache.Cache -- replay.py never calls Cache() itself, it
    takes any object exposing .dir and .load_confluency()/.load_logits()/
    .load_quality() with the same signatures, which is exactly what real
    Cache provides. This minimal stand-in avoids needing Cache.__init__'s
    on-disk directory setup for a fixture that's otherwise pure in-memory
    parquet, while still round-tripping through real parquet files (not
    just Python dicts) so a schema/dtype mismatch would actually surface."""

    def __init__(self, tmp_dir: str):
        self.dir = tmp_dir

    def load_confluency(self):
        return pd.read_parquet(os.path.join(self.dir, "confluency.parquet"))

    def load_logits(self):
        df = pd.read_parquet(os.path.join(self.dir, "logits.parquet"))
        df["logits"] = df["logits"].apply(json.loads)
        return df

    def load_quality(self):
        return pd.read_parquet(os.path.join(self.dir, "quality.parquet"))


def _build_fixture_cache(tmp_path, sequence_id: str, n_frames: int, hours_apart: float,
                          start: str, shas: list[str]) -> None:
    rng = np.random.default_rng(0)
    base = pd.Timestamp(start)

    images_rows, conf_rows, logits_rows, quality_rows = [], [], [], []
    for i, sha in enumerate(shas):
        images_rows.append({
            "image_sha256": sha, "dataset": "fixture", "source_path": f"/fake/{sha}.png",
            "sequence_id": sequence_id, "frame_idx": i,
            "timestamp": (base + pd.Timedelta(hours=hours_apart * i)).isoformat(),
            "height": 256, "width": 256, "bit_depth": "uint8", "normalization": "grayscale_imread",
        })
        full_pct = float(rng.uniform(5, 60))
        conf_rows.append({
            "image_sha256": sha, "crop_spec": "full", "model_name": "seg", "model_version": "cpsam_v2",
            "pct": full_pct, "confidence": 0.8, "extra": json.dumps({}),
        })
        for k in range(4):
            crop_pct = float(np.clip(full_pct + rng.normal(0, 5), 0, 100))
            conf_rows.append({
                "image_sha256": sha, "crop_spec": f"crop_f0.25_s1_k{k}", "model_name": "seg",
                "model_version": "cpsam_v2", "pct": crop_pct, "confidence": 0.75,
                "extra": json.dumps({"frac": 0.25}),
            })
        logits_rows.append({
            "image_sha256": sha, "crop_spec": "full", "model_name": "qc", "model_version": "qc_effnetb0_v1",
            "logits": json.dumps([float(x) for x in rng.normal(0, 2, 4)]),
        })
        quality_rows.append({
            "blur_laplacian_var": float(rng.uniform(200, 800)),
            "exposure_mean": float(rng.uniform(125, 131)),
            "uniformity_block_std": float(rng.uniform(0.1, 1.0)),
            "image_sha256": sha, "model_name": "quality", "model_version": "quality_v1",
        })

    existing_images = None
    images_path = os.path.join(tmp_path, "images.parquet")
    if os.path.exists(images_path):
        existing_images = pd.read_parquet(images_path)
    new_images = pd.DataFrame(images_rows)
    combined = pd.concat([existing_images, new_images], ignore_index=True) if existing_images is not None else new_images
    combined.to_parquet(images_path, index=False)

    for name, rows in [("confluency", conf_rows), ("logits", logits_rows), ("quality", quality_rows)]:
        path = os.path.join(tmp_path, f"{name}.parquet")
        new_df = pd.DataFrame(rows)
        if os.path.exists(path):
            new_df = pd.concat([pd.read_parquet(path), new_df], ignore_index=True)
        new_df.to_parquet(path, index=False)


@pytest.fixture
def fixture_cache(tmp_path):
    shas1 = [_fake_sha(i) for i in range(12)]
    _build_fixture_cache(tmp_path, "fixture_seq_1", 12, hours_apart=8.0, start="2026-01-01T00:00:00Z", shas=shas1)
    shas2 = [_fake_sha(100 + i) for i in range(8)]
    _build_fixture_cache(tmp_path, "fixture_seq_2", 8, hours_apart=8.0, start="2025-12-20T00:00:00Z", shas=shas2)
    return _FakeCache(str(tmp_path))


@pytest.fixture
def schema():
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "schemas", "visit_summary.v1.json")
    with open(path) as f:
        return json.load(f)


def test_build_replay_visits_matches_schema(fixture_cache, schema):
    visits = build_replay_visits(fixture_cache, "fixture_seq_1", "L1", "S1", "flask-1", seed=0)
    assert len(visits) > 1
    for v in visits:
        jsonschema.validate(v, schema)


def test_replay_visits_have_irregular_timestamps(fixture_cache):
    visits = build_replay_visits(fixture_cache, "fixture_seq_1", "L1", "S1", "flask-1", seed=0)
    timestamps = pd.to_datetime(pd.Series([v["timestamp"] for v in visits]), format="ISO8601")
    gaps = timestamps.diff().dropna()
    assert len(gaps) >= 2
    assert gaps.nunique() > 1, "expected irregular (jittered) gaps, not a fixed interval"


def test_replay_visits_simulate_repositioning(fixture_cache):
    visits = build_replay_visits(fixture_cache, "fixture_seq_1", "L1", "S1", "flask-1", seed=0)
    # every visit samples 1..max_crops_per_visit cached crops, not always the same count
    n_fovs = [v["n_fov"] for v in visits]
    assert all(1 <= n <= 4 for n in n_fovs)
    assert len(set(n_fovs)) > 1, "expected a varying number of sampled crops across visits"


def test_replay_is_lineage_and_segment_aware(fixture_cache):
    visits = build_replay_visits(fixture_cache, "fixture_seq_1", "L1", "S1", "flask-1", seed=0)
    assert all(v["lineage_id"] == "L1" and v["segment_id"] == "S1" for v in visits)
    assert all(v["provenance"] == "replay_simulated" for v in visits)


def test_replay_deterministic_given_seed(fixture_cache):
    v1 = build_replay_visits(fixture_cache, "fixture_seq_1", "L1", "S1", "flask-1", seed=42)
    v2 = build_replay_visits(fixture_cache, "fixture_seq_1", "L1", "S1", "flask-1", seed=42)
    assert [v["timestamp"] for v in v1] == [v["timestamp"] for v in v2]
    assert [v["fov_confluency"] for v in v1] == [v["fov_confluency"] for v in v2]
    assert [v["crop_specs"] for v in v1] == [v["crop_specs"] for v in v2]


def test_replay_different_seed_differs(fixture_cache):
    v1 = build_replay_visits(fixture_cache, "fixture_seq_1", "L1", "S1", "flask-1", seed=0)
    v2 = build_replay_visits(fixture_cache, "fixture_seq_1", "L1", "S1", "flask-1", seed=1)
    assert [v["timestamp"] for v in v1] != [v["timestamp"] for v in v2]


def test_replay_unset_sequence_fields_raises(tmp_path):
    """The real Slice 1b cache left sequence_id/frame_idx unset for all
    4,246 rows (none of its datasets are sequences) — replay must fail
    loudly against that, not silently produce a garbage single-frame reading."""
    shas = [_fake_sha(i) for i in range(3)]
    _build_fixture_cache(tmp_path, "", 3, hours_apart=8.0, start="2026-01-01T00:00:00Z", shas=shas)
    # blank out sequence_id/frame_idx the way the real cache actually has them
    images_path = os.path.join(tmp_path, "images.parquet")
    df = pd.read_parquet(images_path)
    df["sequence_id"] = ""
    df["frame_idx"] = -1
    df.to_parquet(images_path, index=False)

    cache = _FakeCache(str(tmp_path))
    with pytest.raises(ValueError):
        build_replay_visits(cache, "", "L1", "S1", "flask-1", seed=0)


def test_replay_lineage_with_passage(fixture_cache):
    visits, event = build_replay_lineage_with_passage(
        fixture_cache, lineage_id="L1",
        parent_sequence_id="fixture_seq_1", parent_segment_id="S1",
        child_sequence_id="fixture_seq_2", child_segment_id="S2",
        flask_id="flask-1", seed=0,
    )
    assert event["event_type"] == "PASSAGED"
    assert event["child_segment_ids"] == ["S2"]
    assert event["provenance"] == "replay_simulated"

    segs = {v["segment_id"] for v in visits}
    assert segs == {"S1", "S2"}
    assert all(v["lineage_id"] == "L1" for v in visits)


def test_replay_integrates_with_history(fixture_cache, tmp_path):
    from culture.history import History

    visits, event = build_replay_lineage_with_passage(
        fixture_cache, lineage_id="L1",
        parent_sequence_id="fixture_seq_1", parent_segment_id="S1",
        child_sequence_id="fixture_seq_2", child_segment_id="S2",
        flask_id="flask-1", seed=0,
    )
    h = History(str(tmp_path / "history"))
    for v in visits:
        h.append_visit(v)
    h.append_event(lineage_id=event["lineage_id"], segment_id=event["segment_id"],
                    event_type=event["event_type"], split_ratio=event["split_ratio"],
                    child_segment_ids=event["child_segment_ids"])

    ok, bad_line = h.verify_lineage("L1")
    assert ok, f"chain broken at line {bad_line}"
    assert len(h.get_segment("S1")) > 0
    assert len(h.get_segment("S2")) > 0
