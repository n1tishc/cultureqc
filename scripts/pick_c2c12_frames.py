"""
Pick the few real C2C12 frames the Mac needs (B2 anomaly parity; B8 single-image
demo set). The frames live only in Drive's staged/c2c12_prepared.zip, so this
writes the list and the Colab notebook that fetches exactly those files.

Rule (fixed before any live scoring; held-out frames only, because
cache/anomaly/scores.parquet scored tuning frames against leave-one-sequence-out
banks that the shipped banks.npz is not):
  normal         2 per bin (0-20, 20-40, 40-100), each from a different sequence
  contamination  1 per held-out contamination sequence, severity >= 150
  dimming        2, intensity factor <= 0.7, from different sequences
seeded (0) sampling within each group.

Outputs:
  results/c2c12_frame_picks.csv       sha, kind, sequence, frame, bin, cached score/z/flag, zip path
  nb/04c_fetch_c2c12_frames.ipynb     Colab: copy the zip to local disk, extract only these
                                      files, verify sha256, zip them back to Drive

Usage:
    python scripts/pick_c2c12_frames.py --cache-dir cache
"""

from __future__ import annotations

import argparse
import json
import os

import numpy as np
import pandas as pd

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED = 0
OUT_CSV = os.path.join(REPO, "results", "c2c12_frame_picks.csv")
OUT_NB = os.path.join(REPO, "nb", "04c_fetch_c2c12_frames.ipynb")


def _pick(df: pd.DataFrame, n: int, rng: np.random.Generator) -> pd.DataFrame:
    """n rows from distinct sequences, seeded."""
    df = df.sample(frac=1.0, random_state=int(rng.integers(1 << 31))).drop_duplicates("seq")
    return df.head(n)


def pick(cache_dir: str) -> pd.DataFrame:
    sc = pd.read_parquet(os.path.join(cache_dir, "anomaly", "scores.parquet"))
    im = pd.read_parquet(os.path.join(cache_dir, "images.parquet"))[["image_sha256", "dataset", "sequence_id",
                                                                    "frame_idx", "source_path"]]
    h = sc[sc.split == "heldout"].merge(im, on="image_sha256", how="left", suffixes=("", "_img"))
    h["seq"] = np.where(h.fault_sequence_id.fillna("") != "", h.fault_sequence_id, h.base_sequence_id)
    h = h.sort_values(["seq", "frame_idx"]).reset_index(drop=True)
    rng = np.random.default_rng(SEED)
    parts = []
    for label in ["0-20", "20-40", "40-100"]:
        parts.append(_pick(h[(h.kind == "normal") & (h.bin_label == label)], 2, rng))
    contam = h[(h.kind == "contamination_onset") & (h.severity >= 150)]
    parts.append(_pick(contam, contam.seq.nunique(), rng))
    parts.append(_pick(h[(h.kind == "lamp_dimming") & (h.severity <= 0.7)], 2, rng))
    out = pd.concat(parts, ignore_index=True)
    # nb/03's prepared PNGs: /content/data/c2c12/png/<seq>/<frame>.png (normal) and
    # /content/data/c2c12_faults/png/<fault seq>/<frame>.png (faults, already their source_path)
    out["zip_path"] = [
        sp if "/c2c12_faults/png/" in sp else f"/content/data/c2c12/png/{r.base_sequence_id}/{int(r.frame_idx):05d}.png"
        for sp, r in zip(out.source_path, out.itertuples())]
    return out[["image_sha256", "kind", "seq", "frame_idx", "bin_label", "pct", "severity", "score_binned",
                "z_binned", "flag_binned", "zip_path"]]


def notebook(picks: pd.DataFrame) -> dict:
    files = {r.image_sha256: r.zip_path for r in picks.itertuples()}
    md = ("# nb/04c: fetch the picked C2C12 frames (B2 parity, B8 demo set)\n\n"
          "Written by `scripts/pick_c2c12_frames.py`. Follows the Drive I/O rule: copy the one archive to "
          "local disk, extract only the listed files there, check each file's SHA-256 against the cache, and "
          "copy one small zip back to Drive. Then download `staged/c2c12_picks.zip` to the Mac and unzip it "
          "into `data/c2c12_picks/`.")
    code = f'''import hashlib, os, shutil, zipfile
from google.colab import drive
drive.mount('/content/drive')
STAGE_DIR = '/content/drive/MyDrive/cultureqc/staged'   # same folder nb/04b used; edit if yours differs
FILES = {json.dumps(files, indent=1)}

local_zip = '/content/c2c12_prepared.zip'
shutil.copy(f'{{STAGE_DIR}}/c2c12_prepared.zip', local_zip)      # one sequential read from Drive
os.makedirs('/content/picks', exist_ok=True)
with zipfile.ZipFile(local_zip) as z:
    names = {{'/' + n.lstrip('/'): n for n in z.namelist()}}
    for sha, path in FILES.items():
        data = z.read(names[path])
        got = hashlib.sha256(data).hexdigest()
        assert got == sha, f'{{path}}: sha256 {{got}} != cache {{sha}}'
        open(f'/content/picks/{{sha}}.png', 'wb').write(data)
os.remove(local_zip)
shutil.make_archive('/content/c2c12_picks', 'zip', '/content/picks')
shutil.copy('/content/c2c12_picks.zip', f'{{STAGE_DIR}}/c2c12_picks.zip')
print(len(FILES), 'frames verified and copied to', f'{{STAGE_DIR}}/c2c12_picks.zip')
'''
    return {"cells": [{"cell_type": "markdown", "metadata": {}, "source": md},
                      {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": code}],
            "metadata": {"kernelspec": {"display_name": "Python 3", "name": "python3"}, "accelerator": "None"},
            "nbformat": 4, "nbformat_minor": 5}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cache-dir", default="cache")
    args = ap.parse_args()
    picks = pick(args.cache_dir)
    picks.to_csv(OUT_CSV, index=False, float_format="%.6g")
    with open(OUT_NB, "w") as f:
        json.dump(notebook(picks), f, indent=1)
        f.write("\n")
    print(picks.drop(columns=["image_sha256", "zip_path"]).to_string(index=False))


if __name__ == "__main__":
    main()
