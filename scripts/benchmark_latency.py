"""Baseline CPU latency for the full single-image pipeline (Slice 0).

Measures wall-clock time for each stage of `culture.pipeline.analyze()` on
every fixture in `test-data/`, using models already resident in the process
(the first call in the run pays the one-time weight-download/load cost and is
reported separately, not folded into the per-image figures).

    .venv/bin/python scripts/benchmark_latency.py

Writes `results/baseline_latency.csv` and prints a markdown summary table
(paste into `results/baseline_latency.md` and the README, per spec rule 3:
"never invent numbers").
"""

from __future__ import annotations

import csv
import glob
import os
import statistics
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

FIXTURE_GLOB = "test-data/*"
OUT_CSV = "results/baseline_latency.csv"


def main() -> None:
    import cv2

    from culture.seg import cpsam_confluency, _get_model as _get_seg_model
    from culture.qc import qc_classify, _get_model as _get_qc_model

    images = sorted(
        p for p in glob.glob(FIXTURE_GLOB)
        if os.path.splitext(p)[1].lower() in (".png", ".tif", ".tiff", ".jpg", ".jpeg")
    )
    if not images:
        raise SystemExit(f"No fixture images found under {FIXTURE_GLOB!r}")

    print(f"Loading models (one-time cost, excluded from per-image figures)...")
    t0 = time.perf_counter()
    _get_seg_model()
    _get_qc_model()
    load_s = time.perf_counter() - t0
    print(f"  models resident in {load_s:.1f}s")

    rows = []
    for path in images:
        img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            print(f"  skip (unreadable): {path}")
            continue

        t0 = time.perf_counter()
        conf_result = cpsam_confluency(img, method="probmap")
        t_seg = time.perf_counter() - t0

        h, w = img.shape[:2]
        tile_size = 256
        if h >= tile_size and w >= tile_size:
            cy, cx = h // 2, w // 2
            tile = img[cy - tile_size // 2: cy + tile_size // 2, cx - tile_size // 2: cx + tile_size // 2]
        else:
            tile = cv2.resize(img, (tile_size, tile_size))

        t0 = time.perf_counter()
        qc_result = qc_classify(tile, run_gradcam=True)
        t_qc = time.perf_counter() - t0

        total = t_seg + t_qc
        rows.append({
            "image": os.path.basename(path),
            "width": w, "height": h,
            "seg_s": round(t_seg, 2),
            "qc_s": round(t_qc, 2),
            "total_s": round(total, 2),
            "confluency_pct": conf_result.pct,
            "qc_flag": qc_result.flag,
        })
        print(f"  {os.path.basename(path):45s} {w}x{h:<6} seg {t_seg:6.2f}s  qc {t_qc:6.2f}s  total {total:6.2f}s")

    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    with open(OUT_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    totals = [r["total_s"] for r in rows]
    print()
    print(f"n={len(totals)}  mean={statistics.mean(totals):.2f}s  "
          f"median={statistics.median(totals):.2f}s  "
          f"min={min(totals):.2f}s  max={max(totals):.2f}s")
    print(f"model load (one-time): {load_s:.1f}s")
    print(f"\nWrote {OUT_CSV}")


if __name__ == "__main__":
    main()
