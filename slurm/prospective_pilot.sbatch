#!/usr/bin/env bash
#SBATCH --job-name=lp-prospective-pilot
#SBATCH --time=00:45:00
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --output=results/prospective-pilots/%x_%A_%a.out

set -euo pipefail
: "${SLURM_SUBMIT_DIR:?submit from the project root}"
: "${SLURM_ARRAY_TASK_ID:?submit with --array=0-1}"
cd "$SLURM_SUBMIT_DIR"
test -f protocols/prospective_v1.toml
datasets=(wikipedia mooc)
if (( SLURM_ARRAY_TASK_ID < 0 || SLURM_ARRAY_TASK_ID >= ${#datasets[@]} )); then
  echo 'array index outside the prospective pilot protocol' >&2
  exit 64
fi
export PYTHONHASHSEED=0
export OMP_NUM_THREADS="$SLURM_CPUS_PER_TASK"
export OPENBLAS_NUM_THREADS="$SLURM_CPUS_PER_TASK"
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$SLURM_SUBMIT_DIR/src${PYTHONPATH:+:$PYTHONPATH}"
"${LP_PYTHON:-python3}" experiments/run_prospective_pilot.py \
  --dataset "${datasets[$SLURM_ARRAY_TASK_ID]}" \
  --output-dir "results/prospective-pilots/${SLURM_ARRAY_JOB_ID}/${SLURM_ARRAY_TASK_ID}"
