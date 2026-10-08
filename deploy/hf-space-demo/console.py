"""cultureQC review console on this Space, for the call day
(cultureQC_upgrade_specv4.md §2B.7, D1).

    python console.py              # http://127.0.0.1:7860

Runs demo/app.py (Analyze with precomputed examples, Flask Timeline,
Detectability) on whatever hardware the Space has. The Space runs on ZeroGPU:
a GPU is attached for each live Analyze only (zerogpu.py); the precomputed
examples and replays need no model and no GPU. The same file also runs on a
dedicated GPU tier, on CPU, and on the Mac and Colab backups, where
SPACES_ZERO_GPU is unset and zerogpu.py is not used. app.py (the raw-output
page, its own ZeroGPU Space) is kept beside it; the README frontmatter's
app_file picks which one runs.

`demo/`, the anomaly banks, the fine-tuned demo set's images and `culture/`,
`config/`, `configs/` are mirrored in by deploy/sync_space.py. The startup log
states what the call depends on: `cuda: True`, whether the banks verified,
whether the fine-tuned demo set is on and its weights match, and the model
warm-up time.
"""
from __future__ import annotations

import os
import sys
import time

# On ZeroGPU, `spaces` has to be imported before torch. Only there: the Colab
# backup doesn't install it.
if os.environ.get("SPACES_ZERO_GPU"):
    import spaces  # noqa: F401

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

import zerogpu  # noqa: E402

# The approved fine-tuned model's demo set (demo/lab_demo.py): four test images
# from the lab it was trained on get its reading beside the shipped one, and it
# decides nothing; any other image gets no fine-tuned reading. On by default
# here; a Space variable CULTUREQC_FINETUNED set to empty turns it off without a
# republish. The weights
# are not in this Space: they come from a private model repo, read with the
# CULTUREQC_HF_TOKEN secret. If they can't be fetched, the set stays off and the
# console runs as before.
FINETUNED = "mcellseg_ftF_r2"
FINETUNED_REPO = "LongGrainRice/cultureqc-finetuned"
os.environ.setdefault("CULTUREQC_FINETUNED", FINETUNED)


def finetuned_setup() -> None:
    from demo import lab_demo

    model = lab_demo.model_id()
    if not model:
        print("cultureQC console: fine-tuned demo set off", flush=True)
        return
    repo = os.environ.get("CULTUREQC_FINETUNED_REPO", FINETUNED_REPO)
    path, how = lab_demo.fetch_weights(model, repo, token=os.environ.get("CULTUREQC_HF_TOKEN") or None)
    if path is None:
        os.environ[lab_demo.MODEL_ENV] = ""              # before demo.app is imported: no buttons
        print(f"cultureQC console: fine-tuned demo set OFF: {how}", flush=True)
        return
    from culture.approvals import check

    c = check("model", model, path)
    n = len(lab_demo.available())
    print(f"cultureQC console: fine-tuned demo set on: {model} ({how}), weights {c.status}"
          + ("" if c.ok else f" ({c.reason}; every reading will be refused)")
          + f", {n} of {len(lab_demo.IMAGES)} demo images present", flush=True)


def startup_report() -> None:
    import torch

    finetuned_setup()

    if zerogpu.ZERO_GPU:
        # No GPU in this process: asking torch.cuda for a device name here
        # would fail. The GPU is attached per live Analyze.
        cuda = mps = False
        print(f"cultureQC console: ZeroGPU (a GPU per live Analyze, up to {zerogpu.DURATION_S} s), "
              f"torch {torch.__version__}", flush=True)
    else:
        cuda = torch.cuda.is_available()
        device = torch.cuda.get_device_name(0) if cuda else "cpu"
        mps = os.environ.get("CULTUREQC_DEVICE") == "mps" and torch.backends.mps.is_available()
        print(f"cultureQC console: cuda: {cuda} ({device}), torch {torch.__version__}"
              + (", Cellpose-SAM on Apple MPS" if mps else ""), flush=True)

    from culture.anomaly import load_anomaly_config, load_banks

    cfg = load_anomaly_config()
    banks, reason = load_banks(cfg) if cfg else (None, "configs/anomaly.yaml not found")
    print(f"cultureQC console: anomaly banks {'verified' if banks else 'UNAVAILABLE: ' + reason}", flush=True)

    # Load the models before the first click. On ZeroGPU, load only (no GPU
    # here). On CPU a warm-up would mean a multi-minute Cellpose-SAM pass, so
    # warm up only on a GPU (CUDA, or Apple MPS on the Mac backup).
    warmup = os.environ.get("CULTUREQC_WARMUP", "1") == "1"
    if zerogpu.ZERO_GPU and warmup:
        t0 = time.perf_counter()
        zerogpu.load_models()
        print(f"cultureQC console: models loaded in {time.perf_counter() - t0:.1f} s", flush=True)
    elif (cuda or mps) and warmup:
        import numpy as np

        from demo.analysis import analyze_image

        t0 = time.perf_counter()
        analyze_image(np.full((512, 512), 128, np.uint8), os.path.join(ROOT, "console.py"), "unknown", 80.0)
        from demo import lab_demo

        if lab_demo.model_id():
            from culture.finetuned import preload

            preload(lab_demo.model_id())
        print(f"cultureQC console: models warmed up in {time.perf_counter() - t0:.1f} s", flush=True)

    # Dry run (Thu Oct 1): parity + latency report in the log, for results/live_latency_gpu.md.
    n = int(os.environ.get("CULTUREQC_SELFCHECK", "0") or 0)
    if n and zerogpu.ZERO_GPU:
        print("cultureQC console: CULTUREQC_SELFCHECK ignored on ZeroGPU (no GPU at startup); "
              "time live Analyze in the browser instead", flush=True)
    elif n:
        from demo.selfcheck import run

        print(run(n), flush=True)


startup_report()

import demo.app as app_module  # noqa: E402
from demo.app import CSS, demo  # noqa: E402
from demo.viz3d import HEAD  # noqa: E402
from demo.theme import CultureQCTheme  # noqa: E402

if zerogpu.ZERO_GPU:
    zerogpu.wrap_live_analysis(app_module)

# Spaces turn on server-side rendering by default (a Node proxy on :7860 in
# front of Python). Off, so the Space serves the page the way every local
# check ran it, straight from Python.
# CULTUREQC_SHARE=1 asks Gradio for a public share link (the Colab backup,
# nb/05_console_colab.ipynb); off otherwise, including inside Colab, where
# Gradio would turn it on by itself.
# HEAD: the 3D views' camera turn and timeline build-up (demo/viz3d.py).
demo.launch(theme=CultureQCTheme(), css=CSS, head=HEAD, footer_links=[], ssr_mode=False,
            share=os.environ.get("CULTUREQC_SHARE") == "1")
