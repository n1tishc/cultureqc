"""Build the v0.3 site's data from the repo's real output → site/src/data.json.

    python site/assets/build_data.py            # data.json only (what CI re-runs and diffs)
    python site/assets/build_data.py --images   # also re-render site/public/img/v3/

Nothing here is typed in by hand. Sources:

- demo/examples/examples.json (+ .png/.jpg, _probmap.npz): the console's seven
  precomputed examples and their hash-chained records.
- demo/replays/*.json and demo/replay_maps/: the five held-out C2C12 flask
  replays and the Cellpose-SAM map at every visit.
- configs/detectability.yaml: what was tested, per fault.
- README.md: the V1-V10 table and the results table, whose numbers
  tests/test_readme_provenance.py checks against their source files.
- demo/figures/contamination_scale.png: the real-size contamination figure.
- demo/examples/cutoff_calibrated.json: the calibrated cutoff's not-fully-blind
  disclosure (scripts/export_cutoff_examples.py, from results/confluency_cutoff.md).

Each record's canonical JSON (sorted keys, compact, ASCII) is written out as
the exact string culture/records.py hashed, and its SHA-256 is checked here, so
the browser re-hashes the same bytes and needs no float formatting of its own.
"""
import argparse
import csv
import hashlib
import json
import os
import re

import sys

import numpy as np
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.dirname(HERE)
REPO = os.path.dirname(SITE)
DATA_OUT = os.path.join(SITE, "src", "data.json")
IMG_OUT = os.path.join(SITE, "public", "img", "v3")
IMG_URL = "img/v3"

CONSOLE_URL = "https://huggingface.co/spaces/LongGrainRice/cultureqc-console"
# The branch, not the repo root: main still shows v0.2 (its headline numbers were synthetic,
# results/v02_headline.md) until the owner merges or annotates it.
REPO_URL = "https://github.com/n1tishc/cultureqc/tree/slice-1b-compute-cache"
C2C12_UM_PER_PX = 1.3        # README "Imaging requirement": C2C12, 5× objective, 1.3 µm/px
TILE_PX, CROP_PX, PATCH_PX = 256, 224, 14   # culture/anomaly.py: qctile, DINOv2 centre crop, 16×16 patches
BAND_LOGIT = 1.0             # culture/seg.py confidence_band (logits) around the 0 cutoff
CONF_FLOOR = 0.30            # culture/rules.py review floor; README review-rate row
# demo/replay_timeline.py SETUP_PROFILE, the replays' imaging setup. Not imported: that module
# needs matplotlib, and the site job installs only numpy and pyyaml (tests keep the two equal).
REPLAY_PROFILE = "c2c12_ker2018"
sys.path.insert(0, REPO)
from culture.records import SCHEMA_VERSION  # noqa: E402
from culture.rules import AMBIGUITY_TOOLTIP, RULES_VERSION, boundary_ambiguity  # noqa: E402

EXAMPLE_ORDER = ["c2c12_normal_20_40", "c2c12_normal_0_20", "c2c12_normal_40_100",
                 "c2c12_contamination_real_size", "c2c12_contamination_1", "evican_pc3", "evican_ht29"]
REPLAY_ORDER = ["normal_1", "normal_2", "contamination", "stall", "dimming"]


def rel(*p):
    return os.path.join(REPO, *p)


def canonical(record):
    body = {k: v for k, v in record.items() if k != "record_hash"}
    return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def r3(x):
    return None if x is None else round(float(x), 3)


# ── README tables (numbers already provenance-checked by the test suite) ──

def md_table(text, header_start):
    lines = text.splitlines()
    i = next(k for k, l in enumerate(lines) if l.startswith(header_start))
    head = [c.strip() for c in lines[i].strip("|").split("|")]
    rows = []
    for l in lines[i + 2:]:
        if not l.startswith("|"):
            break
        cells = [c.strip() for c in l.strip().strip("|").split("|")]
        rows.append(dict(zip(head, cells)))
    return rows


def clean_md(s):
    s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)
    return s.replace("`", "")


def validation_rows(readme):
    out = []
    for r in md_table(readme, "| Check | Held-out result | Verdict |"):
        m = re.match(r"(V\d+)\s+(.*)", r["Check"])
        verdict = clean_md(r["Verdict"])
        v = verdict.lower()
        kind = ("mixed" if v.startswith("pass") and "fail" in v else
                "fail" if v.startswith("fail") else
                "info" if v.startswith("informational") else
                "none" if v.startswith("no verdict") else "pass")
        out.append({"id": m.group(1), "check": m.group(2), "result": clean_md(r["Held-out result"]),
                    "verdict": verdict, "kind": kind})
    return out


def readme_bullets(readme, lead):
    """The bullet list that follows a bold lead-in line, joined across wrapped lines."""
    lines = readme.splitlines()
    i = next(k for k, l in enumerate(lines) if l.startswith(lead))
    items, cur = [], None
    for l in lines[i + 1:]:
        if l.startswith("- "):
            if cur:
                items.append(cur)
            cur = l[2:].strip()
        elif l.startswith("  ") and cur is not None:
            cur += " " + l.strip()
        elif not l.strip() and cur is None:
            continue
        else:
            break
    if cur:
        items.append(cur)
    return [clean_md(re.sub(r"\[(.+?)\]\(.+?\)", r"\1", x)) for x in items]


def readme_paragraph(readme, heading):
    """The first paragraph under a heading, unwrapped."""
    lines = readme.splitlines()
    i = lines.index(heading) + 1
    while not lines[i].strip():
        i += 1
    para = []
    while i < len(lines) and lines[i].strip():
        para.append(lines[i].strip())
        i += 1
    text = " ".join(para)
    text = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", text)
    return clean_md(text)


def readme_lead_paragraph(readme, lead):
    """A paragraph that opens with a bold lead-in, without the lead-in."""
    lines = readme.splitlines()
    i = next(k for k, l in enumerate(lines) if l.startswith(lead))
    para = []
    while i < len(lines) and lines[i].strip():
        para.append(lines[i].strip())
        i += 1
    return clean_md(" ".join(para)[len(lead):].strip())


def results_rows(readme):
    return [{"result": clean_md(r["Result"]), "number": clean_md(r["Number"]),
             "provenance": r["Provenance"], "source": clean_md(r["Source"])}
            for r in md_table(readme, "| Result | Number | Provenance | Source |")]


# ── images ──

def save_webp(src, dst, max_w=None, quality=84, crop=None):
    from PIL import Image
    im = Image.open(src).convert("L")
    if crop:
        im = im.crop(crop)
    if max_w and im.width > max_w:
        im = im.resize((max_w, round(im.height * max_w / im.width)), Image.LANCZOS)
    im.save(dst, "WEBP", quality=quality, method=6)


def save_alpha(alpha, dst):
    """A white RGBA PNG whose alpha is the layer: the page uses it as a CSS mask."""
    from PIL import Image
    a = np.clip(alpha * 255.0, 0, 255).astype(np.uint8)
    rgba = np.dstack([np.full_like(a, 255)] * 3 + [a])
    Image.fromarray(rgba, "RGBA").save(dst, optimize=True)


def contour_path(logits, cut=0.0):
    """SVG path of the cutoff the reading was counted at (the profile's; Cellpose-SAM's
    default is logit 0), in map pixel units."""
    import cv2
    mask = (logits > cut).astype(np.uint8)
    cs, _ = cv2.findContours(mask, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    parts = []
    for c in cs:
        if cv2.contourArea(c) < 1.5:
            continue
        c = cv2.approxPolyDP(c, 0.45, True).reshape(-1, 2)
        if len(c) < 3:
            continue
        parts.append("M" + "L".join(f"{x},{y}" for x, y in c) + "Z")
    return "".join(parts)


def example_layers(ex, out_dir):
    logits = np.load(rel("demo", "examples", ex["probmap"]))["prob_x1000"].astype(np.float32) / 1000.0
    ident = ex["id"]
    cut = (ex["record"].get("confluency_profile") or {}).get("cutoff", 0.0)    # the band and contour sit on it
    if out_dir:
        src = rel("demo", "examples", ex["image"])
        save_webp(src, os.path.join(out_dir, f"{ident}.webp"))
        save_webp(src, os.path.join(out_dir, f"{ident}_thumb.webp"), max_w=320, quality=78)
        save_alpha(1.0 / (1.0 + np.exp(-logits)), os.path.join(out_dir, f"{ident}_prob.png"))
        save_alpha((np.abs(logits - cut) < BAND_LOGIT).astype(np.float32), os.path.join(out_dir, f"{ident}_band.png"))
        with open(os.path.join(out_dir, f"{ident}_contour.json"), "w") as f:
            json.dump({"w": logits.shape[1], "h": logits.shape[0], "d": contour_path(logits, cut)}, f,
                      separators=(",", ":"))
    return {"map_w": int(logits.shape[1]), "map_h": int(logits.shape[0]),
            "band_pct_of_frame": round(float((np.abs(logits - cut) < BAND_LOGIT).mean()) * 100, 2)}


def og_image(out_path):
    """The link preview: a real held-out frame with its cell-probability layer, no text."""
    from PIL import Image
    ident = "c2c12_normal_20_40"
    im = Image.open(rel("demo", "examples", f"{ident}.png")).convert("L")
    logits = np.load(rel("demo", "examples", f"{ident}_probmap.npz"))["prob_x1000"].astype(np.float32) / 1000.0
    p = Image.fromarray((255 / (1 + np.exp(-logits))).astype(np.uint8)).resize(im.size, Image.BILINEAR)
    g = np.asarray(im, np.float32) / 255.0
    a = np.asarray(p, np.float32) / 255.0 * 0.55
    cyan = np.array([44, 199, 218], np.float32) / 255.0
    rgb = g[..., None] * (1 - a[..., None]) + (1 - (1 - g[..., None]) * (1 - cyan)) * a[..., None]
    out = Image.fromarray(np.clip(rgb * 255, 0, 255).astype(np.uint8), "RGB")
    w, h = out.size
    ch = round(w * 630 / 1200)
    out = out.crop((0, (h - ch) // 2, w, (h - ch) // 2 + ch)).resize((1200, 630), Image.LANCZOS)
    out.save(out_path, "JPEG", quality=86, optimize=True, progressive=True)


def replay_map_layers(name, out_dir):
    if not out_dir:
        return
    z = np.load(rel("demo", "replay_maps", f"{name}.npz"))["prob_x1000"].astype(np.float32) / 1000.0
    from PIL import Image
    for v, logits in enumerate(z):
        p = 1.0 / (1.0 + np.exp(-logits))
        a = Image.fromarray(np.clip(p * 255, 0, 255).astype(np.uint8), "L")
        a = a.resize((a.width // 2, a.height // 2), Image.LANCZOS)
        rgba = Image.merge("RGBA", [Image.new("L", a.size, 255)] * 3 + [a])
        rgba.save(os.path.join(out_dir, f"{name}_{v:02d}.png"), optimize=True)


# ── builders ──

def example_checkpoint(records):
    """The anchored checkpoint for the stored chain, made by culture.records.checkpoint
    from the stored records in chain order: their count and head hash. It ships with
    the page so the Records section can show what a chain alone misses; in deployment
    it is stored outside the log. created_at is kept from the last build while the
    chain is unchanged, so CI's rebuild of data.json is byte-identical."""
    import tempfile
    from culture.records import checkpoint, verify_chain
    with tempfile.TemporaryDirectory() as d:
        log = os.path.join(d, "examples.jsonl")
        with open(log, "w") as f:
            f.writelines(json.dumps(r, sort_keys=True) + "\n" for r in records)
        cp = checkpoint(log, scope="demo/examples/examples.json")
        try:
            with open(rel("site", "src", "data.json")) as f:
                old = json.load(f)["examples"].get("checkpoint")
        except (FileNotFoundError, KeyError, json.JSONDecodeError):
            old = None
        if old and all(old.get(k) == cp[k] for k in ("scope", "count", "head_hash", "schema_version", "hash_alg")):
            cp["created_at"] = old["created_at"]
        res = verify_chain(log, checkpoint=cp)
        assert res.ok and res.status == "intact", res
    return cp


def build_examples(img_dir):
    src = json.load(open(rel("demo", "examples", "examples.json")))
    by_id = {e["id"]: e for e in src["examples"]}
    # Change records (approved profile changes) open the stored chain, then the readings in export order.
    changes = src.get("changes", [])
    chain_order = [f"change{k + 1}" for k in range(len(changes))] + [e["id"] for e in src["examples"]]
    change_items = []
    for k, c in enumerate(changes):
        canon = canonical(c)
        assert hashlib.sha256(canon.encode()).hexdigest() == c["record_hash"], f"change{k + 1}"
        change_items.append({"id": f"change{k + 1}", "kind": "change", "label": f"Profile change: {c['after']['id']}",
                             "subject": c["subject"], "after": c["after"], "before": c["before"], "reason": c["reason"],
                             "approved_by": c["approved_by"]["name"], "evidence": c["evidence"],
                             "record": {"index": k + 1, "canonical": canon, "record_hash": c["record_hash"],
                                        "prev_record_hash": c["prev_record_hash"]}})
    out = []
    for ident in EXAMPLE_ORDER:
        e = by_id[ident]
        rec = e["record"]
        canon = canonical(rec)
        assert hashlib.sha256(canon.encode()).hexdigest() == rec["record_hash"], ident
        layers = example_layers(e, img_dir)
        c2c12 = e["kind"].startswith("c2c12")
        h, w = e["height"], e["width"]
        ty, tx = h // 2 - TILE_PX // 2, w // 2 - TILE_PX // 2
        a = e["anomaly"]
        out.append({
            "id": ident, "label": e["label"], "kind": e["kind"], "caption": e["caption"], "credit": e["credit"],
            "sequence": e.get("sequence"), "frame": e.get("frame"),
            "width": w, "height": h, "um_per_px": C2C12_UM_PER_PX if c2c12 else None,
            "image": f"{IMG_URL}/ex/{ident}.webp", "thumb": f"{IMG_URL}/ex/{ident}_thumb.webp",
            "prob": f"{IMG_URL}/ex/{ident}_prob.png", "band": f"{IMG_URL}/ex/{ident}_band.png",
            "contour": f"{IMG_URL}/ex/{ident}_contour.json", **layers,
            "confluency": {"pct": e["confluency"]["pct"], "confidence": e["confluency"]["confidence"],
                           "method": e["confluency"]["method"], "model": e["confluency"]["model_version"],
                           "borderline_fraction": e["confluency"]["extra"]["borderline_fraction"],
                           "instance_pct": e["confluency"]["extra"].get("instance_pct"),
                           "band_logit": BAND_LOGIT, "floor": CONF_FLOOR,
                           "ambiguity": boundary_ambiguity(e["confluency"]["confidence"]),
                           "ambiguity_ceiling": boundary_ambiguity(CONF_FLOOR),
                           "ambiguity_tooltip": AMBIGUITY_TOOLTIP,
                           "profile": rec.get("confluency_profile"), "interval": rec.get("confluency_interval")},
            "quality_gate": rec.get("quality_gate"),
            "target": e["target_confluency"],
            "anomaly": {"score": a["score"], "threshold": a["threshold"], "flag": a["flag"], "bin": a["bin_label"],
                        "z": a["z"], "model": a["model_version"],
                        "patches": [[r3(x) for x in row] for row in a["patch_distances"]],
                        "top": a["top_patches"],
                        "tile": {"x": tx, "y": ty, "size": TILE_PX},
                        "crop": {"x": tx + (TILE_PX - CROP_PX) // 2, "y": ty + (TILE_PX - CROP_PX) // 2,
                                 "size": CROP_PX, "patch": PATCH_PX}},
            "action": e["action"], "action_reason": e["action_reason"], "rationale": e["rationale"],
            "rules": rec["decided_by"], "device": e["device"], "generated_at": e["generated_at"][:10],
            "record": {"index": chain_order.index(ident) + 1, "canonical": canon,
                       "record_hash": rec["record_hash"], "prev_record_hash": rec["prev_record_hash"]},
        })
    return {"items": out, "changes": change_items, "chain_order": chain_order, "generated_by": src["generated_by"],
            "checkpoint": example_checkpoint(changes + [e["record"] for e in src["examples"]])}


def build_replays(img_dir):
    from culture.profiles import get_profile
    prof = get_profile(REPLAY_PROFILE)
    maps = json.load(open(rel("demo", "replay_maps", "maps.json")))
    out = []
    for name in REPLAY_ORDER:
        r = json.load(open(rel("demo", "replays", f"{name}.json")))
        layers = maps["replays"][name]["layers"]
        replay_map_layers(name, img_dir)
        f = r["forecast"]
        visits = []
        for v, L in zip(r["visits"], layers):
            assert v["visit"] == L["visit"]
            visits.append({
                "visit": v["visit"], "hours": v["hours"], "mean": v["confluency_mean"], "sd": v["confluency_sd"],
                "se": v["noise_se"], "fov": v["fov_confluency"], "fov_boxes": L["fov_boxes"],
                "quality_pass": v["quality_pass"], "quality_reasons": v["quality_reasons"], "reimage": v["reimage"],
                "flag": v["anomaly_flag"], "score": v["anomaly_score"], "threshold": v["anomaly_threshold"],
                "post_onset": v.get("post_onset", False), "map": f"{IMG_URL}/tl/{name}_{v['visit']:02d}.png",
                "map_sha256": L["map_sha256"],
            })
        # Only a forecast the replay stands behind is drawn; a suppressed one keeps
        # its fit in the replay JSON but shows its reason instead of a crossing time.
        shown = f.get("status") == "predicted"
        fc = (f.get("fit_curve") or {}) if shown else {}
        out.append({
            "scenario": name, "banner": r["banner"], "caption": r["caption"], "credit": r["credit"],
            "sequence": r["base_sequence_id"], "split": r["split"], "fault": r.get("fault"),
            "noise_band": r["noise_band"], "notes": r.get("notes", []), "summary": r["summary"],
            "target_note": r["target_note"],
            "profile": {"id": prof.id, "status": prof.status, "calibrated": prof.calibrated},
            "frame_hw": maps["frame_hw"], "um_per_px": C2C12_UM_PER_PX, "visits": visits,
            "forecast": {"status": f.get("status"), "model": f.get("chosen_model"), "target": f.get("target_pct"), "cut": f.get("cut_pct"),
                         "made_at_visit": f.get("made_at_visit"), "made_at_hours": f.get("made_at_hours"),
                         "t_star": f.get("t_star_hours") if shown else None,
                         "interval": f.get("interval_hours") if shown else None,
                         "suppressed_reason": f.get("suppressed_reason"),
                         "curve": [[r3(h), r3(m)] for h, m in zip(fc.get("hours", []), fc.get("mean", []))],
                         "backtest": f.get("backtest")},
        })
    return out


def build_profiles():
    """The confluency calibration profiles study (results/confluency_profiles.json, written by
    scripts/confluency_profiles.py) with each profile's live status from configs/confluency_profiles.yaml."""
    src = rel("results", "confluency_profiles.json")
    if not os.path.exists(src):
        return None
    doc = json.load(open(src))
    cfg = yaml.safe_load(open(rel("configs", "confluency_profiles.yaml")))["profiles"]
    order = ["c2c12_ker2018", "msc_phase", "evican_mixed", "livecell_incucyte"]
    items = []
    for pid in sorted(doc["results"], key=lambda k: order.index(k) if k in order else 9):
        r, p, c = doc["results"][pid], doc["profiles"][pid], cfg.get(pid, {})
        items.append({
            "id": pid, "label": c.get("label", pid), "status": c.get("status"), "study": r["status"],
            "n_calib": p["n_calib"], "n_test": r["n_test"], "cutoff": p["cutoff"], "band_pp": r3(p["band_pp"]),
            "shipped": {k: r3(v) for k, v in r["shipped"].items()}, "profile": {k: r3(v) for k, v in r["profile"].items()},
            "bands": [{k: (r3(v) if isinstance(v, float) else v) for k, v in b.items()} for b in r["bands"]],
            "coverage": r3(r["coverage"]), "calls": {T: {k: r3(v) if isinstance(v, float) else v for k, v in cc.items()}
                                                     for T, cc in r["calls"].items()},
            "acceptance": {k: {"verdict": v[0], "detail": v[1]} for k, v in r["acceptance"].items()},
            "transfer": {k: r3(v["mae"]) for k, v in r["transfer"].items()},
            "learning": {k: [r3(x) for x in v] for k, v in r["learning"].items()},
            "folds": [{k: r3(v) if isinstance(v, float) else v for k, v in f.items()} for f in r.get("folds", [])],
        })
    return {"items": items, "cutoffs": {k: v["cutoff"] for k, v in doc["profiles"].items()},
            "source": "results/confluency_profiles.md"}


def build_dense_test():
    """The passage-range test on a dense dataset no model had seen (mCellSeg): the sealed test
    (results/confluency_mcellseg.{md,json,csv}, scored once) and its pre-registered swapped replication
    (results/confluency_mcellseg_swap.{md,json,csv}, scored once). Every image, read by models that never
    trained on it, with the shipped method (C) and the fine-tuned one (F)."""
    srcs = [rel("results", f) for f in ("confluency_mcellseg.json", "confluency_mcellseg.csv",
                                        "confluency_mcellseg_swap.json", "confluency_mcellseg_swap.csv")]
    if not all(os.path.exists(p) for p in srcs):
        return None
    v1, v1_csv, sw, sw_csv = json.load(open(srcs[0])), srcs[1], json.load(open(srcs[2])), srcs[3]
    sys.path.insert(0, rel("scripts"))
    import confluency_mcellseg as mc      # the pre-registered limits, not retyped here
    cal = set(v1["calibrated_setups"])
    pts = [{"half": "sealed", "gt": r3(float(r["gt_pct"])), "C": r3(float(r["C_reading"])), "F": r3(float(r["F_reading"]))}
           for r in csv.DictReader(open(v1_csv)) if r["split"] == "test" and r["setup"] in cal]
    pts += [{"half": "swapped", "gt": r3(float(r["gt_pct"])), "C": r3(float(r["C_reading"])), "F": r3(float(r["F_reading"]))}
            for r in csv.DictReader(open(sw_csv)) if r["split"] == "test"]

    def r6(x):    # full enough that the page's toFixed(2) rounds as the results files do (7.9353 -> 7.94)
        return None if x is None else round(float(x), 6)

    def crit(c):
        keep = ("n", "n_60_90", "n_60_100", "n_ge_T", "B1_mae", "B2_mae", "B3_bias", "B4_passage", "B4_continue",
                "B4_review", "B4_decided", "B4_agree", "B4_ready_called_continue", "B5_covered", "B5_n", "review_share")
        return {k: (r6(c[k]) if isinstance(c[k], float) else c[k]) for k in keep} | {"verdicts": c["verdicts"]}

    def contrast(k):
        return {"diff": r6(k["mae_60_90_diff"]), "ci": [r6(x) for x in k["ci"]],
                "diff_all": r6(k["mae_all_diff"]), "ci_all": [r6(x) for x in k["ci_all"]]}

    def within5(arm, half=None):
        return sum(abs(p[arm] - p["gt"]) <= 5 for p in pts if half in (None, p["half"]))

    def wrong(path, keep):
        # decided calls at T on images at 60% or more that disagree with the experts: the expert value of each
        rows = [r for r in csv.DictReader(open(path)) if keep(r) and float(r["gt_pct"]) >= mc.LO]
        return {a: sorted(r3(float(r["gt_pct"])) for r in rows if r[f"{a}_call"] in ("passage", "continue")
                          and (r[f"{a}_call"] == "passage") != (float(r["gt_pct"]) >= mc.T)) for a in "CF"}

    w1 = wrong(v1_csv, lambda r: r["split"] == "test" and r["setup"] in cal)
    w2 = wrong(sw_csv, lambda r: r["split"] == "test")

    return {
        "dataset": "mCellSeg (Alam, Jackson, Lord & Meijering 2026), CC BY 4.0, doi:10.5281/zenodo.20174259",
        "setups": len(cal), "points": pts,
        # from the pre-registration's "What it cannot show" (results/confluency_mcellseg.md)
        "scope": "one lab, 20× and 40× objectives, two cell lines (HEK-293T and HUVEC), transmitted light",
        "sealed": {"C": crit(v1["criteria"]["C"]), "F": crit(v1["criteria"]["F"]), "contrast": contrast(v1["contrasts"]["C-F"]),
                   "within5": {a: within5(a, "sealed") for a in "CF"}, "wrong": w1,
                   "n_train": v1["fine_tuned_runs"]["mcellseg_ftF"]["n"]},
        "swapped": {"C": crit(sw["criteria"]["C"]), "F": crit(sw["criteria"]["F"]), "contrast": contrast(sw["contrast"]),
                    "within5": {a: within5(a, "swapped") for a in "CF"}, "wrong": w2,
                    "n_train": sw["fine_tuned_runs"]["mcellseg_swap_ftF"]["n"]},
        "both": {"C": crit(sw["both_halves"]["criteria"]["C"]), "F": crit(sw["both_halves"]["criteria"]["F"]),
                 "contrast": contrast(sw["both_halves"]["contrast"]), "within5": {a: within5(a) for a in "CF"},
                 "wrong": {a: sorted(w1[a] + w2[a]) for a in "CF"}},
        "limits": {"mae": mc.MAE_MAX, "bias": mc.BIAS_MAX, "agree": mc.AGREE_MIN, "cover": mc.COVER_MIN, "target": mc.T},
        "sources": ["results/confluency_mcellseg.md", "results/confluency_mcellseg_swap.md"],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--images", action="store_true")
    args = ap.parse_args()
    img_dir = None
    if args.images:
        for sub in ("ex", "tl"):
            os.makedirs(os.path.join(IMG_OUT, sub), exist_ok=True)
        # Rows 56-446 are the four panels; the figure's own titles above them are
        # too small at page scale, so the page sets them in HTML instead.
        fig = rel("demo", "figures", "contamination_scale.png")
        from PIL import Image
        save_webp(fig, os.path.join(IMG_OUT, "contamination_scale.webp"), crop=(0, 56, Image.open(fig).width, 447))
        og_image(os.path.join(SITE, "public", "og.jpg"))
    readme = open(rel("README.md")).read()
    det = yaml.safe_load(open(rel("configs", "detectability.yaml")))
    data = {
        "meta": {"rules": RULES_VERSION, "schema": SCHEMA_VERSION, "console_url": CONSOLE_URL, "repo_url": REPO_URL,
                 "branch": "slice-1b-compute-cache", "generated_by": "site/assets/build_data.py"},
        "examples": build_examples(os.path.join(IMG_OUT, "ex") if args.images else None),
        "replays": build_replays(os.path.join(IMG_OUT, "tl") if args.images else None),
        "detectability": {"tested_setup": det.get("tested_setup"), "note": det.get("provenance_note"),
                          "rows": det["rows"]},
        "validation": validation_rows(readme),
        "validation_intro": readme_paragraph(readme, "## Architecture validation (Phase A)"),
        "not_proven": readme_lead_paragraph(readme, "**What this does and doesn't prove.**"),
        "oversize_factor": re.search(r"bacteria ([\d.]+)× too large", readme).group(1),
        "results": results_rows(readme),
        "profiles": build_profiles(),
        "dense_test": build_dense_test(),
        # scripts/export_cutoff_examples.py, from results/confluency_cutoff.md: why 3.78 pp is not fully blind
        "cutoff_disclosure": json.load(open(rel("demo", "examples", "cutoff_calibrated.json")))["disclosure"]["text"],
        "decisions": readme_bullets(readme, "**What changed because of it**"),
        "review_rate": [{"group": r["group"], "sequences": int(r["sequences"]), "n": int(r["n"]),
                         "n_review": int(r["n_review"]), "pct": float(r["review_pct"]), "note": r["note"]}
                        for r in csv.DictReader(open(rel("results", "review_rate.csv")))],
        # scripts/review_rate.py: the current rules on cached readings and quality metrics, no model run
        "review_rate_v05": [{"rules": r["rules"], "profile": r["profile"], "target": float(r["target"]),
                             "group": r["group"], **{k: int(r[k]) for k in ("n", "reimage", "band_review", "held",
                                                                            "uncalibrated_review", "passage", "review")}}
                            for r in csv.DictReader(open(rel("results", "review_rate_v05.csv")))],
        "contamination_figure": f"{IMG_URL}/contamination_scale.webp",
    }
    with open(DATA_OUT, "w") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print("wrote", os.path.relpath(DATA_OUT, REPO), f"{os.path.getsize(DATA_OUT) / 1024:.0f} KB")


if __name__ == "__main__":
    main()
