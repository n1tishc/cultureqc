"""Publish the API and built frontend together to the existing Hugging Face Space.

Run `npm run build` first, then `.venv/bin/python deploy/publish_space.py`.
Authentication uses the existing Hugging Face login; no token is stored here.
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
    build = ROOT / "site/dist"
    if not (build / "index.html").is_file():
        raise SystemExit("Run npm run build before publishing.")
    with tempfile.TemporaryDirectory() as tmp:
        stage = Path(tmp) / "space"
        shutil.copytree(ROOT / "deploy/hf-space", stage,
                        ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache", "*.pyc"))
        shutil.copytree(build, stage / "frontend")
        commit = HfApi().upload_folder(
            repo_id="LongGrainRice/cultureqc-api", repo_type="space",
            folder_path=stage,
            delete_patterns=["frontend/*"],
            commit_message="Serve cell analysis workspace and preserve signed inference records",
        )
        print(commit.commit_url)


if __name__ == "__main__":
    main()
