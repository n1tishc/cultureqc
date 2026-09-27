"""cultureQC review console on this Space, for the call day
(cultureQC_upgrade_specv4.md §2B.7, D1).

    python console.py              # http://127.0.0.1:7860

Runs demo/app.py (Analyze with precomputed examples, Flask Timeline,
Detectability) on whatever hardware the Space has. The owner switches the
Space to a dedicated GPU tier for the dry run, the rehearsal and the call, and
back to CPU afterwards; the precomputed examples and replays work on CPU with
no model loaded. app.py (the raw-output ZeroGPU page) is kept beside it; the
README frontmatter's app_file picks which one runs.

`demo/`, the anomaly banks and `culture/`, `config/`, `configs/` are mirrored
in by deploy/sync_space.py. The startup log states what the call depends on:
`cuda: True`, whether the banks verified, and the model warm-up time.
"""
from __future__ import annotations

import os
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)


def startup_report() -> None:
    import torch

    cuda = torch.cuda.is_available()
    device = torch.cuda.get_device_name(0) if cuda else "cpu"
    print(f"cultureQC console: cuda: {cuda} ({device}), torch {torch.__version__}", flush=True)

    from culture.anomaly import load_anomaly_config, load_banks

    cfg = load_anomaly_config()
    banks, reason = load_banks(cfg) if cfg else (None, "configs/anomaly.yaml not found")
    print(f"cultureQC console: anomaly banks {'verified' if banks else 'UNAVAILABLE: ' + reason}", flush=True)

    # Load the models before the first click. On CPU this would mean a
    # multi-minute Cellpose-SAM pass, so warm up only on a GPU.
    if cuda and os.environ.get("CULTUREQC_WARMUP", "1") == "1":
        import numpy as np

        from demo.analysis import analyze_image

        t0 = time.perf_counter()
        analyze_image(np.full((512, 512), 128, np.uint8), os.path.join(ROOT, "console.py"), "unknown", 80.0)
        print(f"cultureQC console: models warmed up in {time.perf_counter() - t0:.1f} s", flush=True)

    # Dry run (Thu Oct 1): parity + latency report in the log, for results/live_latency_gpu.md.
    n = int(os.environ.get("CULTUREQC_SELFCHECK", "0") or 0)
    if n:
        from demo.selfcheck import run

        print(run(n), flush=True)


startup_report()

from demo.app import CSS, demo  # noqa: E402
from demo.theme import CultureQCTheme  # noqa: E402

demo.launch(theme=CultureQCTheme(), css=CSS, footer_links=[])
