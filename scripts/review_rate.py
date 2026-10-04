#!/usr/bin/env python3
"""
How often the rules send an image to human review.

Since rules_v0.5 (culture/rules.py), with the classifier demoted, a reading
goes to review when its setup's 90% error band includes the target (the
reading can't tell which side of the target the flask is on), when it is at
or above the target but the anomaly check flagged the image, or when its
setup has no calibration profile and it is at or above the target. The
C2C12 frames are read with the profile configs/confluency_profiles.yaml gives
the demo microscope (`c2c12_ker2018`, or `uncalibrated` if it is not
validated): its cutoff applied to the cached map, its band to the reading.

For comparison, the rules_v0.4 triggers, with the classifier demoted:
  - the boundary-ambiguity trigger (rule 2): many pixels sit near the
    Cellpose-SAM cutoff (the record's confidence below the line's floor, 0.30
    by default; boundary ambiguity above 0.70). It is a density-sensitive
    review trigger and does not predict the reading's error
    (results/confidence_vs_error.md);
  - the passage hold (rule 3, since v0.3): confluency is at or above the
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

Writes results/review_rate.md, results/review_rate_v05.csv (the current rules: one row per
target and group) and results/review_rate.csv (the rules_v0.4 boundary-ambiguity trigger, one row
per group, kept for comparison).
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

import numpy as np  # noqa: E402

from culture.profiles import get_profile  # noqa: E402
from culture.quality import evaluate_thresholds  # noqa: E402
from culture.rules import DEFAULT_CONFIG, RULES_VERSION  # noqa: E402

CACHE = os.path.join(REPO, "cache")
RESULTS = os.path.join(REPO, "results")
BINS = [0, 20, 40, 60, 80, 100.01]
CROP_FRAC = 0.25
TARGETS = (80.0, 50.0)               # the default target, and the replays' (results/growth_backtest.md)
C2C12_PROFILE = "c2c12_ker2018"


def reading_at(sha: str, cutoff: float, pct0: float) -> float:
    """The frame's reading at `cutoff`: the cached full-resolution reading at 0.0, otherwise the
    cached map (1/4 resolution, logit × 1000; within 0.15 pp of full resolution on the examples)."""
    if cutoff == 0.0:
        return pct0
    m = np.load(os.path.join(CACHE, "probmaps", f"{sha}.npz"))["prob_x1000"]
    return float((m > round(cutoff * 1000)).mean() * 100)


def v05(g: pd.DataFrame, target: float, band: float | None) -> dict:
    """rules_v0.5 on readings `g.reading`, flags `g.flag_binned` and the quality gate `g.gate_pass`
    (a failed gate is REIMAGE, before any reading is used; time since passage assumed long enough)."""
    reimage = ~g.gate_pass
    g = g[g.gate_pass]
    r, flag = g.reading, g.flag_binned
    if band is None:
        straddle = pd.Series(False, index=g.index)
        above = r >= target
        passage = pd.Series(False, index=g.index)
        review = above
    else:
        above = (r - band) >= target
        straddle = (~above) & ((r + band) >= target)
        passage = above & ~flag
        review = straddle | (above & flag)
    n = len(g) + int(reimage.sum())
    return {"n": n, "reimage": int(reimage.sum()), "band_review": int(straddle.sum()), "held": int((above & flag).sum()) if band is not None else 0,
            "uncalibrated_review": int(review.sum()) if band is None else 0, "passage": int(passage.sum()),
            "review": int(review.sum()), "review_pct": round(100 * int(review.sum()) / n, 1) if n else None}


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

    # Passage hold: frames with an A4 anomaly score, joined to their cached confidence.
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

    prof = get_profile(C2C12_PROFILE)
    scored["reading"] = [reading_at(sha, prof.cutoff, p) for sha, p in zip(scored.image_sha256, scored.pct)]
    if prof.quality:
        qm = pd.read_parquet(os.path.join(CACHE, "quality.parquet")).set_index("image_sha256")
        assert scored.image_sha256.isin(qm.index).all(), "frame without cached quality metrics"
        scored["gate_pass"] = [evaluate_thresholds(*qm.loc[sha, ["blur_laplacian_var", "exposure_mean",
                                                                 "uniformity_block_std"]], dataset=prof.quality).passed
                               for sha in scored.image_sha256]
    else:
        scored["gate_pass"] = True
    v05_rows = [{"target": target, "group": name, **v05(scored[mask], target, prof.band_pp)}
                for target in TARGETS for name, mask in groups]

    per_seq = {s: rate(g, floor)["review_pct"] for s, g in held.groupby("sequence_id")}
    dense = held[held.pct >= 40]
    per_seq_dense = {s: rate(g, floor) for s, g in dense.groupby("sequence_id")}

    with open(os.path.join(RESULTS, "review_rate.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    with open(os.path.join(RESULTS, "review_rate_v05.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["rules", "profile", "target", *[k for k in v05_rows[0] if k != "target"]])
        w.writeheader()
        w.writerows({"rules": RULES_VERSION, "profile": prof.id, **r} for r in v05_rows)

    band_txt = (f"cutoff {prof.cutoff:+.1f}, 90% band ±{prof.band_pp:.2f} pp" if prof.band_pp is not None
                else f"cutoff {prof.cutoff:+.1f}, no band")
    lines = [
        "# Human-review rate", "",
        f"Generated {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} by `scripts/review_rate.py`. "
        "No model runs: readings, confidences and maps are the compute cache's (Cellpose-SAM cpsam_v2, Colab GPU, "
        "nb/03), same formula as the live path. C2C12 images: Ker et al., *Sci Data* 5:180237 (2018), "
        "CC BY 4.0; fault frames are simulated from them. Frames within a sequence are not independent; "
        "n sequences is the sample size.", "",
        f"## `{RULES_VERSION}`: error band and passage hold", "",
        f"C2C12 frames read with profile `{prof.id}` ({prof.status}; {band_txt}; "
        "`configs/confluency_profiles.yaml`, `results/confluency_profiles.md`)"
        + ("" if prof.cutoff == 0.0 else ", the cutoff applied to the cached map at 1/4 resolution") + ". "
        + ("A reading goes to review when its band includes the target, or when it is at or above the target "
           "and the anomaly check flagged the image." if prof.band_pp is not None else
           "With no calibration profile, every reading at or above the target goes to review: the rules never "
           "passage on an uncalibrated reading alone.")
        + (f" The quality gate calibrated for the setup (`configs/quality.yaml`, entry `{prof.quality}`) runs "
           "first, on the cached metrics, and a frame that fails it returns REIMAGE." if prof.quality else
           " No quality gate is calibrated for the setup.")
        + " Time since passage is assumed long enough. Boundary ambiguity no longer decides.", "",
        "| target | group | images | re-image (quality gate) | band includes the target | held by the anomaly flag | uncalibrated, at or above target | passage | total to review |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in v05_rows:
        lines.append(f"| {r['target']:g}% | {r['group']} | {r['n']} | {r['reimage']} | {r['band_review']} | {r['held']} | "
                     f"{r['uncalibrated_review']} | {r['passage']} | {r['review']} ({r['review_pct']}%) |")
    lines += ["", "## rules_v0.4, for comparison: boundary-ambiguity trigger", "",
        f"With the classifier demoted, rules_v0.4 had two rules that return `human_review`: boundary "
        f"ambiguity above {1 - floor:.2f} (the record's `confidence` below the {floor:.2f} floor), a "
        "density-sensitive review trigger that does not predict the reading's error "
        "(`results/confidence_vs_error.md`), and, since `rules_v0.3`, the passage hold "
        "(confluency at or above the target, but the anomaly check flagged the image). Readings at cutoff 0.0, "
        "full resolution. Quality-gate failures return REIMAGE (`results/quality_gate_c2c12.md`).", "",
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
              "## rules_v0.4, for comparison: passage hold on an anomaly flag (since rules_v0.3)", "",
              "Frames with an anomaly score (A4). Passage-eligible: boundary ambiguity at or below the trigger and confluency "
              "at or above the target (time since passage assumed long enough). Held: passage-eligible and "
              "flagged, so sent to review instead of passage. Total: ambiguity trigger or held.", "",
              "| target | group | images | above the ambiguity trigger | passage-eligible | held by the anomaly flag | total to review |",
              "|---|---|---|---|---|---|---|"]
    for r in hold_rows:
        lines.append(f"| {r['target']:g}% | {r['group']} | {r['n']} | {r['floor']} | {r['eligible']} | {r['hold']} "
                     f"| {r['total']} ({r['total_pct']}%) |")
    lines.append("")
    with open(os.path.join(RESULTS, "review_rate.md"), "w") as f:
        f.write("\n".join(lines))
    print("\n".join(lines))
    print(json.dumps({"floor": floor, "groups": len(rows), "c2c12_profile": prof.id}))


if __name__ == "__main__":
    main()
