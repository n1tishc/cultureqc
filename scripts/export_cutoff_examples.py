"""The calibrated Cellpose-SAM cutoff, for the console's EVICAN examples.

    python scripts/export_cutoff_examples.py

Reads results/confluency_cutoff.csv (scripts/confluency_cutoff.py) and writes
demo/examples/cutoff_calibrated.json: the held-out MAE at the shipped and the
calibrated cutoff, and each EVICAN example's reading at both. The disclosure
(the result is not fully blind) is parsed from results/confluency_cutoff.md's
curve and disclosure paragraph, so its numbers have one source. The console shows
it beside the precomputed example as validated, not live; nothing here changes
the shipped cutoff or any stored example. No model runs.
"""

from __future__ import annotations

import json
import os
import re
import sys

import pandas as pd

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))
from export_demo_examples import EVICAN  # noqa: E402

CSV = os.path.join(REPO, "results", "confluency_cutoff.csv")
MD = os.path.join(REPO, "results", "confluency_cutoff.md")
OUT = os.path.join(REPO, "demo", "examples", "cutoff_calibrated.json")
SHIPPED, PICK = "0", "-3.5"


def disclosure(md_path: str = MD, pick: float = float(PICK)) -> dict:
    """Why the 3.78 pp is not fully blind, from the cutoff study's own report."""
    with open(md_path) as f:
        text = f.read()
    curve = {float(c): (float(cal), float(ev)) for c, cal, ev in
             re.findall(r"^\| ([+-]\d\.\d)[^|]* \| ([\d.]+) \| ([\d.]+) \|$", text, re.M)}
    best = min(curve, key=lambda c: curve[c][1])
    flat = [c for c in sorted(curve) if pick <= c <= pick + 1.0]          # the pick and the next two grid points
    cal = [curve[c][0] for c in flat]
    m = re.search(r"The 33 are all under ([\d,]+) px[^;]*; (\d+) of the 65 calibration images are larger", text)
    d = {"eval_best_cutoff": best, "eval_best_mae": curve[best][1], "pick_mae": curve[pick][1],
         "calib_flat_from": flat[0], "calib_flat_to": flat[-1], "calib_mae_min": min(cal), "calib_mae_max": max(cal),
         "eval_px_under": int(m.group(1).replace(",", "")), "calib_larger": int(m.group(2))}
    fmt = lambda c: format(c, "+.1f").replace("+", "").replace("-", "−")
    d["text"] = (f"Not fully blind: the cutoff idea came from error analysis of these 33 images, and a "
                 f"quarter-resolution sweep showing the evaluation curve was seen before the rule was written. "
                 f"The rule picked {fmt(pick)}, which is not the evaluation-best ({fmt(best)} gives "
                 f"{curve[best][1]:.2f} pp); calibration MAE is flat from {fmt(flat[0])} to {fmt(flat[-1])} "
                 f"({min(cal):.2f}–{max(cal):.2f} pp). The 33 are all under {d['eval_px_under']:,} px, while "
                 f"{d['calib_larger']} of the 65 calibration images are larger.")
    return d


def build(csv_path: str = CSV, md_path: str = MD) -> dict:
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
            "disclosure": disclosure(md_path),
            "examples": examples}


if __name__ == "__main__":
    doc = build()
    with open(OUT, "w") as f:
        json.dump(doc, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print(f"wrote {os.path.relpath(OUT, REPO)}: eval MAE {doc['eval']['mae_shipped']} -> {doc['eval']['mae_calibrated']} pp")
