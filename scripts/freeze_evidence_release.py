#!/usr/bin/env python3
"""Freeze a checksum-closed scientific evidence release.

The command is intentionally fail-closed.  It does not infer missing execution
history, accept historical result files, or bless a runner's self-declared
eligibility.  A release plan must bind every result to a registered scientific
job record and a complete attempt ledger, and must describe how every aggregate
is reconstructed from the retained per-task rows.

Typical usage::

    python scripts/freeze_evidence_release.py \
      --plan release-plans/LP-REL-2026-001.json --activate

Run ``--help`` for the release-plan contract.  The destination is always
``results/frozen/<release-id>`` below the selected project root.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import statistics
import subprocess
import tempfile
from typing import Any, Iterable, Mapping, Sequence

try:  # Python 3.11+
    import tomllib  # type: ignore[import-not-found]
except ModuleNotFoundError:  # pragma: no cover - Python 3.9/3.10
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ModuleNotFoundError:  # dependency-free cluster fallback
        class _MiniToml:
            """Small parser for the repository's scalar/table/array-table subset."""

            TOMLDecodeError = ValueError

            @staticmethod
            def load(stream: Any) -> dict[str, Any]:
                raw = stream.read()
                text = raw.decode("utf-8") if isinstance(raw, bytes) else raw
                root: dict[str, Any] = {}
                current = root
                logical: list[str] = []
                pending = ""
                for raw_line in text.splitlines():
                    line = raw_line.split("#", 1)[0].strip()
                    if not line:
                        continue
                    pending = f"{pending} {line}".strip()
                    if pending.count("[") > pending.count("]"):
                        continue
                    logical.append(pending)
                    pending = ""
                if pending:
                    raise ValueError("unterminated TOML array")
                for line in logical:
                    if line.startswith("[[") and line.endswith("]]" ):
                        name = line[2:-2].strip()
                        container = root
                        parts = name.split(".")
                        for part in parts[:-1]:
                            child = container.setdefault(part, {})
                            if not isinstance(child, dict):
                                raise ValueError(f"invalid array-table path: {name}")
                            container = child
                        array = container.setdefault(parts[-1], [])
                        if not isinstance(array, list):
                            raise ValueError(f"array-table collides with scalar: {name}")
                        current = {}
                        array.append(current)
                        continue
                    if line.startswith("[") and line.endswith("]"):
                        name = line[1:-1].strip()
                        current = root
                        for part in name.split("."):
                            child = current.setdefault(part, {})
                            if not isinstance(child, dict):
                                raise ValueError(f"invalid table path: {name}")
                            current = child
                        continue
                    if "=" not in line:
                        raise ValueError(f"invalid TOML assignment: {line}")
                    key, raw_value = (part.strip() for part in line.split("=", 1))
                    if raw_value.startswith(('"', "[")):
                        value: Any = json.loads(raw_value)
                    elif raw_value in {"true", "false"}:
                        value = raw_value == "true"
                    else:
                        try:
                            value = int(raw_value)
                        except ValueError:
                            value = float(raw_value)
                    current[key] = value
                return root

        tomllib = _MiniToml()  # type: ignore[assignment]


ROOT = Path(__file__).resolve().parents[1]
HEX40 = re.compile(r"[0-9a-f]{40}")
HEX64 = re.compile(r"[0-9a-f]{64}")
RELEASE_ID = re.compile(r"LP-REL-[A-Z0-9-]+")
JOB_ID = re.compile(r"LP-JOB-[A-Z0-9-]+")
CLAIM_ID = re.compile(r"LP-C-[A-Z0-9-]+")
EVIDENCE_ID = re.compile(r"LP-E-[A-Z0-9-]+")


class GateError(RuntimeError):
    """A release prerequisite is absent, ambiguous, or inconsistent."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path) -> Any:
    def reject_constant(value: str) -> None:
        raise ValueError(f"non-finite JSON constant: {value}")

    try:
        return json.loads(
            path.read_text(encoding="utf-8"), parse_constant=reject_constant
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise GateError(f"invalid JSON {path}: {exc}") from exc


def _load_toml(path: Path) -> dict[str, Any]:
    try:
        with path.open("rb") as stream:
            value = tomllib.load(stream)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise GateError(f"invalid TOML {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise GateError(f"expected a TOML table at {path}")
    return value


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(payload, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def _require_mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise GateError(f"{label} must be an object")
    return value


def _require_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise GateError(f"{label} must be an array")
    return value


def _required(mapping: Mapping[str, Any], keys: Iterable[str], label: str) -> None:
    missing = [key for key in keys if key not in mapping]
    if missing:
        raise GateError(f"{label} lacks required fields: {', '.join(missing)}")


def _unique_strings(value: Any, label: str, pattern: re.Pattern[str] | None = None) -> list[str]:
    items = _require_list(value, label)
    if not items or any(not isinstance(item, str) or not item for item in items):
        raise GateError(f"{label} must contain non-empty strings")
    if len(items) != len(set(items)):
        raise GateError(f"{label} contains duplicates")
    if pattern is not None:
        invalid = [item for item in items if pattern.fullmatch(item) is None]
        if invalid:
            raise GateError(f"{label} contains invalid identifiers: {invalid}")
    return items


def _safe_file(root: Path, raw_path: Any, label: str) -> tuple[str, Path]:
    if not isinstance(raw_path, str) or not raw_path:
        raise GateError(f"{label} path must be a non-empty string")
    relative = Path(raw_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise GateError(f"{label} path must be project-relative: {raw_path}")
    candidate = root / relative
    resolved = candidate.resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise GateError(f"{label} path escapes project root: {raw_path}")
    if candidate.is_symlink() or not resolved.is_file():
        raise GateError(f"{label} must be a regular non-symlink file: {raw_path}")
    return relative.as_posix(), resolved


def _file_record(root: Path, value: Any, label: str) -> dict[str, str]:
    record = _require_mapping(value, label)
    _required(record, ("path", "sha256"), label)
    rel, path = _safe_file(root, record["path"], label)
    declared = record["sha256"]
    if not isinstance(declared, str) or HEX64.fullmatch(declared) is None:
        raise GateError(f"{label}.sha256 must be lowercase 64-hex")
    actual = _sha256(path)
    if declared != actual:
        raise GateError(f"{label} checksum mismatch: declared {declared}, actual {actual}")
    return {"path": rel, "sha256": actual}


def _git(root: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *arguments],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise GateError(f"git {' '.join(arguments)} failed: {detail}")
    return result.stdout.strip()


def _verify_clean_worktree(root: Path) -> str:
    head = _git(root, "rev-parse", "HEAD")
    if HEX40.fullmatch(head) is None:
        raise GateError("git HEAD is not a full 40-hex commit")
    dirty = _git(root, "status", "--porcelain", "--untracked-files=normal", "--", ".")
    if dirty:
        preview = "; ".join(dirty.splitlines()[:5])
        raise GateError(f"project worktree is not clean: {preview}")
    return head


def _verify_commit(root: Path, commit: Any, label: str) -> str:
    if not isinstance(commit, str) or HEX40.fullmatch(commit) is None:
        raise GateError(f"{label} must be a full lowercase 40-hex commit")
    _git(root, "cat-file", "-e", f"{commit}^{{commit}}")
    return commit


def _checksum_registry(path: Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise GateError(f"cannot read checksum registry {path}: {exc}") from exc
    for lineno, line in enumerate(lines, 1):
        if not line.strip():
            continue
        pieces = line.split(maxsplit=1)
        if len(pieces) != 2 or HEX64.fullmatch(pieces[0]) is None:
            raise GateError(f"invalid checksum record {path}:{lineno}")
        digest, rel = pieces
        if rel in entries:
            raise GateError(f"duplicate checksum path in {path}: {rel}")
        entries[rel] = digest
    return entries


def _registered_job(root: Path, raw_path: Any) -> tuple[str, Path, dict[str, Any]]:
    rel, path = _safe_file(root, raw_path, "scientific job record")
    expected_parent = (root / "evidence/jobs").resolve()
    if path.parent != expected_parent or path.suffix != ".toml":
        raise GateError("scientific job records must be evidence/jobs/*.toml")
    registry = _checksum_registry(expected_parent / "checksums.sha256")
    if registry.get(rel) != _sha256(path):
        raise GateError(f"scientific job record is not checksum-registered: {rel}")
    return rel, path, _load_toml(path)


def _verify_current_datasets(
    root: Path, manifest: dict[str, str], checksums: dict[str, str]
) -> dict[str, dict[str, str]]:
    manifest_data = _load_toml(root / manifest["path"])
    entries = manifest_data.get("dataset")
    if not isinstance(entries, list):
        raise GateError("data manifest has no [[dataset]] records")
    checksum_entries = _checksum_registry(root / checksums["path"])
    current: dict[str, dict[str, str]] = {}
    for raw in entries:
        entry = _require_mapping(raw, "dataset manifest record")
        if not str(entry.get("state", "")).startswith("CURRENT"):
            continue
        _required(entry, ("id", "path", "sha256", "state"), "current dataset record")
        rel_to_resources = Path(str(entry["path"]))
        if rel_to_resources.is_absolute() or ".." in rel_to_resources.parts:
            raise GateError(f"unsafe dataset path: {entry['path']}")
        corpus_rel = (Path("resources") / rel_to_resources).as_posix()
        _, corpus = _safe_file(root, corpus_rel, f"dataset {entry['id']}")
        digest = str(entry["sha256"])
        if HEX64.fullmatch(digest) is None or _sha256(corpus) != digest:
            raise GateError(f"dataset checksum mismatch: {entry['id']}")
        if checksum_entries.get(corpus_rel) != digest:
            raise GateError(f"dataset absent or stale in data checksum manifest: {entry['id']}")
        name = rel_to_resources.stem
        if name in current:
            raise GateError(f"duplicate CURRENT dataset stem: {name}")
        current[name] = {
            "id": str(entry["id"]),
            "path": rel_to_resources.as_posix(),
            "sha256": digest,
            "state": str(entry["state"]),
        }
    if not current:
        raise GateError("data manifest contains no CURRENT datasets")
    return current


def _same_file_record(actual: Any, expected: Mapping[str, str], label: str) -> None:
    value = _require_mapping(actual, label)
    if value.get("path") != expected["path"] or value.get("sha256") != expected["sha256"]:
        raise GateError(f"{label} does not match the release plan")


def _validate_attempt_ledger(
    payload: Any,
    *,
    job_id: str,
    expected_tasks: Sequence[str],
    declared_counts: Mapping[str, Any],
) -> dict[str, Any]:
    ledger = _require_mapping(payload, "attempt ledger")
    _required(ledger, ("schema_version", "job_id", "expected_tasks", "attempts"), "attempt ledger")
    if ledger["schema_version"] != 1 or ledger["job_id"] != job_id:
        raise GateError(f"attempt ledger identity mismatch for {job_id}")
    ledger_expected = _unique_strings(ledger["expected_tasks"], "attempt ledger expected_tasks")
    if sorted(ledger_expected) != sorted(expected_tasks):
        raise GateError(f"attempt ledger task matrix disagrees with runner coverage for {job_id}")
    attempts = _require_list(ledger["attempts"], "attempt ledger attempts")
    if not attempts:
        raise GateError(f"attempt ledger is empty for {job_id}")
    by_task: dict[str, list[dict[str, Any]]] = {task: [] for task in expected_tasks}
    attempt_ids: set[str] = set()
    failed_count = 0
    excluded_count = 0
    for index, raw in enumerate(attempts):
        item = _require_mapping(raw, f"attempt[{index}]")
        _required(
            item,
            (
                "task_id", "attempt_id", "attempt_index", "status", "exit_code",
                "scheduler_job_id", "array_task_id", "seed", "started_at", "finished_at",
            ),
            f"attempt[{index}]",
        )
        task_id = item["task_id"]
        attempt_id = item["attempt_id"]
        if task_id not in by_task:
            raise GateError(f"attempt references undeclared task: {task_id}")
        if not isinstance(attempt_id, str) or not attempt_id or attempt_id in attempt_ids:
            raise GateError(f"attempt_id is empty or duplicated: {attempt_id!r}")
        attempt_ids.add(attempt_id)
        if not isinstance(item["attempt_index"], int) or item["attempt_index"] < 0:
            raise GateError(f"invalid attempt_index for {attempt_id}")
        if not isinstance(item["seed"], int):
            raise GateError(f"attempt seed must be an integer: {attempt_id}")
        if str(item["scheduler_job_id"]) in {"", "NOT_APPLICABLE", "UNKNOWN"}:
            raise GateError(f"attempt lacks scheduler identity: {attempt_id}")
        if not isinstance(item["started_at"], str) or not isinstance(item["finished_at"], str):
            raise GateError(f"attempt lacks timestamps: {attempt_id}")
        status = item["status"]
        if status == "COMPLETED":
            if item["exit_code"] != 0:
                raise GateError(f"completed attempt has nonzero exit code: {attempt_id}")
        elif status == "FAILED":
            failed_count += 1
            if not isinstance(item["exit_code"], int) or item["exit_code"] == 0 or not item.get("error"):
                raise GateError(f"failed attempt lacks nonzero exit/error: {attempt_id}")
        elif status == "EXCLUDED":
            excluded_count += 1
            if not item.get("reason"):
                raise GateError(f"excluded attempt lacks reason: {attempt_id}")
        else:
            raise GateError(f"invalid attempt status {status!r}: {attempt_id}")
        by_task[str(task_id)].append(item)

    final_seeds: dict[str, int] = {}
    for task_id, task_attempts in by_task.items():
        if not task_attempts:
            raise GateError(f"task has no recorded attempt: {task_id}")
        indexes = [item["attempt_index"] for item in task_attempts]
        if len(indexes) != len(set(indexes)):
            raise GateError(f"task has duplicate attempt indexes: {task_id}")
        final = max(task_attempts, key=lambda item: item["attempt_index"])
        if final["status"] != "COMPLETED" or final["exit_code"] != 0:
            raise GateError(f"task has no successful final attempt: {task_id}")
        final_seeds[task_id] = final["seed"]

    expected_counts = {
        "attempt_count": len(attempts),
        "failed_attempt_count": failed_count,
        "excluded_attempt_count": excluded_count,
    }
    for key, expected in expected_counts.items():
        if declared_counts.get(key) != expected:
            raise GateError(f"job record {key} mismatch: expected {expected}")
    return {
        **expected_counts,
        "task_count": len(expected_tasks),
        "final_seeds": final_seeds,
    }


def _finite_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise GateError(f"{label} is not numeric")
    number = float(value)
    if not math.isfinite(number):
        raise GateError(f"{label} is not finite")
    return number


def _reconstruct_aggregates(result: Mapping[str, Any], spec: Any, label: str) -> dict[str, Any]:
    aggregation = _require_mapping(spec, f"{label} aggregation")
    _required(aggregation, ("group_by", "metrics", "ddof"), f"{label} aggregation")
    group_by = _unique_strings(aggregation["group_by"], f"{label} aggregation.group_by")
    ddof = aggregation["ddof"]
    if ddof not in {0, 1}:
        raise GateError(f"{label} aggregation.ddof must be 0 or 1")
    tolerance = _finite_number(aggregation.get("absolute_tolerance", 1e-12), f"{label} tolerance")
    if tolerance < 0 or tolerance > 1e-9:
        raise GateError(f"{label} absolute_tolerance must be between 0 and 1e-9")
    metrics = _require_list(aggregation["metrics"], f"{label} aggregation.metrics")
    if not metrics:
        raise GateError(f"{label} aggregation.metrics is empty")
    runs = _require_list(result.get("runs"), f"{label}.runs")
    summaries = _require_list(result.get("summary"), f"{label}.summary")
    if not runs or not summaries:
        raise GateError(f"{label} must retain non-empty runs and summary arrays")

    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for index, raw in enumerate(runs):
        run = _require_mapping(raw, f"{label}.runs[{index}]")
        try:
            key = tuple(run[field] for field in group_by)
        except KeyError as exc:
            raise GateError(f"{label} run lacks grouping field {exc.args[0]}") from exc
        grouped.setdefault(key, []).append(run)
    summary_by_key: dict[tuple[Any, ...], dict[str, Any]] = {}
    for index, raw in enumerate(summaries):
        summary = _require_mapping(raw, f"{label}.summary[{index}]")
        try:
            key = tuple(summary[field] for field in group_by)
        except KeyError as exc:
            raise GateError(f"{label} summary lacks grouping field {exc.args[0]}") from exc
        if key in summary_by_key:
            raise GateError(f"{label} has duplicate summary group: {key}")
        summary_by_key[key] = summary
    if set(grouped) != set(summary_by_key):
        raise GateError(f"{label} run and summary group sets differ")

    report_groups: list[dict[str, Any]] = []
    seen_run_fields: set[str] = set()
    for raw_metric in metrics:
        metric = _require_mapping(raw_metric, f"{label} metric")
        _required(metric, ("run", "mean"), f"{label} metric")
        if not all(isinstance(metric.get(key), str) and metric[key] for key in ("run", "mean")):
            raise GateError(f"{label} metric fields must be non-empty strings")
        if metric["run"] in seen_run_fields:
            raise GateError(f"{label} repeats aggregation metric {metric['run']}")
        seen_run_fields.add(metric["run"])
        if "std" in metric and (not isinstance(metric["std"], str) or not metric["std"]):
            raise GateError(f"{label} metric.std must be a non-empty string")

    for key in sorted(grouped, key=lambda item: tuple(str(part) for part in item)):
        rows = grouped[key]
        summary = summary_by_key[key]
        group_report: dict[str, Any] = {
            "group": {field: value for field, value in zip(group_by, key)},
            "n": len(rows),
            "metrics": {},
        }
        count_field = aggregation.get("count_field")
        if count_field is not None:
            if not isinstance(count_field, str) or summary.get(count_field) != len(rows):
                raise GateError(f"{label} aggregate count mismatch for group {key}")
        for raw_metric in metrics:
            metric = _require_mapping(raw_metric, f"{label} metric")
            values = [
                _finite_number(row.get(metric["run"]), f"{label}.{metric['run']} group {key}")
                for row in rows
            ]
            mean = statistics.fmean(values)
            if len(values) < 2:
                std = 0.0
            elif ddof == 1:
                std = statistics.stdev(values)
            else:
                std = statistics.pstdev(values)
            declared_mean = _finite_number(summary.get(metric["mean"]), f"{label}.{metric['mean']}")
            if not math.isclose(mean, declared_mean, rel_tol=0.0, abs_tol=tolerance):
                raise GateError(
                    f"{label} mean reconstruction mismatch for {key}/{metric['run']}: "
                    f"{declared_mean} != {mean}"
                )
            metric_report: dict[str, Any] = {"mean": mean, "values": values}
            if "std" in metric:
                declared_std = _finite_number(summary.get(metric["std"]), f"{label}.{metric['std']}")
                if not math.isclose(std, declared_std, rel_tol=0.0, abs_tol=tolerance):
                    raise GateError(
                        f"{label} std reconstruction mismatch for {key}/{metric['run']}: "
                        f"{declared_std} != {std}"
                    )
                metric_report["std"] = std
            group_report["metrics"][metric["run"]] = metric_report
        report_groups.append(group_report)
    return {"ddof": ddof, "absolute_tolerance": tolerance, "groups": report_groups}


def _validate_job(
    root: Path,
    entry_value: Any,
    *,
    source_commit: str,
    file_records: Mapping[str, Mapping[str, str]],
    current_datasets: Mapping[str, Mapping[str, str]],
    environment_digest: str,
) -> dict[str, Any]:
    entry = _require_mapping(entry_value, "release job entry")
    _required(entry, ("record", "result", "attempt_ledger", "aggregation"), "release job entry")
    record_rel, _, record = _registered_job(root, entry["record"])
    result_rel, result_path = _safe_file(root, entry["result"], "scientific result")
    ledger_rel, ledger_path = _safe_file(root, entry["attempt_ledger"], "attempt ledger")
    if not Path(result_rel).is_relative_to(Path("results/audit")):
        raise GateError(f"scientific result must originate in results/audit: {result_rel}")
    if not Path(ledger_rel).is_relative_to(Path("results/audit")):
        raise GateError(f"attempt ledger must originate in results/audit: {ledger_rel}")

    required_record_fields = (
        "schema_version", "job_id", "scientific", "execution_kind", "scheduler_job_id",
        "source_commit", "source_state", "command", "exit_code", "outcome",
        "protocol_id", "protocol_path", "protocol_sha256", "configuration_path",
        "configuration_sha256", "data_manifest", "data_manifest_sha256",
        "data_checksums", "data_checksums_sha256", "dependency_lock",
        "dependency_lock_sha256", "environment_digest_sha256", "result_pointer",
        "result_sha256", "attempt_ledger", "attempt_ledger_sha256", "attempt_count",
        "failed_attempt_count", "excluded_attempt_count", "supported_evidence_ids",
        "supported_scientific_claim_ids",
    )
    _required(record, required_record_fields, f"job record {record_rel}")
    job_id = record["job_id"]
    if not isinstance(job_id, str) or JOB_ID.fullmatch(job_id) is None:
        raise GateError(f"invalid scientific job_id in {record_rel}")
    if record["scientific"] is not True or record["execution_kind"] != "scheduler":
        raise GateError(f"job is not a scientific scheduler execution: {job_id}")
    if str(record["scheduler_job_id"]) in {"", "NOT_APPLICABLE", "UNKNOWN"}:
        raise GateError(f"job lacks scheduler_job_id: {job_id}")
    if record["source_commit"] != source_commit or record["source_state"] != "CLEAN":
        raise GateError(f"job source identity is not the release source commit: {job_id}")
    if not isinstance(record["command"], str) or not record["command"].strip():
        raise GateError(f"job command is absent: {job_id}")
    if record["exit_code"] != 0 or record["outcome"] != "COMPLETED":
        raise GateError(f"job did not complete successfully: {job_id}")
    expected_records = {
        "protocol_path": file_records["protocol"]["path"],
        "protocol_sha256": file_records["protocol"]["sha256"],
        "configuration_path": file_records["configuration"]["path"],
        "configuration_sha256": file_records["configuration"]["sha256"],
        "data_manifest": file_records["data_manifest"]["path"],
        "data_manifest_sha256": file_records["data_manifest"]["sha256"],
        "data_checksums": file_records["data_checksums"]["path"],
        "data_checksums_sha256": file_records["data_checksums"]["sha256"],
        "dependency_lock": file_records["dependency_lock"]["path"],
        "dependency_lock_sha256": file_records["dependency_lock"]["sha256"],
        "environment_digest_sha256": environment_digest,
        "result_pointer": result_rel,
        "result_sha256": _sha256(result_path),
        "attempt_ledger": ledger_rel,
        "attempt_ledger_sha256": _sha256(ledger_path),
    }
    for field, expected in expected_records.items():
        if record[field] != expected:
            raise GateError(f"job record mismatch {job_id}.{field}: expected {expected}")

    supported_evidence = _unique_strings(
        record["supported_evidence_ids"], f"{job_id}.supported_evidence_ids", EVIDENCE_ID
    )
    supported_claims = _unique_strings(
        record["supported_scientific_claim_ids"],
        f"{job_id}.supported_scientific_claim_ids",
        CLAIM_ID,
    )
    result = _require_mapping(_load_json(result_path), f"scientific result {result_rel}")
    _required(result, ("schema_version", "job", "runs", "summary", "failures"), result_rel)
    if result["schema_version"] != 2:
        raise GateError(f"unsupported runner result schema in {result_rel}")
    job = _require_mapping(result["job"], f"{result_rel}.job")
    _required(
        job,
        (
            "job_id", "execution_kind", "scheduler", "status", "exit_code", "source",
            "resolved_configuration", "inputs", "coverage", "locked_environment",
            "scientific_evidence_eligible", "scientific_evidence_blockers",
        ),
        f"{result_rel}.job",
    )
    if job["job_id"] != job_id or job["execution_kind"] != "scheduler":
        raise GateError(f"runner/job-record identity mismatch: {job_id}")
    if job["status"] != "COMPLETED" or job["exit_code"] != 0:
        raise GateError(f"runner job did not complete successfully: {job_id}")
    if job["scientific_evidence_eligible"] is not True or job["scientific_evidence_blockers"]:
        raise GateError(f"runner did not mark prerequisites eligible: {job_id}")
    scheduler = _require_mapping(job["scheduler"], f"{job_id}.scheduler")
    if scheduler.get("system") != "slurm" or str(scheduler.get("job_id")) != str(record["scheduler_job_id"]):
        raise GateError(f"scheduler identity mismatch: {job_id}")
    source = _require_mapping(job["source"], f"{job_id}.source")
    if source.get("commit") != source_commit or source.get("dirty") is not False or source.get("state") != "CLEAN":
        raise GateError(f"runner source was not clean at {source_commit}: {job_id}")
    resolved = _require_mapping(job["resolved_configuration"], f"{job_id}.resolved_configuration")
    if resolved.get("protocol_id") != record["protocol_id"]:
        raise GateError(f"protocol ID mismatch: {job_id}")
    if resolved.get("protocol_conformant") is not True or resolved.get("deviations") not in ([], ()):
        raise GateError(f"job deviates from the resolved protocol: {job_id}")
    if resolved.get("determinism") != "strict":
        raise GateError(f"job did not use strict determinism: {job_id}")
    inputs = _require_mapping(job["inputs"], f"{job_id}.inputs")
    _same_file_record(inputs.get("protocol"), file_records["protocol"], f"{job_id}.protocol")
    _same_file_record(inputs.get("configuration"), file_records["configuration"], f"{job_id}.configuration")
    _same_file_record(inputs.get("dataset_manifest"), file_records["data_manifest"], f"{job_id}.data_manifest")
    _same_file_record(inputs.get("scientific_dependency_lock"), file_records["dependency_lock"], f"{job_id}.dependency_lock")
    job_datasets = _require_list(inputs.get("datasets"), f"{job_id}.inputs.datasets")
    if not job_datasets:
        raise GateError(f"job has no dataset bindings: {job_id}")
    for raw_dataset in job_datasets:
        dataset = _require_mapping(raw_dataset, f"{job_id} dataset")
        path = Path(str(dataset.get("path", "")))
        expected = current_datasets.get(path.stem)
        if expected is None or any(dataset.get(key) != expected[key] for key in ("id", "path", "sha256", "state")):
            raise GateError(f"job dataset does not match CURRENT manifest: {job_id}/{path.stem}")
    locked = _require_mapping(job["locked_environment"], f"{job_id}.locked_environment")
    if locked.get("matches") is not True or locked.get("environment_digest_sha256") != environment_digest:
        raise GateError(f"job environment does not match the release environment: {job_id}")
    coverage = _require_mapping(job["coverage"], f"{job_id}.coverage")
    expected_tasks = _unique_strings(coverage.get("expected"), f"{job_id}.expected tasks")
    completed = _unique_strings(coverage.get("completed"), f"{job_id}.completed tasks")
    if sorted(completed) != sorted(expected_tasks):
        raise GateError(f"job task coverage is incomplete: {job_id}")
    if coverage.get("failed") != [] or coverage.get("excluded") != [] or result["failures"] != []:
        raise GateError(f"job retains an unresolved failed/excluded task: {job_id}")
    ledger_report = _validate_attempt_ledger(
        _load_json(ledger_path),
        job_id=job_id,
        expected_tasks=expected_tasks,
        declared_counts=record,
    )
    runs = _require_list(result["runs"], f"{job_id}.runs")
    run_tasks: dict[str, dict[str, Any]] = {}
    for index, raw_run in enumerate(runs):
        run = _require_mapping(raw_run, f"{job_id}.runs[{index}]")
        if run.get("job_id") != job_id or not isinstance(run.get("run_id"), str):
            raise GateError(f"run lacks normalized execution identity: {job_id}[{index}]")
        prefix = f"{job_id}:"
        if not run["run_id"].startswith(prefix):
            raise GateError(f"run_id does not belong to job: {run['run_id']}")
        task_id = run["run_id"][len(prefix):]
        if task_id in run_tasks:
            raise GateError(f"duplicate run for task {task_id}")
        run_tasks[task_id] = run
    if set(run_tasks) != set(expected_tasks):
        raise GateError(f"retained runs do not exactly cover the task matrix: {job_id}")
    for task_id, run in run_tasks.items():
        if run.get("seed") != ledger_report["final_seeds"][task_id]:
            raise GateError(f"run/attempt seed mismatch: {job_id}/{task_id}")
    reconstruction = _reconstruct_aggregates(result, entry["aggregation"], result_rel)
    return {
        "job_id": job_id,
        "record_data": record,
        "record": record_rel,
        "result": result_rel,
        "attempt_ledger": ledger_rel,
        "supported_evidence_ids": supported_evidence,
        "supported_scientific_claim_ids": supported_claims,
        "coverage": {
            "expected": expected_tasks,
            "completed": completed,
            **{key: ledger_report[key] for key in (
                "task_count", "attempt_count", "failed_attempt_count", "excluded_attempt_count"
            )},
        },
        "aggregate_reconstruction": reconstruction,
    }


def _validate_supplemental_artifacts(
    root: Path,
    value: Any,
    jobs: Sequence[Mapping[str, Any]],
) -> list[dict[str, str]]:
    raw_artifacts = _require_list(value, "release artifacts")
    jobs_by_id = {str(job["job_id"]): job for job in jobs}
    artifacts: list[dict[str, str]] = []
    seen: set[str] = set()
    for index, raw in enumerate(raw_artifacts):
        item = _require_mapping(raw, f"release artifact[{index}]")
        _required(item, ("path", "sha256", "job_id", "role"), f"release artifact[{index}]")
        record = _file_record(root, item, f"release artifact[{index}]")
        if record["path"] in seen:
            raise GateError(f"duplicate supplemental artifact: {record['path']}")
        seen.add(record["path"])
        if not Path(record["path"]).is_relative_to(Path("results/audit")):
            raise GateError(f"supplemental artifact must originate in results/audit: {record['path']}")
        job_id = item["job_id"]
        if not isinstance(job_id, str) or job_id not in jobs_by_id:
            raise GateError(f"supplemental artifact names an unknown release job: {job_id}")
        role = item["role"]
        if not isinstance(role, str) or not role.strip():
            raise GateError(f"supplemental artifact has no role: {record['path']}")
        job_record = _require_mapping(jobs_by_id[job_id]["record_data"], f"job {job_id}")
        declared = job_record.get("additional_artifacts", [])
        if not isinstance(declared, list) or not any(
            isinstance(entry, dict)
            and entry.get("path") == record["path"]
            and entry.get("sha256") == record["sha256"]
            and entry.get("role") == role
            for entry in declared
        ):
            raise GateError(
                f"scientific job record does not bind supplemental artifact: {record['path']}"
            )
        artifacts.append({**record, "job_id": job_id, "role": role})
    return artifacts


def _toml_status(path: Path, section: str | None, field: str) -> str:
    data: Any = _load_toml(path)
    if section is not None:
        data = _require_mapping(data.get(section), f"{path}:{section}")
    return str(data.get(field, "MISSING"))


def _replace_toml_pointer(text: str, key: str, value: str) -> str:
    pattern = re.compile(rf'^(\s*{re.escape(key)}\s*=\s*)"[^"]*"\s*$', re.MULTILINE)
    matches = list(pattern.finditer(text))
    if len(matches) != 1:
        raise GateError(f"expected exactly one TOML pointer {key}")
    return pattern.sub(lambda match: f'{match.group(1)}"{value}"', text, count=1)


def _atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _activate_release(root: Path, release_id: str, supersedes: str | None) -> None:
    current_path = root / "results/CURRENT"
    project_path = root / "PROJECT.toml"
    reproducibility_path = root / "REPRODUCIBILITY.toml"
    originals = {
        current_path: current_path.read_text(encoding="utf-8"),
        project_path: project_path.read_text(encoding="utf-8"),
        reproducibility_path: reproducibility_path.read_text(encoding="utf-8"),
    }
    current = originals[current_path].strip()
    if current != "UNRELEASED" and supersedes != current:
        raise GateError(
            f"activation would replace {current}; plan.supersedes must name that release"
        )
    updated = {
        current_path: f"{release_id}\n",
        project_path: _replace_toml_pointer(originals[project_path], "evidence_release", release_id),
        reproducibility_path: _replace_toml_pointer(
            originals[reproducibility_path], "evidence_release", release_id
        ),
    }
    written: list[Path] = []
    try:
        for path, text in updated.items():
            _atomic_text(path, text)
            written.append(path)
    except Exception:
        for path in reversed(written):
            _atomic_text(path, originals[path])
        raise


def _copy_payload(root: Path, staging: Path, relative_paths: Iterable[str]) -> None:
    for rel in sorted(set(relative_paths)):
        _, source = _safe_file(root, rel, "release payload")
        destination = staging / "payload" / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def _write_checksums(directory: Path) -> None:
    entries = []
    for path in sorted(directory.rglob("*")):
        if path.is_file() and path.name != "checksums.sha256":
            entries.append(f"{_sha256(path)}  {path.relative_to(directory).as_posix()}")
    (directory / "checksums.sha256").write_text("\n".join(entries) + "\n", encoding="utf-8")


def _verify_release_directory(directory: Path) -> None:
    registry = _checksum_registry(directory / "checksums.sha256")
    files = {
        path.relative_to(directory).as_posix(): path
        for path in directory.rglob("*")
        if path.is_file() and path.name != "checksums.sha256"
    }
    if set(files) != set(registry):
        raise GateError("frozen release checksum manifest does not cover exactly every file")
    for rel, path in files.items():
        if _sha256(path) != registry[rel]:
            raise GateError(f"frozen release checksum mismatch after copy: {rel}")


def freeze_evidence_release(
    root: Path,
    plan_path: Path,
    *,
    activate: bool = False,
) -> dict[str, Any]:
    """Validate and atomically materialize one immutable evidence release."""

    root = root.resolve()
    plan_path = plan_path.resolve()
    if not plan_path.is_relative_to(root):
        raise GateError("release plan must be inside the project root")
    _verify_clean_worktree(root)
    plan = _require_mapping(_load_json(plan_path), "release plan")
    _required(
        plan,
        (
            "schema_version", "release_id", "source_commit", "protocol", "configuration",
            "data_manifest", "data_checksums", "dependency_lock",
            "environment_digest_sha256", "evidence_ids", "claim_ids", "jobs",
        ),
        "release plan",
    )
    if plan["schema_version"] != 1:
        raise GateError("unsupported release-plan schema_version")
    release_id = plan["release_id"]
    if not isinstance(release_id, str) or RELEASE_ID.fullmatch(release_id) is None:
        raise GateError("release_id must match LP-REL-[A-Z0-9-]+")
    source_commit = _verify_commit(root, plan["source_commit"], "release source_commit")
    environment_digest = plan["environment_digest_sha256"]
    if not isinstance(environment_digest, str) or HEX64.fullmatch(environment_digest) is None:
        raise GateError("environment_digest_sha256 must be lowercase 64-hex")
    evidence_ids = _unique_strings(plan["evidence_ids"], "release evidence_ids", EVIDENCE_ID)
    claim_ids = _unique_strings(plan["claim_ids"], "release claim_ids", CLAIM_ID)
    file_records = {
        key: _file_record(root, plan[key], f"release {key}")
        for key in ("protocol", "configuration", "data_manifest", "data_checksums", "dependency_lock")
    }
    if _toml_status(root / file_records["protocol"]["path"], None, "status") not in {"FROZEN", "ADMITTED"}:
        raise GateError("protocol status is not FROZEN or ADMITTED")
    if _toml_status(root / file_records["configuration"]["path"], "evidence", "status") not in {
        "FROZEN", "SCIENTIFIC-FROZEN", "ADMITTED"
    }:
        raise GateError("configuration evidence status is not frozen")
    current_datasets = _verify_current_datasets(
        root, file_records["data_manifest"], file_records["data_checksums"]
    )
    jobs_raw = _require_list(plan["jobs"], "release jobs")
    if not jobs_raw:
        raise GateError("release plan contains no scientific jobs")
    jobs = [
        _validate_job(
            root,
            entry,
            source_commit=source_commit,
            file_records=file_records,
            current_datasets=current_datasets,
            environment_digest=environment_digest,
        )
        for entry in jobs_raw
    ]
    job_ids = [job["job_id"] for job in jobs]
    if len(job_ids) != len(set(job_ids)):
        raise GateError("release plan contains duplicate scientific job IDs")
    covered_evidence = {item for job in jobs for item in job["supported_evidence_ids"]}
    covered_claims = {item for job in jobs for item in job["supported_scientific_claim_ids"]}
    if not set(evidence_ids).issubset(covered_evidence):
        raise GateError(f"scientific jobs do not cover evidence IDs: {sorted(set(evidence_ids)-covered_evidence)}")
    if not set(claim_ids).issubset(covered_claims):
        raise GateError(f"scientific jobs do not cover claim IDs: {sorted(set(claim_ids)-covered_claims)}")
    artifacts = _validate_supplemental_artifacts(root, plan.get("artifacts", []), jobs)

    target = root / "results/frozen" / release_id
    if target.exists():
        raise GateError(f"immutable release already exists: {target.relative_to(root)}")
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{release_id}.staging-", dir=target.parent))
    try:
        payload_paths = [record["path"] for record in file_records.values()]
        for job in jobs:
            payload_paths.extend((job["record"], job["result"], job["attempt_ledger"]))
        payload_paths.extend(artifact["path"] for artifact in artifacts)
        plan_rel = plan_path.relative_to(root).as_posix()
        payload_paths.append(plan_rel)
        _copy_payload(root, staging, payload_paths)
        release_manifest: dict[str, Any] = {
            "schema_version": 1,
            "state": "FROZEN",
            "release_id": release_id,
            "supersedes": plan.get("supersedes"),
            "source_commit": source_commit,
            "assembly_commit": _git(root, "rev-parse", "HEAD"),
            "release_plan": f"payload/{plan_rel}",
            "release_plan_sha256": _sha256(plan_path),
            "protocol": file_records["protocol"],
            "configuration": file_records["configuration"],
            "data_manifest": file_records["data_manifest"],
            "data_checksums": file_records["data_checksums"],
            "dependency_lock": file_records["dependency_lock"],
            "environment_digest_sha256": environment_digest,
            "current_datasets": current_datasets,
            "evidence_ids": evidence_ids,
            "claim_ids": claim_ids,
            "jobs": [
                {
                    **{key: job[key] for key in (
                        "job_id", "supported_evidence_ids", "supported_scientific_claim_ids", "coverage"
                    )},
                    "record": f"payload/{job['record']}",
                    "result": f"payload/{job['result']}",
                    "attempt_ledger": f"payload/{job['attempt_ledger']}",
                }
                for job in jobs
            ],
            "artifacts": [
                {**artifact, "path": f"payload/{artifact['path']}"}
                for artifact in artifacts
            ],
            "aggregate_reconstruction": "aggregate-reconstruction.json",
            "checksum_manifest": "checksums.sha256",
        }
        reconstruction = {
            "schema_version": 1,
            "release_id": release_id,
            "jobs": [
                {
                    "job_id": job["job_id"],
                    **job["aggregate_reconstruction"],
                }
                for job in jobs
            ],
        }
        _write_json(staging / "release.json", release_manifest)
        _write_json(staging / "aggregate-reconstruction.json", reconstruction)
        _write_checksums(staging)
        _verify_release_directory(staging)
        os.replace(staging, target)
        for path in target.rglob("*"):
            if path.is_file():
                path.chmod(path.stat().st_mode & ~0o222)
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise
    if activate:
        try:
            _activate_release(root, release_id, plan.get("supersedes"))
        except Exception:
            # The newly-created directory has never been published by a pointer;
            # removing it preserves fail-closed all-or-nothing semantics.
            for path in target.rglob("*"):
                if path.is_file():
                    path.chmod(path.stat().st_mode | 0o200)
            shutil.rmtree(target)
            raise
    return release_manifest


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate and freeze a scientific evidence release.",
        epilog=(
            "PLAN CONTRACT: JSON schema_version=1 with release_id, source_commit, "
            "protocol/configuration/data_manifest/data_checksums/dependency_lock file "
            "records ({path,sha256}), environment_digest_sha256, evidence_ids, "
            "claim_ids, and jobs[]. Each job declares record, result, attempt_ledger, "
            "and aggregation {group_by,ddof,count_field?,absolute_tolerance?,metrics[]}. "
            "Each metric declares run, mean, and optional std field names."
        ),
    )
    parser.add_argument("--plan", required=True, type=Path, help="reviewed release-plan JSON")
    parser.add_argument(
        "--project-root", type=Path, default=ROOT, help=argparse.SUPPRESS
    )
    parser.add_argument(
        "--activate",
        action="store_true",
        help="after freezing, advance results/CURRENT and matching TOML pointers",
    )
    args = parser.parse_args(argv)
    try:
        manifest = freeze_evidence_release(
            args.project_root, args.plan, activate=args.activate
        )
    except GateError as exc:
        print(json.dumps({"status": "BLOCKED", "error": str(exc)}, indent=2))
        return 2
    except Exception as exc:  # fail closed with a distinct tooling-error code
        print(json.dumps({"status": "TOOL_ERROR", "error": f"{type(exc).__name__}: {exc}"}, indent=2))
        return 3
    print(json.dumps({
        "status": "FROZEN",
        "release_id": manifest["release_id"],
        "jobs": [job["job_id"] for job in manifest["jobs"]],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
