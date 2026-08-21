from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any


SCIENTIFIC_JOB_ID = "LP-JOB-SCI-TEST-001"
BUILD_JOB_ID = "LP-JOB-BUILD-TEST-001"
RELEASE_ID = "LP-REL-TEST-001"
CLAIM_ID = "LP-C-TEST-001"
EVIDENCE_ID = "LP-E-TEST-001"
ENVIRONMENT_DIGEST = "a" * 64


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, value: str | bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(value, bytes):
        path.write_bytes(value)
    else:
        path.write_text(value, encoding="utf-8")


def dump_json(path: Path, value: Any) -> None:
    write(path, json.dumps(value, indent=2, sort_keys=True) + "\n")


def git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        text=True,
        capture_output=True,
        check=True,
    )
    return result.stdout.strip()


def commit(root: Path, message: str) -> str:
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", message)
    return git(root, "rev-parse", "HEAD")


def _job_record(
    root: Path,
    *,
    source_commit: str,
    result: Path,
    ledger: Path,
    protocol: Path,
    config: Path,
    manifest: Path,
    data_checksums: Path,
    dependency_lock: Path,
    final_accounting: Path,
    failed_attempt_count: int,
    excluded_attempt_count: int,
    additional_artifacts: list[dict[str, str]],
) -> str:
    artifact_toml = ""
    for artifact in additional_artifacts:
        artifact_toml += (
            "\n[[additional_artifacts]]\n"
            f'path = "{artifact["path"]}"\n'
            f'sha256 = "{artifact["sha256"]}"\n'
            f'role = "{artifact["role"]}"\n'
        )
    return f'''schema_version = 1
job_id = "{SCIENTIFIC_JOB_ID}"
scientific = true
execution_kind = "scheduler"
scheduler_job_id = "12345"
source_commit = "{source_commit}"
source_state = "CLEAN"
command = "python experiments/run_model.py"
exit_code = 0
outcome = "COMPLETED"
protocol_id = "LP-P-TEST-001"
protocol_path = "protocols/test.toml"
protocol_sha256 = "{sha256(protocol)}"
configuration_path = "configs/test.toml"
configuration_sha256 = "{sha256(config)}"
data_manifest = "resources/manifest.toml"
data_manifest_sha256 = "{sha256(manifest)}"
data_checksums = "resources/checksums.sha256"
data_checksums_sha256 = "{sha256(data_checksums)}"
dependency_lock = "configs/scientific.lock"
dependency_lock_sha256 = "{sha256(dependency_lock)}"
environment_digest_sha256 = "{ENVIRONMENT_DIGEST}"
result_pointer = "results/audit/scientific-result.json"
result_sha256 = "{sha256(result)}"
attempt_ledger = "results/audit/scientific-attempts.json"
attempt_ledger_sha256 = "{sha256(ledger)}"
final_accounting = "evidence/execution/raw/final.psv"
final_accounting_sha256 = "{sha256(final_accounting)}"
attempt_count = 1
failed_attempt_count = {failed_attempt_count}
excluded_attempt_count = {excluded_attempt_count}
audit_attempt_count = 0
audit_failed_attempt_count = 0
audit_cancelled_attempt_count = 0
supported_evidence_ids = ["{EVIDENCE_ID}"]
supported_scientific_claim_ids = ["{CLAIM_ID}"]
{artifact_toml}'''


def create_release_project(
    tmp_path: Path,
    *,
    incomplete_attempt: bool = False,
    aggregate_mismatch: bool = False,
    with_figure: bool = False,
) -> tuple[Path, Path]:
    root = tmp_path / "project"
    root.mkdir()
    git(root, "init", "-q")
    git(root, "config", "user.email", "tests@example.invalid")
    git(root, "config", "user.name", "Release Tests")

    write(
        root / "PROJECT.toml",
        '[pointers]\nevidence_release = "UNRELEASED"\npaper_snapshot = "UNRELEASED"\n',
    )
    write(root / "results/CURRENT", "UNRELEASED\n")
    write(root / "paper/CURRENT", "UNRELEASED\n")
    write(
        root / "REPRODUCIBILITY.toml",
        'status = "REPRODUCIBLE"\nevidence_release = "UNRELEASED"\n'
        'paper_snapshot = "UNRELEASED"\n',
    )
    protocol = root / "protocols/test.toml"
    config = root / "configs/test.toml"
    dependency_lock = root / "configs/scientific.lock"
    corpus = root / "resources/corpora/coedit.bin"
    manifest = root / "resources/manifest.toml"
    data_checksums = root / "resources/checksums.sha256"
    write(
        protocol,
        'protocol_id = "LP-P-TEST-001"\nstatus = "FROZEN"\n'
        'datasets = [\n  "coedit",\n]\n',
    )
    write(config, '[evidence]\nstatus = "SCIENTIFIC-FROZEN"\n')
    write(dependency_lock, "package==1.0 --hash=sha256:" + "b" * 64 + "\n")
    write(corpus, b"scientific corpus bytes\n")
    write(
        manifest,
        'manifest_version = 1\nstatus = "FROZEN"\n\n[[dataset]]\n'
        'id = "LP-D-COEDIT-TEST"\npath = "corpora/coedit.bin"\n'
        f'sha256 = "{sha256(corpus)}"\nstate = "CURRENT"\n',
    )
    write(data_checksums, f"{sha256(corpus)}  resources/corpora/coedit.bin\n")
    write(root / "evidence/jobs/checksums.sha256", "")
    source_commit = commit(root, "scientific source")

    task_id = "model:coedit:seed-1"
    parent_result = root / "results/audit/task.json"
    dump_json(parent_result, {"status": "COMPLETED", "task_id": task_id})
    history = root / "evidence/execution/history.json"
    dump_json(history, {"source": "synthetic scheduler history"})
    attempt = {
        "attempt_id": "slurm:123:0:0",
        "campaign_id": "LP-CAM-TEST",
        "generation": 0,
        "task_id": task_id,
        "attempt_index": 0,
        "scheduler_job_id": "123_0",
        "scheduler_job_id_raw": "456",
        "array_job_id": "123",
        "array_task_id": "0",
        "restart_count": 0,
        "seed": 1,
        "submitted_at": "2026-08-20T00:00:00Z",
        "started_at": "2026-08-20T00:00:01Z",
        "finished_at": "2026-08-20T00:01:00Z",
        "scheduler_state": "FAILED" if incomplete_attempt else "COMPLETED",
        "exit_code": 1 if incomplete_attempt else 0,
        "admissibility": "INADMISSIBLE" if incomplete_attempt else "ELIGIBLE",
        "selected_for_aggregate": not incomplete_attempt,
        "source_commit": source_commit,
        "protocol_sha256": sha256(protocol),
        "configuration_sha256": sha256(config),
        "data_manifest_sha256": sha256(manifest),
        "dependency_lock_sha256": sha256(dependency_lock),
        "environment_digest_sha256": ENVIRONMENT_DIGEST,
        "submission_script_sha256": "c" * 64,
        "result_path": parent_result.relative_to(root).as_posix(),
        "result_sha256": sha256(parent_result),
    }
    if incomplete_attempt:
        attempt["reason"] = "SYNTHETIC_FAILURE"
    ledger = root / "results/audit/scientific-attempts.json"
    dump_json(
        ledger,
        {
            "schema_version": 2,
            "job_id": SCIENTIFIC_JOB_ID,
            "campaign_id": "LP-CAM-TEST",
            "source_artifacts": [
                {"path": history.relative_to(root).as_posix(), "sha256": sha256(history)}
            ],
            "expected_tasks": [task_id],
            "tasks": [{
                "task_id": task_id,
                "terminal_attempt_id": attempt["attempt_id"],
                "selected_attempt_id": None if incomplete_attempt else attempt["attempt_id"],
            }],
            "attempts": [attempt],
            "audit_attempts": [],
            "aggregate_selection": {
                "policy": "exactly-one",
                "included": [] if incomplete_attempt else [{
                    "task_id": task_id,
                    "attempt_id": attempt["attempt_id"],
                    "scheduler_job_id": attempt["scheduler_job_id"],
                    "result_path": attempt["result_path"],
                    "result_sha256": attempt["result_sha256"],
                }],
            },
            "accounting": {
                "scientific_expected": 1,
                "scientific_completed": 0 if incomplete_attempt else 1,
                "scientific_attempt_total": 1,
                "scientific_failed": 1 if incomplete_attempt else 0,
                "scientific_cancelled": 0,
                "scientific_inadmissible": 1 if incomplete_attempt else 0,
                "quarantined_attempt_total": 0,
                "quarantined_failed": 0,
                "quarantined_cancelled": 0,
            },
        },
    )
    result = root / "results/audit/scientific-result.json"
    run = {
        "job_id": SCIENTIFIC_JOB_ID,
        "run_id": f"{SCIENTIFIC_JOB_ID}:{task_id}",
        "model": "model",
        "dataset": "coedit",
        "seed": 1,
        "ind_ap": 0.8,
        "selected_attempt_id": attempt["attempt_id"],
        "parent_result_path": attempt["result_path"],
        "parent_result_sha256": attempt["result_sha256"],
    }
    dump_json(
        result,
        {
            "schema_version": 2,
            "job": {
                "job_id": SCIENTIFIC_JOB_ID,
                "execution_kind": "scheduler",
                "scheduler": {"system": "slurm", "job_id": "12345"},
                "status": "COMPLETED",
                "exit_code": 0,
                "source": {"commit": source_commit, "dirty": False, "state": "CLEAN"},
                "resolved_configuration": {
                    "protocol_id": "LP-P-TEST-001",
                    "protocol_conformant": True,
                    "deviations": [],
                    "determinism": "strict",
                },
                "inputs": {
                    "protocol": {"path": "protocols/test.toml", "sha256": sha256(protocol)},
                    "configuration": {"path": "configs/test.toml", "sha256": sha256(config)},
                    "dataset_manifest": {
                        "path": "resources/manifest.toml",
                        "sha256": sha256(manifest),
                    },
                    "scientific_dependency_lock": {
                        "path": "configs/scientific.lock",
                        "sha256": sha256(dependency_lock),
                    },
                    "datasets": [
                        {
                            "id": "LP-D-COEDIT-TEST",
                            "path": "corpora/coedit.bin",
                            "sha256": sha256(corpus),
                            "state": "CURRENT",
                        }
                    ],
                },
                "coverage": {
                    "expected": [task_id],
                    "completed": [task_id],
                    "failed": [],
                    "excluded": [],
                },
                "locked_environment": {
                    "matches": True,
                    "environment_digest_sha256": ENVIRONMENT_DIGEST,
                },
                "scientific_evidence_eligible": True,
                "scientific_evidence_blockers": [],
            },
            "runs": [run],
            "summary": [
                {
                    "model": "model",
                    "dataset": "coedit",
                    "ind_ap_mean": 0.7 if aggregate_mismatch else 0.8,
                    "ind_ap_std": 0.0,
                    "n_seeds": 1,
                }
            ],
            "failures": [],
        },
    )

    additional_artifacts: list[dict[str, str]] = []
    if with_figure:
        figure = root / "results/audit/figure.png"
        write(figure, b"not-a-real-png-but-checksum-locked")
        # The sidecar uses the eventual snapshot target. Its artifact selector
        # points to the retained runner result, not to pixels.
        sidecar = root / "results/audit/figure.png.numbers.jsonl"
        sidecar_record = {
            "file": "figures/figure.png",
            "line": 0,
            "literal": "0.8",
            "occurrence": 1,
            "kind": "empirical",
            "claim_id": CLAIM_ID,
            "evidence_id": EVIDENCE_ID,
            "job_id": SCIENTIFIC_JOB_ID,
            "plot_job_id": SCIENTIFIC_JOB_ID,
            "artifact_path": "payload/results/audit/scientific-result.json",
            "artifact_sha256": sha256(result),
            "artifact_selector": "$.summary[0].ind_ap_mean",
            "figure_sidecar": True,
        }
        write(sidecar, json.dumps(sidecar_record, sort_keys=True) + "\n")
        for path, role in ((figure, "figure"), (sidecar, "figure-numeric-sidecar")):
            additional_artifacts.append(
                {
                    "path": path.relative_to(root).as_posix(),
                    "sha256": sha256(path),
                    "role": role,
                }
            )

    final_accounting = root / "evidence/execution/raw/final.psv"
    write(
        final_accounting,
        "JobID|JobIDRaw|State|ExitCode|Submit|Start|End|Elapsed\n"
        "123_0|456|COMPLETED|0:0|2026-08-20T00:00:00Z|"
        "2026-08-20T00:00:01Z|2026-08-20T00:01:00Z|00:00:59\n"
        "12345|12345|COMPLETED|0:0|2026-08-20T00:01:01Z|"
        "2026-08-20T00:01:02Z|2026-08-20T00:01:03Z|00:00:01\n",
    )

    record = root / f"evidence/jobs/{SCIENTIFIC_JOB_ID}.toml"
    write(
        record,
        _job_record(
            root,
            source_commit=source_commit,
            result=result,
            ledger=ledger,
            protocol=protocol,
            config=config,
            manifest=manifest,
            data_checksums=data_checksums,
            dependency_lock=dependency_lock,
            final_accounting=final_accounting,
            failed_attempt_count=1 if incomplete_attempt else 0,
            excluded_attempt_count=1 if incomplete_attempt else 0,
            additional_artifacts=additional_artifacts,
        ),
    )
    write(
        root / "evidence/jobs/checksums.sha256",
        f"{sha256(record)}  evidence/jobs/{SCIENTIFIC_JOB_ID}.toml\n",
    )
    plan = root / "release-plan.json"
    dump_json(
        plan,
        {
            "schema_version": 1,
            "release_id": RELEASE_ID,
            "source_commit": source_commit,
            "protocol": {"path": "protocols/test.toml", "sha256": sha256(protocol)},
            "configuration": {"path": "configs/test.toml", "sha256": sha256(config)},
            "data_manifest": {
                "path": "resources/manifest.toml",
                "sha256": sha256(manifest),
            },
            "data_checksums": {
                "path": "resources/checksums.sha256",
                "sha256": sha256(data_checksums),
            },
            "dependency_lock": {
                "path": "configs/scientific.lock",
                "sha256": sha256(dependency_lock),
            },
            "environment_digest_sha256": ENVIRONMENT_DIGEST,
            "evidence_ids": [EVIDENCE_ID],
            "claim_ids": [CLAIM_ID],
            "jobs": [
                {
                    "record": f"evidence/jobs/{SCIENTIFIC_JOB_ID}.toml",
                    "result": "results/audit/scientific-result.json",
                    "attempt_ledger": "results/audit/scientific-attempts.json",
                    "final_accounting": {
                        "path": "evidence/execution/raw/final.psv",
                        "sha256": sha256(final_accounting),
                    },
                    "aggregation": {
                        "group_by": ["model", "dataset"],
                        "metrics": [
                            {"run": "ind_ap", "mean": "ind_ap_mean", "std": "ind_ap_std"}
                        ],
                        "ddof": 1,
                        "count_field": "n_seeds",
                        "absolute_tolerance": 1e-12,
                    },
                }
            ],
            "artifacts": [
                {**artifact, "job_id": SCIENTIFIC_JOB_ID}
                for artifact in additional_artifacts
            ],
        },
    )
    commit(root, "execution evidence and release plan")
    return root, plan


def create_snapshot_inputs(
    root: Path,
    *,
    omit_structural_annotation: bool = False,
    include_figure: bool = False,
    empirical_literal: str = "0.8",
) -> Path:
    claims = root / "wiki/claims/Current-Claim-Language.md"
    evidence = root / "wiki/evidence/Evidence-Ledger.md"
    source = root / "paper/candidate/main.md"
    write(
        claims,
        f"# Claims\n\n### {CLAIM_ID}\n\n- **Lifecycle status:** ADMITTED\n"
        "- **Paper eligibility:** true\n",
    )
    write(evidence, f"# Evidence\n\n## {EVIDENCE_ID}\n")
    write(source, f"Result {empirical_literal} in Section 2.\n")
    source_commit = commit(root, "admitted wiki and paper source")

    rendered = root / "paper/candidate/main.pdf"
    write(rendered, b"%PDF-1.4\nsynthetic test export\n")
    release_dir = root / f"results/frozen/{RELEASE_ID}"
    release_checksums = {}
    for line in (release_dir / "checksums.sha256").read_text().splitlines():
        digest, rel = line.split(maxsplit=1)
        release_checksums[rel] = digest
    result_artifact = "payload/results/audit/scientific-result.json"
    annotations = [
        {
            "file": "main.md",
            "line": 1,
            "literal": empirical_literal,
            "occurrence": 1,
            "kind": "empirical",
            "claim_id": CLAIM_ID,
            "evidence_id": EVIDENCE_ID,
            "job_id": SCIENTIFIC_JOB_ID,
            "artifact_path": result_artifact,
            "artifact_sha256": release_checksums[result_artifact],
            "artifact_selector": "$.summary[0].ind_ap_mean",
        }
    ]
    if not omit_structural_annotation:
        annotations.append(
            {
                "file": "main.md",
                "line": 1,
                "literal": "2",
                "occurrence": 1,
                "kind": "structural",
                "exemption": "section-label",
            }
        )
    annotations_path = root / "paper/candidate/numeric-annotations.jsonl"
    write(
        annotations_path,
        "".join(json.dumps(item, sort_keys=True) + "\n" for item in annotations),
    )
    build_record = root / f"evidence/jobs/{BUILD_JOB_ID}.toml"
    write(
        build_record,
        f'''schema_version = 1
job_id = "{BUILD_JOB_ID}"
scientific = false
execution_kind = "local-build"
source_commit = "{source_commit}"
source_state = "CLEAN"
command = "paper-build --locked"
exit_code = 0
outcome = "COMPLETED"
result_pointer = "paper/candidate/main.pdf"
result_sha256 = "{sha256(rendered)}"
''',
    )
    scientific_record = root / f"evidence/jobs/{SCIENTIFIC_JOB_ID}.toml"
    write(
        root / "evidence/jobs/checksums.sha256",
        f"{sha256(scientific_record)}  evidence/jobs/{SCIENTIFIC_JOB_ID}.toml\n"
        f"{sha256(build_record)}  evidence/jobs/{BUILD_JOB_ID}.toml\n",
    )
    figures = []
    if include_figure:
        figures.append(
            {
                "path": f"results/frozen/{RELEASE_ID}/payload/results/audit/figure.png",
                "target": "figures/figure.png",
                "numbers": (
                    f"results/frozen/{RELEASE_ID}/payload/results/audit/"
                    "figure.png.numbers.jsonl"
                ),
            }
        )
    plan = root / "snapshot-plan.json"
    dump_json(
        plan,
        {
            "schema_version": 1,
            "snapshot_id": "LP-SNAP-TEST-001",
            "venue": "TestConf",
            "submission_state": "candidate",
            "source_commit": source_commit,
            "wiki_commit": source_commit,
            "evidence_release": RELEASE_ID,
            "paper_build_job": BUILD_JOB_ID,
            "source_files": [{"path": "paper/candidate/main.md", "target": "main.md"}],
            "rendered_files": [{"path": "paper/candidate/main.pdf", "target": "main.pdf"}],
            "figure_files": figures,
            "numeric_annotations": "paper/candidate/numeric-annotations.jsonl",
        },
    )
    commit(root, "paper build evidence and snapshot plan")
    return plan
