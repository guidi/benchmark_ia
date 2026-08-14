#!/usr/bin/env bash
set -euo pipefail

MODEL_NAME="${MODEL_NAME:-microsoft/Fara1.5-4B}"
SERVER_PORT="${SERVER_PORT:-8001}"
SERVER_HOST="${SERVER_HOST:-0.0.0.0}"
SERVER_BITS="${SERVER_BITS:-}"
VENV_DIR="${VENV_DIR:-}"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

if [[ -n "$VENV_DIR" ]]; then
  export LD_LIBRARY_PATH="$VENV_DIR/lib/python3.10/site-packages/nvidia/cu13/lib:$VENV_DIR/lib/python3.10/site-packages/nvidia/cuda_runtime/lib:$VENV_DIR/lib/python3.10/site-packages/nvidia/cublas/lib:$VENV_DIR/lib/python3.10/site-packages/nvidia/cudnn/lib:$VENV_DIR/lib/python3.10/site-packages/nvidia/cusparse/lib:$VENV_DIR/lib/python3.10/site-packages/nvidia/cusolver/lib:$VENV_DIR/lib/python3.10/site-packages/nvidia/cufft/lib:$VENV_DIR/lib/python3.10/site-packages/nvidia/curand/lib:$VENV_DIR/lib/python3.10/site-packages/nvidia/nccl/lib:$VENV_DIR/lib/python3.10/site-packages/nvidia/nvjitlink/lib:$VENV_DIR/lib/python3.10/site-packages/nvidia/cusparselt/lib:${LD_LIBRARY_PATH:-}"
  source "$VENV_DIR/bin/activate"
fi

cmd=(
  python
  "$SCRIPT_DIR/transformers_openai_server.py"
  --model "$MODEL_NAME"
  --host "$SERVER_HOST"
  --port "$SERVER_PORT"
)

if [[ -n "$SERVER_BITS" ]]; then
  cmd+=(--bits "$SERVER_BITS")
fi

exec "${cmd[@]}"
