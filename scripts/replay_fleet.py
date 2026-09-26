"""
A2 replay fleet (cultureQC_upgrade_spec.md §2A.3): every C2C12 sequence and
every fault sequence from fault_manifest.parquet, replayed from the compute
cache at 6 h and 12 h mean cadence (jitter ±25%) with 1 and 3 FOVs per visit.
CPU only, no model inference.

Split: seeded, by base sequence, stratified by the fault type built on each
base (split_sequences(strata=fault_strata(...))), so contamination and growth
stall reach both sides. Fault twins follow their base. The split is written
to results/replay_fleet_split.csv; later phases (A1, A4, A6) read that file
rather than recompute it.

Every stream uses the same seed, so a fault twin and its base sample the same
visit times and the same crops until onset (checked here, reported).

FOVs: every visit samples crops of one size (--crop-frac, default 0.25) so
confluency_sd and sigma_fov refer to one FOV size.

Outputs:
    cache/replay_fleet/visits_<cadence>h_fov<n>.jsonl   all visits, both splits (gitignored; regenerable)
    results/replay_fleet_split.csv                      base + fault sequence -> tuning/heldout
    results/replay_fleet_streams.csv                    one row per stream x cadence x n_fov
    results/replay_fleet_summary.md                     counts for both splits; rates on held-out only

Usage:
    python scripts/replay_fleet.py --cache-dir cache
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import yaml

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from culture.cache import Cache  # noqa: E402
from culture.replay import ReplayTables, build_replay_visits, fault_split, fault_strata, split_sequences  # noqa: E402

CADENCES = (6.0, 12.0)
JITTER_FRAC = 0.25
N_FOVS = (1, 3)
with open(os.path.join(REPO, "configs", "growth.yaml")) as _f:
    MIN_GROWTH_VISITS = yaml.safe_load(_f)["minimum_data"]["min_visits"]  # culture/growth.py's minimum for a fit


def _stream_specs(seqs: pd.DataFrame, manifest: pd.DataFrame, split: dict[str, str]) -> list[dict]:
    exp = dict(zip(seqs.sequence_id, seqs.experiment))
    specs = [{"stream_id": sid, "base_sequence_id": sid, "fault_type": "none", "onset_hours": np.nan,
              "split": split[sid], "experiment": exp[sid]} for sid in sorted(seqs.sequence_id)]
    faults = manifest[["fault_sequence_id", "base_sequence_id", "fault_type", "onset_hours"]].drop_duplicates(
        "fault_sequence_id")
    for r in faults.sort_values("fault_sequence_id").itertuples():
        specs.append({"stream_id": r.fault_sequence_id, "base_sequence_id": r.base_sequence_id,
                      "fault_type": r.fault_type, "onset_hours": float(r.onset_hours),
                      "split": split[r.fault_sequence_id], "experiment": exp[r.base_sequence_id]})
    return specs


def _replay(cache, tables, manifest, spec, seed, cadence, n_fov, crop_frac):
    frames = None if spec["fault_type"] == "none" else manifest[manifest.fault_sequence_id == spec["stream_id"]]
    return build_replay_visits(cache, spec["stream_id"], lineage_id=spec["base_sequence_id"],
                               segment_id="S1", flask_id=spec["stream_id"], seed=seed, frames=frames,
                               tables=tables, mean_interval_hours=cadence,
                               jitter_hours=JITTER_FRAC * cadence, n_fov=n_fov, crop_frac=crop_frac)


def _pre_onset_matches(base: list[dict], twin: list[dict], onset_hours: float) -> bool:
    """A twin's visits before onset are its base's visits: same times, frames, crops."""
    t0 = pd.Timestamp(base[0]["timestamp"])
    key = lambda v: (v["timestamp"], v["image_sha256"][0], tuple(v["crop_specs"]))  # noqa: E731
    pre = lambda vs: [key(v) for v in vs if (pd.Timestamp(v["timestamp"]) - t0).total_seconds() / 3600 < onset_hours]  # noqa: E731
    return len(pre(twin)) > 0 and pre(base) == pre(twin)


def _rates(visits: list[dict]) -> dict:
    preds = pd.Series([v["class_pred"] for v in visits]).value_counts()
    return {"n_visits": len(visits),
            "class_pred": {k: int(n) for k, n in preds.items()},
            "quality_pass": int(sum(bool(v["quality"]["pass"]) for v in visits)),
            "gate_reasons": dict(pd.Series([r for v in visits for r in v["quality"]["reasons"]],
                                           dtype=object).value_counts().astype(int))}


def _pct(n, d):
    return f"{n}/{d} ({100 * n / d:.0f}%)" if d else "0/0"


def write_summary(path, args, specs, streams, split_df, pairing, heldout_rates, cadence24, generated_at):
    base = [s for s in specs if s["fault_type"] == "none"]
    lines = [
        "# A2 replay fleet",
        "",
        f"Generated {generated_at} by `scripts/replay_fleet.py` from `{args.cache_dir}`; seed {args.seed}, "
        f"split seed {args.split_seed}, crop_frac {args.crop_frac}. Visits are replayed from the compute cache "
        "(C2C12 time-lapse, Ker et al. 2018, CC BY 4.0; fault sequences are simulated from it). "
        "No model runs at replay time.",
        "",
        "## Split",
        "",
        f"By base sequence, stratified by the fault type built on it, {args.tuning_frac:.0%} tuning. "
        "Fault twins follow their base. Tuning is for fitting thresholds only; nothing below reports a rate on it.",
        "",
        "| stratum | tuning | held-out |",
        "|---|---|---|",
    ]
    ct = pd.crosstab(split_df[split_df.kind == "base"].stratum, split_df[split_df.kind == "base"].split)
    for stratum, row in ct.iterrows():
        lines.append(f"| {stratum} (base sequences) | {row.get('tuning', 0)} | {row.get('heldout', 0)} |")
    ft = pd.crosstab(split_df[split_df.kind == "fault"].fault_type, split_df[split_df.kind == "fault"].split)
    for ftype, row in ft.iterrows():
        lines.append(f"| {ftype} (fault sequences) | {row.get('tuning', 0)} | {row.get('heldout', 0)} |")
    ex = pd.crosstab(split_df[split_df.kind == "base"].experiment, split_df[split_df.kind == "base"].split)
    lines += ["", "Base sequences per experiment: " + "; ".join(
        f"{e}: {row.get('tuning', 0)} tuning / {row.get('heldout', 0)} held-out" for e, row in ex.iterrows()) + ".",
        "", "Held-out fault sequences: " + ", ".join(
            f"{t} {int(n)}" for t, n in ft.get("heldout", pd.Series(dtype=int)).items())
        + ". A detection rate on a type is over that many sequences.",
        "", "## Visits per stream", "",
        f"Jitter ±{JITTER_FRAC:.0%} of the mean interval. The growth model needs at least {MIN_GROWTH_VISITS} visits.",
        "", f"| cadence | FOVs | streams | visits per stream (min / median / max) | streams below {MIN_GROWTH_VISITS} visits |",
        "|---|---|---|---|---|"]
    for (cad, nf), g in streams.groupby(["cadence_h", "n_fov"]):
        lines.append(f"| {cad:g} h | {nf} | {len(g)} | {g.n_visits.min()} / {g.n_visits.median():g} / "
                     f"{g.n_visits.max()} | {int((g.n_visits < MIN_GROWTH_VISITS).sum())} |")
    below = cadence24["n_below_min"]
    lines += ["", f"24 h cadence (jitter ±6 h, measured on the {len(base)} base sequences, 1 FOV): "
              f"{cadence24['min']}–{cadence24['max']} visits per stream, median {cadence24['median']:g}; "
              f"{below} of {len(base)} below the growth model's minimum of {MIN_GROWTH_VISITS}. "
              f"A backtest cut point or a one-step-ahead prediction fits only the visits before it, so with at "
              f"most {cadence24['max']} visits it never has {MIN_GROWTH_VISITS} before the one it scores: "
              "24 h is reported as **not testable on the C2C12 span** (spec §2A.3). "
              "Celltrio's real cadence is an open question.",
              "", "## Fault twins match their base before onset", "",
              "Same seed for every stream, so a twin should repeat its base's visits (time, frame, crops) until onset.",
              "", "| fault type | twins that match, over all cadence × FOV cells |", "|---|---|"]
    for ftype, (ok, n) in sorted(pairing.items()):
        lines.append(f"| {ftype} | {ok}/{n} |")
    lines += ["", "## Held-out rates (6 h, 1 FOV)", "",
              "Per visit, so visits within a stream are not independent: n sequences is the sample size.",
              "Class probabilities are temperature-scaled (configs/calibration.yaml, fit on synthetic tiles).", "",
              "| streams | sequences | visits | quality gate pass | QC class_pred |", "|---|---|---|---|---|"]
    for label, r in heldout_rates.items():
        preds = ", ".join(f"{k} {_pct(n, r['n_visits'])}" for k, n in sorted(r["class_pred"].items()))
        lines.append(f"| {label} | {r['n_sequences']} | {r['n_visits']} | {_pct(r['quality_pass'], r['n_visits'])} "
                     f"| {preds} |")
    lines += ["", "Fault rows count visits after onset (`fault.hours_since_start > onset_hours`). Growth-stall "
              "frames are real earlier frames replayed on a slowed clock, so they are never `is_modified`.", "",
              "Quality gate reasons on the held-out normal visits (a visit can fail several): " + ", ".join(
                  f"{k} {v}" for k, v in heldout_rates["normal (base)"]["gate_reasons"].items()) + ". "
              "The gate's thresholds (configs/quality.yaml) were calibrated on synthetic tiles.", ""]
    with open(path, "w") as f:
        f.write("\n".join(lines))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cache-dir", default="cache")
    ap.add_argument("--seed", type=int, default=0, help="replay seed, same for every stream")
    ap.add_argument("--split-seed", type=int, default=0)
    ap.add_argument("--tuning-frac", type=float, default=0.4)
    ap.add_argument("--crop-frac", type=float, default=0.25)
    ap.add_argument("--visits-out", default=None, help="default: <cache-dir>/replay_fleet")
    ap.add_argument("--out", default=os.path.join(REPO, "results"))
    args = ap.parse_args()

    side = os.path.join(args.cache_dir, "sidecars")
    seqs = pd.read_csv(os.path.join(side, "c2c12_sequences.csv"))
    manifest = pd.read_parquet(os.path.join(side, "fault_manifest.parquet"))
    strata = fault_strata(manifest)
    base_split = split_sequences(seqs.sequence_id, seed=args.split_seed, tuning_frac=args.tuning_frac, strata=strata)
    split = {**base_split, **fault_split(manifest, base_split)}
    specs = _stream_specs(seqs, manifest, split)

    visits_out = args.visits_out or os.path.join(args.cache_dir, "replay_fleet")
    os.makedirs(visits_out, exist_ok=True)
    os.makedirs(args.out, exist_ok=True)

    cache = Cache(args.cache_dir)
    tables = ReplayTables(cache)
    rows, pairing, cells = [], {}, {}
    for cadence in CADENCES:
        for n_fov in N_FOVS:
            by_stream = {}
            path = os.path.join(visits_out, f"visits_{cadence:g}h_fov{n_fov}.jsonl")
            with open(path, "w") as f:
                for spec in specs:
                    visits = _replay(cache, tables, manifest, spec, args.seed, cadence, n_fov, args.crop_frac)
                    by_stream[spec["stream_id"]] = visits
                    for v in visits:
                        f.write(json.dumps({**v, "fleet_split": spec["split"]}) + "\n")
                    t0 = pd.Timestamp(visits[0]["timestamp"])
                    rows.append({**spec, "cadence_h": cadence, "jitter_h": JITTER_FRAC * cadence, "n_fov": n_fov,
                                 "crop_frac": args.crop_frac, "seed": args.seed, "n_visits": len(visits),
                                 "span_hours": (pd.Timestamp(visits[-1]["timestamp"]) - t0).total_seconds() / 3600,
                                 "source_dataset": visits[0]["source_dataset"]})
            for spec in specs:
                if spec["fault_type"] == "none":
                    continue
                ok = _pre_onset_matches(by_stream[spec["base_sequence_id"]], by_stream[spec["stream_id"]],
                                        spec["onset_hours"])
                a, n = pairing.get(spec["fault_type"], (0, 0))
                pairing[spec["fault_type"]] = (a + ok, n + 1)
            cells[(cadence, n_fov)] = by_stream
            print(f"{cadence:g} h, {n_fov} FOV: {sum(len(v) for v in by_stream.values())} visits -> {path}")

    streams = pd.DataFrame(rows)
    streams.to_csv(os.path.join(args.out, "replay_fleet_streams.csv"), index=False)
    split_df = pd.DataFrame([{"sequence_id": s["stream_id"], "kind": "base" if s["fault_type"] == "none" else "fault",
                              "base_sequence_id": s["base_sequence_id"], "fault_type": s["fault_type"],
                              "stratum": strata.get(s["base_sequence_id"], "none"), "experiment": s["experiment"],
                              "split": s["split"]} for s in specs])
    split_df.to_csv(os.path.join(args.out, "replay_fleet_split.csv"), index=False)

    held = [s for s in specs if s["split"] == "heldout"]
    ref = cells[(6.0, 1)]
    heldout_rates = {}
    groups = [("normal (base)", [s for s in held if s["fault_type"] == "none"])]
    groups += [(f"{t} after onset", [s for s in held if s["fault_type"] == t])
               for t in sorted({s["fault_type"] for s in held} - {"none"})]
    for label, group in groups:
        vs = [v for s in group for v in ref[s["stream_id"]]]
        if label != "normal (base)":
            vs = [v for v in vs if v["fault"]["hours_since_start"] > v["fault"]["onset_hours"]]
        heldout_rates[label] = {**_rates(vs), "n_sequences": len(group)}

    n24 = [len(_replay(cache, tables, manifest, s, args.seed, 24.0, 1, args.crop_frac))
           for s in specs if s["fault_type"] == "none"]
    cadence24 = {"min": int(min(n24)), "max": int(max(n24)), "median": float(np.median(n24)),
                 "n_below_min": int(sum(n < MIN_GROWTH_VISITS for n in n24))}

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    write_summary(os.path.join(args.out, "replay_fleet_summary.md"), args, specs, streams, split_df, pairing,
                  heldout_rates, cadence24, generated_at)
    print(f"wrote {args.out}/replay_fleet_{{split,streams}}.csv, replay_fleet_summary.md")


if __name__ == "__main__":
    main()
