"""Publish the Gradio + ZeroGPU demo Space to Hugging Face.

Run `.venv/bin/python deploy/publish_demo_space.py`. Authentication uses the
existing Hugging Face login; no token is stored here.

This targets `LongGrainRice/cultureqc-demo`, a separate Space from
`LongGrainRice/cultureqc-api` (see deploy/publish_space.py). It now runs the
review console for the call day (console.py; see its README). Nothing here
touches the production Space.

Before uploading it syncs the mirrors (including the untracked `demo/` and
anomaly banks), checks the tracked ones, and refuses to publish unless the
banks match configs/anomaly.yaml: a missing or wrong banks file would only
show up on the call as "Anomaly check: Unavailable". The Hub stores the 67 MB
banks file through LFS automatically.
"""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent


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
    with tempfile.TemporaryDirectory() as tmp:
        stage = Path(tmp) / "space"
        shutil.copytree(ROOT / "deploy/hf-space-demo", stage,
                        ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache", "*.pyc"))
        commit = HfApi().upload_folder(
            repo_id="LongGrainRice/cultureqc-demo", repo_type="space",
            folder_path=stage,
            commit_message="cultureQC review console (call day)",
        )
        print(commit.commit_url)


if __name__ == "__main__":
    main()
