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
    # visit_id is derived (uuid5), not random (uuid4) -- must be stable too,
    # since History's hash chain and any UI table key off it.
    assert [v["visit_id"] for v in v1] == [v["visit_id"] for v in v2]


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


# -- A2: fault-sequence adapter (frames=), load-once tables, overrides, split --

from culture.replay import ReplayTables, fault_split, split_sequences

_FAULT_ID = "fixture_seq_1__fault_contam"
_ONSET_H = 48.0


def _fault_manifest(tmp_path) -> pd.DataFrame:
    """fixture_seq_1 (12 frames, 8 h apart) with frames from 48 h on replaced
    by modified frames, cached under the fault sequence's id — the shape
    scripts/make_fault_set.py + nb/03 produce."""
    mod_shas = [_fake_sha(200 + i) for i in range(6)]
    _build_fixture_cache(tmp_path, _FAULT_ID, 6, hours_apart=8.0, start="2026-01-03T00:00:00Z", shas=mod_shas)
    base = pd.Timestamp("2026-01-01T00:00:00Z")
    rows = []
    for i in range(12):
        h = 8.0 * i
        modified = h >= _ONSET_H
        rows.append({
            "fault_sequence_id": _FAULT_ID, "base_sequence_id": "fixture_seq_1",
            "fault_type": "contamination_onset", "onset_hours": _ONSET_H, "frame_idx": i,
            "timestamp": (base + pd.Timedelta(hours=h)).isoformat(), "hours_since_start": h,
            "image_sha256": mod_shas[i - 6] if modified else _fake_sha(i),
            "is_modified": modified, "severity": 150.0 if modified else 0.0, "provenance": "simulated",
        })
    return pd.DataFrame(rows)


def test_fault_replay_reads_frames_from_manifest(fixture_cache, tmp_path, schema):
    man = _fault_manifest(tmp_path)
    visits = build_replay_visits(fixture_cache, _FAULT_ID, "L1", "S1", "flask-1", seed=0, frames=man,
                                 mean_interval_hours=6, jitter_hours=1.5)
    assert len(visits) >= 10
    pre, post = set(man.image_sha256[~man.is_modified]), set(man.image_sha256[man.is_modified])
    for v in visits:
        jsonschema.validate(v, schema)
        assert v["source_sequence_id"] == _FAULT_ID
        f = v["fault"]
        assert f["fault_type"] == "contamination_onset" and f["onset_hours"] == _ONSET_H
        assert f["provenance"] == "simulated"
        assert (v["image_sha256"][0] in post) == f["is_modified"]
        assert (v["image_sha256"][0] in pre) == (not f["is_modified"])
        assert f["is_modified"] == (f["hours_since_start"] >= _ONSET_H)
    assert any(v["fault"]["is_modified"] for v in visits) and not all(v["fault"]["is_modified"] for v in visits)


def test_fault_stream_ids_differ_from_base_stream(fixture_cache, tmp_path):
    man = _fault_manifest(tmp_path)
    base = build_replay_visits(fixture_cache, "fixture_seq_1", "L1", "S1", "flask-1", seed=0)
    fault = build_replay_visits(fixture_cache, _FAULT_ID, "L1", "S1", "flask-1", seed=0, frames=man)
    assert not {v["visit_id"] for v in base} & {v["visit_id"] for v in fault}
    assert all("fault" not in v for v in base)


def test_frames_table_must_match_sequence_id(fixture_cache, tmp_path):
    man = _fault_manifest(tmp_path)
    with pytest.raises(ValueError, match="exactly one fault_sequence_id"):
        build_replay_visits(fixture_cache, "fixture_seq_1", "L1", "S1", "flask-1", frames=man)
    two = pd.concat([man, man.assign(fault_sequence_id="other")], ignore_index=True)
    with pytest.raises(ValueError, match="exactly one fault_sequence_id"):
        build_replay_visits(fixture_cache, _FAULT_ID, "L1", "S1", "flask-1", frames=two)


def test_uncached_frame_raises_instead_of_reading_zero(fixture_cache, tmp_path):
    man = _fault_manifest(tmp_path)
    man.loc[man.index[-1], "image_sha256"] = _fake_sha(999)  # not in the cache
    with pytest.raises(ValueError, match="no cached seg confluency rows"):
        build_replay_visits(fixture_cache, _FAULT_ID, "L1", "S1", "flask-1", frames=man)


def test_frames_ordered_by_time_not_frame_idx(fixture_cache, tmp_path):
    """Growth-stall rows carry a frame_idx from the stalled clock; order must
    come from timestamps."""
    man = _fault_manifest(tmp_path)
    man["frame_idx"] = man["frame_idx"].to_numpy()[::-1]
    man["source_frame_idx"] = np.nan
    man.loc[man.is_modified, "source_frame_idx"] = 3
    man = man.sample(frac=1.0, random_state=0)
    visits = build_replay_visits(fixture_cache, _FAULT_ID, "L1", "S1", "flask-1", seed=0, frames=man,
                                 mean_interval_hours=8, jitter_hours=0)
    hours = [v["fault"]["hours_since_start"] for v in visits]
    assert hours == sorted(hours) and len(set(hours)) == len(hours)
    for v in visits:
        assert ("source_frame_idx" in v["fault"]) == v["fault"]["is_modified"]


def test_cadence_and_fov_overrides_are_applied_and_recorded(fixture_cache):
    visits = build_replay_visits(fixture_cache, "fixture_seq_1", "L1", "S1", "flask-1", seed=0,
                                 mean_interval_hours=6, jitter_hours=1.5, n_fov=3, crop_frac=0.25)
    ts = pd.to_datetime(pd.Series([v["timestamp"] for v in visits]), format="ISO8601")
    gaps_h = ts.diff().dropna().dt.total_seconds() / 3600
    assert gaps_h.between(4.5, 7.5).all()
    assert all(v["n_fov"] == 3 and len(v["fov_confluency"]) == 3 for v in visits)
    assert all(v["replay_params"] == {"mean_interval_hours": 6.0, "jitter_hours": 1.5, "n_fov": 3,
                                      "crop_frac": 0.25, "seed": 0} for v in visits)


def test_fov_design_the_cache_cannot_supply_raises(fixture_cache):
    with pytest.raises(ValueError, match="crop_frac=0.5"):
        build_replay_visits(fixture_cache, "fixture_seq_1", "L1", "S1", "flask-1", crop_frac=0.5)
    with pytest.raises(ValueError, match="n_fov=5"):
        build_replay_visits(fixture_cache, "fixture_seq_1", "L1", "S1", "flask-1", n_fov=5)


def test_tables_loaded_once_per_stream_and_shareable(fixture_cache, monkeypatch):
    calls = {"confluency": 0, "logits": 0, "quality": 0}
    for name in calls:
        orig = getattr(fixture_cache, f"load_{name}")

        def counted(orig=orig, name=name):
            calls[name] += 1
            return orig()
        monkeypatch.setattr(fixture_cache, f"load_{name}", counted)

    visits = build_replay_visits(fixture_cache, "fixture_seq_1", "L1", "S1", "flask-1", seed=0,
                                 mean_interval_hours=6, jitter_hours=1.5)
    assert len(visits) > 5
    assert calls == {"confluency": 1, "logits": 1, "quality": 1}

    tables = ReplayTables(fixture_cache)
    shared = build_replay_visits(fixture_cache, "fixture_seq_1", "L1", "S1", "flask-1", seed=0,
                                 mean_interval_hours=6, jitter_hours=1.5, tables=tables)
    build_replay_visits(fixture_cache, "fixture_seq_2", "L2", "S2", "flask-2", seed=0, tables=tables)
    assert calls == {"confluency": 2, "logits": 2, "quality": 2}
    assert shared == visits


def test_split_by_sequence_is_seeded_and_fault_twins_follow_base():
    ids = [f"seq_{i:02d}" for i in range(48)]
    split = split_sequences(ids, seed=0)
    assert split == split_sequences(list(reversed(ids)), seed=0)
    assert split != split_sequences(ids, seed=1)
    assert sum(s == "tuning" for s in split.values()) == round(0.4 * 48)

    man = pd.DataFrame([{"fault_sequence_id": f"{sid}__fault_{k}", "base_sequence_id": sid}
                        for sid in ids for k in ("dim", "contam") for _ in range(3)])
    fs = fault_split(man, split)
    assert len(fs) == 96
    assert all(fs[f"{sid}__fault_{k}"] == split[sid] for sid in ids for k in ("dim", "contam"))
    with pytest.raises(ValueError, match="not in the split"):
        fault_split(man, {k: v for k, v in split.items() if k != "seq_00"})


def test_visit_ids_differ_across_fov_and_cadence_variants(fixture_cache):
    """Same sequence, segment and seed: the variants share sampled timestamps
    (at least t0) but are different visits, so ids must not collide."""
    run = lambda **kw: {v["visit_id"] for v in build_replay_visits(  # noqa: E731
        fixture_cache, "fixture_seq_1", "L1", "S1", "flask-1", seed=0, **kw)}
    variants = [run(mean_interval_hours=6, jitter_hours=1.5, n_fov=1),
                run(mean_interval_hours=6, jitter_hours=1.5, n_fov=3),
                run(mean_interval_hours=12, jitter_hours=3, n_fov=1),
                run()]
    for i in range(len(variants)):
        for j in range(i + 1, len(variants)):
            assert not variants[i] & variants[j], (i, j)
