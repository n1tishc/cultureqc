"""
cultureqc.replay — build realistic visit streams from cached time-lapse
sequences, entirely from the compute cache, no model inference at replay
time (cultureQC_upgrade.md §5.4).

Reads confluency/logits/quality rows straight from a culture.cache.Cache —
no image ever touched, no model ever loaded — so replay runs on CPU in
seconds. Every visit this module produces carries
`"provenance": "replay_simulated"` so downstream consumers (the app's Flask
timeline tab, any report) can label it correctly; the spec requires the UI
say "Replay of recorded time-lapse (simulated visits)" wherever this feeds
it.

**Requires** the source sequence's cached images to have real `sequence_id`
and `frame_idx` set (culture.cache.ImageRecord's own fields) — the actual
Slice 1b Colab pass built every ImageRecord without them (all blank/-1),
since none of its three image sets (synthetic tiles, EVICAN, AutoQC-Bench)
are sequences. That's fine for those sets; it means replay cannot run
against the current real cache at all, only against a cache built with
sequence_id/frame_idx populated — a fixture for now (tests/test_replay.py),
real C2C12/CTC sequences once nb/03 caches them with these fields set
correctly (see docs/DATASETS.md).

**Fault sequences** (Phase A2) aren't looked up in images.parquet: their
pre-onset frames are the original sequence's frames (same sha), and
images.parquet holds one sequence_id per sha. Pass that fault sequence's
rows of `fault_manifest.parquet` as `frames=` instead. Every frame a stream
uses must have cached seg rows, or build_replay_visits() raises.

Tables are read once per call (ReplayTables). For a fleet, build one
ReplayTables and pass it to every call.

Usage:
    from culture.replay import build_replay_visits
    visits = build_replay_visits(cache, sequence_id="c2c12_seq_04",
                                  lineage_id="L1", segment_id="S1",
                                  flask_id="flask-1", seed=0)

    man = pd.read_parquet("cache/sidecars/fault_manifest.parquet")
    tables = ReplayTables(cache)
    fid = "c2c12_seq_04__fault_contam"
    visits = build_replay_visits(cache, fid, "L1", "S1", "flask-1", seed=0,
                                  frames=man[man.fault_sequence_id == fid],
                                  tables=tables, mean_interval_hours=6,
                                  jitter_hours=1.5, n_fov=3)
"""

from __future__ import annotations

import os
import re
import uuid
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import yaml

from culture.calibration import DEFAULT_CALIBRATION_PATH, calibrated_probs, calibration_config_hash, load_calibration
from culture.model_versions import get_model_versions
from culture.quality import config_hash as quality_config_hash
from culture.quality import evaluate_thresholds

_DEFAULT_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "configs", "replay.yaml"
)

# Fixed namespace for deriving visit_id deterministically (uuid.uuid4() would
# make "deterministic given a seed" false for the one field every downstream
# consumer -- History's hash chain included -- treats as a stable key).
# uuid.uuid5(uuid.NAMESPACE_URL, "https://cultureqc/replay/visit_id"), pinned
# as a literal so it never changes across runs/versions.
_VISIT_ID_NAMESPACE = uuid.UUID("86f1bd44-dc64-5e8e-a831-455e06fc9a68")

_CROP_FRAC_RE = re.compile(r"crop_f([0-9.]+)_")


def _load_config(config_path: str) -> dict:
    with open(config_path) as f:
        return yaml.safe_load(f)


def replay_config_hash(config_path: str = _DEFAULT_CONFIG_PATH) -> str:
    from culture.records import hash_file
    return hash_file(config_path)


class ReplayTables:
    """The cache tables replay reads, loaded once and indexed by image sha
    (A2: 'load confluency/logits/quality tables once per stream, not per
    visit'). build_replay_visits() builds one per call if none is given;
    pass one in to share it across every stream of a fleet.

    Row order within each sha is the table's file order, the same order the
    old per-visit boolean filters returned, so crop sampling for a given
    seed is unchanged."""

    def __init__(self, cache):
        self.dir = cache.dir
        conf = cache.load_confluency()
        seg = conf[conf.model_name == "seg"]
        is_full = seg.crop_spec == "full"
        self._crops = {sha: g for sha, g in seg[~is_full].groupby("image_sha256", sort=False)}
        self._full = {sha: g for sha, g in seg[is_full].groupby("image_sha256", sort=False)}

        logits = cache.load_logits()
        qc = logits[logits.model_name == "qc"].drop_duplicates("image_sha256", keep="first")
        self._logits = {r.image_sha256: (r.logits, r.model_version) for r in qc.itertuples()}

        q = cache.load_quality().drop_duplicates("image_sha256", keep="first")
        self._quality = {r["image_sha256"]: r for r in q.to_dict("records")}

        self._images = None

    @classmethod
    def ensure(cls, cache, tables: "ReplayTables | None") -> "ReplayTables":
        return tables if tables is not None else cls(cache)

    def images(self) -> pd.DataFrame:
        if self._images is None:
            self._images = pd.read_parquet(os.path.join(self.dir, "images.parquet"))
        return self._images

    def crops(self, sha: str) -> pd.DataFrame:
        return self._crops.get(sha, _EMPTY)

    def full(self, sha: str) -> pd.DataFrame:
        return self._full.get(sha, _EMPTY)

    def has_seg(self, sha: str) -> bool:
        return sha in self._crops or sha in self._full

    def logits(self, sha: str):
        return self._logits.get(sha)

    def quality(self, sha: str):
        return self._quality.get(sha)


_EMPTY = pd.DataFrame(columns=["image_sha256", "crop_spec", "model_name", "model_version", "pct"])


def _sequence_frames(tables: ReplayTables, sequence_id: str) -> pd.DataFrame:
    """The sequence's cached frames, ordered by frame_idx, with real
    timestamps (required — see module docstring)."""
    images = tables.images()
    frames = images[images.sequence_id == sequence_id].copy()
    if len(frames) == 0:
        raise ValueError(f"no cached frames with sequence_id={sequence_id!r}")
    if (frames.frame_idx < 0).any() or (frames.timestamp == "").any():
        raise ValueError(
            f"sequence_id={sequence_id!r} has frames with unset frame_idx/timestamp — "
            "replay needs both (see module docstring)"
        )
    return frames.sort_values("frame_idx").reset_index(drop=True)


_FRAMES_REQUIRED = ("image_sha256", "frame_idx", "timestamp")


def _frames_from_table(frames: pd.DataFrame, sequence_id: str) -> pd.DataFrame:
    """A2 adapter: an explicit frames table (the fault_manifest.parquet rows
    of one fault_sequence_id) instead of an images.parquet lookup. Fault
    sequences share their pre-onset frames, by sha, with the original
    sequence, and images.parquet holds one sequence_id per sha, so a fault
    sequence can't be found there.

    Ordered by timestamp, not frame_idx: growth-stall rows carry a frame_idx
    derived from the stalled clock, not a real frame number."""
    missing = [c for c in _FRAMES_REQUIRED if c not in frames.columns]
    if missing:
        raise ValueError(f"frames table is missing columns {missing}")
    if len(frames) == 0:
        raise ValueError(f"frames table for {sequence_id!r} is empty")
    if "fault_sequence_id" in frames.columns:
        ids = frames["fault_sequence_id"].unique().tolist()
        if ids != [sequence_id]:
            raise ValueError(
                f"frames table must hold exactly one fault_sequence_id equal to sequence_id={sequence_id!r}; "
                f"got {ids}"
            )
    if frames["timestamp"].isna().any() or (frames["timestamp"].astype(str) == "").any():
        raise ValueError(f"frames table for {sequence_id!r} has unset timestamps")
    out = frames.copy()
    out["_t"] = pd.to_datetime(out["timestamp"], format="ISO8601")
    if out["_t"].duplicated().any():
        raise ValueError(f"frames table for {sequence_id!r} has duplicate timestamps")
    return out.sort_values("_t").drop(columns="_t").reset_index(drop=True)


def _check_frames_cached(tables: ReplayTables, frames: pd.DataFrame, sequence_id: str) -> None:
    """Every frame must have cached seg rows. Without them a visit would read
    n_fov=0 and confluency 0.0, which in a fault stream looks exactly like a
    growth crash (e.g. a slim cache missing the fault frames)."""
    absent = sorted({sha for sha in frames["image_sha256"] if not tables.has_seg(sha)})
    if absent:
        raise ValueError(
            f"{len(absent)} frame(s) of {sequence_id!r} have no cached seg confluency rows "
            f"(first: {absent[0]}); is this the cache the frames were built into?"
        )


def _sample_visit_timestamps(frames: pd.DataFrame, timing: dict, rng: np.random.Generator, n_visits: int | None) -> list[pd.Timestamp]:
    """Irregular visit times (§5.4: 'sample visit times with jitter ...,
    not every frame'), within the sequence's actual time span."""
    frame_times = pd.to_datetime(frames["timestamp"])
    t0, t1 = frame_times.min(), frame_times.max()

    times = []
    t = t0
    while t <= t1 and (n_visits is None or len(times) < n_visits):
        times.append(t)
        gap_hours = timing["mean_interval_hours"] + rng.uniform(-1, 1) * timing["jitter_hours"]
        t = t + timedelta(hours=max(0.1, gap_hours))
    return times


def _nearest_frame(frames: pd.DataFrame, frame_times: pd.Series, visit_time: pd.Timestamp) -> pd.Series:
    idx = (frame_times - visit_time).abs().idxmin()
    return frames.loc[idx]


def _crop_frac(spec: str) -> float | None:
    m = _CROP_FRAC_RE.search(spec)
    return float(m.group(1)) if m else None


def _sample_crops_for_frame(tables: ReplayTables, image_sha: str, repositioning: dict, rng: np.random.Generator) -> pd.DataFrame:
    """1..N of the frame's cached crops (§5.4: 'simulated repositioning:
    each visit samples 1-N of the cached crops for that frame').

    `repositioning` may also fix `n_fov` (always sample exactly that many)
    and `crop_frac` (only crops of that size). Either one set means the
    caller wants that exact FOV design, so a frame that can't supply it
    raises instead of falling back to the full-frame row."""
    crops = tables.crops(image_sha)
    crop_frac, n_fov = repositioning.get("crop_frac"), repositioning.get("n_fov")
    if crop_frac is not None:
        crops = crops[[_crop_frac(s) == float(crop_frac) for s in crops.crop_spec]]
    if crop_frac is not None or n_fov is not None:
        need = n_fov if n_fov is not None else 1
        if len(crops) < need:
            raise ValueError(
                f"frame {image_sha} has {len(crops)} cached crops"
                f"{f' at crop_frac={crop_frac}' if crop_frac is not None else ''}; n_fov={need} requested"
            )
    if len(crops) == 0:
        # No crops cached for this frame (crop_fracs=() at build time) —
        # fall back to the full-frame row alone, one simulated "reposition."
        return tables.full(image_sha).iloc[:1]
    if n_fov is not None:
        n = int(n_fov)
    else:
        lo, hi = repositioning["min_crops_per_visit"], repositioning["max_crops_per_visit"]
        n = int(rng.integers(lo, min(hi, len(crops)) + 1))
    idx = rng.choice(crops.index, size=n, replace=False)
    return crops.loc[idx]


def _class_probs_and_pred(tables: ReplayTables, image_sha: str,
                          calibration: dict | None) -> tuple[dict | None, str | None, bool]:
    """(class_probs, class_pred, calibrated). Temperature-scaled when
    `calibration` was fit for the cached logits' model_version."""
    from culture.qc import CLASS_NAMES

    entry = tables.logits(image_sha)
    if entry is None:
        return None, None, False
    logits, model_version = entry
    probs, calibrated = calibrated_probs(np.array(logits, dtype=np.float64), calibration, model_version)
    class_probs = {name: float(p) for name, p in zip(CLASS_NAMES, probs)}
    class_pred = CLASS_NAMES[int(np.argmax(probs))]
    return class_probs, class_pred, calibrated


def _quality_for_frame(tables: ReplayTables, image_sha: str) -> dict:
    r = tables.quality(image_sha)
    if r is None:
        return {"blur": 0.0, "mean_intensity": 0.0, "uniformity": 0.0, "pass": False, "reasons": ["no_cached_quality_metrics"]}
    result = evaluate_thresholds(r["blur_laplacian_var"], r["exposure_mean"], r["uniformity_block_std"])
    return result.to_dict()


_FAULT_FIELDS = ("fault_type", "base_sequence_id", "onset_hours", "hours_since_start", "is_modified", "severity",
                 "source_frame_idx", "provenance")


def _fault_truth(frame: pd.Series) -> dict:
    """Ground truth copied from a fault_manifest row, for detection-delay
    scoring. Only fields the row actually has; NaN (e.g. source_frame_idx
    on non-stall rows) is left out."""
    out = {}
    for k in _FAULT_FIELDS:
        if k not in frame.index:
            continue
        v = frame[k]
        if v is None or (isinstance(v, float) and np.isnan(v)):
            continue
        out[k] = v.item() if hasattr(v, "item") else v
    return out


def _source_dataset(tables: ReplayTables, frames: pd.DataFrame, is_fault: bool) -> str | None:
    """The dataset the stream's real frames were acquired in, for growth's
    noise-model choice (configs/noise.yaml entries). A fault stream takes its
    base sequence's dataset, so the noise model doesn't switch at onset when
    the frames' own dataset tag changes to the simulated fault's."""
    images = tables.images()
    if is_fault:
        if "base_sequence_id" not in frames.columns:
            return None
        found = images[images.sequence_id.isin(frames["base_sequence_id"].unique())].dataset.unique()
    else:
        found = frames["dataset"].unique() if "dataset" in frames.columns else []
    return str(found[0]) if len(found) == 1 else None


def build_replay_visits(
    cache,
    sequence_id: str,
    lineage_id: str,
    segment_id: str,
    flask_id: str,
    seed: int = 0,
    n_visits: int | None = None,
    config_path: str = _DEFAULT_CONFIG_PATH,
    frames: pd.DataFrame | None = None,
    tables: ReplayTables | None = None,
    mean_interval_hours: float | None = None,
    jitter_hours: float | None = None,
    n_fov: int | None = None,
    crop_frac: float | None = None,
    calibration_path: str = DEFAULT_CALIBRATION_PATH,
) -> list[dict]:
    """Deterministic given `seed` (and the underlying cache's contents, which
    don't change): the same inputs always produce the same visit stream —
    same sampled timestamps, same sampled crops, same visit_id (uuid5, not
    uuid4 — derived from sequence_id/segment_id/timestamp/seed, not random,
    specifically so this determinism claim holds for the one field every
    downstream consumer, History's hash chain included, treats as a stable
    key). Only exception: the caller's History.append_visit() call assigns
    its own fresh record_id/record_hash on every append (RecordWriter's own
    audit-log semantics — "when this was written", not "what was replayed"
    — see culture/records.py), so two separate append runs of an identical
    visit stream produce different record_hash values even though every
    visit_summary field above is byte-identical. Returns a list of
    visit_summary dicts (schemas/visit_summary.v1.json-shaped, plus a
    'provenance' field the schema permits but doesn't require).

    `frames` (A2): replay from this frames table (the fault_manifest.parquet
    rows of one fault_sequence_id, which must equal `sequence_id`) instead of
    looking `sequence_id` up in images.parquet. Each visit then also carries
    a `fault` dict with that frame's ground truth (fault_type, onset_hours,
    is_modified, severity, ...).

    Every visit carries `source_dataset` (a fault stream: its base sequence's
    dataset), which culture/growth.py uses to pick a configs/noise.yaml entry.

    `tables`: a ReplayTables to reuse across streams; built here if None.

    `mean_interval_hours` / `jitter_hours` override configs/replay.yaml's
    timing, `n_fov` fixes the number of crops per visit and `crop_frac`
    restricts them to one crop size (A2 runs 6 h / 12 h cadences at 1 and 3
    FOVs without changing the config defaults). Every visit records the
    values actually used in `replay_params`, since config_hashes alone would
    no longer describe how it was made.

    Class probabilities are temperature-scaled with configs/calibration.yaml
    (A5) when it exists and was fit for the cached logits' qc model_version;
    `calibrated` says whether they were, and the config's hash joins
    config_hashes."""
    config = _load_config(config_path)
    rng = np.random.default_rng(seed)
    tables = ReplayTables.ensure(cache, tables)

    timing = dict(config["timing"])
    if mean_interval_hours is not None:
        timing["mean_interval_hours"] = float(mean_interval_hours)
    if jitter_hours is not None:
        timing["jitter_hours"] = float(jitter_hours)
    repositioning = dict(config["repositioning"])
    if n_fov is not None:
        if n_fov < 1:
            raise ValueError(f"n_fov must be >= 1, got {n_fov}")
        repositioning["n_fov"] = int(n_fov)
    if crop_frac is not None:
        repositioning["crop_frac"] = float(crop_frac)
    replay_params = {
        "mean_interval_hours": timing["mean_interval_hours"],
        "jitter_hours": timing["jitter_hours"],
        "n_fov": repositioning.get("n_fov"),
        "crop_frac": repositioning.get("crop_frac"),
        "seed": seed,
    }
    # Overrides join the visit_id key: the same sequence + seed at 1 vs 3
    # FOVs, or 6 h vs 12 h, samples the same timestamps (e.g. t0) but makes
    # different visits. Without overrides the key is unchanged.
    overrides = {"mean_interval_hours": mean_interval_hours, "jitter_hours": jitter_hours,
                 "n_fov": n_fov, "crop_frac": crop_frac}
    id_suffix = "".join(f"|{k}={replay_params[k]}" for k, v in overrides.items() if v is not None)

    if frames is None:
        frames = _sequence_frames(tables, sequence_id)
        is_fault = False
    else:
        frames = _frames_from_table(frames, sequence_id)
        is_fault = True
    _check_frames_cached(tables, frames, sequence_id)
    source_dataset = _source_dataset(tables, frames, is_fault)
    frame_times = pd.to_datetime(frames["timestamp"])

    visit_times = _sample_visit_timestamps(frames, timing, rng, n_visits)
    model_versions = get_model_versions()
    cfg_hashes = {"quality.yaml": quality_config_hash(), "replay.yaml": replay_config_hash(config_path)}
    calibration = load_calibration(calibration_path)
    if calibration is not None:
        cfg_hashes["calibration.yaml"] = calibration_config_hash(calibration_path)

    visits = []
    for visit_time in visit_times:
        frame = _nearest_frame(frames, frame_times, visit_time)
        sha = frame["image_sha256"]

        sampled_crops = _sample_crops_for_frame(tables, sha, repositioning, rng)
        fov_confluency = [float(p) for p in sampled_crops["pct"]]
        crop_specs = list(sampled_crops["crop_spec"])
        n_fov_visit = len(fov_confluency)

        class_probs, class_pred, calibrated = _class_probs_and_pred(tables, sha, calibration)
        quality = _quality_for_frame(tables, sha)

        timestamp = visit_time.tz_localize("UTC").isoformat() if visit_time.tzinfo is None else visit_time.isoformat()
        visit_id = str(uuid.uuid5(_VISIT_ID_NAMESPACE, f"{sequence_id}|{segment_id}|{timestamp}|{seed}{id_suffix}"))

        visit = {
            "visit_id": visit_id,
            "lineage_id": lineage_id,
            "segment_id": segment_id,
            "flask_id": flask_id,
            "timestamp": timestamp,
            "image_sha256": [sha] * n_fov_visit,  # all sampled crops are sub-regions of this one cached frame
            "fov_confluency": fov_confluency,
            "confluency_mean": float(np.mean(fov_confluency)) if fov_confluency else 0.0,
            "confluency_sd": float(np.std(fov_confluency)) if len(fov_confluency) > 1 else 0.0,
            "n_fov": n_fov_visit,
            "class_probs": class_probs,
            "class_pred": class_pred,
            "calibrated": calibrated,
            "anomaly_score": None,
            "anomaly_score_density_bin": None,
            "quality": quality,
            "model_versions": model_versions,
            "config_hashes": cfg_hashes,
            # Extra, schema-permitted (not required) provenance fields:
            "provenance": "replay_simulated",
            "source_sequence_id": sequence_id,
            "source_dataset": source_dataset,
            "source_frame_idx": int(frame["frame_idx"]),
            "crop_specs": crop_specs,
            "replay_params": replay_params,
        }
        if is_fault:
            visit["fault"] = _fault_truth(frame)
        visits.append(visit)
    return visits


def split_sequences(sequence_ids, seed: int = 0, tuning_frac: float = 0.4,
                    strata: dict[str, str] | None = None) -> dict[str, str]:
    """A2 fleet split: each base sequence goes to "tuning" (~tuning_frac) or
    "heldout", seeded. Split by sequence, never by visit or frame.

    Fault sequences must take their base sequence's side (fault_split()):
    their pre-onset frames *are* the base sequence's frames, so splitting
    them independently would put the same frames on both sides.

    `strata` (sequence_id -> stratum name; ids not in it form one stratum of
    their own) splits each stratum separately at tuning_frac, so every fault
    type reaches both sides (fault_strata()). make_fault_set.py picks its
    contamination/stall bases with the same seeded permutation of the same
    sorted ids, so an unstratified split at the same seed puts all of them in
    tuning."""
    ids = sorted(set(sequence_ids))
    if not 0.0 < tuning_frac < 1.0:
        raise ValueError(f"tuning_frac must be in (0, 1), got {tuning_frac}")
    rng = np.random.default_rng(seed)
    groups = {}
    for sid in ids:
        groups.setdefault((strata or {}).get(sid, ""), []).append(sid)
    tuning = set()
    for name in sorted(groups):
        members = groups[name]
        order = rng.permutation(len(members))
        tuning |= {members[i] for i in order[:int(round(tuning_frac * len(members)))]}
    return {sid: ("tuning" if sid in tuning else "heldout") for sid in ids}


def fault_strata(manifest: pd.DataFrame, ignore=("lamp_dimming",)) -> dict[str, str]:
    """base_sequence_id -> the fault type built on it, for split_sequences(strata=).
    Fault types applied to every sequence (lamp dimming) carry no information
    and are ignored."""
    pairs = manifest[~manifest.fault_type.isin(ignore)][["base_sequence_id", "fault_type"]].drop_duplicates()
    if pairs.base_sequence_id.duplicated().any():
        raise ValueError("a base sequence carries more than one stratifying fault type")
    return dict(zip(pairs.base_sequence_id, pairs.fault_type))


def fault_split(manifest: pd.DataFrame, base_split: dict[str, str]) -> dict[str, str]:
    """Each fault_sequence_id's split = its base_sequence_id's split."""
    pairs = manifest[["fault_sequence_id", "base_sequence_id"]].drop_duplicates()
    if pairs.fault_sequence_id.duplicated().any():
        raise ValueError("a fault_sequence_id maps to more than one base_sequence_id")
    unknown = sorted(set(pairs.base_sequence_id) - set(base_split))
    if unknown:
        raise ValueError(f"base sequences not in the split: {unknown[:5]}")
    return {r.fault_sequence_id: base_split[r.base_sequence_id] for r in pairs.itertuples()}


def build_replay_lineage_with_passage(
    cache,
    lineage_id: str,
    parent_sequence_id: str,
    parent_segment_id: str,
    child_sequence_id: str,
    child_segment_id: str,
    flask_id: str,
    split_ratio: float = 0.2,
    seed: int = 0,
    n_visits_parent: int | None = None,
    n_visits_child: int | None = None,
    config_path: str = _DEFAULT_CONFIG_PATH,
) -> tuple[list[dict], dict]:
    """§5.4: 'simulated passage: optionally end a segment at a target
    confluency and start a child segment from an earlier frame of another
    sequence (labelled simulated).' Composes two build_replay_visits() runs
    (parent sequence, child sequence — an EARLIER frame of a *different*
    cached sequence, standing in for 'the culture was split and one part
    kept growing') with a PASSAGED event between them, both segments in the
    same lineage. Returns (all_visits_in_order, passaged_event_dict) — the
    caller appends both to a History."""
    parent_visits = build_replay_visits(
        cache, parent_sequence_id, lineage_id, parent_segment_id, flask_id,
        seed=seed, n_visits=n_visits_parent, config_path=config_path,
    )
    child_visits = build_replay_visits(
        cache, child_sequence_id, lineage_id, child_segment_id, flask_id,
        seed=seed + 1, n_visits=n_visits_child, config_path=config_path,
    )
    event = {
        "row_type": "event",
        "lineage_id": lineage_id,
        "segment_id": parent_segment_id,
        "event_type": "PASSAGED",
        "split_ratio": split_ratio,
        "child_segment_ids": [child_segment_id],
        "provenance": "replay_simulated",
    }
    return parent_visits + child_visits, event
