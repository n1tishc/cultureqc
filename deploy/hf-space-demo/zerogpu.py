"""ZeroGPU support for the console (console.py), active only when the Space
runs on ZeroGPU (Spaces set SPACES_ZERO_GPU there). Everywhere else (the Mac
and Colab backups, a dedicated GPU tier, local runs) nothing here is used and
the console behaves as before.

On ZeroGPU the main process never has a GPU: `import spaces` (done first
thing in console.py) makes torch.cuda.is_available() report True so models
can be placed on "cuda" at load time, but a GPU is attached only for the
duration of a call to an @spaces.GPU function, in a worker process. So:
    - load the models at startup, without a forward pass (load_models);
    - run the live Analyze inside @spaces.GPU (wrap_live_analysis);
    - the precomputed examples and replays never touch a model, so they use
      no GPU quota.
See https://huggingface.co/docs/hub/en/spaces-zerogpu.
"""
from __future__ import annotations

import os

ZERO_GPU = bool(os.environ.get("SPACES_ZERO_GPU"))

# The longest one live Analyze may hold the GPU. A visitor needs at least this
# much quota left for the call to start, so it is kept small; 60 s is the value
# the raw-output page (app.py) uses. Tune from measured times
# (results/live_latency_zerogpu.md), not guesses.
DURATION_S = 60


def load_models() -> None:
    """Cellpose-SAM, the QC classifier and DINOv2, loaded onto "cuda" once in
    the main process. Loading only: a forward pass here would have no GPU.
    With the fine-tuned demo set on (demo/lab_demo.py), the fine-tuned model
    too, if its weights pass the approvals check."""
    from culture.cache import _get_dino
    from culture.qc import _get_model as qc_model
    from culture.seg import _get_model as seg_model
    from demo import lab_demo

    seg_model()
    qc_model()
    _get_dino()
    if lab_demo.model_id():
        from culture.finetuned import preload

        preload(lab_demo.model_id())


def wrap_live_analysis(app_module) -> None:
    """Run demo/app.py's live Analyze on a ZeroGPU GPU. run_analysis looks up
    analyze_image in its module at call time, so rebinding it there is enough;
    the record is still written in the main process, outside the GPU call."""
    import spaces

    app_module.analyze_image = spaces.GPU(duration=DURATION_S)(app_module.analyze_image)
