#!/usr/bin/env bash
#SBATCH --job-name=lp-reconcile
#SBATCH --time=00:30:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --output=results/audit/slurm/%x_%j.out

set -euo pipefail

: "${LP_JOB_ID:?submit with --export=ALL,LP_JOB_ID=LP-JOB-*}"

export PYTHONHASHSEED=0
export CUBLAS_WORKSPACE_CONFIG=:4096:8
export LP_SUBMISSION_SCRIPT=slurm/reconcile_scientific_matrix.sbatch

project_root="${SLURM_SUBMIT_DIR:?Slurm did not record the submission directory}"
if [[ ! -f "$project_root/PROJECT.toml" || ! -f "$project_root/protocols/link_prediction_v1.toml" ]]; then
  echo "SLURM_SUBMIT_DIR is not the Link Prediction project root: $project_root" >&2
  exit 66
fi
cd "$project_root"
export PYTHONPATH="$project_root/src${PYTHONPATH:+:$PYTHONPATH}"

python scripts/reconcile_scientific_matrix.py \
  --job-id "$LP_JOB_ID" \
  --input-root results/audit/scientific \
  --out results/audit/scientific-matrix.json \
  --attempt-ledger results/audit/scientific-matrix-attempts.json
