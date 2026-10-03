#!/usr/bin/env bash
#SBATCH --job-name=lp-prospective-development
#SBATCH --time=00:45:00
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --output=results/prospective-pilots/%x_%A_%a.out
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?submit from the pinned project checkout}"
: "${SLURM_ARRAY_TASK_ID:?submit with --array=0-1}"
: "${LP_TGN_SOURCE:?supply the registered clean TGN checkout}"
datasets=(wikipedia mooc)
if (( SLURM_ARRAY_TASK_ID < 0 || SLURM_ARRAY_TASK_ID >= ${#datasets[@]} )); then
  exit 64
fi
export PYTHONHASHSEED=0 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$SLURM_SUBMIT_DIR/src${PYTHONPATH:+:$PYTHONPATH}"
"${LP_PYTHON:-python3}" experiments/run_prospective_development.py \
  --dataset "${datasets[$SLURM_ARRAY_TASK_ID]}" \
  --output-dir "results/prospective-pilots/development/${SLURM_ARRAY_JOB_ID}/${SLURM_ARRAY_TASK_ID}"
