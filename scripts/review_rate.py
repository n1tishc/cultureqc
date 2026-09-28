#!/usr/bin/env python3
"""
How often the rules send an image to human review. With the classifier
demoted, two rules can (culture/rules.py, rules_v0.3):
  - the confidence floor (rule 2): the confluency measurement itself is
    uncertain (confidence below the line's floor, 0.30 by default);
  - the anomaly hold (rule 3, since v0.3): confluency is at or above the
    target but the per-image anomaly check flagged the image, so the passage
    is held for review. This depends on the target, so it is reported at the
    default 80% and at the replays' 50%.
The quality gate returns REIMAGE (results/quality_gate_c2c12.md), not review,
so it is not counted.

No model runs: the confidence is the one the compute cache stored with each
frame's Cellpose-SAM confluency, and the anomaly flag is A4's
(cache/anomaly/scores.parquet: held-out frames against the tuning banks, which
are the deployed ones; tuning frames against banks without their own
sequence) (cache/confluency.parquet, cpsam_v2 on Colab
GPU, nb/03), computed at full resolution with the same formula as the live
path (culture/seg.py). C2C12 base sequences are split as in
results/replay_fleet_split.csv; the floor was not set on C2C12, so both halves
are out of sample for it, and the tuning half is shown only for comparison.

    python scripts/review_rate.py

Writes results/review_rate.md and results/review_rate.csv (one row per group).
"""

from __future__ import annotations

import csv
import json
import os
import sys
import time

import pandas as pd

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from culture.rules import DEFAULT_CONFIG, RULES_VERSION  # noqa: E402

CACHE = os.path.join(REPO, "cache")
RESULTS = os.path.join(REPO, "results")
BINS = [0, 20, 40, 60, 80, 100.01]
CROP_FRAC = 0.25
TARGETS = (80.0, 50.0)               # the default target, and the replays' (results/growth_backtest.md)


def rate(df: pd.DataFrame, floor: float) -> dict:
    n = len(df)
    k = int((df.confidence < floor).sum())
    return {"n": n, "n_review": k, "review_pct": round(100 * k / n, 1) if n else None}


def main():
    floor = DEFAULT_CONFIG.confluency_confidence_floor
    conf = pd.read_parquet(os.path.join(CACHE, "confluency.parquet"))
    conf = conf[(conf.model_name == "seg") & (conf.model_version == "cpsam_v2")]
    images = pd.read_parquet(os.path.join(CACHE, "images.parquet"))[["image_sha256", "dataset", "sequence_id"]]
    split = pd.read_csv(os.path.join(RESULTS, "replay_fleet_split.csv"))
    split = split[split.kind == "base"].set_index("sequence_id")["split"]

    full = conf[conf.crop_spec == "full"].merge(images, on="image_sha256", how="left", validate="one_to_one")
    assert full.dataset.notna().all()
    c2 = full[full.dataset == "c2c12"].copy()
    c2["split"] = c2.sequence_id.map(split)
    assert c2.split.notna().all(), "C2C12 frame outside the replay split"

    rows = []

    def add(group, df, note=""):
        r = rate(df, floor)
        seqs = df.sequence_id.replace("", pd.NA).dropna().nunique()
        rows.append({"group": group, "sequences": seqs, **r, "note": note})

    add("C2C12 held-out, full frames", c2[c2.split == "heldout"])
    add("C2C12 tuning, full frames", c2[c2.split == "tuning"], "comparison only")
    held = c2[c2.split == "heldout"]
    cut = pd.cut(held.pct, BINS, right=False, labels=["0-20", "20-40", "40-60", "60-80", "80-100"])
    for label in cut.cat.categories:
        if (cut == label).any():
            add(f"C2C12 held-out, confluency {label}%", held[cut == label])
    add("EVICAN eval2019 (real, expert masks)", full[full.dataset == "evican_eval2019"])
    add("C2C12 simulated lamp dimming", full[full.dataset == "c2c12_fault_dim"], "simulated fault frames")
    add("C2C12 simulated contamination, bacteria 16.5× too large", full[full.dataset == "c2c12_fault_contam"],
        "simulated fault frames; at real size see results/contamination_scale.md")

    crops = conf[conf.crop_spec.str.startswith(f"crop_f{CROP_FRAC}_")].merge(images, on="image_sha256")
    crops = crops[crops.dataset == "c2c12"].copy()
    crops["split"] = crops.sequence_id.map(split)
    add(f"C2C12 held-out, {CROP_FRAC:g}-frame FOV crops", crops[crops.split == "heldout"],
        "each crop segmented on its own, as the replay visits are")

    # Anomaly hold: frames with an A4 anomaly score, joined to their cached confidence.
    scores = pd.read_parquet(os.path.join(CACHE, "anomaly", "scores.parquet"))[
        ["image_sha256", "kind", "split", "flag_binned"]]
    scored = scores.merge(full[["image_sha256", "pct", "confidence"]], on="image_sha256", how="left",
                          validate="one_to_one")
    assert scored.confidence.notna().all()
    groups = [("C2C12 held-out, normal", (scored.kind == "normal") & (scored.split == "heldout")),
              ("C2C12 tuning, normal (comparison only)", (scored.kind == "normal") & (scored.split == "tuning")),
              ("C2C12 simulated contamination, bacteria 16.5× too large", scored.kind == "contamination_onset"),
              ("C2C12 simulated lamp dimming", scored.kind == "lamp_dimming")]
    hold_rows = []
    for target in TARGETS:
        for name, mask in groups:
            g = scored[mask]
            low = g.confidence < floor
            eligible = (~low) & (g.pct >= target)
            held_back = eligible & g.flag_binned
            n = len(g)
            hold_rows.append({"target": target, "group": name, "n": n, "floor": int(low.sum()),
                              "eligible": int(eligible.sum()), "hold": int(held_back.sum()),
                              "total": int((low | held_back).sum()),
                              "total_pct": round(100 * int((low | held_back).sum()) / n, 1)})

    per_seq = {s: rate(g, floor)["review_pct"] for s, g in held.groupby("sequence_id")}
    dense = held[held.pct >= 40]
    per_seq_dense = {s: rate(g, floor) for s, g in dense.groupby("sequence_id")}

    with open(os.path.join(RESULTS, "review_rate.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    lines = [
        "# Human-review rate: confidence floor and anomaly hold", "",
        f"Generated {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} by `scripts/review_rate.py`. "
        "No model runs: confidences are the compute cache's (Cellpose-SAM cpsam_v2, Colab GPU, nb/03), "
        "full resolution, same formula as the live path. C2C12 images: Ker et al., *Sci Data* 5:180237 (2018), "
        "CC BY 4.0; fault frames are simulated from them.", "",
        f"Rules: `{RULES_VERSION}`. With the classifier demoted, two rules return `human_review`: confidence "
        f"below the floor ({floor:.2f}, `culture/rules.py` default), and, since `rules_v0.3`, the anomaly hold "
        "(confluency at or above the target, but the anomaly check flagged the image). Quality-gate failures "
        "return REIMAGE (`results/quality_gate_c2c12.md`). Frames within a sequence are not independent; "
        "n sequences is the sample size.", "",
        "## Confidence floor", "",
        "| group | sequences | images | sent to review | note |", "|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(f"| {r['group']} | {r['sequences'] or '—'} | {r['n']} | {r['n_review']} ({r['review_pct']}%) "
                     f"| {r['note'] or '—'} |")
    lines += ["", "Held-out C2C12 review rate per sequence: " + ", ".join(
        f"{s.replace('c2c12_', '').replace('_Data', '')} {v:g}%" for s, v in sorted(per_seq.items())) + ".", "",
              f"Highest held-out C2C12 confluency: {held.pct.max():.1f}%, so no frame reaches the 60-100% bins. "
              "Held-out frames at 40% or more, per sequence (sent to review / frames): " + ", ".join(
                  f"{s.replace('c2c12_', '').replace('_Data', '')} {r['n_review']}/{r['n']}"
                  for s, r in sorted(per_seq_dense.items())) + ".", "",
              "## Anomaly hold (rules_v0.3)", "",
              "Frames with an anomaly score (A4). Passage-eligible: confidence at or above the floor and confluency "
              "at or above the target (time since passage assumed long enough). Held: passage-eligible and "
              "flagged, so sent to review instead of passage. Total: floor or held.", "",
              "| target | group | images | below floor | passage-eligible | held by the anomaly flag | total to review |",
              "|---|---|---|---|---|---|---|"]
    for r in hold_rows:
        lines.append(f"| {r['target']:g}% | {r['group']} | {r['n']} | {r['floor']} | {r['eligible']} | {r['hold']} "
                     f"| {r['total']} ({r['total_pct']}%) |")
    lines.append("")
    with open(os.path.join(RESULTS, "review_rate.md"), "w") as f:
        f.write("\n".join(lines))
    print("\n".join(lines))
    print(json.dumps({"floor": floor, "groups": len(rows)}))


if __name__ == "__main__":
    main()
