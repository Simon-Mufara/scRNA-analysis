#!/usr/bin/env bash
#SBATCH --job-name=scrna-pipeline
#SBATCH --output=logs/slurm-%j.out
#SBATCH --error=logs/slurm-%j.err
#SBATCH --time=24:00:00
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G

set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: sbatch scripts/hpc/run_pipeline.sbatch <input_path> <result_json_path>"
  exit 1
fi

INPUT_PATH="$1"
RESULT_JSON="$2"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"
mkdir -p logs
mkdir -p "$(dirname "$RESULT_JSON")"

if [[ -f ".venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

python - <<'PY' "$INPUT_PATH" "$RESULT_JSON"
import json
import sys
from backend.services.pipeline_service import run_pipeline_for_file

input_path = sys.argv[1]
result_json = sys.argv[2]
try:
    result = run_pipeline_for_file(input_path)
    with open(result_json, "w", encoding="utf-8") as fh:
        json.dump({"status": "success", "result": result, "error": None}, fh)
    print(json.dumps(result))
except Exception as exc:
    with open(result_json, "w", encoding="utf-8") as fh:
        json.dump({"status": "error", "result": None, "error": str(exc)}, fh)
    raise
PY
