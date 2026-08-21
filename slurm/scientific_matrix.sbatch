#!/usr/bin/env bash
#SBATCH --job-name=lp-scientific
#SBATCH --account=PGS0407
#SBATCH --partition=nextgen
#SBATCH --time=20:00:00
#SBATCH --gpus-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --output=results/audit/slurm/%x_%A_%a.out

set -euo pipefail

: "${LP_TASK:?submit with --export=ALL,LP_TASK=<protocol-task-id>}"
: "${SLURM_ARRAY_TASK_ID:?this entry point requires a Slurm array}"

export PYTHONHASHSEED=0
export CUBLAS_WORKSPACE_CONFIG=:4096:8
export SRGNN_DEVICE=cuda
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-8}"
export LP_SUBMISSION_SCRIPT=slurm/scientific_matrix.sbatch

project_root="${SLURM_SUBMIT_DIR:?Slurm did not record the submission directory}"
if [[ ! -f "$project_root/PROJECT.toml" || ! -f "$project_root/protocols/link_prediction_v1.toml" ]]; then
  echo "SLURM_SUBMIT_DIR is not the Link Prediction project root: $project_root" >&2
  exit 66
fi
cd "$project_root"
export PYTHONPATH="$project_root/src${PYTHONPATH:+:$PYTHONPATH}"

datasets=(coedit wikipedia mooc)
seeds=(1 7 42)
models=(proxy_jodie proxy_dyrep proxy_tgat proxy_tgn recurrent_mlp_memory proxy_dygformer proxy_cawn diagnostic_edgebank_inf diagnostic_edgebank_tw)
task_index="$SLURM_ARRAY_TASK_ID"

if [[ "$LP_TASK" == "temporal-baselines" ]]; then
  echo "temporal-baselines is quarantined and is not part of the scientific matrix" >&2
  exit 65
  if (( task_index < 0 || task_index >= ${#models[@]} * ${#datasets[@]} * ${#seeds[@]} )); then
    echo "baseline array index outside protocol matrix: $task_index" >&2
    exit 64
  fi
  model_index=$((task_index / (${#datasets[@]} * ${#seeds[@]})))
  remainder=$((task_index % (${#datasets[@]} * ${#seeds[@]})))
  dataset_index=$((remainder / ${#seeds[@]}))
  seed_index=$((remainder % ${#seeds[@]}))
  model="${models[$model_index]}"
  dataset="${datasets[$dataset_index]}"
  seed="${seeds[$seed_index]}"
  suffix="${model//_/-}"
  suffix="${suffix^^}"
  run_dir="results/audit/scientific/$LP_TASK/$SLURM_ARRAY_JOB_ID"
  mkdir -p "$run_dir"
  python experiments/run_baselines.py \
    --task-id temporal-baselines \
    --models "$model" --datasets "$dataset" --seeds "$seed" \
    --job-id "LP-JOB-SLURM-${SLURM_ARRAY_JOB_ID}-${task_index}-${suffix}" \
    --out "$run_dir/task-${task_index}-${model}-${dataset}-seed-${seed}.json"
  exit 0
fi

if (( task_index < 0 || task_index >= ${#datasets[@]} * ${#seeds[@]} )); then
  echo "main-arm array index outside protocol matrix: $task_index" >&2
  exit 64
fi
dataset_index=$((task_index / ${#seeds[@]}))
seed_index=$((task_index % ${#seeds[@]}))
dataset="${datasets[$dataset_index]}"
seed="${seeds[$seed_index]}"
job_task="${LP_TASK^^}"
run_dir="results/audit/scientific/$LP_TASK/$SLURM_ARRAY_JOB_ID"
mkdir -p "$run_dir"

common=(
  --task-id "$LP_TASK" --datasets "$dataset" --seeds "$seed"
  --p0_fix off --lfg on --echo off --interp off --interp_entropy_w 0.01
  --design correct_decoupled --lambda_edge_trans 0.5
  --edge_entropy_w 0.02 --edge_uniform_kl_w 0.01
  --causal_batch --fsm_arch v3 --fsm_decode hier
  --decol_hier_v2 --hier_causal_policy
  --lfg_mode soft --compliance_floor 0.05
  --cc_C band --cc_thr 0.0 --cc_self_consist_w 0.0
)

case "$LP_TASK" in
  coupled-end-to-end)
    task_args=(--detach_scorepath off)
    ;;
  decoupled)
    task_args=(--detach_scorepath on)
    ;;
  freeze-then-probe)
    task_args=(--detach_scorepath on --frozen_probe --probe_epochs 20)
    ;;
  *)
    echo "unknown protocol task: $LP_TASK" >&2
    exit 64
    ;;
esac

python experiments/run_model.py \
  "${common[@]}" "${task_args[@]}" \
  --job-id "LP-JOB-SLURM-${SLURM_ARRAY_JOB_ID}-${task_index}-${job_task}" \
  --out "$run_dir/task-${task_index}-${dataset}-seed-${seed}.json"
