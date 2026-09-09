"""Convert pipeline output into web-ready webp assets + a single data JSON for the landing page."""
import json, os, subprocess, base64, sys
import cv2, numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "assets2")
LAD = os.path.join(HERE, "ladder")
WEB = os.path.join(HERE, "web")
os.makedirs(WEB, exist_ok=True)

def cwebp(src, dst, q=78, lossless=False, alpha=False):
    cmd = ["cwebp", "-quiet", "-mt"]
    if lossless:
        cmd += ["-lossless", "-z", "9"]
    else:
        cmd += ["-q", str(q), "-m", "6"]
    if alpha:
        cmd += ["-alpha_q", "100"]
    cmd += [src, "-o", dst]
    subprocess.run(cmd, check=True)
    return os.path.getsize(dst)

res = json.load(open(os.path.join(SRC, "results.json")))
ladder = json.load(open(os.path.join(LAD, "ladder.json")))
records = [json.loads(l) for l in open(os.path.join(SRC, "events.jsonl")) if l.strip()]

total = 0
manifest = {}

# ── specimen plates + mask overlays ──
for name in ["A172", "BT474", "BV2", "Huh7", "Huh7contam", "normal", "contam", "detach", "imgq"]:
    base_png = os.path.join(SRC, f"{name}_base.png")
    mask_png = os.path.join(SRC, f"{name}_mask.png")

    b = cv2.imread(base_png, cv2.IMREAD_GRAYSCALE)
    # mild contrast normalisation so phase-contrast reads on a dark ground
    b = cv2.normalize(b, None, 0, 255, cv2.NORM_MINMAX)
    tmp = os.path.join(WEB, f"_{name}.png")
    cv2.imwrite(tmp, b)
    sz = cwebp(tmp, os.path.join(WEB, f"{name}.webp"), q=76)
    os.remove(tmp)
    total += sz

    m = cv2.imread(mask_png, cv2.IMREAD_GRAYSCALE)
    rgba = np.zeros((m.shape[0], m.shape[1], 4), np.uint8)
    rgba[:, :, 1] = 210          # green channel
    rgba[:, :, 0] = 10
    rgba[:, :, 2] = 40
    rgba[:, :, 3] = (m > 0).astype(np.uint8) * 255
    tmpm = os.path.join(WEB, f"_{name}_m.png")
    cv2.imwrite(tmpm, rgba)
    szm = cwebp(tmpm, os.path.join(WEB, f"{name}_mask.webp"), lossless=True, alpha=True)
    os.remove(tmpm)
    total += szm
    manifest[name] = {"base": sz, "mask": szm}
    print(f"{name:8s} base={sz/1024:7.1f}KB mask={szm/1024:7.1f}KB", flush=True)

# ── ladder tiles ──
lad_total = 0
for line in ladder:
    for sev in ["clean", "early", "mid", "late"]:
        p = os.path.join(LAD, f"{line}_{sev}.png")
        img = cv2.imread(p, cv2.IMREAD_GRAYSCALE)
        img = cv2.normalize(img, None, 0, 255, cv2.NORM_MINMAX)
        tmp = os.path.join(WEB, f"_l.png")
        cv2.imwrite(tmp, img)
        sz = cwebp(tmp, os.path.join(WEB, f"lad_{line}_{sev}.webp"), q=74)
        os.remove(tmp)
        lad_total += sz
print(f"ladder total = {lad_total/1024:.1f}KB", flush=True)
total += lad_total

print(f"TOTAL RAW = {total/1024:.1f}KB  -> base64 ≈ {total*1.34/1024:.1f}KB", flush=True)

# ── data bundle ──
bundle = {
    "records": records,
    "results": {k: {kk: vv for kk, vv in v.items() if kk != "record"} for k, v in res["results"].items()},
    "chain_intact": res["chain_intact"],
    "ladder": ladder,
}
with open(os.path.join(WEB, "data.json"), "w") as f:
    json.dump(bundle, f, separators=(",", ":"))
print("data.json", os.path.getsize(os.path.join(WEB, "data.json")) / 1024, "KB")
