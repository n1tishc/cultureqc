"""Regenerate every page asset: hero contaminated field, severity ladder, and the 9-leaf hash chain.

Sprites are rescaled to 0.45x so their optical size is plausible against the cells in the field
(median sprite 37px -> ~17px, against Huh7/A172 cells of roughly that size). The shipped
classifier is then run on the result unchanged: this is a harder test than the project's own
synthesis, not an easier one.
"""
import json, os, sys, traceback
sys.path.insert(0, "/Users/nitishc/Desktop/projs/cultureqc")
sys.path.insert(0, "/Users/nitishc/Desktop/projs/cultureqc/scripts")

import cv2, numpy as np
from synth_contamination import load_sprites, get_cell_mask, add_bacteria
from culture.seg import cpsam_confluency, threshold_confluency, _get_model as _get_seg_model
from culture.qc import qc_classify
from culture.rules import decide, LineConfig
from culture.rationale import generate_rationale
from culture.records import RecordWriter, hash_file, verify_chain

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "assets2")
LAD = os.path.join(HERE, "ladder2")
for d in (OUT, LAD):
    os.makedirs(d, exist_ok=True)
LOG = os.path.join(OUT, "events.jsonl")
if os.path.exists(LOG):
    os.remove(LOG)

SPRITE_SCALE = 0.45
TILE = 256

raw = load_sprites(os.path.join(ROOT, "data/sprites/bacteria"))
sprites = []
for s in raw:
    nh, nw = max(3, int(s.shape[0] * SPRITE_SCALE)), max(3, int(s.shape[1] * SPRITE_SCALE))
    sprites.append(cv2.resize(s, (nw, nh), interpolation=cv2.INTER_AREA))
print(f"sprites {len(sprites)} rescaled x{SPRITE_SCALE}", flush=True)

REAL = {
    "A172": "test-data/A172_Phase_C7_1_00d00h00m_1.tif",
    "BT474": "test-data/BT474_Phase_D3_1_04d04h00m_4.tif",
    "BV2": "test-data/BV2_Phase_A4_2_02d08h00m_3.tif",
    "Huh7": "test-data/Huh7_Phase_A12_1_02d16h00m_1.tif",
}

# ─────────────── 1. the hero: a real full field carrying real contamination ───────────────
hero_src = os.path.join(ROOT, REAL["Huh7"])
img = cv2.imread(hero_src, cv2.IMREAD_GRAYSCALE)
h, w = img.shape[:2]
bg = ~get_cell_mask(img).astype(bool)
passes = int(round((w * h) / (TILE * TILE)))
rng = np.random.default_rng(7)
hero, n_hero = img.copy(), 0
for _ in range(passes):
    hero, k = add_bacteria(hero, bg, sprites, severity="early", rng=rng)
    n_hero += k
hero_path = os.path.join(OUT, "Huh7_contaminated_field.png")
cv2.imwrite(hero_path, hero)
print(f"hero field: {n_hero} organisms over {passes} tile-areas", flush=True)

# ─────────────── 2. severity ladder ───────────────
ladder = {}
for line, rel in REAL.items():
    im = cv2.imread(os.path.join(ROOT, rel), cv2.IMREAD_GRAYSCALE)
    hh, ww = im.shape[:2]
    cy, cx = hh // 2, ww // 2
    tile = im[cy - 128:cy + 128, cx - 128:cx + 128].copy()
    bgm = ~get_cell_mask(tile).astype(bool)
    ladder[line] = {}
    for sev in ["clean", "early", "mid", "late"]:
        r_ = np.random.default_rng(42)
        if sev == "clean":
            t, n = tile.copy(), 0
        else:
            t, n = add_bacteria(tile.copy(), bgm, sprites, severity=sev, rng=r_)
        res = qc_classify(t, run_gradcam=True)
        cv2.imwrite(os.path.join(LAD, f"{line}_{sev}.png"), t)
        ladder[line][sev] = {
            "n_sprites": n, "flag": res.flag, "confidence": res.confidence,
            "probs": res.per_class_probs,
            "boxes": [{"x": round(b[0]/256,5), "y": round(b[1]/256,5),
                       "w": round(b[2]/256,5), "h": round(b[3]/256,5)} for b in (res.evidence_bboxes or [])],
        }
        print(f"  {line:6s} {sev:6s} n={n:<4} -> {res.flag:24s} {res.confidence:.4f}", flush=True)
json.dump(ladder, open(os.path.join(LAD, "ladder.json"), "w"), indent=2)

# ─────────────── 3. the nine-leaf chain ───────────────
IMAGES = [
    ("BV2",       os.path.join(ROOT, REAL["BV2"]),   "real"),
    ("A172",      os.path.join(ROOT, REAL["A172"]),  "real"),
    ("Huh7",      os.path.join(ROOT, REAL["Huh7"]),  "real"),
    ("BT474",     os.path.join(ROOT, REAL["BT474"]), "real"),
    ("Huh7contam", hero_path,                        "composite"),
    ("contam",    os.path.join(ROOT, "test-data/contam_00015.png"),  "tile"),
    ("detach",    os.path.join(ROOT, "test-data/detach_00003.png"),  "tile"),
    ("imgq",      os.path.join(ROOT, "test-data/imgq_00012.png"),    "tile"),
    ("normal",    os.path.join(ROOT, "test-data/normal_00005.png"),  "tile"),
]
LINE_OF = {"Huh7contam": "Huh7"}

writer = RecordWriter(LOG)
results = {}
seg_model = _get_seg_model()

for name, path, kind in IMAGES:
    print(f"=== {name}", flush=True)
    im = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    hh, ww = im.shape[:2]
    conf = cpsam_confluency(im, method="probmap")
    base = threshold_confluency(im)
    if hh >= TILE and ww >= TILE:
        cy, cx = hh // 2, ww // 2
        tile = im[cy-128:cy+128, cx-128:cx+128]
    else:
        tile = cv2.resize(im, (TILE, TILE))
    qc = qc_classify(tile, run_gradcam=True)

    masks, flows, _ = seg_model.eval(im, diameter=None, channels=[0, 0])
    cell_mask = flows[2] > 0

    sy, sx = hh / TILE, ww / TILE
    oy = (hh - TILE) // 2 if hh >= TILE else 0
    ox = (ww - TILE) // 2 if ww >= TILE else 0
    boxes = []
    for bx, by, bw, bh in (qc.evidence_bboxes or []):
        ix, iy = bx*sx + ox, by*sy + oy
        boxes.append({"x": round(ix/ww,5), "y": round(iy/hh,5),
                      "w": round((bw*sx)/ww,5), "h": round((bh*sy)/hh,5)})

    line = LINE_OF.get(name, name)
    cfg = LineConfig(cell_line=line, target_confluency=80.0)
    action, reason = decide(confluency_pct=conf.pct, confluency_confidence=conf.confidence,
                            qc_flag=qc.flag, qc_confidence=qc.confidence, line_config=cfg,
                            hours_since_passage=48.0, hours_since_feed=24.0)
    rat = generate_rationale(qc_flag=qc.flag, qc_confidence=qc.confidence,
                             evidence_bbox=qc.evidence_bbox, confluency_pct=conf.pct,
                             target_confluency=80.0, action=action, tile_size=TILE,
                             use_vlm=False, image_path=path)

    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    rec = {
        "schema_version": "0.2", "flask_id": f"F-{name}", "cell_line": line,
        "protocol_stage": None, "captured_at": now,
        "image_ref": os.path.basename(path), "image_hash": hash_file(path),
        "pixel_size_um": None,
        "confluency_pct": conf.pct, "confluency_confidence": conf.confidence,
        "confluency_method": conf.method,
        "qc_flag": qc.flag, "qc_confidence": qc.confidence, "qc_severity": None,
        "qc_evidence_bbox": list(qc.evidence_bbox) if qc.evidence_bbox else None,
        "qc_rationale": rat["rationale"], "growth_trend": None, "eta_to_target_hours": None,
        "recommended_action": action, "action_reason": reason, "decided_by": "rules_v0.2",
        "model_versions": {"seg": conf.model_version, "qc": qc.model_version, "vlm": rat["method"]},
        "model_weights_hash": None, "reviewed_by": None, "review_outcome": None,
    }
    final = writer.append(rec)

    cv2.imwrite(os.path.join(OUT, f"{name}_base.png"), im)
    cv2.imwrite(os.path.join(OUT, f"{name}_mask.png"), (cell_mask.astype(np.uint8) * 255))

    results[name] = {
        "file": os.path.basename(path), "kind": kind, "w": ww, "h": hh,
        "confluency_probmap": conf.pct, "confluency_confidence": conf.confidence,
        "confluency_method": conf.method,
        "confluency_threshold_baseline": base.pct,
        "qc_flag": qc.flag, "qc_confidence": qc.confidence,
        "per_class_probs": qc.per_class_probs, "boxes": boxes,
        "action": action, "action_reason": reason, "rationale": rat["rationale"],
        "n_organisms": n_hero if name == "Huh7contam" else None,
        "record": final,
    }
    print(f"    {conf.pct:6.2f}% base={base.pct:6.2f}% {qc.flag:24s} {qc.confidence:.4f} boxes={len(boxes)} -> {action}", flush=True)

ok, bad = verify_chain(LOG)
json.dump({"chain_intact": ok, "bad_line": bad, "sprite_scale": SPRITE_SCALE,
           "hero_organisms": n_hero, "results": results},
          open(os.path.join(OUT, "results.json"), "w"), indent=2, default=str)
print("DONE chain_intact=", ok, flush=True)
