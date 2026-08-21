from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from release_fixture import RELEASE_ID, create_release_project, sha256


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT_ROOT / "scripts/freeze_evidence_release.py"
HEX40 = "a" * 40
HEX64 = "b" * 64


def _module():
    spec = importlib.util.spec_from_file_location("freeze_evidence_release_under_test", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _v2_ledger(root: Path) -> tuple[dict, dict]:
    history = root / "evidence/execution/history.json"
    history.parent.mkdir(parents=True, exist_ok=True)
    history.write_text('{"history":"test"}\n', encoding="utf-8")
    task_id = "model:coedit:seed-1"
    attempt = {
        "attempt_id": "slurm:123:0:0",
        "campaign_id": "LP-CAM-TEST",
        "generation": 0,
        "task_id": task_id,
        "attempt_index": 0,
        "scheduler_job_id": "456",
        "scheduler_job_id_raw": "456",
        "array_job_id": "123",
        "array_task_id": "0",
        "restart_count": 0,
        "seed": 1,
        "submitted_at": "2026-08-20T00:00:00Z",
        "started_at": "2026-08-20T00:00:01Z",
        "finished_at": "2026-08-20T00:00:02Z",
        "scheduler_state": "COMPLETED",
        "exit_code": 0,
        "admissibility": "ELIGIBLE",
        "selected_for_aggregate": True,
        "source_commit": HEX40,
        "protocol_sha256": HEX64,
        "configuration_sha256": HEX64,
        "data_manifest_sha256": HEX64,
        "dependency_lock_sha256": HEX64,
        "environment_digest_sha256": HEX64,
        "submission_script_sha256": HEX64,
        "result_path": "results/audit/task.json",
        "result_sha256": HEX64,
    }
    ledger = {
        "schema_version": 2,
        "job_id": "LP-JOB-SCI-TEST-001",
        "campaign_id": "LP-CAM-TEST",
        "source_artifacts": [{
            "path": "evidence/execution/history.json",
            "sha256": sha256(history),
        }],
        "expected_tasks": [task_id],
        "tasks": [{
            "task_id": task_id,
            "terminal_attempt_id": attempt["attempt_id"],
            "selected_attempt_id": attempt["attempt_id"],
        }],
        "attempts": [attempt],
        "audit_attempts": [],
        "aggregate_selection": {
            "policy": "exactly-one",
            "included": [{
                "task_id": task_id,
                "attempt_id": attempt["attempt_id"],
                "scheduler_job_id": attempt["scheduler_job_id"],
                "result_path": attempt["result_path"],
                "result_sha256": attempt["result_sha256"],
            }],
        },
        "accounting": {
            "scientific_expected": 1,
            "scientific_completed": 1,
            "scientific_attempt_total": 1,
            "scientific_failed": 0,
            "scientific_cancelled": 0,
            "scientific_inadmissible": 0,
            "quarantined_attempt_total": 0,
            "quarantined_failed": 0,
            "quarantined_cancelled": 0,
        },
    }
    counts = {
        "attempt_count": 1,
        "failed_attempt_count": 0,
        "excluded_attempt_count": 0,
        "audit_attempt_count": 0,
        "audit_failed_attempt_count": 0,
        "audit_cancelled_attempt_count": 0,
    }
    return ledger, counts


def test_v2_ledger_requires_exact_explicit_selected_attempt(tmp_path: Path) -> None:
    freeze = _module()
    ledger, counts = _v2_ledger(tmp_path)

    report = freeze._validate_attempt_ledger(
        tmp_path,
        ledger,
        job_id=ledger["job_id"],
        expected_tasks=ledger["expected_tasks"],
        declared_counts=counts,
    )

    assert report["task_count"] == 1
    assert report["selected_attempts"][ledger["expected_tasks"][0]]["attempt_id"] == "slurm:123:0:0"


def test_v2_ledger_rejects_tampered_selected_result_checksum(tmp_path: Path) -> None:
    freeze = _module()
    ledger, counts = _v2_ledger(tmp_path)
    ledger["aggregate_selection"]["included"][0]["result_sha256"] = "c" * 64

    with pytest.raises(freeze.GateError, match="aggregate selection differs"):
        freeze._validate_attempt_ledger(
            tmp_path,
            ledger,
            job_id=ledger["job_id"],
            expected_tasks=ledger["expected_tasks"],
            declared_counts=counts,
        )


def test_v2_ledger_rejects_tampered_source_artifact(tmp_path: Path) -> None:
    freeze = _module()
    ledger, counts = _v2_ledger(tmp_path)
    (tmp_path / "evidence/execution/history.json").write_text(
        '{"history":"tampered"}\n', encoding="utf-8"
    )

    with pytest.raises(freeze.GateError, match="checksum mismatch"):
        freeze._validate_attempt_ledger(
            tmp_path,
            ledger,
            job_id=ledger["job_id"],
            expected_tasks=ledger["expected_tasks"],
            declared_counts=counts,
        )


def test_v2_ledger_rejects_false_accounting(tmp_path: Path) -> None:
    freeze = _module()
    ledger, counts = _v2_ledger(tmp_path)
    ledger["accounting"]["scientific_attempt_total"] = 0

    with pytest.raises(freeze.GateError, match="accounting mismatch"):
        freeze._validate_attempt_ledger(
            tmp_path,
            ledger,
            job_id=ledger["job_id"],
            expected_tasks=ledger["expected_tasks"],
            declared_counts=counts,
        )


def test_legacy_ledger_cannot_back_a_frozen_release(tmp_path: Path) -> None:
    freeze = _module()
    ledger, counts = _v2_ledger(tmp_path)
    ledger["schema_version"] = 1

    with pytest.raises(freeze.GateError, match="schema_version=2"):
        freeze._validate_attempt_ledger(
            tmp_path,
            ledger,
            job_id=ledger["job_id"],
            expected_tasks=ledger["expected_tasks"],
            declared_counts=counts,
        )


def test_final_accounting_requires_exact_successful_terminal_rows(tmp_path: Path) -> None:
    freeze = _module()
    accounting = tmp_path / "final.psv"
    accounting.write_text(
        "JobID|JobIDRaw|State|ExitCode|Submit|Start|End|Elapsed\n"
        "123_0|456|FAILED|1:0|s|t|u|v\n"
        "12345|12345|COMPLETED|0:0|s|t|u|v\n",
        encoding="utf-8",
    )
    selected = {
        "model:coedit:seed-1": {
            "scheduler_job_id": "123_0",
            "scheduler_job_id_raw": "456",
        }
    }

    with pytest.raises(freeze.GateError, match="not successful"):
        freeze._validate_final_slurm_accounting(
            accounting,
            scheduler_job_id="12345",
            selected_attempts=selected,
        )

    accounting.write_text(
        "JobID|JobIDRaw|State|ExitCode|Submit|Start|End|Elapsed\n"
        "123_0|456|COMPLETED|0:0|s|t|u|v\n",
        encoding="utf-8",
    )
    with pytest.raises(freeze.GateError, match="coverage mismatch"):
        freeze._validate_final_slurm_accounting(
            accounting,
            scheduler_job_id="12345",
            selected_attempts=selected,
        )


def test_freeze_creates_checksum_closed_non_overwritable_release(tmp_path: Path) -> None:
    freeze = _module()
    root, plan = create_release_project(tmp_path)

    manifest = freeze.freeze_evidence_release(root, plan)

    release = root / f"results/frozen/{RELEASE_ID}"
    assert manifest["state"] == "FROZEN"
    assert manifest["jobs"][0]["coverage"]["task_count"] == 1
    checksums = {}
    for line in (release / "checksums.sha256").read_text().splitlines():
        digest, rel = line.split(maxsplit=1)
        checksums[rel] = digest
    actual = {
        path.relative_to(release).as_posix(): sha256(path)
        for path in release.rglob("*")
        if path.is_file() and path.name != "checksums.sha256"
    }
    assert checksums == actual
    assert (release / "release.json").stat().st_mode & 0o222 == 0
    with pytest.raises(freeze.GateError):
        freeze.freeze_evidence_release(root, plan)


def test_freeze_rejects_incomplete_final_attempt_without_output(tmp_path: Path) -> None:
    freeze = _module()
    root, plan = create_release_project(tmp_path, incomplete_attempt=True)

    with pytest.raises(freeze.GateError, match="no unique explicit selected attempt"):
        freeze.freeze_evidence_release(root, plan)

    assert not (root / f"results/frozen/{RELEASE_ID}").exists()
    assert (root / "results/CURRENT").read_text().strip() == "UNRELEASED"


def test_freeze_recomputes_and_rejects_false_aggregate(tmp_path: Path) -> None:
    freeze = _module()
    root, plan = create_release_project(tmp_path, aggregate_mismatch=True)

    with pytest.raises(freeze.GateError, match="mean reconstruction mismatch"):
        freeze.freeze_evidence_release(root, plan)

    assert not (root / f"results/frozen/{RELEASE_ID}").exists()


def test_cli_blocks_current_repository_without_mutating_pointers() -> None:
    freeze = _module()
    current_before = (PROJECT_ROOT / "results/CURRENT").read_text()
    # A minimal intentionally incomplete plan reaches the clean-tree gate first
    # in this migration worktree; either condition must fail before any output.
    with pytest.raises(freeze.GateError):
        freeze.freeze_evidence_release(PROJECT_ROOT, PROJECT_ROOT / "PROJECT.toml")
    assert (PROJECT_ROOT / "results/CURRENT").read_text() == current_before
