"""Publish the API-only Space to Hugging Face.

Run `.venv/bin/python deploy/publish_space.py`. Authentication uses the
existing Hugging Face login; no token is stored here.

The Space carries no frontend build. It is `culture.pipeline.analyze()` behind
FastAPI and nothing else — the product frontend lives on Vercel, which is where
`site/dist` gets deployed instead. `delete_patterns=["frontend/*"]` clears out
a `frontend/` folder pushed by an older version of this script; harmless once
the Space no longer has one.
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
        shutil.copytree(ROOT / "deploy/hf-space", stage,
                        ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache", "*.pyc"))
        commit = HfApi().upload_folder(
            repo_id="LongGrainRice/cultureqc-api", repo_type="space",
            folder_path=stage,
            delete_patterns=["frontend/*"],
            commit_message="Drop bundled frontend — Space is the model and API only",
        )
        print(commit.commit_url)


if __name__ == "__main__":
    main()
