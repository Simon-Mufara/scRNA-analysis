#!/usr/bin/env bash
set -euo pipefail

# Start Streamlit frontend for HPC deployment.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

STREAMLIT_HOST="${STREAMLIT_HOST:-0.0.0.0}"
STREAMLIT_PORT="${STREAMLIT_PORT:-8501}"

if [[ -f ".venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

exec streamlit run app.py \
  --server.address="$STREAMLIT_HOST" \
  --server.port="$STREAMLIT_PORT" \
  --server.headless=true \
  --browser.gatherUsageStats=false
