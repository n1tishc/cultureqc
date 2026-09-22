#!/usr/bin/env python3
"""
Download source data for synthetic contamination generation.

    python scripts/download_sources.py --out data/sources
"""

import argparse
import os
import subprocess


def run(cmd, desc):
    print(f"\n{'='*60}\n{desc}\n{'='*60}")
    return subprocess.run(cmd, shell=True).returncode


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="data/sources")
    args = parser.parse_args()
    os.makedirs(args.out, exist_ok=True)

    # ── DeepBacs E. coli brightfield (Zenodo 5550935, ~555 MB) ──
    # The record's actual filename (queried from Zenodo's own API, not
    # guessed) — an earlier hardcoded "training.zip" 404s; Zenodo's current
    # download path is also /api/records/.../files/<name>/content, not the
    # human-facing /records/.../files/<name> URL.
    DEEPBACS_ZIP_NAME = "DeepBacs_Data_Segmentation_E.coli_Brightfield_dataset.zip"
    DEEPBACS_ZIP_SIZE = 555573806  # bytes, from the Zenodo API's file listing
    DEEPBACS_URL = f"https://zenodo.org/api/records/5550935/files/{DEEPBACS_ZIP_NAME}/content"

    deepbacs_dir = os.path.join(args.out, "deepbacs")
    n_tifs = sum(len([f for f in files if f.lower().endswith(".tif")])
                 for _, _, files in os.walk(deepbacs_dir)) if os.path.isdir(deepbacs_dir) else 0
    if n_tifs == 0:
        os.makedirs(deepbacs_dir, exist_ok=True)
        zip_path = os.path.join(deepbacs_dir, "deepbacs.zip")
        rc = run(f"wget -q -O {zip_path} {DEEPBACS_URL}", "Downloading DeepBacs E. coli BF dataset")
        got_size = os.path.getsize(zip_path) if os.path.exists(zip_path) else 0
        if rc != 0 or got_size != DEEPBACS_ZIP_SIZE:
            raise SystemExit(
                f"DeepBacs download failed: wget exit {rc}, got {got_size} bytes, "
                f"expected {DEEPBACS_ZIP_SIZE}. URL: {DEEPBACS_URL}"
            )
        rc = run(f"unzip -q -o {zip_path} -d {deepbacs_dir}", "Unzipping")
        if rc != 0:
            raise SystemExit(f"unzip failed (exit {rc}) on {zip_path}")
    else:
        print(f"DeepBacs already at {deepbacs_dir} ({n_tifs} .tif files)")

    # ── Summary ──
    print(f"\n{'='*60}\nDone.\n{'='*60}")
    for root, dirs, files in os.walk(deepbacs_dir):
        level = root.replace(deepbacs_dir, "").count(os.sep)
        if level < 3:
            indent = "  " * level
            tifs = [f for f in files if f.lower().endswith(".tif")]
            print(f"{indent}{os.path.basename(root)}/  ({len(tifs)} tifs)")


if __name__ == "__main__":
    main()
