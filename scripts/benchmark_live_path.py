"""
A8 — live per-visit latency (cultureQC_upgrade_spec.md §2A.9; V9).

Times the live per-FOV path, per model, with the models already resident
(loading is timed once and reported separately):
  1. quality gate        culture.quality.quality_gate (metrics + thresholds)
  2. Cellpose-SAM        culture.seg.cpsam_confluency(method="probmap")
  3. classifier          culture.qc.qc_classify on the 256 px centre tile
                         (with Grad-CAM, as the app runs it; without, for reference)
  4. DINOv2-small qctile culture.cache.dino_embed on the same tile
  5. patch kNN           L2-normalise, pick the confluency bin's bank
                         (cache/anomaly/banks.npz, A4), nearest-patch distance, top-1% mean
A visit is n_fov independent FOV images, so per visit = n_fov × per FOV (1 and 3).

Hardware: the product Space is HF "CPU Basic" (2 vCPU, deploy/README.md).
This runs on the Mac with torch and OpenCV limited to --threads (default 2).
Apple Silicon cores are faster than a shared cloud vCPU, so these numbers are
an approximation and most likely a lower bound for the Space.

Input: no C2C12 frames are on the Mac (they live on Drive), so the image is a
real phase-contrast LIVECell fixture from test-data/, tiled 2 × 2 and cropped
to the C2C12 frame size (1392 × 1040). Cellpose time tracks pixel count, not
content (results/baseline_latency.md). Also timed: the fixture at native
704 × 520, and 348 × 260 (the replay's 0.25-frac FOV crop of a C2C12 frame),
as the spec's "smaller input" option.

Usage:
    python scripts/benchmark_live_path.py [--threads 2] [--repeats 2]
"""

from __future__ import annotations

import argparse
import os
import platform
import statistics
import sys
import time

import numpy as np
import pandas as pd

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

FIXTURE = os.path.join(REPO, "test-data", "A172_Phase_C7_1_00d00h00m_1.tif")
C2C12_HW = (1040, 1392)
BUDGET_S = 5.0  # V9 (spec §2A.10); no config key exists yet


def _t(fn):
    t0 = time.perf_counter()
    out = fn()
    return time.perf_counter() - t0, out


def images(fixture: str) -> dict[str, np.ndarray]:
    import cv2
    img = cv2.imread(fixture, cv2.IMREAD_GRAYSCALE)
    big = np.tile(img, (2, 2))[:C2C12_HW[0], :C2C12_HW[1]]
    h, w = C2C12_HW
    crop = big[(h - h // 4) // 2:(h - h // 4) // 2 + h // 4, (w - w // 4) // 2:(w - w // 4) // 2 + w // 4]
    return {"1392x1040 (C2C12 frame size)": np.ascontiguousarray(big),
            f"{img.shape[1]}x{img.shape[0]} (fixture native)": img,
            f"{crop.shape[1]}x{crop.shape[0]} (replay 0.25 FOV crop)": np.ascontiguousarray(crop)}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--threads", type=int, default=2)
    ap.add_argument("--repeats", type=int, default=2)
    ap.add_argument("--out", default=os.path.join(REPO, "results"))
    args = ap.parse_args()

    import cv2
    import torch
    torch.set_num_threads(args.threads)
    cv2.setNumThreads(args.threads)

    import yaml
    from culture import seg, qc
    from culture.anomaly import bin_index, image_score, nn_distance
    from culture.cache import _get_dino, dino_embed, qc_tile_from
    from culture.quality import quality_gate

    acfg = yaml.safe_load(open(os.path.join(REPO, "configs", "anomaly.yaml")))
    edges = [float(e) for e in acfg["bins"]["edges"]]
    top_frac = float(acfg["method"]["top_frac"])

    load = {}
    load["Cellpose-SAM"], _ = _t(seg._get_model)
    load["classifier"], _ = _t(qc._get_model)
    load["DINOv2-small"], _ = _t(_get_dino)

    def _banks():
        b = np.load(os.path.join(REPO, "cache", "anomaly", "banks.npz"))
        return {k: b[k].astype(np.float32) / (np.linalg.norm(b[k], axis=1, keepdims=True) + 1e-8) for k in b.files}
    load["kNN banks"], banks = _t(_banks)

    def knn(patches, conf_pct):
        x = patches.astype(np.float32)
        x /= np.linalg.norm(x, axis=1, keepdims=True) + 1e-8
        i = bin_index(conf_pct, edges)
        return image_score(nn_distance(x, banks[f"bin_{edges[i]:g}-{edges[i + 1]:g}"]), top_frac)

    imgs = images(FIXTURE)
    # warm-up on the smallest image (first-call kernel set-up is not per-visit cost)
    small = list(imgs.values())[-1]
    seg.cpsam_confluency(small)
    qc.qc_classify(qc_tile_from(small))
    knn(dino_embed(qc_tile_from(small))["patches"], 10.0)

    rows = []
    for name, img in imgs.items():
        for r in range(args.repeats):
            tile = qc_tile_from(img)
            t_gate, _ = _t(lambda: quality_gate(img))
            t_seg, conf = _t(lambda: seg.cpsam_confluency(img))
            t_qc, _ = _t(lambda: qc.qc_classify(tile, run_gradcam=True))
            t_qc_nocam, _ = _t(lambda: qc.qc_classify(tile, run_gradcam=False))
            t_dino, emb = _t(lambda: dino_embed(tile))
            t_knn, score = _t(lambda: knn(emb["patches"], conf.pct))
            rows.append({"input": name, "repeat": r + 1, "quality_gate_s": t_gate, "cellpose_sam_s": t_seg,
                         "classifier_gradcam_s": t_qc, "classifier_no_gradcam_s": t_qc_nocam, "dinov2_qctile_s": t_dino,
                         "patch_knn_s": t_knn, "confluency_pct": conf.pct, "anomaly_score": score})
            print(f"{name:34s} run {r + 1}: gate {t_gate:.3f}s  cellpose {t_seg:.1f}s  cls {t_qc:.2f}s "
                  f"(no cam {t_qc_nocam:.2f}s)  dino {t_dino:.2f}s  knn {t_knn:.3f}s", flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(args.out, "live_latency.csv"), index=False, float_format="%.4f")
    write_summary(df, load, args)


def _cpu_name() -> str:
    try:
        import subprocess
        return subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True, text=True).stdout.strip()
    except OSError:
        return platform.machine()


def write_summary(df, load, args):
    comp = ["quality_gate_s", "cellpose_sam_s", "classifier_gradcam_s", "dinov2_qctile_s", "patch_knn_s"]
    label = {"quality_gate_s": "quality gate", "cellpose_sam_s": "Cellpose-SAM", "classifier_gradcam_s":
             "classifier (+ Grad-CAM)", "dinov2_qctile_s": "DINOv2-small qctile", "patch_knn_s": "patch kNN"}
    import torch
    lines = ["# A8: live per-visit latency", "",
             f"Generated {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} by `scripts/benchmark_live_path.py`; "
             "per-run data in `results/live_latency.csv`.", "",
             f"**Hardware (approximation):** {_cpu_name()} Mac, "
             f"torch {torch.__version__}, torch and OpenCV limited to **{args.threads} threads** to mimic the product "
             "Space (HF CPU Basic, 2 vCPU; `deploy/README.md`). Apple Silicon cores are faster than a shared cloud "
             "vCPU, so treat these as a lower bound for the Space. Median of "
             f"{args.repeats} runs per input after a warm-up; models resident.", "",
             "**Input:** no C2C12 frames are on the Mac, so a real phase-contrast LIVECell fixture "
             f"(`test-data/{os.path.basename(FIXTURE)}`) is tiled 2 × 2 and cropped to the C2C12 frame size. Cellpose "
             "time tracks pixel count, not content (`results/baseline_latency.md`).", "",
             "One-time model load (excluded): " + ", ".join(f"{k} {v:.1f} s" for k, v in load.items()) + ".", "",
             "## Per FOV (seconds, median)", "",
             "| input | " + " | ".join(label[c] for c in comp) + " | total per FOV |", "|---|" + "---|" * (len(comp) + 1)]
    med = df.groupby("input", sort=False)[comp + ["classifier_no_gradcam_s"]].median()
    for name, r in med.iterrows():
        lines.append(f"| {name} | " + " | ".join(f"{r[c]:.3g}" for c in comp) + f" | {r[comp].sum():.1f} |")
    lines += ["", "Classifier without Grad-CAM: " + ", ".join(
        f"{n.split(' ')[0]} {r['classifier_no_gradcam_s']:.2f} s" for n, r in med.iterrows()) + ".", "",
        f"## V9: per visit (budget {BUDGET_S:g} s)", "",
        "A visit is n_fov independent FOV images, each through the whole path.", "",
        "| input | 1 FOV | 3 FOVs | Cellpose share | V9 (1 FOV) |", "|---|---|---|---|---|"]
    for name, r in med.iterrows():
        tot = r[comp].sum()
        lines.append(f"| {name} | {tot:.1f} s | {3 * tot:.1f} s | {100 * r['cellpose_sam_s'] / tot:.0f}% | "
                     f"{'pass' if tot <= BUDGET_S else 'fail'} ({tot / BUDGET_S:.0f}× budget) |")
    no_seg = med[[c for c in comp if c != "cellpose_sam_s"]].sum(axis=1)
    lines += ["", "Everything except Cellpose-SAM, per FOV: " + ", ".join(
        f"{n.split(' ')[0]} {v:.2f} s" for n, v in no_seg.items()) + ".", "",
        "Growth fit per visit (not in the spec's list; `results/growth_runtime.txt`, default threads): 0.32 s median "
        "for a 20-visit segment.", "",
        "## Consequence (spec fail branch)", "",
        "Cellpose-SAM is essentially the whole cost; everything else fits the budget many times over. The spec's "
        "listed levers do not close the gap on this path: the backbone is already ViT-S, fewer crops only divides "
        "by n_fov, and even the smallest input tried is well over budget. What remains in the spec is \"precompute "
        "demo examples and say so\"; beyond it, a GPU Space or a lighter confluency model for the live path "
        "(a Phase B decision, with V1 rechecked on whatever replaces Cellpose-SAM). For reference, Slice 0 measured "
        "the same 704 × 520 fixture at 140 s with default threads (`results/baseline_latency.md`).", ""]
    with open(os.path.join(args.out, "live_latency.md"), "w") as f:
        f.write("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
