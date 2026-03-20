#!/usr/bin/env bash
#SBATCH --job-name=scrna-streamlit
#SBATCH --output=logs/streamlit-%j.out
#SBATCH --error=logs/streamlit-%j.err
#SBATCH --time=7-00:00:00
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G

set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"
mkdir -p logs

if [[ -f ".venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

exec bash scripts/hpc/start_streamlit.sh
