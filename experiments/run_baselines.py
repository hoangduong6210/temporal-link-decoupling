"""
Quarantined diagnostic proxy runner; not external-comparator evidence.

Runs simplified architectural proxies through the SAME train.py harness
that produces the v3.3 numbers (identical get_data_splits chronological split,
identical fair inductive negative sampling, identical AP/AUC metric, identical
epochs/batch). This controls the local harness only; it does not establish
faithful upstream model identity or publication eligibility.

Metric aggregation is packed INTO the run: after every completed (model,dataset,seed)
run the output json is rewritten with both `runs` (per-seed) and `summary`
(mean±std grouped by model×dataset). A wall-clock timeout therefore still leaves a
diagnostic partial result on disk — no separate post-hoc aggregator pass.

Default protocol matches the v3.3 A/B exactly:
  seeds [1,7,42] x 20 epochs x hidden 128 x batch 500 x lr 1e-3.

All outputs are excluded by protocol amendment LP-P-DECOUPLING-001-A002.
"""
import argparse
from pathlib import Path
import numpy as np

from temporal_link_decoupling.training import run_experiment, DEVICE
from temporal_link_decoupling.reproducibility import (
    atomic_write_json,
    build_job_metadata,
    configure_determinism,
    finish_job_metadata,
    resolve_run_config,
    utc_now,
    validate_task_profile,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# These labels deliberately cannot be confused with faithful external models.
# The entire task profile is excluded from scientific-matrix and paper evidence.
DEFAULT_MODELS = [
    "proxy_jodie", "proxy_dyrep", "proxy_tgat", "proxy_tgn",
    "recurrent_mlp_memory", "proxy_cawn",
]


def summarize(results):
    """Group by (model, dataset); mean±SAMPLE std (ddof=1, n-1).

 (id-fix baseline re-run): switched from population std (np.std,
    ddof=0) to SAMPLE std (ddof=1) per the paper's reporting convention for the
    3-seed baseline tables. Per-seed values are retained in `runs[]` so either
    statistic is recoverable. Falls back to 0.0 std when <2 valid seeds.
    """
    by = {}
    for r in results:
        by.setdefault((r["model"], r["dataset"]), []).append(r)
    summary = []
    for (model, ds), rows in by.items():
        def col(key):
            vals = [x[key] for x in rows if not np.isnan(x[key])]
            if not vals:
                return (float("nan"), float("nan"))
            std = float(np.std(vals, ddof=1)) if len(vals) > 1 else 0.0
            return (float(np.mean(vals)), std)
        ta_m, ta_s = col("trans_ap"); tu_m, tu_s = col("trans_auc")
        ia_m, ia_s = col("ind_ap");   iu_m, iu_s = col("ind_auc")
        times = [x["train_time_s"] for x in rows]
        summary.append({
            "model": model, "dataset": ds,
            "trans_ap_mean": ta_m, "trans_ap_std": ta_s,
            "trans_auc_mean": tu_m, "trans_auc_std": tu_s,
            "ind_ap_mean": ia_m, "ind_ap_std": ia_s,
            "ind_auc_mean": iu_m, "ind_auc_std": iu_s,
            "time_mean": float(np.mean(times)),
            "num_params": rows[0].get("num_params"),
            "n_seeds": len(rows),
        })
    return summary


def main():
    p = argparse.ArgumentParser(description="External baseline benchmark (v3.3-parity harness)")
    p.add_argument("--config", default=str(PROJECT_ROOT / "configs/default.toml"),
                   help="tracked executable configuration")
    p.add_argument("--protocol", default=str(PROJECT_ROOT / "protocols/link_prediction_v1.toml"),
                   help="tracked scientific protocol")
    p.add_argument("--job-id", default=None,
                   help="normalized LP-JOB-* identity (or set LP_JOB_ID)")
    p.add_argument("--task-id", default=None,
                   help="checksum-owned protocol task profile")
    p.add_argument("--determinism", choices=["strict", "warn", "off"], default=None)
    p.add_argument("--models", default=",".join(DEFAULT_MODELS),
                   help="comma-sep baseline keys (default: working 6)")
    p.add_argument("--datasets", default=None)
    p.add_argument("--seeds", default=None)
    p.add_argument("--epochs", type=int, default=None)
    p.add_argument("--hidden", type=int, default=None)
    p.add_argument("--batch", type=int, default=None)
    p.add_argument("--lr", type=float, default=None)
    p.add_argument("--out",
                   default=str(PROJECT_ROOT / "results" / "audit" / "baselines_benchmark.json"))
    p.add_argument("--dump_dir", default=None,
                   help="If set, write per-edge (y_true,y_score,test_idx) .npz per "
                        "(model,dataset,seed) here for post-CP eval; inline post-CP AP "
                        "computed on synthetic_regime.")
    args = p.parse_args()

    MODELS = [m.strip() for m in args.models.split(",") if m.strip()]
    requested_datasets = (
        [item.strip() for item in args.datasets.split(",") if item.strip()]
        if args.datasets is not None else None
    )
    requested_seeds = (
        [int(item) for item in args.seeds.split(",") if item.strip()]
        if args.seeds is not None else None
    )
    resolved = resolve_run_config(
        PROJECT_ROOT,
        config_path=args.config,
        protocol_path=args.protocol,
        datasets=requested_datasets,
        seeds=requested_seeds,
        epochs=args.epochs,
        hidden=args.hidden,
        batch_size=args.batch,
        learning_rate=args.lr,
        determinism=args.determinism,
    )
    if resolved.optimizer != "adam" or resolved.scheduler != "cosine-annealing":
        raise ValueError(
            f"Runner does not implement optimizer/scheduler "
            f"{resolved.optimizer}/{resolved.scheduler}"
        )
    DATASETS = list(resolved.datasets)
    SEEDS = list(resolved.seeds)
    args.datasets = ",".join(DATASETS)
    args.seeds = ",".join(str(seed) for seed in SEEDS)
    args.epochs = resolved.epochs
    args.hidden = resolved.hidden
    args.batch = resolved.batch_size
    args.lr = resolved.learning_rate
    args.determinism = resolved.determinism
    determinism_state = configure_determinism(
        resolved.determinism,
        python_hash_seed=resolved.python_hash_seed,
        cublas_workspace_config=resolved.cublas_workspace_config,
    )
    for warning in determinism_state["warnings"]:
        print(f"[determinism][WARN] {warning}")
    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = PROJECT_ROOT / out_path

    print(f"[device] {DEVICE}")
    print(f"[protocol] models={MODELS} datasets={DATASETS} seeds={SEEDS} "
          f"epochs={args.epochs} hidden={args.hidden} batch={args.batch} lr={args.lr}")

    results = []
    failures = []
    total = len(MODELS) * len(DATASETS) * len(SEEDS)
    expected_tasks = [
        f"{model}:{dataset}:seed-{seed}"
        for model in MODELS for dataset in DATASETS for seed in SEEDS
    ]
    task_profile_validation = validate_task_profile(
        PROJECT_ROOT / resolved.protocol_path,
        task_id=args.task_id,
        runner="run_baselines",
        arguments=vars(args),
    )
    job = build_job_metadata(
        PROJECT_ROOT,
        job_id=args.job_id,
        runner_path=Path(__file__),
        resolved=resolved,
        arguments=vars(args),
        expected_tasks=expected_tasks,
        determinism_state=determinism_state,
        task_profile_validation=task_profile_validation,
        device=DEVICE,
        started_at=utc_now(),
    )

    def persist() -> None:
        atomic_write_json(out_path, {
            "schema_version": 2,
            "job": job,
            "runs": results,
            "summary": summarize(results),
            "failures": failures,
        })

    persist()
    if job["scientific_mode_requested"] and job["scientific_evidence_blockers"]:
        blockers = list(job["scientific_evidence_blockers"])
        failures.append({
            "task_id": "JOB-STARTUP",
            "job_id": job["job_id"],
            "error": f"scientific startup blockers: {blockers}",
        })
        finish_job_metadata(job, failures)
        persist()
        raise RuntimeError(
            "Scientific mode is blocked before training: " + "; ".join(blockers)
        )
    idx = 0
    for model in MODELS:
        for ds in DATASETS:
            for s in SEEDS:
                idx += 1
                task_id = f"{model}:{ds}:seed-{s}"
                print(f"\n{'='*64}\nRUN {idx}/{total}  model={model}  dataset={ds}  seed={s}\n{'='*64}")
                try:
                    r = run_experiment(model, ds, args.epochs, args.hidden,
                                       args.batch, args.lr, s,
                                       dump_dir=args.dump_dir,
                                       train_ratio=resolved.train_ratio,
                                       validation_ratio=resolved.validation_ratio,
                                       weight_decay=resolved.weight_decay)
                    r["job_id"] = job["job_id"]
                    r["run_id"] = f"{job['job_id']}:{task_id}"
                    results.append(r)
                    job["coverage"]["completed"].append(task_id)
                    persist()
                    print(f"  -> {model} {ds} s{s}: Trans AP={r['trans_ap']:.4f} "
                          f"Ind AP={r['ind_ap']:.4f} [{r['train_time_s']:.0f}s]")
                except Exception as e:
                    print(f"  X FAILED {model} {ds} s{s}: {e}")
                    failures.append({"task_id": task_id, "job_id": job["job_id"],
                                     "model": model, "dataset": ds, "seed": s,
                                     "error": str(e)})
                    job["coverage"]["failed"].append(task_id)
                    persist()
                    import traceback; traceback.print_exc()

    summary = summarize(results)
    print("\n" + "="*92)
    print(f"BASELINE BENCHMARK  ({len(SEEDS)} seeds x {args.epochs} epochs x {len(DATASETS)} datasets)")
    print("="*92)
    print(f"{'Model':<12} {'Dataset':<11} | {'Trans AP':>15} | {'Ind AP':>15} | {'Time':>7} | seeds")
    print("-"*92)
    for s in summary:
        print(f"{s['model']:<12} {s['dataset']:<11} | "
              f"{s['trans_ap_mean']:.4f}+-{s['trans_ap_std']:.4f} | "
              f"{s['ind_ap_mean']:.4f}+-{s['ind_ap_std']:.4f} | "
              f"{s['time_mean']:>6.0f}s | {s['n_seeds']}")
    finish_job_metadata(job, failures)
    persist()
    print(f"\nSaved -> {out_path}")
    if failures:
        raise SystemExit(f"{len(failures)} experiment(s) failed; see {args.out}")


if __name__ == "__main__":
    main()
