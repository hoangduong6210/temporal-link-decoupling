#!/usr/bin/env bash
#SBATCH --job-name=lp-prospective-diagnostics
#SBATCH --time=00:35:00
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --output=results/prospective-pilots/%x_%A_%a.out
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?submit from the pinned project checkout}"
: "${SLURM_ARRAY_TASK_ID:?submit with --array=0-5}"
: "${LP_TGN_SOURCE:?supply the registered clean TGN checkout}"
if (( SLURM_ARRAY_TASK_ID < 0 || SLURM_ARRAY_TASK_ID > 5 )); then exit 64; fi
datasets=(wikipedia mooc)
dataset="${datasets[$((SLURM_ARRAY_TASK_ID / 3))]}"
seed="$((SLURM_ARRAY_TASK_ID % 3 + 1))"
export PYTHONHASHSEED=0 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$SLURM_SUBMIT_DIR/src${PYTHONPATH:+:$PYTHONPATH}"
"${LP_PYTHON:-python3}" experiments/run_prospective_diagnostics.py \
 --dataset "$dataset" --seed "$seed" \
 --output-dir "results/prospective-pilots/diagnostics/${SLURM_ARRAY_JOB_ID}/${SLURM_ARRAY_TASK_ID}"
