#!/usr/bin/env bash
#SBATCH --job-name=linkpred-ftp
#SBATCH --partition=nextgen
#SBATCH --time=08:00:00
#SBATCH --gpus-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --output=results/audit/slurm/%x_%j.out

set -euo pipefail

# These variables must exist before Python/CUDA starts; setting them inside the
# runner would not retroactively make hash iteration or cuBLAS deterministic.
export PYTHONHASHSEED=0
export CUBLAS_WORKSPACE_CONFIG=:4096:8
export LP_SUBMISSION_SCRIPT=slurm/freeze_then_probe.sbatch

project_root="${SLURM_SUBMIT_DIR:?Slurm did not record the submission directory}"
if [[ ! -f "$project_root/PROJECT.toml" || ! -f "$project_root/protocols/link_prediction_v1.toml" ]]; then
  echo "SLURM_SUBMIT_DIR is not the Link Prediction project root: $project_root" >&2
  exit 66
fi
cd "$project_root"
export PYTHONPATH="$project_root/src${PYTHONPATH:+:$PYTHONPATH}"

python_cmd="${PYTHON_CMD:-python}"
common=(
  --design correct_decoupled --p0_fix off --fsm_arch v3 --fsm_decode hier
  --decol_hier_v2 --causal_batch --hier_causal_policy --lambda_edge_trans 0.5
  --edge_entropy_w 0.02 --edge_uniform_kl_w 0.01
  --lfg_mode soft --compliance_floor 0.05
)

"$python_cmd" experiments/run_model.py \
  --datasets coedit,wikipedia "${common[@]}" \
  --task-id decoupled \
  --job-id "LP-JOB-SLURM-${SLURM_JOB_ID}-ARM1" \
  --out results/audit/frozen_probe_arm1.json

"$python_cmd" experiments/run_model.py \
  --datasets coedit,wikipedia "${common[@]}" --frozen_probe --probe_epochs 20 \
  --task-id freeze-then-probe \
  --job-id "LP-JOB-SLURM-${SLURM_JOB_ID}-ARM2" \
  --out results/audit/frozen_probe_arm2.json

"$python_cmd" experiments/aggregate_frozen_probe_control.py \
  --arm1 results/audit/frozen_probe_arm1.json \
  --arm2 results/audit/frozen_probe_arm2.json \
  --out results/audit/frozen_probe_control.json
