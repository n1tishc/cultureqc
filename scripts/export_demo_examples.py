"""
Precomputed single-image examples for the console's Analyze tab
(cultureQC_upgrade_specv4.md §2B.7 item 2, B8): each example is run once
through demo/analysis.py, the same code the Analyze button runs, and its
outputs are stored in demo/examples/ so the tab shows them instantly on CPU,
with no model loaded. The app labels them as precomputed; pressing Analyze
runs the same image live.

Examples (fixed before any output was seen):
  C2C12 normal         the first pick per confluency bin in results/c2c12_frame_picks.csv
                       (held-out, seeded; scripts/pick_c2c12_frames.py)
  C2C12 contamination  both held-out contamination picks (simulated, 16.5× scale)
  EVICAN               the two real-image examples the console already showed
                       (one accurate, one error case; results/confluency_real_summary.md)
Lamp dimming is left out: this tab runs no quality gate, and the anomaly flag
does not catch dimming (AUROC 0.47), so a dimmed frame would show nothing. The
Flask Timeline's dimming replay shows the gate catching it.

For the C2C12 frames the JSON also holds the compute cache's values for the
same image (Colab GPU, nb/03), so CPU vs GPU agreement is visible.

Usage (needs data/c2c12_picks/ from nb/04c_fetch_c2c12_frames.ipynb, and the
cache for the parity columns):
    python scripts/export_demo_examples.py [--only ID ...]
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import sys
import tempfile
import time
from datetime import datetime, timezone

import cv2
import pandas as pd

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from culture.records import RecordWriter, hash_file  # noqa: E402
from demo.analysis import analyze_image, build_record  # noqa: E402

OUT_DIR = os.path.join(REPO, "demo", "examples")
OUT_JSON = os.path.join(OUT_DIR, "examples.json")
PICKS = os.path.join(REPO, "results", "c2c12_frame_picks.csv")
FRAMES = os.path.join(REPO, "data", "c2c12_picks")
CACHE = os.path.join(REPO, "cache")
TARGET = 80.0                      # the console's default target
CELL_LINE = "unknown"
C2C12_CREDIT = "C2C12: Ker et al., Sci Data 5:180237 (2018), CC BY 4.0"
EVICAN_CREDIT = "EVICAN: Bioinformatics 36(12):3863 (2020), CC BY 4.0"

EVICAN = [
    # id, file, ground truth (%, union of the dataset's expert masks), label
    ("evican_pc3", "test-data/evican_66_PC3.jpg", 5.50, "EVICAN PC3 (real, accurate)"),
    ("evican_ht29", "test-data/evican_48_HT29.jpg", 51.60, "EVICAN HT29 (real, error case)"),
]


def c2c12_examples() -> list[dict]:
    picks = pd.read_csv(PICKS)
    out = []
    normals = picks[picks.kind == "normal"].drop_duplicates("bin_label")
    for r in normals.itertuples():
        out.append({"id": f"c2c12_normal_{r.bin_label.replace('-', '_')}", "kind": "c2c12_normal", "row": r,
                    "label": f"C2C12 normal, {r.bin_label}% bin"})
    for i, r in enumerate(picks[picks.kind == "contamination_onset"].itertuples(), 1):
        out.append({"id": f"c2c12_contamination_{i}", "kind": "c2c12_contamination", "row": r,
                    "label": f"C2C12 simulated contamination {i}"})
    for e in out:
        r = e.pop("row")
        e.update(src=os.path.join(FRAMES, f"{r.image_sha256}.png"), image_sha256=r.image_sha256,
                 sequence=r.seq, frame=int(r.frame_idx), severity=None if pd.isna(r.severity) else float(r.severity),
                 credit=C2C12_CREDIT,
                 cache={"confluency_pct": float(r.pct), "anomaly_score": float(r.score_binned),
                        "anomaly_flag": bool(r.flag_binned), "anomaly_bin": r.bin_label})
    return out


def evican_examples() -> list[dict]:
    return [{"id": i, "kind": "evican", "label": label, "src": os.path.join(REPO, f), "gt_pct": gt,
             "credit": EVICAN_CREDIT} for i, f, gt, label in EVICAN]


def caption(e: dict, rec: dict) -> str:
    """One data-driven sentence or two on what this example shows."""
    flag = rec["anomaly_flag"]
    an = ("anomaly check unavailable" if rec["anomaly_status"] != "ok" else
          f"anomaly {'flagged' if flag else 'not flagged'} (score {rec['anomaly_score']:.3f}, "
          f"threshold {rec['anomaly_threshold']:.3f})")
    conf = f"Cellpose-SAM reads {rec['confluency_pct']:.1f}%"
    if e["kind"] == "evican":
        return (f"Real image, ground truth {e['gt_pct']:.1f}% from the dataset's expert masks; {conf}; {an}. "
                "The anomaly banks hold only C2C12 frames, so on other cell types the flag is uncalibrated.")
    if e["kind"] == "c2c12_normal":
        return f"Held-out normal frame ({e['sequence']}, frame {e['frame']}); {conf}; {an}."
    return (f"Held-out frame with simulated contamination ({e['severity']:.0f} bacteria pasted at 16.5× their "
            f"real size); {an}. {conf}: the pasted bacteria are counted as cells, so the confluency rules "
            f"recommend {rec['recommended_action']}. The flag is shown for review only and does not change "
            "the action.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", nargs="*", help="example ids to (re)run; the rest are kept from examples.json")
    args = ap.parse_args()

    import torch

    os.makedirs(OUT_DIR, exist_ok=True)
    old = {}
    if os.path.exists(OUT_JSON):
        with open(OUT_JSON) as f:
            old = {e["id"]: e for e in json.load(f)["examples"]}
    examples = c2c12_examples() + evican_examples()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    writer = RecordWriter(os.path.join(tempfile.mkdtemp(prefix="cultureqc_examples_"), "records.jsonl"))
    out = []
    for e in examples:
        if args.only and e["id"] not in args.only:
            if e["id"] in old:
                out.append(old[e["id"]])
            continue
        ext = os.path.splitext(e["src"])[1].lower()
        image_file = f"{e['id']}{ext}"
        dst = os.path.join(OUT_DIR, image_file)
        shutil.copyfile(e["src"], dst)
        sha = hash_file(dst)
        if e.get("image_sha256"):
            assert sha == e["image_sha256"], f"{e['id']}: {sha} != cache {e['image_sha256']}"
        img = cv2.imread(dst, cv2.IMREAD_GRAYSCALE)
        t0 = time.perf_counter()
        a = analyze_image(img, dst, CELL_LINE, TARGET)
        wall = time.perf_counter() - t0
        overlay_file = f"{e['id']}_overlay.jpg"
        cv2.imwrite(os.path.join(OUT_DIR, overlay_file), cv2.cvtColor(a.overlay, cv2.COLOR_RGB2BGR),
                    [cv2.IMWRITE_JPEG_QUALITY, 90])
        rec = writer.append(build_record(a, dst, CELL_LINE, datetime.now(timezone.utc).isoformat()))
        entry = {k: v for k, v in e.items() if k not in ("src",)}
        entry.update(
            image=image_file, overlay=overlay_file, image_sha256=sha, height=int(img.shape[0]),
            width=int(img.shape[1]), cell_line=CELL_LINE, target_confluency=TARGET,
            confluency=a.confluency.to_dict(), qc=a.qc.to_dict(), demoted=a.demoted,
            anomaly=a.anomaly.__dict__ | {"top_patches": [list(p) for p in a.anomaly.top_patches]},
            action=a.action, action_reason=a.reason, rationale=a.rationale["rationale"],
            evidence_region_count=len(a.evidence_boxes), record=rec, caption=caption(e, rec),
            generated_at=rec["captured_at"], device=device, torch_threads=torch.get_num_threads(),
            timings_s=a.timings_s | {"wall": round(wall, 3)})
        out.append(entry)
        print(f"{e['id']}: {a.confluency.pct:.2f}% (cache {e.get('cache', {}).get('confluency_pct')}), "
              f"anomaly {a.anomaly.score} flag {a.anomaly.flag}, action {a.action}, {wall:.0f} s", flush=True)
    doc = {
        "generated_by": "scripts/export_demo_examples.py",
        "note": ("Precomputed by the console's own analysis code (demo/analysis.py), once, before the app "
                 "started. Pressing Analyze runs the same image live."),
        "platform": f"{platform.system()} {platform.machine()}, python {platform.python_version()}",
        "examples": out,
    }
    with open(OUT_JSON, "w") as f:
        json.dump(doc, f, indent=1, sort_keys=True)
        f.write("\n")
    print(f"wrote {os.path.relpath(OUT_JSON, REPO)} ({len(out)} examples)")


if __name__ == "__main__":
    main()
