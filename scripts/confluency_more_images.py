"""
More training images: does fine-tuning on all 169 labelled images of the four calibrated setups read four setups
it never trained on better than the approved model trained on 79? Pre-registered in
results/confluency_more_images.md, committed with this file and the training sets (PLAN) before any model here is
trained or any of the 31 images is read by a fine-tuned model.

Test images: the 31 mCellSeg images outside the four calibrated setups (polymer_lowmag, bf_20x_3440, jp_bf_2048,
huvec_bf_2752), both halves of the committed split. No fine-tuned model has read them; only the zero-shot map has
(results/confluency_mcellseg_curves.json). Every reading is at cutoff 0.0, the cutoff the product reads a
fine-tuned model at (configs/finetuned_models.yaml); these setups have no calibration profile.

GPU steps run on Colab (nb/10_more_images.ipynb), one model at a time, the curves file rewritten after each:

    python scripts/confluency_more_images.py read --run mcellseg_ftF_r2     # the approved model: no training
    python scripts/confluency_more_images.py train --run mcellseg_more_n169 # then read --run, and so on (RUNS)

CPU, on the Mac:

    .venv/bin/python scripts/confluency_more_images.py plan    # writes PLAN (before the pre-registration commit)
    .venv/bin/python scripts/confluency_more_images.py score   # once
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import defaultdict

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))
os.chdir(REPO)

import confluency_mcellseg as m  # noqa: E402

APPROVED = "mcellseg_ftF_r2"
APPROVED_SHA = "2d1549682c1da4829e7766bebf6e90e2373aa6c439f5138b098a71259d1239a2"
APPROVED_WEIGHTS = os.path.join("cache", "finetune", APPROVED, "models", APPROVED)
RUNS = {                                    # run -> (images, draw); trained in this order after the approved model is read
    "mcellseg_more_n169": (169, None),
    "mcellseg_more_n40_s0": (40, 0),
    "mcellseg_more_n40_s1": (40, 1),
    "mcellseg_more_n120_s0": (120, 0),
}
PRIMARY = "mcellseg_more_n169"
PLAN = os.path.join("results", "confluency_more_images_plan.json")
CURVES = os.path.join("results", "confluency_more_images_curves.json")
OUT_MD = os.path.join("results", "confluency_more_images.md")
OUT_JSON = os.path.join("results", "confluency_more_images.json")
OUT_PNG = os.path.join("results", "confluency_more_images.png")
ARM_DIR = "more"                            # maps under cache/probmaps_mcellseg/more/<run>/
J0 = m.GRID.index(0.0)


def pools() -> tuple[list[dict], list[dict], list[str]]:
    """(the 169 training candidates, the 31 test images, the four calibrated setups)."""
    its = m.loaded()
    cal = m.calibrated_setups(its)
    return [i for i in its if i["setup"] in cal], [i for i in its if i["setup"] not in cal], cal


def unit_order(pool: list[dict], seed: int) -> list[list[dict]]:
    """Units of the 169 in a random order (seeded), interleaved so every prefix spans the four setups in proportion
    to their image counts: the next unit always comes from the setup with the smallest share taken so far."""
    rng = np.random.default_rng(seed)
    by = defaultdict(lambda: defaultdict(list))
    for i in pool:
        by[i["setup"]][i["unit"]].append(i)
    queue = {s: [sorted(by[s][u], key=lambda i: i["name"]) for u in rng.permutation(sorted(by[s]))] for s in sorted(by)}
    total = {s: sum(len(u) for u in q) for s, q in queue.items()}
    taken = dict.fromkeys(queue, 0)
    out = []
    while any(queue.values()):
        s = min((s for s in queue if queue[s]), key=lambda s: (taken[s] / total[s], s))
        u = queue[s].pop(0)
        out.append(u)
        taken[s] += len(u)
    return out


def draw(pool: list[dict], n: int, seed: int | None) -> list[str]:
    """The first whole units of the seeded order until at least n images: nested across sizes for one seed."""
    if seed is None:
        return sorted(i["name"] for i in pool)
    names = []
    for u in unit_order(pool, seed):
        if len(names) >= n:
            break
        names += [i["name"] for i in u]
    return names


def plan() -> dict:
    return json.load(open(PLAN))


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ── Mac, before the pre-registration commit ─────────────────────────────────

def cmd_plan(a):
    assert not os.path.exists(PLAN), f"{PLAN} exists: the training sets are fixed"
    pool, test, cal = pools()
    by_name = {i["name"]: i for i in pool}
    runs = {}
    for run, (n, seed) in RUNS.items():
        names = draw(pool, n, seed)
        runs[run] = {"target_n": n, "draw": seed, "n": len(names),
                     "per_setup": {s: sum(by_name[x]["setup"] == s for x in names) for s in cal},
                     "at_60_90": sum(m.LO <= by_name[x]["gt"] <= m.HI for x in names), "train_images": names}
    approved = json.load(open(os.path.join("results", "confluency_finetune_figure_curves.json")))["run"]
    assert approved["weights_sha256"] == APPROVED_SHA
    doc = {"generated_by": "scripts/confluency_more_images.py plan", "calibrated_setups": cal,
           "test_images": sorted(i["name"] for i in test),
           "approved": {"run": APPROVED, "weights_sha256": APPROVED_SHA, "n": approved["n"],
                        "train_images": approved["train_images"]},
           "runs": runs}
    assert not set(doc["test_images"]) & {x for r in runs.values() for x in r["train_images"]}
    json.dump(doc, open(PLAN, "w"), indent=1)
    for run, r in runs.items():
        print(run, r["n"], r["per_setup"], "at 60-90:", r["at_60_90"])
    print("test images", len(doc["test_images"]), "->", PLAN)


# ── GPU steps (Colab) ───────────────────────────────────────────────────────

def cmd_train(a):
    from confluency_finetune import RUNS as RUN_DIR, train_run
    p = plan()
    if os.path.exists(os.path.join(RUN_DIR, a.run, "manifest.json")):
        print(a.run, "already trained")
        return
    by_name = {i["name"]: i for i in pools()[0]}
    items = [by_name[x] for x in p["runs"][a.run]["train_images"]]
    man = train_run(a.run, items, label_fn=m.instance_mask)          # the approved model's function, recipe and labels
    assert man["n"] == p["runs"][a.run]["n"]
    print(json.dumps({k: man[k] for k in ("run", "n", "weights_sha256", "seconds")}), flush=True)


def load_model(run: str):
    from cellpose import models
    from confluency_finetune import RUNS as RUN_DIR, device
    if run == APPROVED:
        path, sha = APPROVED_WEIGHTS, APPROVED_SHA
        man = {"run": APPROVED, "weights_sha256": APPROVED_SHA, "n": plan()["approved"]["n"]}
    else:
        man = json.load(open(os.path.join(RUN_DIR, run, "manifest.json")))
        path, sha = man["weights"], man["weights_sha256"]
    assert sha256(path) == sha, f"{run}: weights do not match"
    return models.CellposeModel(gpu=True, device=device(), pretrained_model=path), man


def cmd_read(a):
    """The run's map of each of the 31 test images, then CURVES rewritten with every map on disk."""
    from confluency_finetune import environment
    p = plan()
    by_name = {i["name"]: i for i in pools()[1]}
    mdl, man = load_model(a.run)
    for k, x in enumerate(p["test_images"]):
        i = by_name[x]
        m.cached(os.path.join(ARM_DIR, a.run), x, lambda: mdl.eval(m.gray(i["path"]), diameter=None, channels=[0, 0],
                                                                   compute_masks=False)[1][2])
    print(a.run, len(p["test_images"]), "read", flush=True)
    out = json.load(open(CURVES)) if os.path.exists(CURVES) else {
        "generated_by": "scripts/confluency_more_images.py read", "grid": m.GRID, "maps": {}, "manifests": {}}
    out["environment"] = environment()
    out["maps"][a.run] = {x: [float(v) for v in m.curve(np.load(os.path.join(m.MAPS, ARM_DIR, a.run, x + ".npz"))["prob"]
                                                        .astype(np.float32))] for x in p["test_images"]}
    out["manifests"][a.run] = man
    json.dump(out, open(CURVES, "w"))
    print("wrote", CURVES, sorted(out["maps"]))


# ── scoring (once) ──────────────────────────────────────────────────────────

def rows_of(C: dict, arms: dict[str, str]) -> list[dict]:
    """One row per test image: the expert reading and each arm's reading at cutoff 0.0."""
    p = plan()
    by_name = {i["name"]: i for i in pools()[1]}
    zero = json.load(open(m.CURVES))["maps"]["zero"]
    rows = []
    for x in p["test_images"]:
        i = by_name[x]
        r = {k: i[k] for k in ("name", "setup", "unit", "gt")} | {"cluster": i["setup"] + "/" + i["unit"]}
        for arm, run in arms.items():
            r[arm] = (zero if run == "zero" else C["maps"][run])[x][J0]
        rows.append(r)
    return rows


def summary(rows: list[dict], arm: str, rng) -> dict:
    d = m.dense(rows)
    return {"mae": m.mae(rows, arm), "ci": m.clustered(rows, lambda x: m.mae(x, arm), rng),
            "bias": float(np.mean([r[arm] - r["gt"] for r in rows])),
            "within5": sum(abs(r[arm] - r["gt"]) <= 5 for r in rows),
            "mae_60_90": m.mae(d, arm), "bias_60_90": float(np.mean([r[arm] - r["gt"] for r in d])) if d else None,
            "per_setup": {s: m.mae([r for r in rows if r["setup"] == s], arm) for s in sorted({r["setup"] for r in rows})}}


def diff(rows: list[dict], a: str, b: str, rng) -> dict:
    f = lambda x: m.mae(x, a) - m.mae(x, b)                                     # noqa: E731
    d = m.dense(rows)
    return {"all": f(rows), "ci": m.clustered(rows, f, rng), "60_90": f(d) if d else None,
            "ci_60_90": m.clustered(d, f, rng) if d else None}


def cmd_score(a):
    assert not os.path.exists(OUT_JSON), f"{OUT_JSON} exists: scored once"
    C = json.load(open(CURVES))
    p = plan()
    missing = [r for r in [APPROVED, *RUNS] if r not in C["maps"]]
    if missing:
        sys.exit(f"no readings for {missing}: run them on Colab first; score computes nothing new")
    for run in RUNS:
        man = C["manifests"][run]
        assert man["train_images"] == p["runs"][run]["train_images"], f"{run} trained on other images than PLAN"
    assert C["manifests"][APPROVED]["weights_sha256"] == APPROVED_SHA
    arms = {"Z": "zero", "A": APPROVED} | {r: r for r in RUNS}
    rows = rows_of(C, arms)
    rng = np.random.default_rng(0)
    res = {"n": len(rows), "n_60_90": len(m.dense(rows)), "units": len({r["cluster"] for r in rows}),
           "arms": {k: summary(rows, k, rng) for k in arms},
           "primary": diff(rows, "A", PRIMARY, rng),
           "approved_vs_shipped": diff(rows, "Z", "A", rng),
           "n_train": {"A": p["approved"]["n"]} | {r: p["runs"][r]["n"] for r in RUNS},
           "rows": rows}
    lo, hi = res["primary"]["ci"]
    res["verdict"] = ("more images read these setups better" if lo > 0 else
                      "more images read these setups worse" if hi < 0 else
                      "not shown with these 31 images")
    json.dump(res, open(OUT_JSON, "w"), indent=1)
    write_md(res)
    figure(res)


def f(v, s="+.2f"):
    return "–" if v is None else format(v, s)


def write_md(res: dict) -> None:
    A = res["arms"]
    name = {"Z": "Shipped (zero-shot)", "A": f"Approved fine-tuned, {res['n_train']['A']} images (`{APPROVED}`)"} | {
        r: f"Fine-tuned, {res['n_train'][r]} images (`{r}`)" for r in RUNS}
    setups = sorted(A["Z"]["per_setup"])
    L = ["", "## Results (generated by `scripts/confluency_more_images.py score`, run once)", "",
         f"{res['n']} test images from {res['units']} units, {res['n_60_90']} of them at 60–90%. Every reading at "
         "cutoff 0.0. Intervals: 95%, bootstrap over units.", "",
         "| Model | Training images | MAE, all (95% interval) | Mean signed error | Within 5 pp | MAE at 60–90% | "
         + " | ".join(f"MAE `{s}`" for s in setups) + " |",
         "|---|---|---|---|---|---|" + "---|" * len(setups)]
    for k, s in A.items():
        L.append(f"| {name[k]} | {res['n_train'].get(k, 0) if k != 'Z' else '–'} | {s['mae']:.2f} ({s['ci'][0]:.2f}–"
                 f"{s['ci'][1]:.2f}) | {s['bias']:+.2f} | {s['within5']} of {res['n']} | {f(s['mae_60_90'], '.2f')} | "
                 + " | ".join(f"{s['per_setup'][x]:.2f}" for x in setups) + " |")
    P, Q = res["primary"], res["approved_vs_shipped"]
    L += ["", f"Pre-registered contrast, MAE(approved) − MAE({PRIMARY}) on all {res['n']}: {P['all']:+.2f} pp "
          f"({P['ci'][0]:+.2f} to {P['ci'][1]:+.2f}). By the rule fixed in advance: **{res['verdict']}**.",
          f"At 60–90% (reported, not judged): {f(P['60_90'])} pp"
          + (f" ({P['ci_60_90'][0]:+.2f} to {P['ci_60_90'][1]:+.2f})." if P["ci_60_90"] else "."), "",
          f"Approved fine-tuned model against the shipped model (reported, whatever it shows), MAE(shipped) − "
          f"MAE(approved): {Q['all']:+.2f} pp ({Q['ci'][0]:+.2f} to {Q['ci'][1]:+.2f}); at 60–90% {f(Q['60_90'])} pp.",
          "", "| Image | Setup | Experts | " + " | ".join(["Shipped", "Approved", *[f"n{res['n_train'][r]}"
                                                                         + (f" s{RUNS[r][1]}" if RUNS[r][1] is not None else "")
                                                                         for r in RUNS]]) + " |",
          "|---|---|---|" + "---|" * (2 + len(RUNS))]
    for r in sorted(res["rows"], key=lambda r: (r["setup"], r["gt"])):
        L.append(f"| `{r['name']}` | {r['setup']} | {r['gt']:.1f} | " + " | ".join(f"{r[k]:.1f}" for k in A) + " |")
    L += ["", f"![MAE by number of training images]({os.path.basename(OUT_PNG)})", ""]
    with open(OUT_MD, "a") as fh:
        fh.write("\n".join(L))
    print("\n".join(L))


def figure(res: dict) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    A, N = res["arms"], res["n_train"]
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
    for j, k in enumerate(RUNS):
        ax[0].errorbar(N[k], A[k]["mae"], yerr=[[A[k]["mae"] - A[k]["ci"][0]], [A[k]["ci"][1] - A[k]["mae"]]],
                       fmt="o", color="#1f6f8b", capsize=3, label=None if j else "drawn by unit across the four setups")
    ax[0].errorbar(N["A"], A["A"]["mae"], yerr=[[A["A"]["mae"] - A["A"]["ci"][0]], [A["A"]["ci"][1] - A["A"]["mae"]]],
                   fmt="s", color="#c2571a", capsize=3, label="approved model (the other half's 79, not a random draw)")
    ax[0].axhline(A["Z"]["mae"], color="#888", ls="--", label="shipped model, no fine-tuning")
    ax[0].set_xlabel("training images (four setups)")
    ax[0].set_ylabel(f"mean error on the {res['n']} new-setup images (pp)")
    ax[0].set_ylim(bottom=0)
    ax[0].legend(fontsize=8)
    gt = [r["gt"] for r in res["rows"]]
    for k, c, lab in (("Z", "#888", "shipped"), ("A", "#c2571a", "approved"), (PRIMARY, "#1f6f8b", f"{N[PRIMARY]} images")):
        ax[1].scatter(gt, [r[k] for r in res["rows"]], s=18, color=c, label=lab)
    ax[1].plot([0, 100], [0, 100], color="#bbb", lw=1)
    ax[1].set_xlabel("experts (%)")
    ax[1].set_ylabel("reading at cutoff 0.0 (%)")
    ax[1].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=130)
    print("wrote", OUT_PNG)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("plan")
    sub.add_parser("score")
    for c in ("train", "read"):
        s = sub.add_parser(c)
        s.add_argument("--run", required=True, choices=([APPROVED] if c == "read" else []) + list(RUNS))
    a = ap.parse_args()
    {"plan": cmd_plan, "train": cmd_train, "read": cmd_read, "score": cmd_score}[a.cmd](a)


if __name__ == "__main__":
    main()
