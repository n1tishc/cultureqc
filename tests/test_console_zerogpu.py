"""The console's ZeroGPU mode (deploy/hf-space-demo/zerogpu.py), with a stub
`spaces` module: on ZeroGPU the live Analyze is wrapped in @spaces.GPU and
startup only loads the models (no forward pass, no torch.cuda device query,
since the main process has no GPU there); off ZeroGPU nothing changes.
console.py launches on import, so it runs in a subprocess with launch stubbed."""

import json
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPACE = os.path.join(REPO, "deploy", "hf-space-demo")

DRIVER = r"""
import json, runpy, sys, types
sys.path.insert(0, SPACE)

calls = []

spaces = types.ModuleType("spaces")
def GPU(duration=None):
    def deco(fn):
        def wrapper(*a, **k):
            return fn(*a, **k)
        wrapper.zerogpu_duration = duration
        wrapper.__wrapped__ = fn
        return wrapper
    return deco
spaces.GPU = GPU
sys.modules["spaces"] = spaces

import torch
if ZERO:
    torch.cuda.is_available = lambda: True          # what `import spaces` does on ZeroGPU
def no_device(*a, **k):
    raise AssertionError("torch.cuda.get_device_name called at startup")
torch.cuda.get_device_name = no_device

import culture.cache, culture.qc, culture.seg
culture.seg._get_model = lambda: calls.append("seg")
culture.qc._get_model = lambda: calls.append("qc")
culture.cache._get_dino = lambda: calls.append("dino")

import demo.analysis
def no_forward(*a, **k):
    raise AssertionError("forward pass at startup")
demo.analysis.analyze_image = no_forward

import gradio as gr
gr.Blocks.launch = lambda self, *a, **k: None

runpy.run_path(SPACE + "/console.py", run_name="__main__")
live = sys.modules["demo.app"].analyze_image
print("RESULT " + json.dumps({"loaded": calls,
                              "duration": getattr(live, "zerogpu_duration", None),
                              "wraps_original": getattr(live, "__wrapped__", live) is no_forward}))
"""


def _run(zero: bool) -> dict:
    env = {k: v for k, v in os.environ.items() if k not in ("SPACES_ZERO_GPU", "CULTUREQC_SELFCHECK")}
    env.update(PYTHONPATH=REPO, GRADIO_ANALYTICS_ENABLED="False")
    if zero:
        env.update(SPACES_ZERO_GPU="true", CULTUREQC_SELFCHECK="3")   # the self-check must be skipped
    else:
        env["CULTUREQC_WARMUP"] = "0"     # a CUDA test machine would otherwise warm up for real
    code = f"SPACE = {SPACE!r}\nZERO = {zero}\n" + DRIVER
    r = subprocess.run([sys.executable, "-c", code], cwd=SPACE, env=env, capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stderr[-3000:]
    line = [ln for ln in r.stdout.splitlines() if ln.startswith("RESULT ")][-1]
    out = json.loads(line[len("RESULT "):])
    out["log"] = r.stdout
    return out


def test_zerogpu_wraps_live_analyze_and_only_loads_at_startup():
    out = _run(zero=True)
    assert out["duration"] == 60
    assert out["wraps_original"]
    assert sorted(out["loaded"]) == ["dino", "qc", "seg"]
    assert "ZeroGPU" in out["log"]
    assert "CULTUREQC_SELFCHECK ignored on ZeroGPU" in out["log"]


def test_off_zerogpu_nothing_changes():
    out = _run(zero=False)
    assert out["duration"] is None
    assert out["wraps_original"]
    assert out["loaded"] == []
    assert "ZeroGPU" not in out["log"]
