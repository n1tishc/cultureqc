"""
Fine-tuning Cellpose-SAM on a setup's own labelled images: does it read dense cells better than calibration alone?

Development runs only (MSC, leave one population out). These images have already been scored as whole
images and as dense quarters (results/confluency_profiles.md, results/confluency_dense_tiles.md), so nothing
here is a held-out result: it checks that the recipe works, beside the sealed test in
results/confluency_mcellseg.md, and compares alternatives (rescaling; SAMCell and DINOCell, each run by its
own script in its own environment: scripts/alt_model_samcell.py, scripts/alt_model_dinocell.py).

GPU steps run on Colab (nb/06_confluency_evidence.ipynb):

    python scripts/confluency_finetune.py train --holdout 218-4 --n 20       # fine-tune on 20 images of the other two
    python scripts/confluency_finetune.py maps --run msc_218-4_n20_s0         # read the held-out population
    python scripts/confluency_finetune.py maps --run base                     # zero-shot, same device and code path
    python scripts/confluency_finetune.py maps --run base_d89                 # zero-shot, rescaled to 89 px cells
    python scripts/confluency_finetune.py curves                              # readings at every cutoff -> results/

    python scripts/confluency_finetune.py final --n 20                        # nb/07: 20 images of all three (seed 0)

CPU, on the Mac:

    .venv/bin/python scripts/confluency_finetune.py dev                       # results/confluency_finetune_dev.md

Recipe: the one Cellpose documents for fine-tuning Cellpose-SAM (learning rate 1e-5, weight decay 0.1, 100
epochs, batch size 1), not tuned here. Labels: the MSC masks are binary, so connected components stand in for
instances; the cell-probability output the reading uses is trained on foreground vs background either way.
89 px is the median equivalent diameter of the connected components in the MSC masks of images under 25%
(where components are mostly single cells).

Weights and maps stay under cache/ (gitignored). `curves` writes the readings at every cutoff, per image and
per dense quarter, with each run's manifest (training images, weights SHA-256), to
results/confluency_finetune_dev_curves.json; `dev` reads only that file.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone

import cv2
import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))
os.chdir(REPO)

from confluency_profiles import GRID, msc_items  # noqa: E402

RUNS = os.path.join("cache", "finetune")
MAPS = os.path.join("cache", "probmaps_ft")
ALT_ROOT = os.path.join("cache", "probmaps_alt")
POPS = ["218-4", "218-5", "218-6"]
RECIPE = {"learning_rate": 1e-5, "weight_decay": 0.1, "n_epochs": 100, "batch_size": 1}
# other models (development only): map key, cutoff grid on their own output, and their own default cutoff
ALTS = {"samcell": ("dist", [0.01, 0.03, 0.05, 0.07, 0.09, 0.12, 0.15, 0.2, 0.25, 0.3], 0.09,
                    "SAMCell-Generalist (distance map)"),
        "dinocell": ("prob", [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9], 0.5,
                     "DINOCell (cell probability)")}
LO, HI = 60.0, 90.0
CURVES = os.path.join("results", "confluency_finetune_dev_curves.json")
OUT_MD = os.path.join("results", "confluency_finetune_dev.md")
OUT_JSON = os.path.join("results", "confluency_finetune_dev.json")


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def device():
    import torch
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("mps") if torch.backends.mps.is_available() else torch.device("cpu")


def model(run: str):
    from cellpose import models
    if run == "base" or run.startswith("base_d"):
        return models.CellposeModel(gpu=True, device=device())
    man = json.load(open(os.path.join(RUNS, run, "manifest.json")))
    assert sha256(man["weights"]) == man["weights_sha256"], run
    return models.CellposeModel(gpu=True, device=device(), pretrained_model=man["weights"])


def gray(path: str) -> np.ndarray:
    img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    assert img is not None, path
    return img


def instances(mask_path: str) -> np.ndarray:
    from skimage.measure import label
    m = cv2.imread(mask_path, cv2.IMREAD_UNCHANGED)
    assert m is not None, mask_path
    return label(m > 0).astype(np.int32)


def environment() -> dict:
    import torch
    sha = None
    if os.path.exists("COMMIT"):                      # the Colab bundle is a git archive; COMMIT names it
        sha = open("COMMIT").read().strip()
    else:
        try:
            sha = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip() or None
        except OSError:
            pass
    try:
        from importlib.metadata import version
        cp = version("cellpose")
    except Exception:
        cp = "?"
    return {"commit": sha, "torch": torch.__version__, "cellpose": cp, "device": str(device()),
            "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None}


def train_run(name: str, items: list[dict], label_fn=instances) -> dict:
    from cellpose import train
    out = os.path.join(RUNS, name)
    os.makedirs(out, exist_ok=True)
    X = [gray(i["path"]) for i in items]
    Y = [label_fn(i["mask"]) for i in items]
    net = model("base")
    t0 = time.time()
    path = train.train_seg(net.net, train_data=X, train_labels=Y, save_path=out, model_name=name,
                           min_train_masks=1, **RECIPE)
    path = str(path[0] if isinstance(path, tuple) else path)
    man = {"run": name, "recipe": RECIPE, "train_images": [i["name"] for i in items], "n": len(items),
           "weights": path, "weights_sha256": sha256(path), "seconds": round(time.time() - t0, 1),
           "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "environment": environment()}
    json.dump(man, open(os.path.join(out, "manifest.json"), "w"), indent=1)
    return man


def run_map(run: str, src: str, name: str, path: str, mdl=None) -> np.ndarray:
    dst = os.path.join(MAPS, run, src, name + ".npz")
    if not os.path.exists(dst):
        mdl = mdl or model(run)
        diam = float(run[len("base_d"):]) if run.startswith("base_d") else None
        _, flows, _ = mdl.eval(gray(path), diameter=diam, channels=[0, 0], compute_masks=False)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        np.savez_compressed(dst, prob=flows[2].astype(np.float16))
    return np.load(dst)["prob"].astype(np.float32)


# ── GPU steps (Colab) ───────────────────────────────────────────────────────

def dev_name(holdout: str, n: int, seed: int) -> str:
    return f"msc_{holdout}_n{n}_s{seed}"


def cmd_train(a):
    items = msc_items()
    assert len(items) == 320, len(items)
    cal = [i for i in items if i["group"] != a.holdout]
    rng = np.random.default_rng(a.seed)
    pick = sorted(rng.choice(len(cal), a.n, replace=False)) if a.n < len(cal) else range(len(cal))
    name = dev_name(a.holdout, a.n, a.seed)
    if os.path.exists(os.path.join(RUNS, name, "manifest.json")):
        print(name, "already trained")
        return
    man = train_run(name, [cal[k] for k in pick])
    print(json.dumps({k: man[k] for k in ("run", "n", "weights_sha256", "seconds")}))


def cmd_final(a):
    """The model a fine-tuned MSC profile would use, if the repository owner approves one: the development
    runs' recipe and n, drawn at random (seed 0) from all three populations. Fixed before training. Its cutoff
    and band would come from the development runs' out-of-population readings, not from this model's
    readings of its own setup. A measurement until approved: nothing in the product loads it."""
    items = msc_items()
    assert len(items) == 320, len(items)
    rng = np.random.default_rng(a.seed)
    pick = sorted(rng.choice(len(items), a.n, replace=False))
    name = f"msc_all_n{a.n}_s{a.seed}"
    if os.path.exists(os.path.join(RUNS, name, "manifest.json")):
        print(name, "already trained")
        return
    man = train_run(name, [items[k] for k in pick])
    print(json.dumps({k: man[k] for k in ("run", "n", "weights_sha256", "seconds")}))


def cmd_maps(a):
    items = msc_items()
    assert len(items) == 320, len(items)
    if a.run == "base" or a.run.startswith("base_d"):
        todo = items
    else:
        holdout = json.load(open(os.path.join(RUNS, a.run, "manifest.json")))["run"].split("_")[1]
        todo = [i for i in items if i["group"] == holdout]
    mdl = None
    t0 = time.time()
    for k, i in enumerate(todo):
        if not os.path.exists(os.path.join(MAPS, a.run, "msc", i["name"] + ".npz")):
            mdl = mdl or model(a.run)
        run_map(a.run, "msc", i["name"], i["path"], mdl)
        if k % 40 == 0:
            print(a.run, k, len(todo), f"{time.time() - t0:.0f}s", flush=True)


def cmd_curves(a):
    """Readings at every cutoff, whole image and each dense quarter, for every map set present."""
    from confluency_dense_tiles import regions
    items = msc_items()
    quarters = regions(items, 2, LO, HI)
    out = {"generated_by": "scripts/confluency_finetune.py curves", "environment": environment(),
           "grid": GRID, "alt_grids": {k: v[1] for k, v in ALTS.items()},
           "gt": {i["name"]: float((cv2.imread(i["mask"], cv2.IMREAD_GRAYSCALE) > 0).mean() * 100) for i in items},
           "group": {i["name"]: i["group"] for i in items},
           "quarters": [{"name": q["name"], "cell": q["cell"], "gt": q["gt"]} for q in quarters],
           "runs": {}, "manifests": {}}

    def add(key: str, path_of, grid: list[float], field: str):
        rows = {}
        for i in items:
            p = path_of(i["name"])
            if not os.path.exists(p):
                continue
            m = np.load(p)[field].astype(np.float32)
            rows[i["name"]] = {"whole": [float((m > c).mean() * 100) for c in grid],
                               "quarters": {str(q["cell"]): [float((m[q["ys"], q["xs"]] > c).mean() * 100) for c in grid]
                                            for q in quarters if q["name"] == i["name"]}}
        if rows:
            out["runs"][key] = rows
            print(key, len(rows), flush=True)

    for run in sorted(os.listdir(MAPS)) if os.path.isdir(MAPS) else []:
        add(run, lambda n, r=run: os.path.join(MAPS, r, "msc", n + ".npz"), GRID, "prob")
        if os.path.exists(os.path.join(RUNS, run, "manifest.json")):
            out["manifests"][run] = json.load(open(os.path.join(RUNS, run, "manifest.json")))
    for key, (field, grid, _, _) in ALTS.items():
        add(key, lambda n, k=key: os.path.join(ALT_ROOT, k, "msc", n + ".npz"), grid, field)
        if os.path.exists(os.path.join(ALT_ROOT, key, "manifest.json")):
            out["manifests"][key] = json.load(open(os.path.join(ALT_ROOT, key, "manifest.json")))
    json.dump(out, open(CURVES, "w"))
    print("wrote", CURVES)


# ── development report (CPU) ────────────────────────────────────────────────

def summarise(err: list[float]) -> dict:
    e = np.array(err)
    return {"n": int(len(e)), "mae": float(np.abs(e).mean()) if len(e) else None,
            "bias": float(e.mean()) if len(e) else None, "over10": int((np.abs(e) > 10).sum())}


def score_arm(C: dict, rows_of, j_of) -> dict:
    """rows_of(pop) -> {name: row} of the map set that reads that population; j_of(pop) -> cutoff index."""
    whole, dense_whole, dense_q, used = [], [], [], []
    for h in POPS:
        rows = rows_of(h)
        test = [n for n, g in C["group"].items() if g == h]
        if rows is None or not all(n in rows for n in test):
            continue
        used.append(h)
        j = j_of(h)
        for n in test:
            e = rows[n]["whole"][j] - C["gt"][n]
            whole.append(e)
            if LO <= C["gt"][n] <= HI:
                dense_whole.append(e)
            for q in (q for q in C["quarters"] if q["name"] == n):
                dense_q.append(rows[n]["quarters"][str(q["cell"])][j] - q["gt"])
    return {"populations": used, "whole": summarise(whole), "whole_60_90": summarise(dense_whole),
            "dense_quarters": summarise(dense_q)}


def calibrated_j(C: dict, rows: dict, h: str, grid: list[float]) -> int:
    """The cutoff with the lowest whole-image MAE on the other two populations (ties to the one nearest 0)."""
    cal = [n for n, g in C["group"].items() if g != h]
    mae = np.array([np.mean([abs(rows[n]["whole"][j] - C["gt"][n]) for n in cal]) for j in range(len(grid))])
    best = np.flatnonzero(np.isclose(mae, mae.min()))
    return int(min(best, key=lambda j: abs(grid[j])))


def cmd_dev(a):
    C = json.load(open(CURVES))
    grid = C["grid"]
    j0 = grid.index(0.0)
    R = C["runs"]
    arms = {}
    if "base" in R:
        arms["zero-shot, cutoff 0.0"] = score_arm(C, lambda h: R["base"], lambda h: j0)
        arms["zero-shot, calibrated cutoff (other two populations)"] = score_arm(
            C, lambda h: R["base"], lambda h: calibrated_j(C, R["base"], h, grid))
    for run in sorted(r for r in R if r.startswith("base_d")):
        arms[f"zero-shot rescaled to {run[6:]} px cells, calibrated cutoff"] = score_arm(
            C, lambda h, r=run: R[r], lambda h, r=run: calibrated_j(C, R[r], h, grid))
    ft = sorted(r for r in R if r.startswith("msc_"))
    for n in sorted({r.split("_n")[1].split("_")[0] for r in ft}):
        def rows_of(h, n=n):
            run = next((r for r in ft if r.startswith(f"msc_{h}_n{n}_")), None)
            return R.get(run) if run else None
        arms[f"fine-tuned on {n} images (other two populations), cutoff 0.0"] = score_arm(C, rows_of, lambda h: j0)
    for key, (_, _, own, label) in ALTS.items():
        if key in R:
            g = C["alt_grids"][key]
            arms[f"{label}, its own cutoff {own}"] = score_arm(C, lambda h, k=key: R[k], lambda h, g=g, o=own: g.index(o))
            arms[f"{label}, calibrated cutoff (other two populations)"] = score_arm(
                C, lambda h, k=key: R[k], lambda h, k=key, g=g: calibrated_j(C, R[k], h, g))
    json.dump({"generated_by": "scripts/confluency_finetune.py dev", "arms": arms, "environment": C["environment"],
               "runs": {k: {f: m.get(f) for f in ("run", "n", "weights_sha256", "seconds")} for k, m in C["manifests"].items()}},
              open(OUT_JSON, "w"), indent=1)
    write_dev_md(arms, C["manifests"], C["environment"])
    print(json.dumps(arms, indent=1))


def f(v, s="+.2f"):
    return "—" if v is None else format(v, s)


def write_dev_md(arms: dict, manifests: dict, env: dict) -> None:
    lines = [
        "# Fine-tuning and alternatives on the MSC images: development runs",
        "",
        "**Status: development, not a held-out result.** These 320 MSC images were already scored as whole",
        "images (`results/confluency_profiles.md`) and as dense quarters (`results/confluency_dense_tiles.md`).",
        "The runs here check the fine-tuning recipe and compare alternatives; the held-out answer is the",
        "sealed test in `results/confluency_mcellseg.md`. Generated by `scripts/confluency_finetune.py dev` from",
        f"`{CURVES}` (maps computed on {env.get('gpu') or env.get('device')}, commit `{(env.get('commit') or '?')[:7]}`).",
        "",
        "Each population is held out in turn. Calibrated cutoffs are picked on the other two populations' whole",
        "images. Fine-tuned models train on 20 images drawn at random (seed 0) from the other two populations,",
        "with the documented recipe (learning rate 1e-5, weight decay 0.1, 100 epochs, batch 1).",
        "",
        "| arm | whole images: MAE / bias (n) | whole 60–90%: MAE / bias (n) | dense quarters 60–90%: MAE / bias (n), >10 pp |",
        "|---|---|---|---|",
    ]
    for arm, r in arms.items():
        w, d, q = r["whole"], r["whole_60_90"], r["dense_quarters"]
        lines.append(f"| {arm} | {f(w['mae'], '.2f')} / {f(w['bias'])} ({w['n']}) | "
                     f"{f(d['mae'], '.2f')} / {f(d['bias'])} ({d['n']}) | {f(q['mae'], '.2f')} / {f(q['bias'])} ({q['n']}), {q['over10']} |")
    lines += ["", "Runs:", ""]
    for k, m in manifests.items():
        lines.append(f"- `{k}`: " + (f"{m['n']} training images, {m['seconds'] / 60:.0f} min, " if "n" in m else "")
                     + f"weights SHA-256 `{m['weights_sha256'][:16]}…`")
    open(OUT_MD, "w").write("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("train")
    t.add_argument("--holdout", required=True, choices=POPS)
    t.add_argument("--n", type=int, default=20)
    t.add_argument("--seed", type=int, default=0)
    fi = sub.add_parser("final")
    fi.add_argument("--n", type=int, default=20)
    fi.add_argument("--seed", type=int, default=0)
    m = sub.add_parser("maps")
    m.add_argument("--run", required=True)
    sub.add_parser("curves")
    sub.add_parser("dev")
    a = ap.parse_args()
    {"train": cmd_train, "final": cmd_final, "maps": cmd_maps, "curves": cmd_curves, "dev": cmd_dev}[a.cmd](a)


if __name__ == "__main__":
    main()
