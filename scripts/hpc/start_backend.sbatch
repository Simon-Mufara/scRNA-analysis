#!/usr/bin/env bash
#SBATCH --job-name=scrna-backend
#SBATCH --output=logs/backend-%j.out
#SBATCH --error=logs/backend-%j.err
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

export ANALYSIS_RUNNER="${ANALYSIS_RUNNER:-slurm}"
export SLURM_RESULTS_DIR="${SLURM_RESULTS_DIR:-$ROOT_DIR/data/slurm_results}"
mkdir -p "$SLURM_RESULTS_DIR"

exec bash scripts/hpc/start_backend.sh
