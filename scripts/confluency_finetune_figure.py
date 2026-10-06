"""
A before/after picture for the mCellSeg passage-range test (results/confluency_mcellseg.md): what the
calibration profile per setup covers, and what the fine-tuned model covers, on four dense test images.

The fine-tuned models of that test were not kept (Colab deletes a runtime's disk). The picture is drawn with a
model retrained with the same recipe on the same 79 calibration images (`mcellseg_ftF_r2`). Its readings are
used only to check that it reproduces the scored model; they are never scored against the experts again (the
test was scored once). Rules fixed before the run, in this file:

- Images: from the sealed test's test images, one per calibrated setup, the one at 60-90% expert confluency
  closest to 75%, ties by name (`chosen`). Whatever images that gives are drawn; none is swapped afterwards.
- Cutoffs: the scored profiles' (results/confluency_mcellseg.json): C per setup on the zero-shot map, F per setup
  on the retrained map. Masks are made on the GPU at full resolution, so the coverage drawn is the reading shown.
- Tolerance: the picture is drawn only if each chosen image's retrained reading is within TOL pp of its scored F
  reading; otherwise `figure` reports the miss instead.

GPU steps run on Colab (nb/08_finetune_figure.ipynb):

    python scripts/confluency_finetune_figure.py train      # retrain with the recipe on the 79 calibration images
    python scripts/confluency_finetune_figure.py readings   # reproducibility readings + full-size masks of the 4

CPU, on the Mac:

    .venv/bin/python scripts/confluency_finetune_figure.py figure
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))
os.chdir(REPO)

import confluency_mcellseg as m  # noqa: E402

RUN = "mcellseg_ftF_r2"
TOL = 2.0                    # pp: each drawn image's retrained reading vs its scored F reading
MID = 75.0                   # the image per setup closest to the middle of the passage range
DISP = 900                   # px, longest side of each drawn panel
MASKS = os.path.join("cache", "figure_masks")
CURVES = os.path.join("results", "confluency_finetune_figure_curves.json")
OUT_PNG = os.path.join("results", "confluency_finetune_figure.png")
OUT_MD = os.path.join("results", "confluency_finetune_figure.md")


def scored() -> dict:
    return json.load(open(m.OUT_JSON))


def chosen(its: list[dict], cal: list[str]) -> list[dict]:
    out = []
    for s in cal:
        dense = [i for i in its if i["setup"] == s and i["split"] == "test" and m.LO <= i["gt"] <= m.HI]
        out.append(min(dense, key=lambda i: (abs(i["gt"] - MID), i["name"])))
    return out


def cutoffs(cal: list[str]) -> dict:
    prof = scored()["profiles"]
    return {s: {"C": prof[f"C/{s}"]["cutoff"], "F": prof[f"F/{s}"]["cutoff"]} for s in cal}


# ── GPU steps (Colab) ───────────────────────────────────────────────────────

def cmd_train(a):
    from confluency_finetune import RUNS, train_run
    its = m.loaded()
    cal = m.calibrated_setups(its)
    pool = [i for i in its if i["setup"] in cal and i["split"] == "calib"]
    committed = json.load(open(m.CURVES))["manifests"]["mcellseg_ftF"]["train_images"]
    assert sorted(i["name"] for i in pool) == sorted(committed), "not the scored model's training set"
    pool = sorted(pool, key=lambda i: committed.index(i["name"]))       # same order as the scored run
    if os.path.exists(os.path.join(RUNS, RUN, "manifest.json")):
        print(RUN, "already trained")
        return
    man = train_run(RUN, pool, label_fn=m.instance_mask)
    print(json.dumps({k: man[k] for k in ("run", "n", "weights_sha256", "seconds")}), flush=True)


def cmd_readings(a):
    import cv2
    from confluency_finetune import RUNS, environment, model
    its = m.loaded()
    cal = m.calibrated_setups(its)
    cuts = cutoffs(cal)
    pick = chosen(its, cal)
    test = [i for i in its if i["setup"] in cal and i["split"] == "test"]
    ft, base = model(RUN), model("base")
    os.makedirs(MASKS, exist_ok=True)
    out = {"generated_by": "scripts/confluency_finetune_figure.py readings", "environment": environment(),
           "grid": m.GRID, "run": json.load(open(os.path.join(RUNS, RUN, "manifest.json"))),
           "retrained": {}, "chosen": []}
    for k, i in enumerate(test):
        p = ft.eval(m.gray(i["path"]), diameter=None, channels=[0, 0], compute_masks=False)[1][2]
        out["retrained"][i["name"]] = [float(x) for x in m.curve(p)]
        if i in pick:
            z = base.eval(m.gray(i["path"]), diameter=None, channels=[0, 0], compute_masks=False)[1][2]
            c, f = cuts[i["setup"]]["C"], cuts[i["setup"]]["F"]
            cv2.imwrite(os.path.join(MASKS, i["name"][:-4] + "_C.png"), ((z > c) * 255).astype(np.uint8))
            cv2.imwrite(os.path.join(MASKS, i["name"][:-4] + "_F.png"), ((p > f) * 255).astype(np.uint8))
            out["chosen"].append({"name": i["name"], "setup": i["setup"], "gt": i["gt"],
                                  "zero_curve": [float(x) for x in m.curve(z)],
                                  "C_cut": c, "F_cut": f, "C_drawn": float((z > c).mean() * 100),
                                  "F_drawn": float((p > f).mean() * 100)})
        if k % 10 == 0:
            print(k, len(test), flush=True)
    json.dump(out, open(CURVES, "w"))
    print("wrote", CURVES, "and", len(out["chosen"]) * 2, "masks in", MASKS)


# ── picture (Mac) ───────────────────────────────────────────────────────────

def cmd_figure(a):
    import csv
    import cv2
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from skimage.segmentation import find_boundaries
    its = m.loaded()
    cal = m.calibrated_setups(its)
    R = json.load(open(CURVES))
    rows = {r["name"]: r for r in csv.DictReader(open(m.OUT_CSV))}
    cuts = cutoffs(cal)
    names = [i["name"] for i in chosen(its, cal)]
    assert [c["name"] for c in R["chosen"]] == [i["name"] for i in its if i["name"] in names], "chosen images differ"

    # reproducibility: the retrained model's readings at the F cutoff against the scored model's, all 90 images
    j = {s: m.GRID.index(cuts[s]["F"]) for s in cal}
    setup = {i["name"]: i["setup"] for i in its}
    d = np.array([R["retrained"][n][j[setup[n]]] - float(rows[n]["F_reading"]) for n in R["retrained"]])
    Z = json.load(open(m.CURVES))["maps"]["zero"]
    zero_gap = max(abs(a - b) for c in R["chosen"] for a, b in zip(c["zero_curve"], Z[c["name"]]))
    lines = ["# Before/after picture: what calibration covers, what fine-tuning covers", "",
             "Generated by `scripts/confluency_finetune_figure.py figure` from "
             f"`{CURVES}` (computed on {R['environment'].get('gpu')}, commit `{(R['environment'].get('commit') or '?')[:7]}`).", "",
             "**Not a new result.** The test in `results/confluency_mcellseg.md` was scored once. The fine-tuned model it "
             f"scored was not kept, so this picture is drawn with `{RUN}`, retrained with the same recipe on the same "
             f"{R['run']['n']} calibration images (weights SHA-256 `{R['run']['weights_sha256'][:16]}…`). Its readings are "
             "compared with the scored model's, never with the experts.", "",
             f"- Retrained against scored fine-tuned readings, all {len(d)} test images, at each setup's F cutoff: "
             f"mean {d.mean():+.2f} pp, mean absolute {np.abs(d).mean():.2f} pp, largest {np.abs(d).max():.2f} pp.",
             f"- Zero-shot readings of the drawn images against the committed ones, every cutoff: largest difference {zero_gap:.3f} pp.", ""]
    miss = []
    for c in R["chosen"]:
        g = c["F_drawn"] - float(rows[c["name"]]["F_reading"])
        if abs(g) > TOL:
            miss.append(f"{c['name']} ({g:+.2f} pp)")
    if miss:
        lines += [f"**Tolerance missed** (each drawn image within {TOL} pp of its scored reading): " + ", ".join(miss)
                  + ". The picture is not drawn.", ""]
        open(OUT_MD, "w").write("\n".join(lines))
        print("\n".join(lines))
        return

    fig, axes = plt.subplots(len(R["chosen"]), 2, figsize=(9.2, 4.55 * len(R["chosen"])))
    for row, c in zip(axes, R["chosen"]):
        i = next(x for x in its if x["name"] == c["name"])
        full = m.gray(i["path"]).astype(np.float32)
        size = (round(full.shape[1] * DISP / max(full.shape)), round(full.shape[0] * DISP / max(full.shape)))
        img = cv2.resize(full, size, interpolation=cv2.INTER_AREA)       # display size; coverage drawn from full-size masks
        lo, hi = np.percentile(img, (1, 99))
        img = np.clip((img - lo) / max(hi - lo, 1e-6), 0, 1)
        union = cv2.resize((m.instance_mask(i["mask"]) > 0).astype(np.uint8), size, interpolation=cv2.INTER_NEAREST) > 0
        expert = cv2.dilate(find_boundaries(union, mode="inner").astype(np.uint8), np.ones((2, 2), np.uint8)) > 0
        r = rows[c["name"]]
        for ax, arm, title in ((row[0], "C", "calibration profile per setup"), (row[1], "F", "fine-tuned, then calibrated")):
            cov = cv2.imread(os.path.join(MASKS, c["name"][:-4] + f"_{arm}.png"), cv2.IMREAD_GRAYSCALE)
            cov = cv2.resize(cov, size, interpolation=cv2.INTER_AREA) >= 128
            rgb = np.dstack([img] * 3)
            rgb[cov] = rgb[cov] * 0.45 + np.array([0.17, 0.78, 0.85]) * 0.55          # cyan: what the model covers
            rgb[expert] = [1.0, 0.85, 0.1]                                          # yellow: the experts' outline
            ax.imshow(rgb)
            ax.set_axis_off()
            read = float(r[f"{arm}_reading"])
            drawn = c[f"{arm}_drawn"]
            ax.set_title(f"{i['setup']} · {title}\nreading {read:.1f}% (drawn {drawn:.1f}%) · experts {c['gt']:.1f}%", fontsize=9.5)
    fig.suptitle("mCellSeg test images (Alam et al. 2026, CC BY 4.0): cyan = covered by the reading, yellow = experts' outline",
                 fontsize=10.5)
    fig.tight_layout(rect=[0, 0, 1, 0.985])
    fig.savefig(OUT_PNG, dpi=110)
    lines += [f"Drawn: one test image per setup, the one at 60–90% closest to {MID:.0f}% (rule fixed before the run). "
              f"Each drawn reading is within {TOL} pp of the scored one. Readings are the scored model's; '(drawn …)' is the "
              "retrained model's at full resolution.", "", f"![before/after]({os.path.basename(OUT_PNG)})", ""]
    open(OUT_MD, "w").write("\n".join(lines))
    print("\n".join(lines))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for c in ("train", "readings", "figure", "show"):
        sub.add_parser(c)
    a = ap.parse_args()
    if a.cmd == "show":                     # masks only: which images the rule picks
        its = m.loaded()
        for i in chosen(its, m.calibrated_setups(its)):
            print(i["setup"], i["name"], round(i["gt"], 1))
        return
    {"train": cmd_train, "readings": cmd_readings, "figure": cmd_figure}[a.cmd](a)


if __name__ == "__main__":
    main()
