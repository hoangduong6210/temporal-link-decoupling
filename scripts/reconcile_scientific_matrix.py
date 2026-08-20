#!/usr/bin/env python3
"""Reconcile scheduler attempts into one checksumable scientific matrix.

The command is a fail-closed reduction step, not a result importer.  It accepts
only runner envelopes produced from the current clean source commit, frozen
protocol/configuration, current datasets, exact dependency environment, and a
fully recorded CUDA accelerator.  Every retry is retained in the attempt
ledger.  The final attempt for each protocol task must succeed before the
aggregate result becomes evidence-eligible.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import copy
import json
import math
import os
from pathlib import Path
import re
import statistics
import sys
from typing import Any, Iterable, Mapping, Sequence

import torch


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from temporal_link_decoupling.reproducibility import (  # noqa: E402
    _load_toml,
    atomic_write_json,
    capture_environment,
    capture_source_state,
    sha256_file,
    utc_now,
    verify_locked_environment,
)


JOB_ID = re.compile(r"LP-JOB-[A-Z0-9-]+")
SEED_SUFFIX = re.compile(r":seed-(\d+)$")
MAIN_PROFILES = ("coupled-end-to-end", "decoupled", "freeze-then-probe")
BASELINE_PROFILE = "temporal-baselines"
BASELINE_MODELS = (
    "jodie", "dyrep", "tgat", "tgn", "graphmixer", "dygformer", "cawn",
    "edgebank_inf", "edgebank_tw",
)
METRICS = ("trans_ap", "trans_auc", "ind_ap", "ind_auc")


class MatrixError(RuntimeError):
    """The retained execution set cannot support a complete scientific matrix."""


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise MatrixError(f"{label} must be an object")
    return value


def _list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise MatrixError(f"{label} must be an array")
    return value


def _file_record(root: Path, relative: str) -> dict[str, str]:
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file() or path.is_symlink():
        raise MatrixError(f"missing or unsafe matrix input: {relative}")
    return {"path": relative, "sha256": sha256_file(path)}


def _current_datasets(root: Path) -> dict[str, dict[str, Any]]:
    manifest = _load_toml(root / "resources/manifest.toml")
    datasets: dict[str, dict[str, Any]] = {}
    for raw in manifest.get("dataset", []):
        item = _mapping(raw, "dataset manifest entry")
        if not str(item.get("state", "")).startswith("CURRENT"):
            continue
        relative = Path(str(item.get("path", "")))
        name = relative.stem
        corpus = root / "resources" / relative
        if (
            not name
            or name in datasets
            or not corpus.is_file()
            or sha256_file(corpus) != item.get("sha256")
        ):
            raise MatrixError(f"invalid CURRENT dataset binding: {name or relative}")
        datasets[name] = {
            "id": item.get("id"),
            "path": relative.as_posix(),
            "sha256": item.get("sha256"),
            "state": item.get("state"),
            "local_verification": "MATCH",
        }
    if not datasets:
        raise MatrixError("no CURRENT datasets are available")
    return datasets


def expected_matrix(protocol: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    study = _mapping(protocol.get("study"), "protocol study")
    datasets = tuple(study.get("datasets", ()))
    seeds = tuple(study.get("seeds", ()))
    profiles = _mapping(protocol.get("task_profiles"), "protocol task profiles")
    if tuple(profile for profile in MAIN_PROFILES if profile in profiles) != MAIN_PROFILES:
        raise MatrixError("protocol main task profiles are incomplete")
    baseline = _mapping(profiles.get(BASELINE_PROFILE), "baseline profile")
    models = tuple(baseline.get("allowed_models", ()))
    if models != BASELINE_MODELS:
        raise MatrixError("protocol baseline allowlist differs from the audited matrix")
    expected: dict[str, dict[str, Any]] = {}
    for profile in MAIN_PROFILES:
        for dataset in datasets:
            for seed in seeds:
                runner_task = f"p0-off:{dataset}:seed-{seed}"
                task = f"{profile}/{runner_task}"
                expected[task] = {
                    "task_profile": profile,
                    "runner_task": runner_task,
                    "model": "srgnn-v3-3",
                    "dataset": dataset,
                    "seed": seed,
                }
    for model in models:
        for dataset in datasets:
            for seed in seeds:
                runner_task = f"{model}:{dataset}:seed-{seed}"
                task = f"{BASELINE_PROFILE}/{runner_task}"
                expected[task] = {
                    "task_profile": BASELINE_PROFILE,
                    "runner_task": runner_task,
                    "model": model,
                    "dataset": dataset,
                    "seed": seed,
                }
    return expected


def _same_record(actual: Any, expected: Mapping[str, str], label: str) -> list[str]:
    if not isinstance(actual, dict):
        return [f"{label} record is absent"]
    if actual.get("path") != expected["path"] or actual.get("sha256") != expected["sha256"]:
        return [f"{label} checksum binding differs"]
    return []


def _attempt_error(payload: Mapping[str, Any]) -> str:
    failures = payload.get("failures")
    if isinstance(failures, list):
        messages = [str(item.get("error")) for item in failures if isinstance(item, dict) and item.get("error")]
        if messages:
            return "; ".join(messages)
    return "runner attempt did not complete"


def _candidate_files(input_root: Path, excluded: Iterable[Path]) -> list[Path]:
    excluded_resolved = {path.resolve() for path in excluded}
    return [
        path for path in sorted(input_root.rglob("*.json"))
        if path.resolve() not in excluded_resolved and path.is_file() and not path.is_symlink()
    ]


def _validate_candidate(
    *,
    payload: Mapping[str, Any],
    task_spec: Mapping[str, Any],
    source_commit: str,
    records: Mapping[str, Mapping[str, str]],
    datasets: Mapping[str, Mapping[str, Any]],
    environment_digest: str,
) -> list[str]:
    issues: list[str] = []
    job = _mapping(payload.get("job"), "runner job")
    source = job.get("source")
    if not isinstance(source, dict) or source.get("commit") != source_commit or source.get("state") != "CLEAN" or source.get("dirty") is not False:
        issues.append("source commit/state differs from reconciliation source")
    resolved = job.get("resolved_configuration")
    if not isinstance(resolved, dict) or resolved.get("protocol_conformant") is not True or resolved.get("deviations") not in ([], ()): 
        issues.append("resolved protocol is absent or nonconformant")
    elif resolved.get("determinism") != "strict":
        issues.append("determinism mode is not strict")
    profile = job.get("task_profile_validation")
    if (
        not isinstance(profile, dict)
        or profile.get("valid") is not True
        or profile.get("task_id") != task_spec["task_profile"]
    ):
        issues.append("task profile validation is absent or mismatched")
    determinism = job.get("determinism")
    if not isinstance(determinism, dict) or determinism.get("strict_prerequisites_satisfied") is not True:
        issues.append("strict deterministic prerequisites were not satisfied")
    inputs = job.get("inputs")
    if not isinstance(inputs, dict):
        issues.append("input bindings are absent")
    else:
        issues.extend(_same_record(inputs.get("protocol"), records["protocol"], "protocol"))
        issues.extend(_same_record(inputs.get("configuration"), records["configuration"], "configuration"))
        issues.extend(_same_record(inputs.get("dataset_manifest"), records["dataset_manifest"], "dataset manifest"))
        issues.extend(_same_record(inputs.get("scientific_dependency_lock"), records["dependency_lock"], "dependency lock"))
        bound = inputs.get("datasets")
        expected_dataset = datasets.get(str(task_spec["dataset"]))
        if not isinstance(bound, list) or len(bound) != 1 or expected_dataset is None:
            issues.append("runner does not bind exactly one CURRENT dataset")
        else:
            for field in ("id", "path", "sha256", "state", "local_verification"):
                if bound[0].get(field) != expected_dataset.get(field):
                    issues.append(f"CURRENT dataset binding differs at {field}")
    locked = job.get("locked_environment")
    if (
        not isinstance(locked, dict)
        or locked.get("matches") is not True
        or locked.get("environment_digest_sha256") != environment_digest
    ):
        issues.append("locked dependency environment differs")
    environment = job.get("environment")
    accelerator = environment.get("accelerator") if isinstance(environment, dict) else None
    if (
        not isinstance(environment, dict)
        or environment.get("device_type") != "cuda"
        or not isinstance(accelerator, dict)
        or accelerator.get("record_state") != "RECORDED"
        or not isinstance(accelerator.get("nvidia_smi"), dict)
    ):
        issues.append("complete CUDA accelerator/driver record is absent")
    scheduler = job.get("scheduler")
    submission = scheduler.get("submission_script") if isinstance(scheduler, dict) else None
    if (
        job.get("execution_kind") != "scheduler"
        or not isinstance(scheduler, dict)
        or scheduler.get("system") != "slurm"
        or str(scheduler.get("job_id", "")) in {"", "NOT_APPLICABLE"}
        or not isinstance(submission, dict)
        or submission.get("sha256") in {None, "MISSING"}
    ):
        issues.append("scheduler/submission identity is incomplete")
    return issues


def _finite(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise MatrixError(f"{label} is not numeric")
    number = float(value)
    if not math.isfinite(number):
        raise MatrixError(f"{label} is not finite")
    return number


def _summary(runs: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for run in runs:
        grouped[(str(run["task_profile"]), str(run["model"]), str(run["dataset"]))].append(run)
    summary: list[dict[str, Any]] = []
    for (profile, model, dataset), rows in sorted(grouped.items()):
        seeds = sorted(int(row["seed"]) for row in rows)
        if len(seeds) != len(set(seeds)):
            raise MatrixError(f"duplicate seed in aggregate group: {profile}/{model}/{dataset}")
        item: dict[str, Any] = {
            "task_profile": profile,
            "model": model,
            "dataset": dataset,
            "n_seeds": len(rows),
            "seeds": seeds,
        }
        for metric in METRICS:
            values = [_finite(row.get(metric), f"{profile}/{model}/{dataset}/{metric}") for row in rows]
            item[f"{metric}_mean"] = statistics.fmean(values)
            item[f"{metric}_std"] = statistics.stdev(values) if len(values) > 1 else 0.0
        summary.append(item)
    return summary


def reconcile(
    root: Path,
    input_root: Path,
    out_path: Path,
    ledger_path: Path,
    job_id: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    root = root.resolve()
    input_root = input_root.resolve()
    if not input_root.is_relative_to(root) or not input_root.is_dir():
        raise MatrixError("input root must be an existing project-relative directory")
    if JOB_ID.fullmatch(job_id) is None:
        raise MatrixError("aggregation job ID must match LP-JOB-*")
    source = capture_source_state(root)
    protocol_path = "protocols/link_prediction_v1.toml"
    config_path = "configs/default.toml"
    lock_path = "configs/scientific-requirements-py39-cu128.lock"
    policy_path = "configs/dependency-lock-policy.toml"
    records = {
        "protocol": _file_record(root, protocol_path),
        "configuration": _file_record(root, config_path),
        "dataset_manifest": _file_record(root, "resources/manifest.toml"),
        "data_checksums": _file_record(root, "resources/checksums.sha256"),
        "source_registry": _file_record(root, "resources/source_registry.json"),
        "dependency_lock": _file_record(root, lock_path),
        "dependency_lock_policy": _file_record(root, policy_path),
        "runner": _file_record(root, "scripts/reconcile_scientific_matrix.py"),
    }
    protocol = _load_toml(root / protocol_path)
    expected = expected_matrix(protocol)
    datasets = _current_datasets(root)
    locked = verify_locked_environment(root / lock_path, root / policy_path)
    environment_digest = str(locked.get("environment_digest_sha256", "MISSING"))
    started_at = utc_now()
    candidates: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen_job_ids: set[str] = set()

    for path in _candidate_files(input_root, (out_path, ledger_path)):
        try:
            payload = _mapping(json.loads(path.read_text(encoding="utf-8")), str(path))
            if payload.get("schema_version") != 2:
                continue
            job = _mapping(payload.get("job"), f"{path}.job")
            parent_job_id = job.get("job_id")
            if not isinstance(parent_job_id, str) or JOB_ID.fullmatch(parent_job_id) is None:
                raise MatrixError(f"invalid parent job ID in {path}")
            if parent_job_id in seen_job_ids:
                raise MatrixError(f"duplicate parent job ID: {parent_job_id}")
            seen_job_ids.add(parent_job_id)
            coverage = _mapping(job.get("coverage"), f"{path}.coverage")
            runner_tasks = _list(coverage.get("expected"), f"{path}.coverage.expected")
            if len(runner_tasks) != 1 or not isinstance(runner_tasks[0], str):
                raise MatrixError(f"parent output is not one scheduler matrix cell: {path}")
            profile_record = job.get("task_profile_validation")
            profile = profile_record.get("task_id") if isinstance(profile_record, dict) else None
            semantic_task = f"{profile}/{runner_tasks[0]}"
            if semantic_task not in expected:
                continue
            spec = expected[semantic_task]
            seed_match = SEED_SUFFIX.search(runner_tasks[0])
            if seed_match is None or int(seed_match.group(1)) != spec["seed"]:
                raise MatrixError(f"cannot reconcile task seed: {semantic_task}")
            issues = _validate_candidate(
                payload=payload,
                task_spec=spec,
                source_commit=str(source.get("commit")),
                records=records,
                datasets=datasets,
                environment_digest=environment_digest,
            )
            completed = (
                not issues
                and job.get("status") == "COMPLETED"
                and job.get("exit_code") == 0
                and job.get("scientific_evidence_eligible") is True
                and coverage.get("completed") == runner_tasks
                and coverage.get("failed") == []
                and coverage.get("excluded") == []
                and payload.get("failures") == []
            )
            if completed:
                status = "COMPLETED"
                exit_code = 0
            elif issues:
                status = "EXCLUDED"
                exit_code = int(job.get("exit_code") or 1)
            else:
                status = "FAILED"
                exit_code = int(job.get("exit_code") or 1)
            scheduler = _mapping(job.get("scheduler"), f"{path}.scheduler")
            relative = path.relative_to(root).as_posix()
            candidates[semantic_task].append({
                "task_id": semantic_task,
                "parent_job_id": parent_job_id,
                "scheduler_job_id": str(scheduler.get("job_id", "UNKNOWN")),
                "array_job_id": str(scheduler.get("array_job_id", "UNKNOWN")),
                "array_task_id": str(scheduler.get("array_task_id", "UNKNOWN")),
                "seed": spec["seed"],
                "started_at": job.get("started_at") or "UNKNOWN",
                "finished_at": job.get("finished_at") or "UNKNOWN",
                "status": status,
                "exit_code": exit_code,
                "error": _attempt_error(payload),
                "reason": "; ".join(issues),
                "result_path": relative,
                "result_sha256": sha256_file(path),
                "payload": payload,
            })
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise MatrixError(f"invalid runner result {path}: {error}") from error

    attempts: list[dict[str, Any]] = []
    chosen: dict[str, dict[str, Any]] = {}
    matrix_failures: list[dict[str, str]] = []
    for task, spec in expected.items():
        task_attempts = sorted(
            candidates.get(task, []),
            key=lambda item: (str(item["started_at"]), str(item["parent_job_id"])),
        )
        for index, item in enumerate(task_attempts):
            attempt = {
                key: item[key]
                for key in (
                    "task_id", "scheduler_job_id", "array_task_id", "seed",
                    "started_at", "finished_at", "status", "exit_code",
                    "result_path", "result_sha256", "parent_job_id", "array_job_id",
                )
            }
            attempt["attempt_id"] = item["parent_job_id"]
            attempt["attempt_index"] = index
            if item["status"] == "FAILED":
                attempt["error"] = item["error"]
            elif item["status"] == "EXCLUDED":
                attempt["reason"] = item["reason"] or item["error"]
            attempts.append(attempt)
        if not task_attempts:
            matrix_failures.append({"task_id": task, "error": "no retained attempt"})
            continue
        final = task_attempts[-1]
        if final["status"] != "COMPLETED":
            matrix_failures.append({"task_id": task, "error": "final attempt is not completed"})
            continue
        chosen[task] = final

    runs: list[dict[str, Any]] = []
    for task, item in sorted(chosen.items()):
        payload = item["payload"]
        parent_runs = _list(payload.get("runs"), f"{task}.runs")
        if len(parent_runs) != 1:
            matrix_failures.append({"task_id": task, "error": "completed attempt has no unique run"})
            continue
        spec = expected[task]
        run = copy.deepcopy(_mapping(parent_runs[0], f"{task}.run"))
        if run.get("seed") != spec["seed"] or run.get("dataset") != spec["dataset"]:
            matrix_failures.append({"task_id": task, "error": "run row differs from task identity"})
            continue
        run.update({
            "job_id": job_id,
            "run_id": f"{job_id}:{task}",
            "task_profile": spec["task_profile"],
            "model": spec["model"],
            "parent_job_id": item["parent_job_id"],
            "parent_result_path": item["result_path"],
            "parent_result_sha256": item["result_sha256"],
        })
        runs.append(run)

    completed_tasks = sorted(run["run_id"].split(f"{job_id}:", 1)[1] for run in runs)
    if completed_tasks != sorted(expected):
        matrix_failures.append({"task_id": "MATRIX", "error": "normalized runs do not cover the expected matrix"})
    scheduler_job_id = os.environ.get("SLURM_JOB_ID")
    submission_value = os.environ.get("LP_SUBMISSION_SCRIPT")
    blockers: list[str] = []
    if source.get("state") != "CLEAN":
        blockers.append("reconciliation source tree is not clean")
    if protocol.get("status") != "FROZEN":
        blockers.append("protocol is not frozen")
    if not locked.get("matches"):
        blockers.append("active environment differs from the dependency lock")
    if not scheduler_job_id:
        blockers.append("reconciliation scheduler identity is absent")
    if not submission_value:
        blockers.append("reconciliation submission script identity is absent")
        submission_record = {"path": "NOT_RECORDED", "sha256": "MISSING"}
    else:
        submission_record = _file_record(root, submission_value)
    if matrix_failures:
        blockers.append("task/seed/attempt matrix is incomplete")
    status = "COMPLETED" if not blockers else "FAILED"
    exit_code = 0 if not blockers else 1
    parent_accelerators = []
    for item in chosen.values():
        environment = item["payload"]["job"]["environment"]
        parent_accelerators.append({
            "parent_job_id": item["parent_job_id"],
            "accelerator": environment["accelerator"],
            "torch_cuda_runtime": environment.get("torch_cuda_runtime"),
            "cudnn_version": environment.get("cudnn_version"),
        })
    job = {
        "schema_version": 1,
        "job_id": job_id,
        "execution_kind": "scheduler" if scheduler_job_id else "local",
        "scheduler": {
            "system": "slurm" if scheduler_job_id else "none",
            "job_id": scheduler_job_id or "NOT_APPLICABLE",
            "array_job_id": os.environ.get("SLURM_ARRAY_JOB_ID", "NOT_APPLICABLE"),
            "array_task_id": os.environ.get("SLURM_ARRAY_TASK_ID", "NOT_APPLICABLE"),
            "submission_script": submission_record,
        },
        "started_at": started_at,
        "finished_at": utc_now(),
        "status": status,
        "exit_code": exit_code,
        "source": source,
        "resolved_configuration": {
            "protocol_id": protocol.get("protocol_id"),
            "protocol_status": protocol.get("status"),
            "protocol_conformant": True,
            "deviations": [],
            "determinism": "strict",
            "aggregation_ddof": 1,
        },
        "determinism": {"strict_prerequisites_satisfied": not blockers},
        "environment": {
            **capture_environment(torch.device("cpu")),
            "parent_accelerator_records": parent_accelerators,
        },
        "inputs": {
            "runner": records["runner"],
            "protocol": records["protocol"],
            "configuration": records["configuration"],
            "scientific_dependency_lock": records["dependency_lock"],
            "dependency_lock_policy": records["dependency_lock_policy"],
            "dataset_manifest": records["dataset_manifest"],
            "data_checksums": records["data_checksums"],
            "dataset_source_registry": records["source_registry"],
            "datasets": [datasets[name] for name in protocol["study"]["datasets"]],
        },
        "coverage": {
            "expected": sorted(expected),
            "completed": completed_tasks,
            "failed": [],
            "excluded": [],
        },
        "locked_environment": locked,
        "scientific_execution_prerequisites_satisfied": not blockers,
        "scientific_mode_requested": bool(scheduler_job_id),
        "scientific_evidence_eligible": not blockers,
        "scientific_evidence_blockers": blockers,
    }
    result = {
        "schema_version": 2,
        "job": job,
        "runs": runs,
        "summary": _summary(runs) if runs else [],
        "failures": matrix_failures,
    }
    ledger = {
        "schema_version": 1,
        "job_id": job_id,
        "expected_tasks": sorted(expected),
        "attempts": attempts,
    }
    return result, ledger


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job-id", required=True, help="normalized LP-JOB-* aggregation identity")
    parser.add_argument("--input-root", type=Path, default=Path("results/audit/scientific"))
    parser.add_argument("--out", type=Path, default=Path("results/audit/scientific-matrix.json"))
    parser.add_argument(
        "--attempt-ledger",
        type=Path,
        default=Path("results/audit/scientific-matrix-attempts.json"),
    )
    parser.add_argument("--project-root", type=Path, default=ROOT, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    root = args.project_root.resolve()
    paths = []
    for value in (args.input_root, args.out, args.attempt_ledger):
        path = value if value.is_absolute() else root / value
        path = path.resolve()
        if not path.is_relative_to(root):
            parser.error("matrix paths must remain inside the project root")
        paths.append(path)
    input_root, out_path, ledger_path = paths
    try:
        result, ledger = reconcile(root, input_root, out_path, ledger_path, args.job_id)
        atomic_write_json(ledger_path, ledger)
        atomic_write_json(out_path, result)
    except MatrixError as error:
        print(json.dumps({"status": "BLOCKED", "error": str(error)}, indent=2))
        return 2
    print(json.dumps({
        "status": result["job"]["status"],
        "job_id": args.job_id,
        "expected_tasks": len(result["job"]["coverage"]["expected"]),
        "completed_tasks": len(result["job"]["coverage"]["completed"]),
        "attempts": len(ledger["attempts"]),
    }, indent=2))
    return int(result["job"]["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
