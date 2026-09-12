"""Publish the Gradio + ZeroGPU demo Space to Hugging Face.

Run `.venv/bin/python deploy/publish_demo_space.py`. Authentication uses the
existing Hugging Face login; no token is stored here.

This targets `LongGrainRice/cultureqc-demo`, a separate Space from
`LongGrainRice/cultureqc-api` (see deploy/publish_space.py) — it exists only
so a link can go to one person and they see the model's raw output on
ZeroGPU. Nothing here touches the production Space.
"""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent


def main():
    from huggingface_hub import HfApi

    subprocess.run([sys.executable, str(ROOT / "deploy/sync_space.py"), "--check"], check=True)
    with tempfile.TemporaryDirectory() as tmp:
        stage = Path(tmp) / "space"
        shutil.copytree(ROOT / "deploy/hf-space-demo", stage,
                        ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache", "*.pyc"))
        commit = HfApi().upload_folder(
            repo_id="LongGrainRice/cultureqc-demo", repo_type="space",
            folder_path=stage,
            commit_message="cultureQC raw model demo",
        )
        print(commit.commit_url)


if __name__ == "__main__":
    main()
