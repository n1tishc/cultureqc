"""
Product-path readings with the approved fine-tuned model (culture/finetuned.py), beside the shipped model.

The before/after picture (results/confluency_finetune_figure.md) was drawn by the research scripts, which read the
raw images. The product reads an image as 8-bit grayscale (culture/pipeline.py) and checks each model's weights
against the approvals log (culture/approvals.py) first. This runs the product path itself, on Colab, and compares
its readings with the research path's. Nothing here is scored against the experts. Rules fixed before the run, in
this file:

- Images: the 90 test images of the sealed mCellSeg test (results/confluency_mcellseg.md), each read once with
  `culture.pipeline.analyze(..., finetuned_id=RUN)` and the `uncalibrated` profile (mCellSeg has no product
  profile). Records go to one hash-chained log, LOG.
- Then one more reading of the first picture image, with the fine-tuned weights replaced by a copy with one byte
  changed (CULTUREQC_WEIGHTS_DIR): the record must show the refusal, with the shipped reading and the action the
  same as that image's first record.
- Compared (`compare`, on the Mac, no model): the product's fine-tuned reading against the research path's reading
  of the same weights at the same cutoff (results/confluency_finetune_figure_curves.json); the product's shipped
  reading against the committed zero-shot reading at the same cutoff (results/confluency_mcellseg_curves.json).
  Reported: mean, mean absolute and largest difference, and the images over TOL. Over TOL is reported, not fixed:
  then the picture's numbers are not presented as the product's.

    python scripts/finetuned_product_readings.py run        # Colab GPU (nb/09_finetuned_product.ipynb)
    .venv/bin/python scripts/finetuned_product_readings.py compare
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))
sys.path.insert(0, REPO)
os.chdir(REPO)

import confluency_mcellseg as m  # noqa: E402

RUN = "mcellseg_ftF_r2"
TOL = 2.0                    # pp, per image: product path against research path, same weights, same cutoff
LOG = os.path.join("results", "finetuned_product_readings.jsonl")
OUT_MD = os.path.join("results", "finetuned_product_readings.md")
FIGURE = os.path.join("results", "confluency_finetune_figure_curves.json")


def test_images() -> list[dict]:
    its = m.loaded()
    cal = m.calibrated_setups(its)
    return [i for i in its if i["setup"] in cal and i["split"] == "test"]


def cmd_run(a):
    from culture.approvals import approved, check
    from culture.finetuned import load_config, weights_file
    from culture.pipeline import analyze
    assert not os.path.exists(LOG), f"{LOG} exists: readings are made once"
    entry = load_config()[RUN]
    real = weights_file(entry)
    assert check("model", RUN, real).ok, "the fine-tuned weights do not match their approval"
    test = test_images()
    for k, i in enumerate(test):
        analyze(i["path"], flask_id=i["name"], cell_line=i["setup"], log_path=LOG, finetuned_id=RUN)
        if k % 10 == 0:
            print(k, len(test), flush=True)
    first = json.load(open(FIGURE))["chosen"][0]["name"]
    i = next(x for x in test if x["name"] == first)
    d = tempfile.mkdtemp()
    bad = os.path.join(d, os.path.basename(entry["path"]))
    shutil.copyfile(real, bad)
    with open(bad, "r+b") as f:
        f.seek(10_000_000)
        b = f.read(1)
        f.seek(10_000_000)
        f.write(bytes([b[0] ^ 1]))
    os.environ["CULTUREQC_WEIGHTS_DIR"] = d
    try:
        analyze(i["path"], flask_id=i["name"], cell_line=i["setup"], log_path=LOG, finetuned_id=RUN)
    finally:
        del os.environ["CULTUREQC_WEIGHTS_DIR"]
        shutil.rmtree(d)
    print("wrote", LOG, "approvals head", approved()["head"])


def stats(d: np.ndarray) -> str:
    return f"mean {d.mean():+.2f} pp, mean absolute {np.abs(d).mean():.2f} pp, largest {np.abs(d).max():.2f} pp"


def cmd_compare(a):
    import jsonschema
    from culture.records import verify_chain
    chain = verify_chain(LOG)
    assert chain.ok, chain.reason
    recs = [json.loads(x) for x in open(LOG) if x.strip()]
    schema = json.load(open(os.path.join("culture", "schema.json")))
    for r in recs:
        jsonschema.validate(r, schema)
    test = test_images()
    main, tampered = recs[:len(test)], recs[len(test):]
    assert [r["flask_id"] for r in main] == [i["name"] for i in test] and len(tampered) == 1
    j0 = m.GRID.index(0.0)
    R = json.load(open(FIGURE))
    Z = json.load(open(m.CURVES))["maps"]["zero"]
    ft = np.array([r["finetuned_reading"]["confluency_pct"] - R["retrained"][r["flask_id"]][j0] for r in main])
    sh = np.array([r["confluency_pct"] - Z[r["flask_id"]][j0] for r in main])
    over = [(r["flask_id"], f"{x:+.2f}", f"{y:+.2f}") for r, x, y in zip(main, ft, sh) if abs(x) > TOL or abs(y) > TOL]
    checks = {(r["model_check"]["status"], r["finetuned_reading"]["check"]["status"]) for r in main}
    t = tampered[0]
    same = next(r for r in main if r["flask_id"] == t["flask_id"])
    lines = ["# Product-path readings with the approved fine-tuned model", "",
             f"Generated by `scripts/finetuned_product_readings.py compare` from `{LOG}` ({len(recs)} records, chain "
             f"{chain.status}, every record valid against schema {recs[0]['schema_version']}). Not a new result: "
             "nothing here is compared with the experts.", "",
             f"- Model checks on the {len(main)} readings (shipped, fine-tuned): "
             + ", ".join(f"{a} / {b}" for a, b in sorted(checks)) + ".",
             f"- Fine-tuned, product path against research path (same weights, cutoff 0.0): {stats(ft)}.",
             f"- Shipped, product path against the committed zero-shot reading (cutoff 0.0): {stats(sh)}.",
             "- Anomaly check status: " + ", ".join(f"{k} {v}" for k, v in sorted(
                 {s: sum(r["anomaly_status"] == s for r in main) for s in {r["anomaly_status"] for r in main}}.items()))
             + " (its reference banks are in cache/, which the Colab bundle does not carry; without them the check "
               "returns `unavailable`).",
             f"- Images over {TOL} pp on either: " + ("none." if not over else
                                                     "; ".join(f"{n} (fine-tuned {x}, shipped {y})" for n, x, y in over)
                                                     + ". The picture's numbers are not presented as the product's."),
             "", "## One changed byte", "",
             f"`{t['flask_id']}` read again with a copy of the fine-tuned weights with one byte changed:", "",
             f"- Fine-tuned check: `{t['finetuned_reading']['check']['status']}`, "
             + ("no reading" if t["finetuned_reading"]["confluency_pct"] is None
                else f"reading {t['finetuned_reading']['confluency_pct']:.2f}%")
             + f"; reason: {t['finetuned_reading']['reason']}.",
             f"- Shipped reading {t['confluency_pct']:.2f}% and action `{t['recommended_action']}`, against "
             f"{same['confluency_pct']:.2f}% and `{same['recommended_action']}` in its first record.", "",
             "## The picture's four images, as the product reads them", "",
             "Both at cutoff 0.0 with no band: mCellSeg has no product profile, so the shipped reading is "
             "uncalibrated (the picture's left panels used the test's calibration profiles instead).", "",
             "| Image | Setup | Shipped | Fine-tuned (decides nothing) | Action |", "|---|---|---|---|---|"]
    for c in R["chosen"]:
        r = next(x for x in main if x["flask_id"] == c["name"])
        lines.append(f"| `{c['name']}` | {c['setup']} | {r['confluency_pct']:.1f}% | "
                     f"{r['finetuned_reading']['confluency_pct']:.1f}% | `{r['recommended_action']}` |")
    lines.append("")
    open(OUT_MD, "w").write("\n".join(lines))
    print("\n".join(lines))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for c in ("run", "compare"):
        sub.add_parser(c)
    a = ap.parse_args()
    {"run": cmd_run, "compare": cmd_compare}[a.cmd](a)


if __name__ == "__main__":
    main()
