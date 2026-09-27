"""
B1 (cultureQC_upgrade_specv4.md §2B.3): export the Flask Timeline's
precomputed replays to demo/replays/*.json. The app reads only these files;
it never needs the cache. CPU, no model inference, ~1 min.

Scenarios, all from held-out streams (results/replay_fleet_split.csv).
Selection rule fixed before looking at any output:
  normal_1, normal_2   held-out base sequences whose recorded full-frame
                       confluency crosses 50% (results/growth_backtest_truth.csv),
                       by sequence_id: the first, then the first from another
                       experiment
  contamination        first held-out contamination_onset stream by id
  stall                first held-out growth_stall stream by id
  dimming              the lamp_dimming twin of normal_1 (held-out with it)

Replay settings are the A2 fleet's (scripts/replay_fleet.py): 6 h mean cadence,
jitter ±25%, 3 FOVs of 0.25-frac crops, seed 0. Each stream is checked against
cache/replay_fleet/visits_6h_fov3.jsonl when that file exists.

Per visit:
  confluency   mean of the 3 FOVs; band = ±1 standard error of that mean,
               sigma_fov(pct) / sqrt(3) from configs/noise.yaml's C2C12 fit
               (culture.growth._sigma_fov_for_visit), the noise V2 compares to
  anomaly      the frame's A4 score and per-bin flag, looked up by sha in
               cache/anomaly/scores.parquet (held-out frames scored against the
               tuning banks, thresholds in configs/anomaly.yaml), as eval_spc.py
  quality      the cached quality gate; a fail is REIMAGE and leaves the trend
  post_onset   visit hours since stream start > the fault's onset_hours
No classifier fields: the classifier is demoted (configs/qc.yaml).

Passage forecast (target 50%, as Cellpose-SAM measures it): made once, at the
first quality-passing visit whose mean reaches the cut (target − 10), by
culture.growth.fit_growth on the quality-passing visits so far (seed 0,
configs/growth.yaml bootstrap), and held after that. This is the backtest's
procedure (scripts/backtest_growth.py::_outcome) plus the quality filter the
product's trend path applies; parity with results/growth_backtest.csv is
checked and reported for every scenario that has a backtest row. The caption's
numbers are read from that CSV (50%, target-10, 6 h, 3 crops).

Usage:
    python scripts/export_demo_replays.py --cache-dir cache
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys

import numpy as np
import pandas as pd
import yaml

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from culture import detectability  # noqa: E402
from culture.cache import Cache  # noqa: E402
from culture.growth import _load_yaml, _sigma_fov_for_visit, fit_growth  # noqa: E402
from culture.records import hash_file  # noqa: E402
from culture.replay import ReplayTables, build_replay_visits  # noqa: E402

CADENCE_H = 6.0
JITTER_FRAC = 0.25
N_FOV = 3
CROP_FRAC = 0.25
SEED = 0
TARGET_PCT = 50.0
CUT_OFFSET = 10.0
OUT_DIR = os.path.join(REPO, "demo", "replays")
BANNER = "Replay of recorded time-lapse (simulated visits and faults)"
CREDIT = ("C2C12 time-lapse: Ker, D.F.E. et al., Sci Data 5:180237 (2018), CC BY 4.0. "
          "Real recorded frames; visit times, FOV positions and faults are simulated.")
CONFIGS = ["anomaly.yaml", "detectability.yaml", "growth.yaml", "noise.yaml", "qc.yaml", "quality.yaml",
           "replay.yaml"]


def _r(x, nd=3):
    """Round for byte-stable JSON; None/NaN -> None."""
    if x is None:
        return None
    x = float(x)
    return None if math.isnan(x) else round(x, nd)


def _hours(visits: list[dict]) -> list[float]:
    t0 = pd.Timestamp(visits[0]["timestamp"])
    return [(pd.Timestamp(v["timestamp"]) - t0).total_seconds() / 3600.0 for v in visits]


def select_scenarios(split: pd.DataFrame, truth: pd.DataFrame) -> dict[str, dict]:
    held = split[split.split == "heldout"]
    crossing = set(truth[(truth.target_pct == TARGET_PCT) & truth.crosses].sequence_id)
    bases = held[(held.kind == "base") & held.sequence_id.isin(crossing)].sort_values("sequence_id")
    if bases.empty:
        raise SystemExit("no held-out base sequence crosses the target")
    n1 = bases.iloc[0]
    others = bases[bases.experiment != n1.experiment]
    if others.empty:
        raise SystemExit("no second held-out crossing sequence from another experiment")
    n2 = others.iloc[0]
    faults = held[held.kind == "fault"].sort_values("sequence_id")

    def first(fault_type):
        rows = faults[faults.fault_type == fault_type]
        if rows.empty:
            raise SystemExit(f"no held-out {fault_type} stream")
        return rows.iloc[0]

    dim = faults[(faults.fault_type == "lamp_dimming") & (faults.base_sequence_id == n1.sequence_id)]
    if dim.empty:
        raise SystemExit(f"no held-out lamp_dimming twin of {n1.sequence_id}")
    picks = {"normal_1": n1, "normal_2": n2, "contamination": first("contamination_onset"),
             "stall": first("growth_stall"), "dimming": dim.iloc[0]}
    return {k: {"stream_id": r.sequence_id, "base_sequence_id": r.base_sequence_id, "fault_type": r.fault_type,
                "experiment": str(r.experiment), "split": r.split} for k, r in picks.items()}


def backtest_row(bt: pd.DataFrame, sequence_id: str) -> dict | None:
    row = bt[(bt.sequence_id == sequence_id) & (bt.target_pct == TARGET_PCT) & (bt.cut == f"target-{CUT_OFFSET:g}")
             & (bt.cadence_h == CADENCE_H) & (bt.repositioning == "with_repositioning") & (bt.n_fov == N_FOV)]
    return None if row.empty else row.iloc[0].to_dict()


def backtest_caption(bt: pd.DataFrame) -> dict:
    cell = bt[(bt.target_pct == TARGET_PCT) & (bt.cut == f"target-{CUT_OFFSET:g}") & (bt.cadence_h == CADENCE_H)
              & (bt.repositioning == "with_repositioning") & (bt.n_fov == N_FOV)]
    pred = cell[cell.outcome == "predicted"]
    with_iv = pred[pred.covered.notna()]
    return {"n_sequences": int(len(cell)), "n_predicted": int(len(pred)),
            "median_abs_error_h": _r(pred.abs_error_hours.median(), 1),
            "interval_covers": f"{int(with_iv.covered.astype(bool).sum())}/{len(with_iv)}",
            "source": "results/growth_backtest.csv, 6 h cadence, 3 FOVs"}


def forecast(visits: list[dict], hours: list[float], quality_filter: bool = True) -> dict:
    cut = TARGET_PCT - CUT_OFFSET
    prefix = []
    for i, v in enumerate(visits):
        if quality_filter and not v["quality"]["pass"]:
            continue
        prefix.append(v)
        if v["confluency_mean"] >= cut:
            break
    else:
        return {"status": "cut_not_reached", "cut_pct": cut, "target_pct": TARGET_PCT}
    r = fit_growth(prefix, target_pct=TARGET_PCT, seed=SEED)
    out = {"cut_pct": cut, "target_pct": TARGET_PCT, "made_at_visit": i, "made_at_hours": _r(hours[i], 2),
           "n_visits_fit": len(prefix), "fit_status": r.status, "chosen_model": r.chosen_model}
    if r.status != "OK":
        return {**out, "status": f"fit_{r.status.lower()}"}
    if r.t_star_status != "REACHED":
        return {**out, "status": "not_reached"}
    iv = r.t_star_interval_hours
    return {**out, "status": "predicted", "t_star_hours": _r(r.t_star_hours, 2),
            "interval_hours": [_r(iv[0], 2), _r(iv[1], 2)] if iv else None,
            "fit_curve": {"hours": [_r(h, 2) for h in r.t_grid_hours],
                          "mean": [_r(y, 2) for y in r.y_grid["mean"]]}}


def captions(kind: str, onset: float | None, severity: float | None, matrix: dict) -> str:
    rows = {r["issue"]: r for r in matrix["rows"]}
    if kind == "normal":
        return "Recorded C2C12 sequence, held out from all tuning. No fault was added."
    if kind == "contamination_onset":
        return (f"Simulated contamination from {onset:.0f} h. {matrix['provenance_note']} Pasted bacteria also "
                "raise measured confluency, so the curve jumps at onset.")
    if kind == "growth_stall":
        return (f"Simulated growth slowdown from {onset:.0f} h: after onset the flask replays its own recorded "
                f"frames at {severity:.0%} speed. No flag is expected: growth stalls are not detectable at the "
                f"tested setup. {rows['Growth stall / slowdown']['evidence']}")
    if kind == "lamp_dimming":
        gate = next(c.strip() for c in rows["Instrument drift (illumination)"]["evidence"].split(";")
                    if "quality gate" in c)
        return (f"Simulated lamp dimming from {onset:.0f} h. The quality gate asks for a re-image on some dimmed "
                f"visits, not all: {gate}.")
    raise ValueError(kind)


def notes_for(kind: str, onset: float | None, summary: dict, fc: dict) -> list[str]:
    """What this particular replay shows that a viewer could misread, from its
    own counts. Explanations, never suppression rules."""
    out = []
    pre_flags, pre_reimage = summary["anomaly_flags_before_onset"], summary["reimage_before_onset"]
    n_pre = summary["n_visits"] - (summary["n_post_onset_visits"] or 0)
    if pre_flags:
        out.append(f"{pre_flags} of {n_pre} visits {'before onset ' if onset is not None else ''}"
                   f"{'raises' if pre_flags == 1 else 'raise'} an anomaly "
                   "flag with no fault present: false alarms. Thresholds allow about 5% on tuning normals, and "
                   "calibration does not transfer across experiments (results/anomaly_summary.md).")
    if pre_reimage:
        out.append(f"{pre_reimage} of {n_pre} visits {'before onset ' if onset is not None else ''}fail the quality "
                   "gate with no fault present: false re-image requests, left out of the trend "
                   "(results/quality_gate_c2c12.md).")
    if fc["status"] == "cut_not_reached":
        out.append(f"No passage forecast: the visits that pass the quality gate never reach {fc['cut_pct']:.0f}% "
                   "(target − 10), where a forecast is first made.")
    if kind == "contamination_onset" and fc["status"] == "predicted" and fc["made_at_hours"] > onset:
        out.append("The passage forecast here is made after onset and is driven by the pasted bacteria raising "
                   "measured confluency, not by growth.")
    return out


def build(cache_dir: str) -> tuple[dict[str, dict], list[str]]:
    split = pd.read_csv(os.path.join(REPO, "results", "replay_fleet_split.csv"))
    truth = pd.read_csv(os.path.join(REPO, "results", "growth_backtest_truth.csv"))
    bt = pd.read_csv(os.path.join(REPO, "results", "growth_backtest.csv"))
    manifest = pd.read_parquet(os.path.join(cache_dir, "sidecars", "fault_manifest.parquet"))
    scores = pd.read_parquet(os.path.join(cache_dir, "anomaly", "scores.parquet")).drop_duplicates("image_sha256")
    scores = scores.set_index("image_sha256")
    anomaly_cfg = _load_yaml(os.path.join(REPO, "configs", "anomaly.yaml"))
    noise_cfg = _load_yaml(os.path.join(REPO, "configs", "noise.yaml"))
    growth_cfg = _load_yaml(os.path.join(REPO, "configs", "growth.yaml"))
    matrix = detectability.load()
    fleet_path = os.path.join(cache_dir, "replay_fleet", f"visits_{CADENCE_H:g}h_fov{N_FOV}.jsonl")
    fleet = {}
    if os.path.exists(fleet_path):
        for line in open(fleet_path):
            v = json.loads(line)
            fleet.setdefault(v["flask_id"], []).append(v)

    cache = Cache(cache_dir)
    tables = ReplayTables(cache)
    bt_caption = backtest_caption(bt)
    hashes = {name: hash_file(os.path.join(REPO, "configs", name)) for name in CONFIGS}
    notes, out = [], {}
    for name, sc in select_scenarios(split, truth).items():
        sid, kind = sc["stream_id"], sc["fault_type"]
        frames = None if kind == "none" else manifest[manifest.fault_sequence_id == sid]
        onset = None if frames is None else float(frames.onset_hours.iloc[0])
        severity = None if frames is None else float(frames[frames.is_modified.astype(bool) | (
            frames.hours_since_start > onset)].severity.dropna().iloc[0])
        visits = build_replay_visits(cache, sid, lineage_id=sc["base_sequence_id"], segment_id="S1", flask_id=sid,
                                     seed=SEED, frames=frames, tables=tables, mean_interval_hours=CADENCE_H,
                                     jitter_hours=JITTER_FRAC * CADENCE_H, n_fov=N_FOV, crop_frac=CROP_FRAC)
        if sid in fleet:
            key = lambda v: (v["timestamp"], v["crop_specs"], v["confluency_mean"])  # noqa: E731
            if [key(v) for v in fleet[sid]] != [key(v) for v in visits]:
                raise AssertionError(f"{sid}: differs from the A2 fleet stream in {fleet_path}")
            notes.append(f"{name}: matches the A2 fleet stream ({len(visits)} visits)")
        else:
            notes.append(f"{name}: no A2 fleet file to compare against")
        hours = _hours(visits)

        rows, missing = [], 0
        for i, (v, h) in enumerate(zip(visits, hours)):
            sha = v["image_sha256"][0]
            a = scores.loc[sha] if sha in scores.index else None
            missing += a is None
            bin_label = None if a is None else a.bin_label
            se = _sigma_fov_for_visit(v, noise_cfg, growth_cfg["fallback_crop_frac"]) / math.sqrt(v["n_fov"])
            rows.append({
                "visit": i, "hours": _r(h, 2), "timestamp": v["timestamp"],
                "confluency_mean": _r(v["confluency_mean"], 2), "confluency_sd": _r(v["confluency_sd"], 2),
                "fov_confluency": [_r(p, 2) for p in v["fov_confluency"]], "noise_se": _r(se, 2),
                "quality_pass": bool(v["quality"]["pass"]), "quality_reasons": list(v["quality"]["reasons"]),
                "reimage": not v["quality"]["pass"],
                "anomaly_score": None if a is None else _r(a.score_binned, 4),
                "anomaly_z": None if a is None else _r(a.z_binned, 2),
                "anomaly_bin": bin_label,
                "anomaly_threshold": None if a is None else _r(anomaly_cfg["calibration"]["bins"][bin_label]["threshold"], 4),
                "anomaly_flag": None if a is None else bool(a.flag_binned),
                "post_onset": None if onset is None else bool(h > onset),
                "source_frame_idx": v["source_frame_idx"], "image_sha256": sha,
            })
        if missing:
            notes.append(f"{name}: {missing} visits have no anomaly score")

        fc = forecast(visits, hours)
        fc["backtest"] = bt_caption
        bt_row = backtest_row(bt, sc["base_sequence_id"]) if kind == "none" else None
        if bt_row is not None:
            unfiltered = forecast(visits, hours, quality_filter=False)
            same = (unfiltered.get("made_at_visit") is not None and bt_row.get("n_visits_fit") == unfiltered.get(
                "made_at_visit") + 1 and np.isclose(unfiltered.get("t_star_hours") or np.nan,
                                                    bt_row.get("predicted_hours") or np.nan, atol=0.01))
            fc["backtest_parity"] = {"backtest_predicted_hours": _r(bt_row.get("predicted_hours"), 2),
                                     "unfiltered_t_star_hours": unfiltered.get("t_star_hours"),
                                     "unfiltered_matches_backtest": bool(same),
                                     "quality_filter_changes_forecast": fc.get("t_star_hours") != unfiltered.get(
                                         "t_star_hours")}
            notes.append(f"{name}: backtest parity {'ok' if same else 'MISMATCH'}; quality filter "
                         f"{'changes' if fc['backtest_parity']['quality_filter_changes_forecast'] else 'does not change'}"
                         " the forecast")
        tr = truth[(truth.sequence_id == sc["base_sequence_id"]) & (truth.target_pct == TARGET_PCT)]
        true_h = _r(tr.true_hours.iloc[0], 2) if len(tr) and bool(tr.crosses.iloc[0]) else None

        post = [r for r in rows if r["post_onset"]]
        pre = [r for r in rows if r["post_onset"] is False or r["post_onset"] is None]
        summary = {
            "n_visits": len(rows),
            "anomaly_flags_before_onset": sum(bool(r["anomaly_flag"]) for r in pre),
            "anomaly_flags_after_onset": sum(bool(r["anomaly_flag"]) for r in post) if onset is not None else None,
            "first_flag_after_onset_visit": next((j + 1 for j, r in enumerate(post) if r["anomaly_flag"]), None),
            "reimage_before_onset": sum(r["reimage"] for r in pre),
            "reimage_after_onset": sum(r["reimage"] for r in post) if onset is not None else None,
            "n_post_onset_visits": len(post) if onset is not None else None,
        }
        out[name] = {
            "scenario": name, "stream_id": sid, "base_sequence_id": sc["base_sequence_id"],
            "experiment": sc["experiment"], "split": sc["split"],
            "fault": None if onset is None else {"type": kind, "onset_hours": _r(onset, 2)},
            "banner": BANNER, "caption": captions("normal" if kind == "none" else kind, onset, severity, matrix),
            "notes": notes_for(kind, onset, summary, fc),
            "credit": CREDIT,
            "replay_params": {"mean_interval_hours": CADENCE_H, "jitter_hours": JITTER_FRAC * CADENCE_H,
                              "n_fov": N_FOV, "crop_frac": CROP_FRAC, "seed": SEED},
            "noise_band": "±1 standard error of the 3-FOV mean: sigma_fov(confluency) / sqrt(3), "
                          "configs/noise.yaml C2C12 fit (the noise V2 compares one visit's growth to)",
            "anomaly_source": "cache/anomaly/scores.parquet (A4, held-out frames vs tuning banks); "
                              "per-bin thresholds at 5% FPR on tuning normals, configs/anomaly.yaml",
            "recorded_crossing_hours": true_h,
            "forecast": fc, "summary": summary, "visits": rows,
            "provenance": "replay_simulated", "config_hashes": hashes,
            "model_versions": visits[0]["model_versions"],
            "generated_by": "scripts/export_demo_replays.py",
        }
    return out, notes


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cache-dir", default="cache")
    ap.add_argument("--out-dir", default=OUT_DIR)
    args = ap.parse_args()
    out, notes = build(args.cache_dir)
    os.makedirs(args.out_dir, exist_ok=True)
    for name, doc in out.items():
        with open(os.path.join(args.out_dir, f"{name}.json"), "w") as f:
            json.dump(doc, f, indent=1, sort_keys=True, ensure_ascii=False)
            f.write("\n")
    for n in notes:
        print(n)
    for name, doc in out.items():
        fc, s = doc["forecast"], doc["summary"]
        print(f"{name:14s} {doc['stream_id']:42s} visits={s['n_visits']:2d} "
              f"flags pre/post={s['anomaly_flags_before_onset']}/{s['anomaly_flags_after_onset']} "
              f"reimage pre/post={s['reimage_before_onset']}/{s['reimage_after_onset']} "
              f"forecast={fc['status']} at={fc.get('made_at_hours')} t*={fc.get('t_star_hours')} "
              f"iv={fc.get('interval_hours')} truth={doc['recorded_crossing_hours']} onset="
              f"{(doc['fault'] or {}).get('onset_hours')}")


if __name__ == "__main__":
    main()
