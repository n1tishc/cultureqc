#!/usr/bin/env python3
"""
One zip that runs the call-day console on a Colab GPU with no Hugging Face at
run time (nb/05_console_colab.ipynb; deploy/README.md, "Backup: Colab").

    python scripts/make_console_bundle.py [--out ../cultureqc_console_bundle.zip]

Contents, under console/:
    the synced deploy/hf-space-demo/ (console.py, demo/, culture/, configs/,
        the anomaly banks), the same files the Space is published from;
    weights/cellpose/cpsam_v2         Cellpose-SAM, from ~/.cellpose/models;
    weights/hf/hub/models--*          DINOv2-small and the QC checkpoint, from
        the local Hugging Face cache (refs + snapshots, symlinks resolved), so
        HF_HUB_OFFLINE=1 finds them;
    BUNDLE.json                       git commit and the SHA-256 of every file.

The zip goes outside the repo (about 1.2 GB). Upload it to Drive; the notebook
copies it to Colab's local disk before unzipping (never run from Drive).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPACE = ROOT / "deploy" / "hf-space-demo"
CELLPOSE = Path.home() / ".cellpose" / "models" / "cpsam_v2"
HF_HUB = Path(os.environ.get("HF_HUB_CACHE", Path.home() / ".cache" / "huggingface" / "hub"))
HF_REPOS = ["models--facebook--dinov2-small", "models--LongGrainRice--cultureqc-qc-effnetb0-v1"]
SKIP_DIRS = {"__pycache__", ".pytest_cache", ".git"}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def files_to_bundle() -> list[tuple[Path, str]]:
    out = []
    for dirpath, dirnames, filenames in os.walk(SPACE):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if name.endswith(".pyc"):
                continue
            src = Path(dirpath) / name
            out.append((src, "console/" + src.relative_to(SPACE).as_posix()))
    if not CELLPOSE.is_file():
        sys.exit(f"missing {CELLPOSE}: run Cellpose-SAM once on this machine first")
    out.append((CELLPOSE, "console/weights/cellpose/cpsam_v2"))
    for repo in HF_REPOS:
        base = HF_HUB / repo
        ref = base / "refs" / "main"
        if not ref.is_file():
            sys.exit(f"missing {ref}: load that model once on this machine first")
        out.append((ref, f"console/weights/hf/hub/{repo}/refs/main"))
        snap = base / "snapshots" / ref.read_text().strip()
        for src in sorted(snap.iterdir()):
            out.append((src.resolve(), f"console/weights/hf/hub/{repo}/snapshots/{snap.name}/{src.name}"))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(ROOT.parent / "cultureqc_console_bundle.zip"))
    args = ap.parse_args()

    subprocess.run([sys.executable, str(ROOT / "deploy" / "sync_space.py")], check=True, stdout=subprocess.DEVNULL)
    subprocess.run([sys.executable, str(ROOT / "deploy" / "sync_space.py"), "--check"], check=True)
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    dirty = bool(subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=ROOT,
                                capture_output=True, text=True).stdout.strip())

    entries = files_to_bundle()
    manifest = {"generated_by": "scripts/make_console_bundle.py", "git_commit": commit, "git_dirty": dirty,
                "files": {arc: sha256(src) for src, arc in entries}}
    with zipfile.ZipFile(args.out, "w", zipfile.ZIP_STORED) as z:
        for src, arc in entries:
            z.write(src, arc)
        z.writestr("console/BUNDLE.json", json.dumps(manifest, indent=1, sort_keys=True))
    size = os.path.getsize(args.out) / 1e9
    print(f"wrote {args.out}: {len(entries)} files, {size:.2f} GB, commit {commit[:10]}{' (dirty)' if dirty else ''}")


if __name__ == "__main__":
    main()
