#!/usr/bin/env bash
# Call-day backup: the review console on this Mac, with no Hugging Face
# dependency at run time (deploy/README.md, "Backup: the Mac").
#
#   deploy/run_console_mac.sh              # http://127.0.0.1:7860
#   deploy/run_console_mac.sh --selfcheck  # dry run: writes results/live_latency_mac_mps.md, then exits
#
# Runs the same console.py the Space runs, from deploy/hf-space-demo/ after a
# fresh sync. Cellpose-SAM runs on Apple's GPU (CULTUREQC_DEVICE=mps); DINOv2
# and the classifier stay on CPU. Model weights come from the local caches
# only (offline flags below), so an outage at Hugging Face can't stop it; if a
# weight is missing locally it fails at startup, not on the call.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ROOT/.venv/bin/python"

export CULTUREQC_DEVICE=mps
export PYTORCH_ENABLE_MPS_FALLBACK=1   # any op MPS lacks runs on CPU instead of failing
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export GRADIO_ANALYTICS_ENABLED=False

"$PY" "$ROOT/deploy/sync_space.py" >/dev/null
"$PY" "$ROOT/deploy/sync_space.py" --check

if [[ "${1:-}" == "--selfcheck" ]]; then
    cd "$ROOT/deploy/hf-space-demo"
    exec "$PY" -m demo.selfcheck --n "${2:-5}" --out "$ROOT/results/live_latency_mac_mps.md"
fi

cd "$ROOT/deploy/hf-space-demo"
exec "$PY" console.py
