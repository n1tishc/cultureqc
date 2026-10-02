"""
v0.2's QC classifier against v0.3's anomaly check, on the same real frames.
Context for the call and for "Since v0.2"; not a spec criterion. Compute cache
only: no model is run and nothing is tuned.

v0.2 is the classifier (`qc_effnetb0_v1`) as v0.2 used it: plain softmax over
its cached logits (v0.2 had no temperature scaling; scaling doesn't change the
arg-max) and v0.2's rule 1 (`main:culture/rules.py`): a call other than normal
at confidence >= 0.7 (`qc_review_threshold`, the default; v0.2 had no C2C12
line config) sends the image to human_review. v0.3 is the anomaly check's flag
(`flag_binned`) and z-score from `cache/anomaly/scores.parquet`, the scores
behind `results/anomaly_summary.md`.

  1. Held-out C2C12 frames (results/replay_fleet_split.csv): both.
  2. Per held-out sequence, healthy frames: both.
  3. All 24 C2C12 sequences: the classifier only (the anomaly banks and
     thresholds come from the 10 tuning sequences).
  4. AutoQC-Bench test set, real anomalies from another lab: the classifier
     only (the anomaly banks are C2C12 patches).

Usage:
    python scripts/compare_v02_v03_flags.py --cache-dir cache
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np
import pandas as pd

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from culture.qc import CLASS_NAMES  # noqa: E402

V02_REVIEW_THRESHOLD = 0.7          # main:culture/rules.py, LineConfig.qc_review_threshold
NORMAL = CLASS_NAMES.index("normal")
CONTAM = CLASS_NAMES.index("contamination_suspected")
AUTOQC_GROUPS = ["good", "contamination", "air_bubble", "artifacts", "illumination", "z-shift"]


def _auroc(neg, pos):
    from sklearn.metrics import roc_auc_score

    return float(roc_auc_score(np.r_[np.zeros(len(neg)), np.ones(len(pos))], np.r_[neg, pos]))


def _softmax(logit_json):
    L = np.array([json.loads(x) for x in logit_json])
    p = np.exp(L - L.max(axis=1, keepdims=True))
    return p / p.sum(axis=1, keepdims=True)


def _v02(p):
    """Per-frame v0.2 outputs from softmax probabilities."""
    call = p.argmax(axis=1)
    return pd.DataFrame({"p_normal": p[:, NORMAL], "p_contam": p[:, CONTAM],
                         "not_normal": call != NORMAL, "called_contam": call == CONTAM,
                         "rule1_review": (call != NORMAL) & (p.max(axis=1) >= V02_REVIEW_THRESHOLD),
                         "call": [CLASS_NAMES[i] for i in call]})


def _pct(x):
    return f"{100.0 * float(np.mean(x)):.1f}%"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cache-dir", default="cache")
    ap.add_argument("--split", default=os.path.join(REPO, "results", "replay_fleet_split.csv"))
    ap.add_argument("--out", default=os.path.join(REPO, "results"))
    args = ap.parse_args()

    images = pd.read_parquet(os.path.join(args.cache_dir, "images.parquet"))
    logits = pd.read_parquet(os.path.join(args.cache_dir, "logits.parquet"))
    logits = logits[logits.model_name == "qc"].drop_duplicates("image_sha256")
    lv = dict(zip(logits.image_sha256, logits.logits))
    scores = pd.read_parquet(os.path.join(args.cache_dir, "anomaly", "scores.parquet"))
    split = pd.read_csv(args.split)
    held = set(split[(split.split == "heldout") & (split.kind == "base")].sequence_id)

    # 1. held-out C2C12: the anomaly scores table already holds every held-out frame, with its kind
    s = scores[scores.split == "heldout"].reset_index(drop=True)
    assert set(s[s.kind == "normal"].base_sequence_id) == held
    s = pd.concat([s, _v02(_softmax(s.image_sha256.map(lv)))], axis=1)
    norm = s[s.kind == "normal"]
    kinds = [("normal", "healthy"), ("contamination_onset", "simulated contamination, bacteria 16.5× too large, after onset"),
             ("lamp_dimming", "simulated lamp dimming, after onset")]
    t1 = []
    for k, label in kinds:
        g = s[s.kind == k]
        t1.append({"frames": label, "n": len(g), "sequences": g.base_sequence_id.nunique(),
                   "v02_not_normal": _pct(g.not_normal), "v02_rule1_review": _pct(g.rule1_review),
                   "v02_called_contam": _pct(g.called_contam), "v03_flag": _pct(g.flag_binned),
                   "v03_flag_n": f"{int(g.flag_binned.sum())} of {len(g)}"})
    t2 = []
    for k, label in kinds[1:]:
        g = s[s.kind == k]
        t2.append({"frames": label,
                   "v02_any": _auroc(1 - norm.p_normal, 1 - g.p_normal),
                   "v02_contam": _auroc(norm.p_contam, g.p_contam),
                   "v03": _auroc(norm.z_binned, g.z_binned)})

    # 2. per held-out sequence, healthy frames
    per = (norm.assign(experiment=norm.base_sequence_id.str.extract(r"c2c12_(\d{6})_")[0])
           .groupby(["experiment", "base_sequence_id"])
           .agg(n=("not_normal", "size"), v02=("not_normal", "mean"), v03=("flag_binned", "mean"))
           .reset_index())
    per[["v02", "v03"]] *= 100.0
    per["gap_pp"] = per.v02 - per.v03
    per.to_csv(os.path.join(args.out, "v02_vs_v03_flags_per_sequence.csv"), index=False, float_format="%.1f")
    lower = int((per.v03 < per.v02).sum())
    smallest = per.loc[per.gap_pp.idxmin()]

    # 3. classifier on all 24 C2C12 sequences
    c = images[images.dataset == "c2c12"]
    c_all = _v02(_softmax(c.image_sha256.map(lv)))

    # 4. AutoQC-Bench test set
    a = images[images.dataset == "autoqc_bench_test"].reset_index(drop=True)
    grp = np.where(a.source_path.str.contains("/good_data/"), "good",
                   a.source_path.str.extract(r"/anomalies/([^/]+)/")[0])
    a = pd.concat([a.assign(group=grp), _v02(_softmax(a.image_sha256.map(lv)))], axis=1)
    assert set(a.group) == set(AUTOQC_GROUPS), set(a.group)
    good = a[a.group == "good"]
    t4 = []
    for gname in AUTOQC_GROUPS:
        g = a[a.group == gname]
        calls = g.call.value_counts()
        t4.append({"group": gname, "n": len(g),
                   **{f"called_{cn}": f"{int(calls.get(cn, 0))}" for cn in CLASS_NAMES},
                   "v02_rule1_review": _pct(g.rule1_review)})
    auto_any = _auroc(1 - good.p_normal, 1 - a[a.group != "good"].p_normal)
    auto_contam = _auroc(good.p_contam, a[a.group == "contamination"].p_contam)

    L = ["# v0.2's QC classifier vs v0.3's anomaly check, on the same real frames", "",
         f"Generated {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} by `scripts/compare_v02_v03_flags.py` "
         "from the compute cache; no model run, nothing tuned. C2C12 images: Ker et al., *Sci Data* 5:180237 "
         "(2018), CC BY 4.0; fault frames are simulated from them. AutoQC-Bench: BioStudies S-BIAD2133 "
         "(doi:10.6019/S-BIAD2133), MIT; human and mouse neutrophil granulocytes, with real anomalies.", "",
         "**v0.2** = the QC classifier `qc_effnetb0_v1` as v0.2 used it: plain softmax over its cached logits "
         "and v0.2's rule 1 (`main:culture/rules.py`), a call other than normal at confidence ≥ "
         f"{V02_REVIEW_THRESHOLD} sends the image to `human_review`. **v0.3** = the anomaly check's flag and "
         "binned z-score (`cache/anomaly/scores.parquet`, the scores behind `results/anomaly_summary.md`). "
         "Since `rules_v0.3` the flag acts only at passage: an image at or above the target that it flags goes "
         "to review instead of passage.", "",
         "## 1. Held-out C2C12 frames", "",
         "| frames | n | sequences | v0.2: not called normal | v0.2: sent to review by rule 1 | "
         "v0.2: called contamination | v0.3: anomaly flag |", "|---|---|---|---|---|---|---|"]
    L += [f"| {r['frames']} | {r['n']} | {r['sequences']} | {r['v02_not_normal']} | {r['v02_rule1_review']} | "
          f"{r['v02_called_contam']} | {r['v03_flag']} ({r['v03_flag_n']}) |" for r in t1]
    L += ["", "AUROC of the simulated faults against the held-out healthy frames (0.5 = chance):", "",
          "| frames | v0.2: 1 − p(normal), any problem | v0.2: p(contamination) | v0.3: anomaly z |",
          "|---|---|---|---|"]
    L += [f"| {r['frames']} | {r['v02_any']:.2f} | {r['v02_contam']:.2f} | {r['v03']:.2f} |" for r in t2]
    L += ["",
          "Simulated lamp dimming is pooled over every intensity after onset; `results/anomaly_summary.md` gives v0.3's "
          "AUROC per intensity band (0.41 to 0.49).", "",
          f"v0.2's rule 1 alone sends {t1[0]['v02_rule1_review']} of held-out healthy frames to review; its rule 2 "
          "(confluency confidence below 0.3) sends more, so v0.2's total is at least that. v0.3's total review "
          "rate on the same frames, and the one frame the anomaly flag adds to it, are in "
          "`results/review_rate.md`.", "",
          "## 2. Per held-out sequence, healthy frames", "",
          "| experiment | sequence | frames | v0.2: not called normal | v0.3: anomaly flag | gap (pp) |",
          "|---|---|---|---|---|---|"]
    L += [f"| {r.experiment} | {r.base_sequence_id} | {r.n} | {r.v02:.1f}% | {r.v03:.1f}% | {r.gap_pp:.1f} |"
          for r in per.itertuples()]
    L += ["",
          f"The anomaly flag rate is lower in {lower} of {len(per)} sequences; the smallest gap is "
          f"{smallest.base_sequence_id} ({smallest.v02:.1f}% vs {smallest.v03:.1f}%). The {len(per)} sequences are "
          f"fields of view from {per.experiment.nunique()} experiments, not {len(per)} independent cultures. "
          "Per-sequence rows: `results/v02_vs_v03_flags_per_sequence.csv`.", "",
          "## 3. The classifier on all C2C12 sequences", "",
          f"{_pct(~c_all.not_normal)} of {len(c_all)} frames from {c.sequence_id.nunique()} sequences are called "
          "normal (the classifier never saw C2C12). The anomaly check is not scored on the tuning sequences: its "
          "banks and thresholds come from them.", "",
          "## 4. AutoQC-Bench test set: real anomalies from another lab (classifier only)", "",
          "| group | n | " + " | ".join(f"called {cn}" for cn in CLASS_NAMES) + " | v0.2: sent to review by rule 1 |",
          "|---|---|" + "---|" * (len(CLASS_NAMES) + 1)]
    L += [f"| {r['group']} | {r['n']} | " + " | ".join(r[f"called_{cn}"] for cn in CLASS_NAMES)
          + f" | {r['v02_rule1_review']} |" for r in t4]
    L += ["",
          f"AUROC against the good images: any anomaly, 1 − p(normal), {auto_any:.2f}; real contamination, "
          f"p(contamination), {auto_contam:.2f}.", "",
          "**Not run: v0.3's anomaly check.** Its banks are C2C12 patches, so scoring these images against them "
          "would measure the change of microscope and cell type, not the method. A fair test builds the bank "
          "from AutoQC-Bench's own normal training split; not done here.", "",
          "## Limits", "",
          "- On C2C12 the comparison is on v0.3's home ground: the anomaly banks and thresholds come from tuning "
          "sequences of the same three experiments, while the classifier never saw C2C12. It shows that "
          "calibrating to the setup's real healthy images beats training on synthetic faults; it does not show "
          "that the anomaly check transfers to another setup.",
          "- Frames within a sequence are not independent. Held-out contamination is 2 sequences, with bacteria "
          "16.5× too large; at their real size the anomaly flag is at chance (`results/contamination_scale.md`), "
          "and the classifier was not scored at real size.",
          "- Both models read only the 256 px centre tile: about 4.5% of a C2C12 frame and 6.4% of an AutoQC-Bench "
          "frame (1280 × 800), so an anomaly outside it is invisible to both. AutoQC-Bench's neutrophils are not a cell type "
          "in LIVECell, which the classifier's training tiles came from, and its pixel size is not matched to them.",
          "- This compares the problem detectors only. Confluency is measured separately "
          "(`results/confluency_real_summary.md`, n = 33).", ""]
    with open(os.path.join(args.out, "v02_vs_v03_flags.md"), "w") as f:
        f.write("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
