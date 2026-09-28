"""Cellpose-SAM's device: CUDA if present, else CPU, unless CULTUREQC_DEVICE=mps
opts in to Apple's GPU (the call-day Mac backup, deploy/run_console_mac.sh).
The opt-in must not change the default the tests, cache checks and Space use."""

import os
import subprocess
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CODE = "from culture import seg; print(seg._get_model().device)"


def _device(extra_env: dict) -> str:
    env = {k: v for k, v in os.environ.items() if k != "CULTUREQC_DEVICE"}
    env.update(extra_env)
    r = subprocess.run([sys.executable, "-c", CODE], cwd=REPO, env=env, capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stderr[-2000:]
    return r.stdout.strip().splitlines()[-1]


def test_default_device_is_unchanged():
    import torch

    assert _device({}).startswith("cuda" if torch.cuda.is_available() else "cpu")


@pytest.mark.skipif(sys.platform != "darwin", reason="Apple GPU only")
def test_mps_is_opt_in():
    import torch

    if not torch.backends.mps.is_available():
        pytest.skip("no MPS on this machine")
    assert _device({"CULTUREQC_DEVICE": "mps"}).startswith("mps")
