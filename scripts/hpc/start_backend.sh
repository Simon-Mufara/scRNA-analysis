#!/usr/bin/env bash
set -euo pipefail

# Start FastAPI backend for HPC deployment (DEBUG ONLY values should not be enabled in production).

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
WORKERS="${WORKERS:-1}"

if [[ -f ".venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

exec uvicorn backend.main:app --host "$HOST" --port "$PORT" --workers "$WORKERS"
