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

    # ── DeepBacs E. coli brightfield (Zenodo 5550935, ~50 MB) ──
    deepbacs_dir = os.path.join(args.out, "deepbacs")
    if not os.path.exists(deepbacs_dir) or len(os.listdir(deepbacs_dir)) < 2:
        os.makedirs(deepbacs_dir, exist_ok=True)
        run(
            f"wget -q --show-progress -P {deepbacs_dir} "
            "https://zenodo.org/records/5550935/files/training.zip",
            "Downloading DeepBacs E. coli BF training set"
        )
        run(f"unzip -q -o {deepbacs_dir}/training.zip -d {deepbacs_dir}", "Unzipping")
    else:
        print(f"DeepBacs already at {deepbacs_dir}")

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
