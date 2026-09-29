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
  C2C12 contamination  the first held-out contamination pick as the stress test (simulated,
                       bacteria 16.5× too large); the second pick's frame rebuilt with the
                       bacteria at their real size (scripts/contamination_scale.py, haze variant,
                       the original simulator's design; owner decision 2026-09-28)
  EVICAN               the two real-image examples the console already showed
                       (one accurate, one error case; results/confluency_real_summary.md)
Lamp dimming is left out: this tab runs no quality gate, and the anomaly flag
does not catch dimming (AUROC 0.47), so a dimmed frame would show nothing. The
Flask Timeline's dimming replay shows the gate catching it.

For the C2C12 frames the JSON also holds the compute cache's values for the
same image (Colab GPU, nb/03), so CPU vs GPU agreement is visible.

Each example also stores the cell-probability map its confluency was counted
from (<id>_probmap.npz, the cache's stored form), for the 3D confluency view;
its SHA-256 is the record's confluency_map_hash. For C2C12 frames, the share
of map pixels whose side of the cutoff differs from the cache's map is stored
under cache.probmap_sign_disagree_pct.

Usage (needs data/c2c12_picks/ from nb/04c_fetch_c2c12_frames.ipynb, and the
cache for the parity columns):
    python scripts/export_demo_examples.py [--only ID ...]

After a change to the rules only (culture/rules.py), re-derive the decisions
from the stored model outputs, with no model run:
    python scripts/export_demo_examples.py --rederive
The action, reason, rationale, caption and the record's decision fields are
recomputed; the records are re-chained in their original order (record_id and
timestamps kept, so every record_hash changes with decided_by); the example
gains decision_rederived = {"at", "rules"}, shown on the precomputed card.
Model outputs (confluency, maps, anomaly, classifier, overlay) are untouched.
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
import numpy as np
import pandas as pd

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from culture.cache import probmap_sha256  # noqa: E402
from culture.rationale import generate_rationale  # noqa: E402
from culture.rules import RULES_VERSION, LineConfig, decide  # noqa: E402
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

REAL_SIZE_VARIANT = "scale0.060769_haze"      # scripts/contamination_scale.py variant_name(REALISTIC, True)
SCALE_DIR = os.path.join(REPO, "data", "contamination_scale")
SCALE_CSV = os.path.join(REPO, "results", "contamination_scale.csv")

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
    contam = list(picks[picks.kind == "contamination_onset"].itertuples())
    out.append({"id": "c2c12_contamination_1", "kind": "c2c12_contamination", "row": contam[0],
                "label": "C2C12 contamination stress test (bacteria 16.5× too large)"})
    real = contam[1]
    man = pd.read_parquet(os.path.join(SCALE_DIR, REAL_SIZE_VARIANT, "manifest.parquet"))
    m = man[(man.fault_sequence_id == real.seq) & (man.frame_idx == real.frame_idx)].iloc[0]
    for e in out:
        r = e.pop("row")
        e.update(src=os.path.join(FRAMES, f"{r.image_sha256}.png"), image_sha256=r.image_sha256,
                 sequence=r.seq, frame=int(r.frame_idx), severity=None if pd.isna(r.severity) else float(r.severity),
                 credit=C2C12_CREDIT,
                 cache={"confluency_pct": float(r.pct), "anomaly_score": float(r.score_binned),
                        "anomaly_flag": bool(r.flag_binned), "anomaly_bin": r.bin_label})
    out.append({"id": "c2c12_contamination_real_size", "kind": "c2c12_contamination_real",
                "label": "C2C12 contamination, bacteria at real size", "src": m.png_path,
                "image_sha256": m.image_sha256, "sequence": real.seq, "frame": int(real.frame_idx),
                "severity": float(m.severity), "credit": C2C12_CREDIT + "; bacteria: DeepBacs, Zenodo 5550935"})
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
    if e["kind"] == "c2c12_contamination_real":
        sc = pd.read_csv(SCALE_CSV)
        real, clean = sc[sc.variant == REAL_SIZE_VARIANT], sc[sc.variant == "clean"]
        clean_pct = clean[(clean.fault_sequence_id == e["sequence"]) & (clean.frame_idx == e["frame"])].pct.iloc[0]
        n, k_real, k_clean = len(real), int(real.flag.sum()), int(clean.flag.sum())
        chance = (f"the only one of the {n} frames flagged at real size" if flag and k_real == 1 else
                  f"{k_real} of the {n} frames are flagged at real size") + \
            f", against {k_clean} of {n} for the same frames without bacteria, so the flag is at chance"
        return (f"Held-out frame with simulated contamination at the bacteria's real size ({e['severity']:.0f} per "
                f"256 px tile area; the stress test's second pick, rebuilt); {an}: {chance} "
                f"(results/contamination_scale.md). {conf}, against {clean_pct:.1f}% for the same frame without "
                f"bacteria. The rules recommend {rec['recommended_action']}: the flag only holds a passage, and "
                "this flask is far below the target.")
    held = rec["recommended_action"] == "human_review" and flag
    return (f"Held-out frame with simulated contamination ({e['severity']:.0f} bacteria pasted at 16.5× their "
            f"real size); {an}. {conf}: the pasted bacteria are counted as cells, so confluency alone is above "
            f"the target"
            + ("; the anomaly flag holds the passage, and the rules recommend human review." if held
               else f", and the rules recommend {rec['recommended_action']}."))


def rederive(date: str) -> None:
    """Re-derive every example's decision under the current rules from its stored
    outputs (no model run); see the module docstring."""
    from demo.analysis import DEFAULT_HOURS_SINCE_FEED, DEFAULT_HOURS_SINCE_PASSAGE

    with open(OUT_JSON) as f:
        doc = json.load(f)
    writer = RecordWriter(os.path.join(tempfile.mkdtemp(prefix="cultureqc_examples_"), "records.jsonl"))
    for ex in doc["examples"]:
        a, conf, qc = ex["anomaly"], ex["confluency"], ex["qc"]
        flag = a["flag"] if a["status"] == "ok" else None
        demoted = ex["demoted"]
        action, reason = decide(
            confluency_pct=conf["pct"], confluency_confidence=conf["confidence"],
            qc_flag=None if demoted else qc["flag"], qc_confidence=None if demoted else qc["confidence"],
            line_config=LineConfig(cell_line=ex["cell_line"], target_confluency=ex["target_confluency"]),
            hours_since_passage=DEFAULT_HOURS_SINCE_PASSAGE, hours_since_feed=DEFAULT_HOURS_SINCE_FEED,
            anomaly_flag=flag)
        rationale = generate_rationale(
            qc_flag=None if demoted else qc["flag"], qc_confidence=None if demoted else qc["confidence"],
            evidence_bbox=(qc.get("evidence_bboxes") or [None])[0], confluency_pct=conf["pct"],
            target_confluency=ex["target_confluency"], action=action, tile_size=256, use_vlm=False,
            anomaly_flag=flag)["rationale"]
        old_action = ex["action"]
        rec = dict(ex["record"], recommended_action=action, action_reason=reason, qc_rationale=rationale,
                   decided_by=RULES_VERSION, anomaly_used_in_decision=flag is not None)
        changed = old_action != action or ex["record"].get("decided_by") != RULES_VERSION
        rec = writer.append(rec)
        ex.update(action=action, action_reason=reason, rationale=rationale, record=rec, caption=caption(ex, rec))
        if changed or "decision_rederived" in ex:     # an example made under the current rules is not marked
            ex["decision_rederived"] = {"at": ex.get("decision_rederived", {}).get("at", date) if not changed
                                        else date, "rules": RULES_VERSION}
        print(f"{ex['id']}: {old_action} -> {action}")
    with open(OUT_JSON, "w") as f:
        json.dump(doc, f, indent=1, sort_keys=True)
        f.write("\n")
    print(f"wrote {os.path.relpath(OUT_JSON, REPO)} ({len(doc['examples'])} examples, decisions under {RULES_VERSION})")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", nargs="*", help="example ids to (re)run; the rest are kept from examples.json")
    ap.add_argument("--rederive", action="store_true",
                    help="re-derive decisions from the stored outputs under the current rules; no model run")
    args = ap.parse_args()
    if args.rederive:
        rederive(datetime.now(timezone.utc).date().isoformat())
        return

    import torch

    os.makedirs(OUT_DIR, exist_ok=True)
    old = {}
    if os.path.exists(OUT_JSON):
        with open(OUT_JSON) as f:
            old = {e["id"]: e for e in json.load(f)["examples"]}
    examples = c2c12_examples() + evican_examples()
    device = ("cuda" if torch.cuda.is_available() else
              "mps" if os.environ.get("CULTUREQC_DEVICE") == "mps" and torch.backends.mps.is_available() else "cpu")
    writer = RecordWriter(os.path.join(tempfile.mkdtemp(prefix="cultureqc_examples_"), "records.jsonl"))
    out = []
    for e in examples:
        if args.only and e["id"] not in args.only:
            if e["id"] in old:
                out.append(dict(old[e["id"]], label=e["label"]))      # labels always from this file
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
        probmap_file = f"{e['id']}_probmap.npz"
        np.savez_compressed(os.path.join(OUT_DIR, probmap_file), prob_x1000=a.probmap_x1000)
        assert probmap_sha256(a.probmap_x1000) == rec["confluency_map_hash"]
        entry = {k: v for k, v in e.items() if k not in ("src",)}
        if "cache" in e:
            cached = np.load(os.path.join(CACHE, "probmaps", f"{sha}.npz"))["prob_x1000"]
            assert cached.shape == a.probmap_x1000.shape
            entry["cache"] = dict(e["cache"], probmap_sign_disagree_pct=round(
                float(((cached > 0) != (a.probmap_x1000 > 0)).mean() * 100), 4))
        entry.update(
            image=image_file, overlay=overlay_file, probmap=probmap_file, image_sha256=sha, height=int(img.shape[0]),
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
