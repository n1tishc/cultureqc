"""Copy the pipeline into each Space directory so it can be pushed standalone.

    python deploy/sync_space.py [--check]

A HuggingFace Space is a git repo of its own, so it has to carry `culture/` and
`config/` inside it. Keeping a second hand-maintained copy of the analysis code
is how the deployed pipeline quietly stops being the one in the repo, so those
directories are *generated* here and the repo root stays the single source of
truth. `--check` reports drift without writing, which is the useful form in CI.

There are two Spaces, both fed from the same repo root: `hf-space` (the FastAPI
backend the product frontend calls) and `hf-space-demo` (a Gradio + ZeroGPU
demo of the same pipeline). Everything else inside each — api.py/app.py,
Dockerfile, requirements.txt, packages.txt, README.md — is hand-written and
never touched by this script.
"""

from __future__ import annotations

import argparse
import filecmp
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SPACES = [os.path.join(HERE, "hf-space"), os.path.join(HERE, "hf-space-demo")]

# (source, destination) relative to ROOT and each Space
MIRRORED = ["culture", "config"]
SKIP = {"__pycache__", ".DS_Store", ".pytest_cache"}


def _ignore(_dir, names):
    return [n for n in names if n in SKIP or n.endswith(".pyc")]


def _walk(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP]
        for f in filenames:
            if f in SKIP or f.endswith(".pyc"):
                continue
            yield os.path.relpath(os.path.join(dirpath, f), root)


def check() -> int:
    drift = []
    for space in SPACES:
        for name in MIRRORED:
            src, dst = os.path.join(ROOT, name), os.path.join(space, name)
            rel_space = os.path.relpath(space, HERE)
            if not os.path.isdir(dst):
                drift.append(f"{rel_space}/{name}/ is missing")
                continue
            s, d = set(_walk(src)), set(_walk(dst))
            drift += [f"{rel_space}/{name}/{p} not synced" for p in sorted(s - d)]
            drift += [f"{rel_space}/{name}/{p} is stale" for p in sorted(d - s)]
            drift += [f"{rel_space}/{name}/{p} differs" for p in sorted(s & d)
                      if not filecmp.cmp(os.path.join(src, p), os.path.join(dst, p), shallow=False)]
    if drift:
        print("Spaces are out of sync with the repo:")
        for d in drift:
            print("  " + d)
        print("\nrun: python deploy/sync_space.py")
        return 1
    print(f"Spaces match the repo ({', '.join(n + '/' for n in MIRRORED)}, "
          f"{len(SPACES)} space(s))")
    return 0


def sync() -> int:
    for space in SPACES:
        for name in MIRRORED:
            src, dst = os.path.join(ROOT, name), os.path.join(space, name)
            if not os.path.isdir(src):
                print(f"  !! {src} does not exist", file=sys.stderr)
                return 1
            shutil.rmtree(dst, ignore_errors=True)
            shutil.copytree(src, dst, ignore=_ignore)
            print(f"  {name}/ -> {os.path.relpath(dst, ROOT)}  "
                  f"({sum(1 for _ in _walk(dst))} files)")
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--check", action="store_true",
                   help="report drift instead of writing")
    a = p.parse_args()
    sys.exit(check() if a.check else sync())
