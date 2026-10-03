#!/usr/bin/env bash
#SBATCH --job-name=lp-prospective-mechanism
#SBATCH --time=00:40:00
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --output=results/prospective-pilots/%x_%A_%a.out
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?submit from the pinned scratch checkout}"
: "${SLURM_ARRAY_TASK_ID:?submit with --array=0-11}"
: "${LP_PYTHON:?supply the verified isolated CPU interpreter}"
if (( SLURM_ARRAY_TASK_ID < 0 || SLURM_ARRAY_TASK_ID > 11 )); then exit 64; fi
datasets=(wikipedia mooc)
policies=(random mixed)
dataset="${datasets[$((SLURM_ARRAY_TASK_ID / 6))]}"
seed="$(((SLURM_ARRAY_TASK_ID % 6) / 2 + 1))"
policy="${policies[$((SLURM_ARRAY_TASK_ID % 2))]}"
export PYTHONHASHSEED=0 PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
export PYTHONPATH="$SLURM_SUBMIT_DIR/src"
"$LP_PYTHON" experiments/run_prospective_mechanism.py \
 --dataset "$dataset" --seed "$seed" --policy "$policy" \
 --output-dir "results/prospective-pilots/mechanism/${SLURM_ARRAY_JOB_ID}/${SLURM_ARRAY_TASK_ID}"
