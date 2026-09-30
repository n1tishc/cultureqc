"""The calibrated Cellpose-SAM cutoff, for the console's EVICAN examples.

    python scripts/export_cutoff_examples.py

Reads results/confluency_cutoff.csv (scripts/confluency_cutoff.py) and writes
demo/examples/cutoff_calibrated.json: the held-out MAE at the shipped and the
calibrated cutoff, and each EVICAN example's reading at both. The console shows
it beside the precomputed example as validated, not live; nothing here changes
the shipped cutoff or any stored example. No model runs.
"""

from __future__ import annotations

import json
import os
import sys

import pandas as pd

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))
from export_demo_examples import EVICAN  # noqa: E402

CSV = os.path.join(REPO, "results", "confluency_cutoff.csv")
OUT = os.path.join(REPO, "demo", "examples", "cutoff_calibrated.json")
SHIPPED, PICK = "0", "-3.5"


def build(csv_path: str = CSV) -> dict:
    df = pd.read_csv(csv_path).set_index("file_name")
    ev = df[df.split == "eval33"]
    mae = lambda c: round(float((ev[f"pct_cut{c}"] - ev.gt_pct).abs().mean()), 2)
    examples = {}
    for ex_id, path, _gt, _label in EVICAN:
        r = df.loc[os.path.basename(path).removeprefix("evican_")]
        examples[ex_id] = {"file": r.name, "split": r.split, "gt_pct": round(float(r.gt_pct), 1),
                           "shipped": {"pct": round(float(r[f"pct_cut{SHIPPED}"]), 1),
                                       "confidence": float(r[f"conf_cut{SHIPPED}"])},
                           "calibrated": {"pct": round(float(r[f"pct_cut{PICK}"]), 1),
                                          "confidence": float(r[f"conf_cut{PICK}"])}}
    return {"generated_by": "scripts/export_cutoff_examples.py",
            "source": "results/confluency_cutoff.md",
            "status": "validated, not live",
            "cutoff": {"shipped": float(SHIPPED), "calibrated": float(PICK)},
            "calibration_images": int((df.split == "calib65").sum()),
            "eval": {"n": len(ev), "mae_shipped": mae(SHIPPED), "mae_calibrated": mae(PICK)},
            "examples": examples}


if __name__ == "__main__":
    doc = build()
    with open(OUT, "w") as f:
        json.dump(doc, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print(f"wrote {os.path.relpath(OUT, REPO)}: eval MAE {doc['eval']['mae_shipped']} -> {doc['eval']['mae_calibrated']} pp")
