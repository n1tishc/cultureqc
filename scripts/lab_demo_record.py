"""
The fine-tuned demo set through the console's own path, once, before the console is opened (Colab GPU,
nb/11_lab_demo.ipynb). Two jobs:

1. Checkpoint. Each demo image (demo/lab_demo.py) is read as the console's Analyze reads it: `uncalibrated`
   profile, target 80%, the fine-tuned model beside the shipped one, and this time with the anomaly check's
   reference banks present (nb/09 ran without them, so its anomaly check returned `unavailable`). Both weights
   checks must be `match`; the shipped and fine-tuned readings are compared with the product-path records of the
   same images (results/finetuned_product_readings.jsonl); the anomaly status and flag, the action and its reason
   are printed. What the console will show is known before anyone presents it.
2. Fallback. Each reading's record goes to one hash-chained log, and its results panel and overlay to one
   self-contained HTML page, labelled as a recorded run with the commit and the date, to open if the live console
   is unavailable.

    CULTUREQC_FINETUNED=mcellseg_ftF_r2 python scripts/lab_demo_record.py
"""

from __future__ import annotations

import base64
import html
import json
import os
import sys
from datetime import datetime, timezone

import cv2

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
os.chdir(REPO)

from culture.records import RecordWriter, verify_chain  # noqa: E402
from demo import lab_demo  # noqa: E402

OUT_DIR = os.path.join("cache", "lab_demo_recorded")
LOG = os.path.join(OUT_DIR, "lab_demo_records.jsonl")
PRODUCT = os.path.join("results", "finetuned_product_readings.jsonl")
TARGET = 80.0
TOL = 0.1                    # pp: same weights, same 8-bit read, same cutoff as the product-path records


def page(title: str, banner: str, overlay_png: str, results_html: str, css: str) -> str:
    img = base64.b64encode(open(overlay_png, "rb").read()).decode()
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>{html.escape(title)}</title>
<style>{css}
body {{ background: var(--bg-primary); color: var(--text-primary); font-family: system-ui, sans-serif; margin: 0; }}
.rec-banner {{ padding: 10px 16px; background: #3a2a05; color: #f5d27a; font-size: 13px; }}
.rec-main {{ display: flex; gap: 16px; padding: 16px; align-items: flex-start; }}
.rec-main img {{ width: 60%; height: auto; border-radius: 8px; }}
.rec-main .rc-stack {{ width: 40%; }}
.audit-details[open] .audit-json {{ max-height: 420px; overflow: auto; }}
</style></head><body><div class="rec-banner">{html.escape(banner)}</div>
<div class="rec-main"><img src="data:image/png;base64,{img}" alt="overlay">{results_html}</div></body></html>"""


def main():
    from demo import app
    from demo.analysis import analyze_image, build_record
    model = lab_demo.model_id()
    assert model, f"set {lab_demo.MODEL_ENV} (the launcher sets it)"
    images = lab_demo.available()
    assert len(images) == len(lab_demo.IMAGES), "demo images missing or not the listed bytes"
    os.makedirs(OUT_DIR, exist_ok=True)
    assert not os.path.exists(LOG), f"{LOG} exists: one recorded run per session"
    writer = RecordWriter(LOG)
    product = {}
    for x in open(PRODUCT):
        if x.strip():
            r = json.loads(x)
            product.setdefault(r["flask_id"], r)                 # the first record of each image
    commit = open("COMMIT").read().strip()[:7] if os.path.exists("COMMIT") else "local"
    when = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    css = open(os.path.join("demo", "style.css")).read()
    rows, links = [], []
    for k, lab in enumerate(images):
        img = cv2.imread(lab["path"], cv2.IMREAD_GRAYSCALE)
        a = analyze_image(img, lab["path"], lab["cell_line"], TARGET, profile_id="uncalibrated", finetuned_id=model)
        rec = writer.append(build_record(a, lab["path"], lab["cell_line"]))
        fr, mc = rec["finetuned_reading"], rec["model_check"]
        assert mc["status"] == "match" and fr["check"]["status"] == "match", (lab["name"], mc, fr["check"])
        p = product[lab["name"]]
        d_ship = rec["confluency_pct"] - p["confluency_pct"]
        d_ft = fr["confluency_pct"] - p["finetuned_reading"]["confluency_pct"]
        rows.append((lab["name"], lab["experts_pct"], rec["confluency_pct"], d_ship, fr["confluency_pct"], d_ft,
                     rec["anomaly_status"], rec.get("anomaly_flag"), rec["recommended_action"], rec["action_reason"]))
        overlay = os.path.join(OUT_DIR, f"overlay_{k}.png")
        cv2.imwrite(overlay, cv2.cvtColor(a.overlay, cv2.COLOR_RGB2BGR))
        panel = app.render_results(
            anomaly_html=app.render_anomaly(img, a.anomaly), demoted=a.demoted, qc_calibrated=a.qc.calibrated,
            qc_flag=a.qc.flag, qc_confidence=a.qc.confidence, per_class_probs=a.qc.per_class_probs,
            evidence_region_count=len(a.evidence_boxes), confluency_pct=a.confluency.pct,
            confluency_confidence=a.confluency.confidence, confluency_method=a.confluency.method,
            target_confluency=TARGET, action=a.action, rationale=a.rationale["rationale"], record=rec,
            chain_ok=verify_chain(LOG).ok, record_count=writer.record_count, finetuned=a.finetuned, lab=lab)
        name = f"{k + 1}_{lab['name'][:-4]}.html"
        banner = (f"Recorded run, not live: read by the console's own code on {when} from commit {commit}. "
                  f"{lab['label']}. Record {writer.record_count} of the chain in lab_demo_records.jsonl.")
        open(os.path.join(OUT_DIR, name), "w").write(page(lab["label"], banner, overlay, panel, css))
        links.append(f'<li><a href="{name}">{html.escape(lab["label"])}</a></li>')
    open(os.path.join(OUT_DIR, "index.html"), "w").write(
        f"<!doctype html><meta charset='utf-8'><title>Recorded runs</title><h3>Recorded runs, {when}, commit "
        f"{commit}</h3><ul>{''.join(links)}</ul>")
    chain = verify_chain(LOG)
    print(f"chain {chain.status}, {chain.n_records} records")
    print("| Image | Experts | Shipped (Δ vs product run) | Fine-tuned (Δ) | Anomaly | Action | Reason |")
    over = []
    for n, e, s, ds, f, df, ast, afl, act, why in rows:
        print(f"| {n} | {e:.1f} | {s:.2f} ({ds:+.3f}) | {f:.2f} ({df:+.3f}) | {ast} {afl or ''} | {act} | {why} |")
        if abs(ds) > TOL or abs(df) > TOL:
            over.append(n)
    print("readings over", TOL, "pp from the product-path records:", over or "none")


if __name__ == "__main__":
    main()
