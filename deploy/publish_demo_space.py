"""Publish the Gradio + ZeroGPU demo Space to Hugging Face.

Run `.venv/bin/python deploy/publish_demo_space.py`. Authentication uses the
existing Hugging Face login; no token is stored here.

This targets `LongGrainRice/cultureqc-console`, the call-day review console
(console.py; see its README), creating it on first use. It is a new Space so
that the ones already running are left as they are: `LongGrainRice/cultureqc-demo`
keeps the raw model demo, and `LongGrainRice/cultureqc-api` (see
deploy/publish_space.py) keeps serving the product frontend. Nothing here
touches either.

Before uploading it syncs the mirrors (including the untracked `demo/`,
anomaly banks and fine-tuned demo images), checks the tracked ones, and
refuses to publish unless the banks match configs/anomaly.yaml and the four
demo images are the listed files (demo/lab_demo.py): a missing or wrong banks
file would only show up on the call as "Anomaly check: Unavailable", and
missing images as a console without the demo set. The Hub stores the 67 MB
banks file through LFS automatically. The fine-tuned weights are never part
of the Space: it downloads them from a private model repo at startup
(console.py).
"""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
SPACE_ID = "LongGrainRice/cultureqc-console"


def main():
    from huggingface_hub import HfApi

    subprocess.run([sys.executable, str(ROOT / "deploy/sync_space.py")], check=True)
    subprocess.run([sys.executable, str(ROOT / "deploy/sync_space.py"), "--check"], check=True)
    space = ROOT / "deploy/hf-space-demo"
    sys.path.insert(0, str(space))
    from culture.anomaly import load_anomaly_config, load_banks

    banks, reason = load_banks(load_anomaly_config(str(space / "configs/anomaly.yaml")),
                               str(space / "cache/anomaly/banks.npz"))
    if banks is None:
        sys.exit(f"not publishing: {reason}")
    from culture.records import hash_file
    from demo import lab_demo

    wrong = [n for n, sha, *_ in lab_demo.IMAGES
             if not os.path.exists(os.path.join(lab_demo.DATA, "images", n))
             or hash_file(os.path.join(lab_demo.DATA, "images", n)) != sha]
    if wrong:
        sys.exit(f"not publishing: fine-tuned demo images missing or not the listed files: {wrong}")
    stray = [str(p) for p in space.rglob("*") if p.is_file() and p.stat().st_size > 500e6]
    if stray:
        sys.exit(f"not publishing: files over 500 MB in the Space folder (weights belong in the private repo): {stray}")
    with tempfile.TemporaryDirectory() as tmp:
        stage = Path(tmp) / "space"
        shutil.copytree(ROOT / "deploy/hf-space-demo", stage,
                        ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache", "*.pyc"))
        api = HfApi()
        api.create_repo(SPACE_ID, repo_type="space", space_sdk="gradio", exist_ok=True)
        commit = api.upload_folder(
            repo_id=SPACE_ID, repo_type="space",
            folder_path=stage,
            commit_message="cultureQC review console",
        )
        print(commit.commit_url)


if __name__ == "__main__":
    main()
