"""Build the page's reference data: real pipeline output → site/src/data.json.

This replaces the old assemble.py, which inlined everything as base64 into a
single 767 KB index.html. Vite bundles the app now, so the images are copied to
site/public/img/ as real files the browser can cache, and the JSON carries their
URLs instead of their bytes.

    python site/assets/build_data.py

The arithmetic below (fix_boxes, fix_rationale, canonical) is carried over
unchanged. `canonical()` in particular must stay byte-identical to what
culture/records.py hashes, because the page recomputes those digests in the
browser and shows them failing if they disagree.
"""
import base64, json, os, re, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.dirname(HERE)
WEB = os.path.join(HERE, "web")
SRC = os.path.join(HERE, "pipeline-output")
LAD = os.path.join(HERE, "ladder")
IMG_OUT = os.path.join(SITE, "public", "img")
DATA_OUT = os.path.join(SITE, "src", "data.json")

results = json.load(open(os.path.join(SRC, "results.json")))["results"]
records = [json.loads(l) for l in open(os.path.join(SRC, "events.jsonl")) if l.strip()]
ladder = json.load(open(os.path.join(LAD, "ladder.json")))


def img(name):
    """Copy a webp into public/ and return the URL the page will request."""
    src = os.path.join(WEB, name)
    os.makedirs(IMG_OUT, exist_ok=True)
    shutil.copy2(src, os.path.join(IMG_OUT, name))
    return "/img/" + name


# canonical JSON exactly as culture/records.py hashes it
def canonical(rec):
    r = dict(rec)
    r.pop("record_hash", None)
    return json.dumps(r, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


TILE = 256

QUAD_RE = re.compile(r"\bin the (?:upper|lower|centre|center)-(?:left|right|centre|center) quadrant\b")


def fix_rationale(text, tile_bbox):
    """A box covering essentially the whole analysed tile has no quadrant; say so."""
    if not tile_bbox:
        return text
    _, _, bw, bh = tile_bbox
    if (bw * bh) / float(TILE * TILE) >= 0.85:
        return QUAD_RE.sub("across the whole analysed field", text)
    return text


def fix_boxes(boxes, w, h):
    out = []
    for b in boxes:
        bw = b["w"] * TILE / w if w > TILE else b["w"]
        bh = b["h"] * TILE / h if h > TILE else b["h"]
        x, y = b["x"], b["y"]
        bw, bh = min(bw, 1.0 - x), min(bh, 1.0 - y)
        out.append({"x": round(x, 5), "y": round(y, 5),
                    "w": round(max(bw, 0.01), 5), "h": round(max(bh, 0.01), 5)})
    return out


ORDER = ["BV2", "A172", "Huh7", "BT474", "Huh7contam", "contam", "detach", "imgq", "normal"]
SHORT = {
    "BV2": "BV2", "A172": "A172", "Huh7": "HUH7", "BT474": "BT474",
    "Huh7contam": "HUH7+C", "contam": "CONTAM", "detach": "DETACH",
    "imgq": "IMGQ", "normal": "CLEAN",
}
TITLE = {
    "A172": "A172 glioblastoma",
    "BT474": "BT474 breast carcinoma",
    "BV2": "BV2 microglia",
    "Huh7": "Huh7 hepatocytes",
    "Huh7contam": "Huh7 hepatocytes",
    "contam": "Contamination challenge tile",
    "detach": "Detachment challenge tile",
    "imgq": "Image-quality challenge tile",
    "normal": "Clean control tile",
}
KIND = {
    "A172": "real field", "BT474": "real field", "BV2": "real field", "Huh7": "real field",
    "Huh7contam": "real field, contamination composited in",
    "contam": "challenge tile", "detach": "challenge tile",
    "imgq": "challenge tile", "normal": "challenge tile",
}

leaves = []
for i, name in enumerate(ORDER):
    r = results[name]
    rec = records[i]

    leaves.append({
        "id": name,
        "short": SHORT[name],
        "title": TITLE[name],
        "kind": KIND[name],
        "file": r["file"],
        "w": r["w"], "h": r["h"],
        "img": img(f"{name}.webp"),
        "mask": img(f"{name}_mask.webp"),
        "confluency": r["confluency_probmap"],
        "confluencyConf": r["confluency_confidence"],
        "method": r["confluency_method"],
        "baseline": r["confluency_threshold_baseline"],
        "flag": r["qc_flag"],
        "qcConf": r["qc_confidence"],
        "probs": r["per_class_probs"],
        "boxes": fix_boxes(r["boxes"], r["w"], r["h"]),
        "action": r["action"],
        "actionReason": r["action_reason"],
        "rationale": fix_rationale(r["rationale"], r["record"]["qc_evidence_bbox"]),
        "organisms": r.get("n_organisms"),
        "record": rec,
        "canonical": canonical(rec),
    })

lad = []
for line in ["A172", "BT474", "BV2", "Huh7"]:
    for sev in ["clean", "early", "mid", "late"]:
        e = ladder[line][sev]
        lad.append({
            "line": line, "sev": sev, "n": e["n_sprites"], "flag": e["flag"],
            "conf": e["confidence"], "boxes": e["boxes"],
            "img": img(f"lad_{line}_{sev}.webp"),
        })

os.makedirs(os.path.dirname(DATA_OUT), exist_ok=True)
with open(DATA_OUT, "w") as f:
    json.dump({"leaves": leaves, "ladder": lad}, f, separators=(",", ":"))

print(f"wrote {DATA_OUT}  {os.path.getsize(DATA_OUT)/1024:.0f} KB")
print(f"wrote {len(os.listdir(IMG_OUT))} images to {IMG_OUT}")
