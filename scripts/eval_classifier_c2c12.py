"""
How the QC classifier (trained on synthetic tiles) calls real C2C12 frames.
Not a spec criterion; context for V5/V6/V8 and the Phase A report.

Held-out frames only (results/replay_fleet_split.csv): every frame of the
held-out base sequences, and the held-out simulated fault frames after
onset (is_modified). Calibrated probabilities (configs/calibration.yaml,
culture.calibration.calibrated_probs) on the cached logits of the 256 px
centre tile; the call is the arg-max class.

Usage:
    python scripts/eval_classifier_c2c12.py --cache-dir cache
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

from culture.calibration import calibrated_probs, load_calibration  # noqa: E402
from culture.qc import CLASS_NAMES  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cache-dir", default="cache")
    ap.add_argument("--split", default=os.path.join(REPO, "results", "replay_fleet_split.csv"))
    ap.add_argument("--out", default=os.path.join(REPO, "results"))
    args = ap.parse_args()

    split = pd.read_csv(args.split)
    held = set(split[(split.split == "heldout") & (split.kind == "base")].sequence_id)
    images = pd.read_parquet(os.path.join(args.cache_dir, "images.parquet"))
    manifest = pd.read_parquet(os.path.join(args.cache_dir, "sidecars", "fault_manifest.parquet"))
    logits = pd.read_parquet(os.path.join(args.cache_dir, "logits.parquet"))
    logits = logits[logits.model_name == "qc"].drop_duplicates("image_sha256")
    cal = load_calibration()

    groups = {"normal (held-out base frames)": images[(images.dataset == "c2c12") & images.sequence_id.isin(held)]
              .image_sha256.unique()}
    post = manifest[manifest.base_sequence_id.isin(held) & manifest.is_modified]
    for ft, g in post.groupby("fault_type"):
        groups[f"{ft} (held-out, after onset)"] = g.image_sha256.unique()

    lg = dict(zip(logits.image_sha256, logits.model_version))
    lv = dict(zip(logits.image_sha256, logits.logits))
    rows = []
    for name, shas in groups.items():
        probs = []
        for sha in shas:
            if sha not in lv:
                continue
            p, _ = calibrated_probs(np.array(json.loads(lv[sha])), cal, lg[sha])
            probs.append(p)
        probs = np.array(probs)
        calls = probs.argmax(axis=1)
        row = {"frames": name, "n": len(probs)}
        for i, c in enumerate(CLASS_NAMES):
            row[f"called_{c}_pct"] = 100.0 * float((calls == i).mean())
        for i, c in enumerate(CLASS_NAMES):
            row[f"mean_p_{c}"] = float(probs[:, i].mean())
        rows.append(row)
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(args.out, "classifier_c2c12.csv"), index=False, float_format="%.4f")

    lines = ["# QC classifier on real C2C12 frames (context, not a spec criterion)", "",
             f"Generated {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} by `scripts/eval_classifier_c2c12.py`. "
             "C2C12 images: Ker et al., *Sci Data* 5:180237 (2018), CC BY 4.0; fault frames are simulated. The "
             "classifier (`qc_effnetb0_v1`) was trained on synthetic tiles only. Calibrated probabilities "
             "(temperature from `configs/calibration.yaml`) on the 256 px centre tile; call = arg-max. Held-out "
             "sequences only.", "",
             "| frames | n | " + " | ".join(f"called {c}" for c in CLASS_NAMES) + " | " +
             " | ".join(f"mean p({c})" for c in CLASS_NAMES) + " |", "|---|---|" + "---|" * (2 * len(CLASS_NAMES))]
    for r in rows:
        lines.append(f"| {r['frames']} | {r['n']} | " + " | ".join(f"{r[f'called_{c}_pct']:.1f}%" for c in CLASS_NAMES)
                     + " | " + " | ".join(f"{r[f'mean_p_{c}']:.2f}" for c in CLASS_NAMES) + " |")
    lines += ["", "Frames within a sequence are not independent (14 held-out base sequences; 2 contamination, "
              "2 growth-stall and 14 dimming fault sequences). Growth-stall frames are re-timed copies of normal "
              "frames, so the classifier cannot see a stall by design.", ""]
    with open(os.path.join(args.out, "classifier_c2c12.md"), "w") as f:
        f.write("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
