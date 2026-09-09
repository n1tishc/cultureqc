"""Render the link-preview card and the favicon from real pipeline output.

The card is the one asset that cannot be inlined: crawlers do not fetch data:
URIs, so og:image has to be a real file at a real URL. The favicon can be, and
is, inlined by assemble.py — so this breaks the page's zero-external-requests
rule by exactly one file.

Everything on the card is real: the field is the composited Huh7 frame the page
already ships, the box is the Grad-CAM evidence box the classifier drew on it,
and the readouts and record hash are read straight out of results.json.

    python site/src/make_og.py        ->  site/og.png, site/favicon.png
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
ARCHIVO = b64(os.path.join(HERE, "archivo-latin.woff2"))
MARTIAN = b64(os.path.join(HERE, "martian-latin.woff2"))

# The evidence box is measured on a centred 256x256 crop; mapping it back to the
# 704x520 field offsets the origin and leaves the box's own size in tile pixels.
w, h = R["w"], R["h"]
ox, oy = (w - TILE) // 2, (h - TILE) // 2

# The plate shows the field cover-cropped so it fills the panel, which means the
# box cannot be placed in fractions of the original frame — the crop would slide
# the image out from under it and it would point at a region it was never
# measured on. So do the cover arithmetic here and place the box in panel
# coordinates: whatever the plate's proportions, the box lands on its evidence.
PLATE_W, PLATE_H = 470, 630
scale = max(PLATE_W / w, PLATE_H / h)
crop_x, crop_y = (w * scale - PLATE_W) / 2, (h * scale - PLATE_H) / 2
bx = (ox * scale - crop_x) / PLATE_W * 100
by = (oy * scale - crop_y) / PLATE_H * 100
bw = TILE * scale / PLATE_W * 100
bh = TILE * scale / PLATE_H * 100

CARD = f"""<!DOCTYPE html>
<meta charset="utf-8">
<style>
@font-face{{font-family:'Archivo';font-weight:100 900;font-stretch:62% 125%;
  src:url(data:font/woff2;base64,{ARCHIVO}) format('woff2');}}
@font-face{{font-family:'Martian Mono';font-weight:300 700;font-stretch:75% 112.5%;
  src:url(data:font/woff2;base64,{MARTIAN}) format('woff2');}}
*{{box-sizing:border-box;margin:0}}
body{{width:1200px;height:630px;background:#08191A;color:#EBE5D6;
  font-family:'Archivo',sans-serif;display:grid;grid-template-columns:1fr 470px;
  overflow:hidden}}
.copy{{padding:56px 44px 48px 60px;display:flex;flex-direction:column;justify-content:space-between}}
.brand{{font-size:26px;font-weight:800;font-variation-settings:'wdth' 78;letter-spacing:-.01em}}
.brand i{{font-style:normal;color:#E2C21A}}
h1{{font-size:56px;line-height:.97;font-weight:800;font-variation-settings:'wdth' 66;
  text-transform:uppercase;letter-spacing:-.005em}}
.reads{{display:flex;gap:34px;border-top:2px solid #17403D;padding-top:18px}}
.r b{{display:block;font-family:'Martian Mono',monospace;font-size:11px;font-weight:400;
  letter-spacing:.14em;color:#8A968F;margin-bottom:7px}}
.r span{{font-size:25px;font-weight:800;font-variation-settings:'wdth' 76;
  text-transform:uppercase;letter-spacing:-.01em}}
.r.f span{{color:#E0492E}}
.hash{{font-family:'Martian Mono',monospace;font-size:10.5px;letter-spacing:.06em;
  color:#8A968F;margin-top:16px}}
.hash u{{text-decoration:none;color:#A08C25}}
/* The field fills the plate; the box below is placed in panel coordinates by
   the cover arithmetic above, so the crop cannot slide it off its evidence. */
/* obsolete note removed:
   image under the evidence box, which is positioned in fractions of the full
   704x520 frame — the box would then point at a region it was not measured on. */
.plate{{position:relative;border-left:1px solid #123230;background:#04100F;overflow:hidden}}
.fig{{position:absolute;inset:0}}
.fig img{{width:100%;height:100%;object-fit:cover;display:block;filter:contrast(1.05)}}
.box{{position:absolute;border:2px solid #E0492E;
  left:{bx:.3f}%;top:{by:.3f}%;width:{bw:.3f}%;height:{bh:.3f}%}}
.box::after{{content:"ANALYSED REGION 256\\00d7 256";position:absolute;left:-2px;top:100%;
  background:#E0492E;color:#04100F;font-family:'Martian Mono',monospace;font-size:9.5px;
  font-weight:700;letter-spacing:.1em;padding:3px 6px;white-space:nowrap}}
.tag{{position:absolute;left:0;bottom:0;right:0;padding:11px 14px;
  background:rgba(4,16,15,.88);border-top:1px solid #123230;
  font-family:'Martian Mono',monospace;font-size:10px;letter-spacing:.09em;color:#B8C0B8}}
</style>
<div class="copy">
  <div class="brand">culture<i>QC</i></div>
  <h1>One image in.<br>Four bound outputs,<br>and a record<br>you can verify.</h1>
  <div>
    <div class="reads">
      <div class="r"><b>CONFLUENCY</b><span>{REC['confluency_pct']:.1f}%</span></div>
      <div class="r f"><b>QC FLAG</b><span>Contamination</span></div>
      <div class="r"><b>ACTION</b><span>Human review</span></div>
    </div>
    <p class="hash">RECORD <u>{REC['record_hash'][:24]}</u>&#8230; &middot;
      seg {REC['model_versions']['seg']} &middot; qc {REC['model_versions']['qc']}</p>
  </div>
</div>
<div class="plate">
  <div class="fig">
    <img src="{FIELD}" alt="">
    <div class="box"></div>
    <div class="tag">REAL Huh7 FIELD, CONTAMINATION COMPOSITED IN &middot; {w}&times;{h}</div>
  </div>
</div>
"""

ICON = f"""<!DOCTYPE html>
<meta charset="utf-8">
<style>
@font-face{{font-family:'Archivo';font-weight:100 900;font-stretch:62% 125%;
  src:url(data:font/woff2;base64,{ARCHIVO}) format('woff2');}}
*{{box-sizing:border-box;margin:0}}
body{{width:512px;height:512px;background:#08191A;display:flex;
  align-items:center;justify-content:center;overflow:hidden}}
.m{{width:352px;height:352px;border:26px solid #E2C21A;display:flex;
  align-items:center;justify-content:center;
  font-family:'Archivo',sans-serif;font-weight:800;font-size:196px;
  font-variation-settings:'wdth' 70;color:#EBE5D6;letter-spacing:-.04em;
  line-height:1;padding-bottom:14px}}
</style>
<div class="m">QC</div>
"""


def shoot(html, path, w, h):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": w, "height": h}, device_scale_factor=1)
        pg.set_content(html)
        pg.wait_for_timeout(900)
        pg.screenshot(path=path)
        b.close()
    print(f"  wrote {path}  {os.path.getsize(path) // 1024} KB")


if __name__ == "__main__":
    shoot(CARD, os.path.join(SITE, "og.png"), 1200, 630)
    shoot(ICON, os.path.join(SITE, "favicon.png"), 512, 512)
