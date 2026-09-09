"""Assemble the single-file cultureQC landing page: template + inlined fonts + inlined webp + real pipeline data."""
import base64, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(HERE, "web")
SRC = os.path.join(HERE, "pipeline-output")
LAD = os.path.join(HERE, "ladder")
OUT = os.path.join(os.path.dirname(HERE), "index.html")
TEMPLATE = os.path.join(HERE, "template.html")

# Where the page will live, e.g. "https://cultureqc.example". Open Graph needs an
# absolute URL, so link previews stay off until this is filled in.
SITE_URL = "https://cultureqc.vercel.app"


def b64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")


def webp(name):
    return "data:image/webp;base64," + b64(os.path.join(WEB, name))


results = json.load(open(os.path.join(SRC, "results.json")))["results"]
records = [json.loads(l) for l in open(os.path.join(SRC, "events.jsonl")) if l.strip()]
ladder = json.load(open(os.path.join(LAD, "ladder.json")))

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
        "img": webp(f"{name}.webp"),
        "mask": webp(f"{name}_mask.webp"),
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
            "img": webp(f"lad_{line}_{sev}.webp"),
        })

data = {"leaves": leaves, "ladder": lad}

html = open(TEMPLATE).read()
html = html.replace("/*{{FONT_ARCHIVO}}*/", b64(os.path.join(HERE, "archivo-latin.woff2")))
html = html.replace("/*{{FONT_MARTIAN}}*/", b64(os.path.join(HERE, "martian-latin.woff2")))
payload = json.dumps(data, separators=(",", ":"))
assert "</script" not in payload
html = html.replace("/*{{DATA}}*/", payload)

# The favicon inlines, so it costs no request. og:image cannot: crawlers do not
# fetch data: URIs and Open Graph needs an absolute URL, so it is the single
# external asset on the page — and only once SITE_URL says where the page lives.
# Empty SITE_URL emits no og:image at all rather than a URL that 404s.
head = []
icon = os.path.join(os.path.dirname(HERE), "favicon.png")
if os.path.exists(icon):
    head.append('<link rel="icon" type="image/png" href="data:image/png;base64,%s">' % b64(icon))
if SITE_URL:
    base = SITE_URL.rstrip("/")
    head += ['<link rel="canonical" href="%s/">' % base,
             '<meta property="og:url" content="%s/">' % base,
             '<meta property="og:image" content="%s/og.png">' % base,
             '<meta property="og:image:width" content="1200">',
             '<meta property="og:image:height" content="630">',
             '<meta property="og:image:alt" content="A real Huh7 field with the '
             'classifier\'s evidence box drawn on it, beside its confluency, QC flag, '
             'recommended action and record hash.">']
else:
    head.append("<!-- og:image omitted: set SITE_URL in assemble.py once the page has a home -->")
html = html.replace("/*{{HEAD_EXTRA}}*/", "\n".join(head))

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w") as f:
    f.write(html)
print(f"wrote {OUT}  {os.path.getsize(OUT)/1024:.0f} KB")
