"""
Upload the approved fine-tuned weights to a PRIVATE Hugging Face model repo, for the console Space to download at
startup (deploy/hf-space-demo/console.py, demo/lab_demo.fetch_weights). Run by the repository owner with their own
Hugging Face login; no token is read or stored here.

    .venv/bin/python scripts/upload_finetuned_weights.py ~/Downloads/mcellseg_ftF_r2.weights

Refuses unless the file is the weights the latest approved change record names (configs/approved_changes.jsonl),
and unless the repo is private: the weights inherit Cellpose-SAM's non-commercial terms and are not published.
After the upload it compares the Hub's SHA-256 of the stored file with the approved one.
"""

from __future__ import annotations

import argparse
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from culture.approvals import check  # noqa: E402
from culture.finetuned import load_config  # noqa: E402

MODEL = "mcellseg_ftF_r2"
REPO_ID = "LongGrainRice/cultureqc-finetuned"             # deploy/hf-space-demo/console.py FINETUNED_REPO


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("weights", help="the local weights file")
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--repo", default=REPO_ID)
    a = ap.parse_args()
    from huggingface_hub import HfApi

    c = check("model", a.model, os.path.expanduser(a.weights))
    if not c.ok:
        sys.exit(f"not uploading: {c.reason}")
    name = os.path.basename(load_config()[a.model]["path"])           # the file name the Space looks for
    print(f"{a.weights}: {c.status} ({c.sha256[:12]}…)")
    api = HfApi()
    api.create_repo(a.repo, repo_type="model", private=True, exist_ok=True)
    if not api.model_info(a.repo).private:
        sys.exit(f"not uploading: {a.repo} exists and is public")
    api.upload_file(path_or_fileobj=os.path.expanduser(a.weights), path_in_repo=name, repo_id=a.repo,
                    repo_type="model", commit_message=f"{a.model}: approved weights {c.sha256[:12]}")
    info = api.model_info(a.repo, files_metadata=True)
    stored = next((s for s in info.siblings if s.rfilename == name), None)
    sha = stored.lfs.sha256 if stored is not None and stored.lfs else None
    if sha != c.sha256:
        sys.exit(f"uploaded, but the Hub's SHA-256 {sha} is not the approved {c.sha256}: tell me")
    print(f"{a.repo}/{name}: private, SHA-256 matches the approved record")


if __name__ == "__main__":
    main()
