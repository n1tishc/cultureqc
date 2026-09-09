"""Render the link-preview card and the favicon from real pipeline output.

The card is the one asset that cannot be inlined: crawlers do not fetch data:
URIs, so og:image has to be a real file at a real URL. The favicon can be, and
is, served from public/ — so this is the page's one external-request
rule by exactly one file.

Everything on the card is real: the field is the composited Huh7 frame the page
already ships, the mask is the segmenter's own output for that frame, the box is
the Grad-CAM evidence box the classifier drew on it, and the readouts and record
hash are read straight out of results.json.

    python site/assets/make_og.py     ->  site/public/og.png, site/public/favicon.png
"""
import base64, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.dirname(HERE)
SRC = os.path.join(HERE, "pipeline-output")

R = json.load(open(os.path.join(SRC, "results.json")))["results"]["Huh7contam"]
REC = R["record"]
BOX = R["boxes"][0]
TILE = 256


def b64(p):
    with open(p, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")


FIELD = "data:image/png;base64," + b64(os.path.join(SRC, REC["image_ref"]))
# The shipped mask, not the raw one beside results.json: the raw file is white
# cells on black, which multiplied into the field would black out everything the
# segmenter did not claim. This is the same green-on-white asset the page draws.
MASK = "data:image/webp;base64," + b64(
    os.path.join(SITE, "public", "img", "Huh7contam_mask.webp")
)
FONTS = os.path.join(HERE, "..", "src", "assets", "fonts")
ARCHIVO = b64(os.path.join(FONTS, "archivo-latin.woff2"))
PLEX = b64(os.path.join(FONTS, "plexmono-latin.woff2"))
PLEX6 = b64(os.path.join(FONTS, "plexmono-latin-600.woff2"))

# The evidence box is measured on a centred 256x256 crop; mapping it back to the
# 704x520 field offsets the origin and leaves the box's own size in tile pixels.
w, h = R["w"], R["h"]
ox, oy = (w - TILE) // 2, (h - TILE) // 2

# The field is shown cover-cropped so it fills the panel, which means the box
# cannot be placed in fractions of the original frame — the crop would slide the
# image out from under it and it would point at a region it was never measured
# on. So do the cover arithmetic here and place the box in panel coordinates:
# whatever the panel's proportions, the box lands on its evidence.
PLATE_W, PLATE_H = 560, 566
scale = max(PLATE_W / w, PLATE_H / h)
crop_x, crop_y = (w * scale - PLATE_W) / 2, (h * scale - PLATE_H) / 2
bx = (ox * scale - crop_x) / PLATE_W * 100
by = (oy * scale - crop_y) / PLATE_H * 100
bw = TILE * scale / PLATE_W * 100
bh = TILE * scale / PLATE_H * 100

# The logomark, identical in construction to the one Rail.jsx draws.
LOGO = """<svg viewBox="0 0 96 96" aria-hidden="true">
  <g fill="none" stroke="currentColor" stroke-width="2.4">
    <circle cx="48" cy="48" r="43"/><circle cx="48" cy="48" r="25" stroke-width="1.4"/>
  </g>
  <g fill="currentColor">
    <ellipse cx="39" cy="37" rx="5.2" ry="2.5" transform="rotate(-28 39 37)"/>
    <ellipse cx="52" cy="34" rx="4.1" ry="2.2" transform="rotate(64 52 34)"/>
    <ellipse cx="61" cy="44" rx="5.6" ry="2.4" transform="rotate(-12 61 44)"/>
    <ellipse cx="36" cy="52" rx="4.4" ry="2.3" transform="rotate(18 36 52)"/>
    <ellipse cx="49" cy="59" rx="5.8" ry="2.6" transform="rotate(-46 49 59)"/>
    <ellipse cx="60" cy="60" rx="3.9" ry="2.1" transform="rotate(30 60 60)"/>
    <ellipse cx="47" cy="46" rx="3.2" ry="1.9" transform="rotate(78 47 46)"/>
  </g>
</svg>"""

# The record rows the card prints, built from the same fields the first viewport
# prints, so the card and the page cannot disagree about what the run wrote.
ROWS = [
    ("flask_id", REC["flask_id"]),
    ("analysed_at", REC["analysed_at"].replace("T", " ")[:19] + "Z"),
    ("record_hash", REC["record_hash"][:46] + "…"),
    ("schema_version", REC["schema_version"]),
]
RECHTML = "".join(f"<b>{k}</b><i>{v}</i>" for k, v in ROWS)

CARD = f"""<!DOCTYPE html>
<meta charset="utf-8">
<style>
@font-face{{font-family:'Archivo';font-weight:100 900;font-stretch:62% 125%;
  src:url(data:font/woff2;base64,{ARCHIVO}) format('woff2');}}
@font-face{{font-family:'IBM Plex Mono';font-weight:400;
  src:url(data:font/woff2;base64,{PLEX}) format('woff2');}}
@font-face{{font-family:'IBM Plex Mono';font-weight:600;
  src:url(data:font/woff2;base64,{PLEX6}) format('woff2');}}
*{{box-sizing:border-box;margin:0}}
body{{width:1200px;height:630px;background:#fff;color:#0E1116;
  font-family:'Archivo',sans-serif;overflow:hidden}}
/* the application bar, exactly as the page wears it */
.bar{{height:64px;background:#0B0E12;color:#fff;display:flex;align-items:center;
  gap:10px;padding:0 32px;border-bottom:1px solid #232B35}}
.bar svg{{width:28px;height:28px;color:#7FB2F5;flex:none}}
.brand{{font-size:19px;font-weight:700;letter-spacing:-.018em}}
.brand i{{font-style:normal;color:#7FB2F5}}
.barmeta{{margin-left:auto;font-family:'IBM Plex Mono',monospace;font-size:12px;
  letter-spacing:.06em;color:#98A2AE}}
.barmeta b{{color:#fff;font-weight:400}}
.body{{display:grid;grid-template-columns:1fr {PLATE_W}px;height:566px}}
.copy{{padding:34px 34px 30px 32px;display:flex;flex-direction:column;
  justify-content:space-between;min-width:0}}
h1{{font-size:41px;line-height:1.08;font-weight:650;letter-spacing:-.032em;max-width:15ch}}
h1 em{{font-style:normal;color:#0B5FCE}}
.sub{{margin-top:16px;max-width:44ch;color:#39424E;font-size:16px;line-height:1.6}}
.sub b{{color:#0E1116;font-weight:600}}
.reads{{display:flex;border-top:1px solid #D8DDE4;border-bottom:1px solid #D8DDE4}}
.r{{padding:13px 22px 13px 0}}
.r+.r{{border-left:1px solid #D8DDE4;padding-left:24px}}
.r b{{display:block;font-family:'IBM Plex Mono',monospace;font-size:11px;font-weight:400;
  letter-spacing:.1em;color:#5A6572;margin-bottom:5px}}
.r span{{font-size:27px;font-weight:650;letter-spacing:-.03em;line-height:1.06;display:block}}
.r.f span{{color:#C0261B;font-size:21px}}
.rec{{display:grid;grid-template-columns:auto 1fr;gap:1px 14px;margin-top:16px;
  border:1px solid #D8DDE4;border-radius:4px;background:#F7F8FA;padding:11px 13px;
  font-family:'IBM Plex Mono',monospace;font-size:12px;line-height:1.6}}
.rec u{{grid-column:1/-1;text-decoration:none;font-size:11px;letter-spacing:.1em;
  text-transform:uppercase;color:#5A6572;margin-bottom:4px}}
.rec b{{font-weight:400;color:#5A6572;white-space:nowrap}}
.rec i{{font-style:normal;font-weight:600;color:#0E1116;white-space:nowrap;overflow:hidden}}
/* the field fills the panel; the box below is placed in panel coordinates by the
   cover arithmetic above, so the crop cannot slide it off its evidence */
.plate{{position:relative;background:#0C0E11;overflow:hidden;border-left:1px solid #D8DDE4}}
.fig{{position:absolute;inset:0}}
.fig img{{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;display:block}}
.fig .base{{filter:contrast(1.06)}}
/* the mask is bright green on white; multiplied in, the white is a no-op and
   only the pixels the segmenter claimed are stained */
.fig .mask{{mix-blend-mode:multiply;opacity:.9}}
.box{{position:absolute;border:2px solid #CC3520;
  left:{bx:.3f}%;top:{by:.3f}%;width:{bw:.3f}%;height:{bh:.3f}%}}
/* a CSS escape swallows the space that terminates it, so the separator needs
   two — one to close \\00b7 and one to actually print */
.box::after{{content:"E01 \\00b7  ANALYSED REGION, CENTRE 256\\00d7 256";position:absolute;
  left:-2px;bottom:100%;background:#CC3520;color:#fff;
  font-family:'IBM Plex Mono',monospace;font-size:11px;font-weight:600;
  letter-spacing:.04em;padding:3px 6px;white-space:nowrap}}
.tag{{position:absolute;left:0;bottom:0;right:0;padding:10px 14px;z-index:4;
  background:linear-gradient(0deg,rgba(12,14,17,.95),rgba(12,14,17,.7) 62%,transparent);
  font-family:'IBM Plex Mono',monospace;font-size:11px;letter-spacing:.03em;color:#B5BCC6}}
/* the status chip: a hard-cornered heavy box, because this field was refused */
.chip{{position:absolute;right:14px;top:14px;z-index:5;display:flex;align-items:baseline;
  gap:9px;padding:6px 13px;color:#C0261B;border:2.5px solid currentColor;
  background:rgba(255,255,255,.95);box-shadow:0 1px 3px rgba(14,17,22,.2)}}
.chip .t,.chip .d{{font-family:'IBM Plex Mono',monospace;font-size:11px;
  letter-spacing:.05em;color:#5A6572;line-height:1.3}}
.chip .m{{font-weight:700;font-size:13px;letter-spacing:.03em;text-transform:uppercase;
  line-height:1.3}}
</style>
<div class="bar">{LOGO}<div class="brand">culture<i>QC</i></div>
  <div class="barmeta">Schema {REC['schema_version']} &nbsp; <b>9 records</b></div></div>
<div class="body">
  <div class="copy">
    <div>
      <h1>One image in. Four bound outputs, <em>and a record you can verify.</em></h1>
      <p class="sub">A confluency estimate, a QC flag with the pixels that raised
        it, a recommended action, and a hash-chained record.
        <b>Software, not an instrument.</b></p>
    </div>
    <div>
      <div class="reads">
        <div class="r"><b>CONFLUENCY</b><span>{REC['confluency_pct']:.1f}%</span></div>
        <div class="r f"><b>QC FLAG</b><span>Contamination</span></div>
        <div class="r f"><b>ACTION</b><span>Human review</span></div>
      </div>
      <div class="rec"><u>Canonical record</u>{RECHTML}</div>
    </div>
  </div>
  <div class="plate">
    <div class="fig">
      <img class="base" src="{FIELD}" alt="">
      <img class="mask" src="{MASK}" alt="">
      <div class="box"></div>
      <div class="tag">REAL Huh7 FIELD, CONTAMINATION COMPOSITED IN &middot; {w}&times;{h}</div>
    </div>
    <div class="chip">
      <span class="t">QC</span>
      <span class="m">Contamination</span>
      <span class="d">{REC['flask_id']}</span>
    </div>
  </div>
</div>
"""

ICON = f"""<!DOCTYPE html>
<meta charset="utf-8">
<style>
*{{box-sizing:border-box;margin:0}}
body{{width:512px;height:512px;background:#0B0E12;display:flex;
  align-items:center;justify-content:center;overflow:hidden;color:#7FB2F5}}
.m{{width:380px;height:380px;display:flex;align-items:center;justify-content:center}}
.m svg{{width:100%;height:100%}}
</style>
<div class="m">{LOGO}</div>
"""


PROVENANCE = (
    "Rendered by site/assets/make_og.py: a headless Chromium screenshot of markup "
    "written in that script. Not an image-model output. "
)
CARD_PROV = PROVENANCE + (
    "Field, segmentation mask, evidence box, readouts and record fields all read "
    "from site/assets/pipeline-output/results.json and the PNGs beside it; the "
    "logomark is authored SVG in the same script. "
    "Regenerate with: python site/assets/make_og.py"
)
ICON_PROV = PROVENANCE + (
    "The mark is the authored logomark SVG (a ruled dish of cells) on the "
    "application bar's near-black, the same mark Rail.jsx draws. "
    "Regenerate with: python site/assets/make_og.py"
)


def stamp_provenance(path, text):
    """Write the raster's origin into the file itself, as a PNG tEXt chunk.

    A sidecar note is one `mv` away from being separated from the image it
    describes; the chunk travels with the bytes. Written here rather than only
    by hand, so regenerating the card does not quietly strip its own record.
    Same keyword the Impeccable tooling reads, so `embed-prompt --scan` sees it.
    """
    import binascii, struct

    payload = b"impeccable:prompt\x00" + text.encode("utf-8")
    chunk = (
        struct.pack(">I", len(payload))
        + b"tEXt"
        + payload
        + struct.pack(">I", binascii.crc32(b"tEXt" + payload) & 0xFFFFFFFF)
    )
    with open(path, "rb") as f:
        png = f.read()
    end = png.rindex(b"\x00\x00\x00\x00IEND")  # length-0 IEND, always last
    with open(path, "wb") as f:
        f.write(png[:end] + chunk + png[end:])


def shoot(html, path, w, h, provenance):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": w, "height": h}, device_scale_factor=1)
        pg.set_content(html)
        pg.wait_for_timeout(900)
        pg.screenshot(path=path)
        b.close()
    stamp_provenance(path, provenance)
    print(f"  wrote {path}  {os.path.getsize(path) // 1024} KB")


if __name__ == "__main__":
    shoot(CARD, os.path.join(SITE, "public", "og.png"), 1200, 630, CARD_PROV)
    shoot(ICON, os.path.join(SITE, "public", "favicon.png"), 512, 512, ICON_PROV)
