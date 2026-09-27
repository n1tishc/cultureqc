"""
demo/selfcheck.py — the GPU dry run's parity and latency check
(cultureQC_upgrade_specv4.md §2B.7 item 3): re-run the first N precomputed
Analyze examples live, compare with their stored outputs (confluency, anomaly
score and flag, action, and the 3D view's cell-probability map: share of map
points on the other side of the cutoff), and time each stage.

    python -m demo.selfcheck [--n 5] [--out results/live_latency_gpu.md]

On the Space, console.py runs it at startup when CULTUREQC_SELFCHECK=N is set
and prints the report to the log. The stored C2C12 examples were themselves
checked against the compute cache (Colab GPU) by tests/test_demo_examples.py.
--out refuses to write a *_gpu file unless CUDA is present.
"""

from __future__ import annotations

import argparse
import platform
import statistics
from datetime import datetime, timezone

import cv2

from demo import precomputed
from demo.analysis import analyze_image


def run(n: int = 5) -> str:
    import torch

    cuda = torch.cuda.is_available()
    device = torch.cuda.get_device_name(0) if cuda else f"cpu ({torch.get_num_threads()} threads)"
    examples = sorted(precomputed.load(), key=lambda e: e["kind"] == "evican")[:n]   # C2C12 first
    rows, totals = [], []
    # One untimed pass loads the models, so the timed rows are per-image cost.
    first = examples[0]
    analyze_image(cv2.imread(precomputed.image_path(first), cv2.IMREAD_GRAYSCALE), precomputed.image_path(first),
                  first["cell_line"], first["target_confluency"])
    for ex in examples:
        path = precomputed.image_path(ex)
        img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        a = analyze_image(img, path, ex["cell_line"], ex["target_confluency"])
        t = a.timings_s
        stored_map = precomputed.probmap(ex)
        map_diff = (f"{((stored_map > 0) != (a.probmap_x1000 > 0)).mean() * 100:.3f}"
                    if stored_map is not None and stored_map.shape == a.probmap_x1000.shape else "n/a")
        if img.shape == (1040, 1392):
            totals.append(t["total"])
        rows.append(
            f"| {ex['id']} | {img.shape[1]}×{img.shape[0]} | {t['segmentation']:.2f} | {t['anomaly']:.3f} | "
            f"{t['qc_classifier']:.3f} | {t['total']:.2f} | {a.confluency.pct:.2f} vs {ex['confluency']['pct']:.2f} | "
            f"{a.anomaly.score} vs {ex['anomaly']['score']} | "
            f"{'same' if a.anomaly.flag == ex['anomaly']['flag'] else 'DIFFERENT'} | "
            f"{'same' if a.action == ex['action'] else 'DIFFERENT'} | {map_diff} |")
    median = f"{statistics.median(totals):.2f} s" if totals else "n/a"
    return "\n".join([
        "# Live latency and parity on the Space (live_latency_gpu)",
        "",
        f"Generated {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')} by `demo/selfcheck.py` on "
        f"**{device}** (cuda: {cuda}), {platform.system()} {platform.machine()}, torch {torch.__version__}.",
        "Per image, models already loaded (one untimed warm-up pass first). Live values vs the stored "
        "precomputed example (`demo/examples/examples.json`). Compare with the CPU figure in "
        "`results/live_latency.md` (V9).",
        "",
        "| example | size | Cellpose-SAM (s) | anomaly (s) | classifier (s) | total (s) | confluency live vs stored (%) "
        "| anomaly score live vs stored | anomaly flag | action | map points across the cutoff (%) |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
        *rows,
        "",
        f"Median total per 1392×1040 C2C12 frame: **{median}** (n = {len(totals)}).",
        "",
    ])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n", type=int, default=5)
    ap.add_argument("--out")
    args = ap.parse_args()
    report = run(args.n)
    print(report, flush=True)
    if args.out:
        import torch

        if "gpu" in args.out and not torch.cuda.is_available():
            raise SystemExit(f"not writing {args.out}: no CUDA device")
        with open(args.out, "w") as f:
            f.write(report)


if __name__ == "__main__":
    main()
