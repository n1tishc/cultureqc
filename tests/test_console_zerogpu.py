"""The console's ZeroGPU mode (deploy/hf-space-demo/zerogpu.py), with a stub
`spaces` module: on ZeroGPU the live Analyze is wrapped in @spaces.GPU and
startup only loads the models (no forward pass, no torch.cuda device query,
since the main process has no GPU there); off ZeroGPU nothing changes. The
fine-tuned demo set is on by default: its weights download (stubbed here) and,
on ZeroGPU, the model preloads; if the download fails the set stays off.
console.py launches on import, so it runs in a subprocess with launch stubbed."""

import json
import os
import subprocess
import sys
import tempfile

from conftest import require_module

require_module("torch")
require_module("gradio")

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
if ZERO or WARM:
    torch.cuda.is_available = lambda: True          # what `import spaces` does on ZeroGPU; a CUDA backup
def no_device(*a, **k):
    raise AssertionError("torch.cuda.get_device_name called at startup")
torch.cuda.get_device_name = (lambda *a, **k: "stub GPU") if WARM else no_device

import huggingface_hub
def fake_download(repo_id, filename, revision=None, local_dir=None, **k):
    assert repo_id == "mouseland/cellpose-sam" and len(revision or "") == 40, (repo_id, revision)
    calls.append("provision:" + filename)
    return local_dir + "/" + filename                # nothing written: the log then says missing_file
huggingface_hub.hf_hub_download = fake_download     # never a real 1.2 GB download in a test

import culture.cache, culture.qc, culture.seg
culture.seg._get_model = lambda: calls.append("seg")
culture.qc._get_model = lambda: calls.append("qc")
culture.cache._get_dino = lambda: calls.append("dino")

import culture.finetuned, demo.lab_demo
culture.finetuned.preload = lambda model: calls.append("finetuned")
fetched = []
def fake_fetch(model, repo, token=None):
    fetched.append(repo)
    return ("/nonexistent/" + model, "stub") if FT == "ok" else (None, "stub: no access")
demo.lab_demo.fetch_weights = fake_fetch

import demo.analysis
def no_forward(*a, **k):
    raise AssertionError("forward pass at startup")
def warm_forward(img, image_path, *a, **k):
    import numpy as np
    from culture.ingestion import read_image
    assert np.array_equal(read_image(image_path).pixels, img), "warm-up path is not the warm-up image"
    calls.append("warmup")
demo.analysis.analyze_image = warm_forward if WARM else no_forward

import gradio as gr
gr.Blocks.launch = lambda self, *a, **k: None

runpy.run_path(SPACE + "/console.py", run_name="__main__")
live = sys.modules["demo.app"].analyze_image
import os
print("RESULT " + json.dumps({"loaded": calls, "fetched": fetched, "ft_env": os.environ.get("CULTUREQC_FINETUNED"),
                              "lab_images": len(sys.modules["demo.app"].LAB_IMAGES),
                              "duration": getattr(live, "zerogpu_duration", None),
                              "wraps_original": getattr(live, "__wrapped__", live) is no_forward}))
"""


def _run(zero: bool, ft: str = "off", warm: bool = False, cpsam_present: bool = False) -> dict:
    """ft: "off" (the Space variable set to empty), "ok" or "fail" (the weights download, stubbed).
    warm: a CUDA backup (Colab) warming up, with the forward pass stubbed.
    cpsam_present: the Cellpose model folder already holds cpsam_v2 (the Mac backup); else it is empty."""
    env = {k: v for k, v in os.environ.items()
           if k not in ("SPACES_ZERO_GPU", "CULTUREQC_SELFCHECK", "CULTUREQC_FINETUNED", "CULTUREQC_HF_TOKEN",
                        "CULTUREQC_WARMUP", "CULTUREQC_DEVICE")}
    models_dir = tempfile.mkdtemp(prefix="cpsam_")     # a fresh Space has no weights, whatever this machine has
    if cpsam_present:
        open(os.path.join(models_dir, "cpsam_v2"), "wb").close()
    env.update(PYTHONPATH=REPO, GRADIO_ANALYTICS_ENABLED="False", CELLPOSE_LOCAL_MODELS_PATH=models_dir)
    if ft == "off":
        env["CULTUREQC_FINETUNED"] = ""
    if zero:
        env.update(SPACES_ZERO_GPU="true", CULTUREQC_SELFCHECK="3")   # the self-check must be skipped
    elif not warm:
        env["CULTUREQC_WARMUP"] = "0"     # a CUDA test machine would otherwise warm up for real
    code = f"SPACE = {SPACE!r}\nZERO = {zero}\nFT = {ft!r}\nWARM = {warm}\n" + DRIVER
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
    # the approved Cellpose-SAM file is fetched first: culture/seg.py no longer downloads it
    assert out["loaded"][0] == "provision:cpsam_v2"
    assert sorted(out["loaded"][1:]) == ["dino", "qc", "seg"]
    assert "Cellpose-SAM weights downloaded, missing_file" in out["log"]   # stub writes nothing; the log says so
    assert "ZeroGPU" in out["log"]
    assert "CULTUREQC_SELFCHECK ignored on ZeroGPU" in out["log"]


def test_off_zerogpu_nothing_changes():
    out = _run(zero=False)
    assert out["duration"] is None
    assert out["wraps_original"]
    assert out["loaded"] == ["provision:cpsam_v2"]                # even with the warm-up off
    assert "ZeroGPU" not in out["log"]


def test_present_weights_are_not_downloaded_again():
    out = _run(zero=True, cpsam_present=True)
    assert "provision:cpsam_v2" not in out["loaded"]
    assert "Cellpose-SAM weights present, mismatch" in out["log"]     # an empty stand-in file, checked all the same


def test_gpu_warmup_reads_a_real_image_file():
    """The Mac/Colab backups warm up with one forward pass; analyze_image refuses an
    image_path that is not the image it is given, so the warm-up frame must be a file."""
    out = _run(zero=False, warm=True)
    assert out["loaded"] == ["provision:cpsam_v2", "warmup"]
    assert "models warmed up" in out["log"]


def test_finetuned_demo_set_preloads_on_zerogpu():
    out = _run(zero=True, ft="ok")
    assert out["loaded"][0] == "provision:cpsam_v2"
    assert sorted(out["loaded"][1:]) == ["dino", "finetuned", "qc", "seg"]
    assert out["fetched"] == ["LongGrainRice/cultureqc-finetuned"] and out["ft_env"] == "mcellseg_ftF_r2"
    assert "fine-tuned demo set on: mcellseg_ftF_r2 (stub), weights missing_file" in out["log"]


def test_finetuned_demo_set_off_when_the_weights_cannot_be_fetched():
    out = _run(zero=True, ft="fail")
    assert sorted(out["loaded"]) == ["dino", "provision:cpsam_v2", "qc", "seg"]
    assert out["ft_env"] == "" and out["lab_images"] == 0
    assert "fine-tuned demo set OFF: stub: no access" in out["log"]


def test_finetuned_demo_set_off_by_space_variable():
    out = _run(zero=True, ft="off")
    assert out["fetched"] == [] and out["lab_images"] == 0
    assert "fine-tuned demo set off" in out["log"]
