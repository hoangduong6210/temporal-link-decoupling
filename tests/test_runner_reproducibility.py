from __future__ import annotations

import json
import os
from pathlib import Path
import random
from types import SimpleNamespace

import numpy as np
import pytest
import torch

from temporal_link_decoupling.reproducibility import (
    atomic_write_json,
    build_job_metadata,
    capture_environment,
    configure_determinism,
    finish_job_metadata,
    parse_chronological_split,
    resolve_run_config,
    seed_everything,
    state_neutral_optimizer_warmup,
    validate_task_profile,
    verify_locked_environment,
)


ROOT = Path(__file__).resolve().parents[1]


def _decoupled_arguments() -> dict:
    return {
        "p0_fix": "off",
        "lfg": "on",
        "echo": "off",
        "interp": "off",
        "interp_entropy_w": 0.01,
        "design": "correct_decoupled",
        "lambda_edge_trans": 0.5,
        "edge_entropy_w": 0.02,
        "edge_uniform_kl_w": 0.01,
        "causal_batch": True,
        "fsm_arch": "v3",
        "fsm_decode": "hier",
        "decol_hier_v2": True,
        "hier_causal_policy": True,
        "lfg_mode": "soft",
        "compliance_floor": 0.05,
        "causal_confidence": False,
        "cc_C": "band",
        "cc_thr": 0.0,
        "cc_self_consist_w": 0.0,
        "cc_grounded_init": False,
        "detach_scorepath": "on",
        "frozen_probe": False,
        "probe_epochs": None,
    }


def test_tracked_protocol_and_config_resolve_without_hidden_defaults() -> None:
    resolved = resolve_run_config(ROOT)
    assert resolved.protocol_id == "LP-P-DECOUPLING-001"
    assert resolved.protocol_status == "FROZEN"
    assert resolved.datasets == ("coedit", "wikipedia", "mooc")
    assert resolved.seeds == (1, 7, 42)
    assert (resolved.train_ratio, resolved.validation_ratio, resolved.test_ratio) == (
        0.70, 0.15, 0.15,
    )
    assert resolved.epochs == 20
    assert resolved.optimizer == "adam"
    assert resolved.scheduler == "cosine-annealing"
    assert resolved.warmup_policy == "state-neutral-training-pass"
    assert resolved.finite_policy == "fail-task-before-metric-or-retained-optimizer-state"
    assert (
        resolved.node_memory_collision_semantics
        == "batch-snapshot-stable-last-row-commit-v1"
    )
    assert resolved.causal_batch_scope == "deterministic-pair-accumulators-not-full-event-replay"
    assert resolved.requires_disjoint_bipartite_ids is True
    assert resolved.protocol_conformant
    assert not resolved.deviations
    assert len(resolved.protocol_sha256) == 64
    assert len(resolved.config_sha256) == 64


def test_task_subsets_conform_but_training_override_is_recorded() -> None:
    subset = resolve_run_config(ROOT, datasets=["coedit"], seeds=[42])
    assert subset.protocol_conformant
    assert subset.datasets == ("coedit",)
    assert subset.seeds == (42,)

    exploratory = resolve_run_config(ROOT, epochs=1, determinism="warn")
    assert not exploratory.protocol_conformant
    assert set(exploratory.deviations) == {"epochs", "determinism"}


def test_main_task_profiles_validate_exact_arm_flags() -> None:
    protocol = ROOT / "protocols/link_prediction_v1.toml"
    decoupled = _decoupled_arguments()
    result = validate_task_profile(
        protocol, task_id="decoupled", runner="run_model", arguments=decoupled
    )
    assert result["valid"] is True

    coupled = dict(decoupled, detach_scorepath="off")
    assert validate_task_profile(
        protocol, task_id="coupled-end-to-end", runner="run_model", arguments=coupled
    )["valid"] is True

    freeze_then_probe = dict(decoupled, frozen_probe=True, probe_epochs=20)
    assert validate_task_profile(
        protocol,
        task_id="freeze-then-probe",
        runner="run_model",
        arguments=freeze_then_probe,
    )["valid"] is True

    mismatch = validate_task_profile(
        protocol,
        task_id="decoupled",
        runner="run_model",
        arguments=dict(decoupled, detach_scorepath="off"),
    )
    assert mismatch["valid"] is False
    assert mismatch["mismatches"][0]["field"] == "detach_scorepath"


def test_baseline_profile_allows_only_registered_unique_subsets() -> None:
    protocol = ROOT / "protocols/link_prediction_v1.toml"
    valid = validate_task_profile(
        protocol,
        task_id="temporal-baselines",
        runner="run_baselines",
        arguments={"models": "proxy_jodie,proxy_tgat,diagnostic_edgebank_inf"},
    )
    assert valid["valid"] is True
    assert valid["scientific_matrix_eligible"] is False

    duplicate = validate_task_profile(
        protocol,
        task_id="temporal-baselines",
        runner="run_baselines",
        arguments={"models": "proxy_jodie,proxy_jodie"},
    )
    assert duplicate["valid"] is False
    assert "duplicates" in duplicate["errors"][0]

    unknown = validate_task_profile(
        protocol,
        task_id="temporal-baselines",
        runner="run_baselines",
        arguments={"models": "proxy_jodie,unknown"},
    )
    assert unknown["valid"] is False
    assert "outside registry" in unknown["errors"][0]

    missing = validate_task_profile(
        protocol, task_id=None, runner="run_baselines", arguments={"models": "proxy_jodie"}
    )
    assert missing["valid"] is False
    assert missing["errors"] == ["task_id is missing"]


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"datasets": ["unknown"]}, "Datasets outside"),
        ({"seeds": [999]}, "Seeds outside"),
        ({"datasets": ["coedit", "coedit"]}, "duplicates"),
    ],
)
def test_protocol_rejects_unregistered_or_duplicate_tasks(kwargs, message) -> None:
    with pytest.raises(ValueError, match=message):
        resolve_run_config(ROOT, **kwargs)


def test_split_parser_fails_closed() -> None:
    assert parse_chronological_split("chronological-70-15-15") == (0.7, 0.15, 0.15)
    for invalid in ("random-70-15-15", "chronological-70-15", "chronological-70-20-20"):
        with pytest.raises(ValueError):
            parse_chronological_split(invalid)


class _ResettableLinear(torch.nn.Linear):
    def __init__(self) -> None:
        super().__init__(2, 1)
        self.reset_calls = 0

    def reset(self) -> None:
        self.reset_calls += 1


def test_optimizer_warmup_restores_model_optimizer_and_rng() -> None:
    model = _ResettableLinear()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
    before_model = {key: value.detach().clone() for key, value in model.state_dict().items()}
    before_optimizer = optimizer.state_dict()

    seed_everything(73)
    expected_python = random.random()
    expected_numpy = float(np.random.random())
    expected_torch = torch.rand(1)
    seed_everything(73)

    def training_pass() -> None:
        optimizer.zero_grad()
        inputs = torch.randn(4, 2)
        loss = model(inputs).square().mean()
        loss.backward()
        optimizer.step()
        random.random()
        np.random.random()

    report = state_neutral_optimizer_warmup(model, optimizer, training_pass)

    for key, expected in before_model.items():
        assert torch.equal(model.state_dict()[key], expected)
    assert optimizer.state_dict() == before_optimizer
    assert random.random() == expected_python
    assert float(np.random.random()) == expected_numpy
    assert torch.equal(torch.rand(1), expected_torch)
    assert model.reset_calls == 1
    assert report["retained_optimizer_steps"] == 0
    assert report["rng_state_restored"] is True


def test_determinism_policy_does_not_pretend_process_start_variables_apply(
    monkeypatch,
) -> None:
    previous = torch.are_deterministic_algorithms_enabled()
    monkeypatch.delenv("PYTHONHASHSEED", raising=False)
    try:
        with pytest.raises(RuntimeError, match="PYTHONHASHSEED"):
            configure_determinism("strict", python_hash_seed=0)
        report = configure_determinism("warn", python_hash_seed=0)
        assert report["strict_prerequisites_satisfied"] is False
        assert any("PYTHONHASHSEED" in item for item in report["warnings"])
    finally:
        torch.use_deterministic_algorithms(previous)


def test_job_metadata_is_fail_closed_and_contains_resolved_input_hashes(
    monkeypatch,
) -> None:
    monkeypatch.delenv("SLURM_JOB_ID", raising=False)
    monkeypatch.delenv("LP_JOB_ID", raising=False)
    resolved = resolve_run_config(ROOT, datasets=["coedit"], seeds=[1])
    task_validation = validate_task_profile(
        ROOT / resolved.protocol_path,
        task_id=None,
        runner="run_model",
        arguments={},
    )
    job = build_job_metadata(
        ROOT,
        job_id=None,
        runner_path=ROOT / "experiments/run_model.py",
        resolved=resolved,
        arguments={
            "config": ROOT / "configs/default.toml",
            "protocol": ROOT / "protocols/link_prediction_v1.toml",
            "out": ROOT / "results/audit/test.json",
            "dump_dir": None,
        },
        expected_tasks=["p0-off:coedit:seed-1"],
        determinism_state={
            "mode": "strict",
            "strict_prerequisites_satisfied": True,
            "warnings": [],
        },
        task_profile_validation=task_validation,
        device=torch.device("cpu"),
        started_at="2026-08-20T00:00:00Z",
    )
    assert job["job_id"] == "UNREGISTERED"
    assert job["scientific_evidence_eligible"] is False
    assert job["inputs"]["protocol"]["sha256"] == resolved.protocol_sha256
    assert job["inputs"]["configuration"]["sha256"] == resolved.config_sha256
    assert job["inputs"]["datasets"][0]["id"].startswith("LP-D-COEDIT-")
    assert job["task_profile_validation"]["valid"] is False
    assert "task profile is missing or does not match resolved arguments" in (
        job["scientific_evidence_blockers"]
    )
    rendered = json.dumps(job)
    assert str(ROOT) not in rendered


def test_accelerator_record_queries_the_allocated_visible_device(monkeypatch) -> None:
    properties = SimpleNamespace(
        name="Audited GPU",
        major=8,
        minor=0,
        total_memory=1024,
        multi_processor_count=1,
        uuid="GPU-PYTORCH",
    )
    observed: dict[str, object] = {}

    def fake_run(command, **kwargs):
        observed["command"] = command
        return SimpleNamespace(
            returncode=0,
            stdout="GPU-SMI, 00000000:03:00.0, 570.00, Audited GPU\n",
            stderr="",
        )

    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "3,5")
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    monkeypatch.setattr(torch.cuda, "get_device_properties", lambda index: properties)
    monkeypatch.setattr(
        "temporal_link_decoupling.reproducibility.subprocess.run", fake_run
    )

    environment = capture_environment(torch.device("cuda:0"))

    accelerator = environment["accelerator"]
    assert accelerator["record_state"] == "RECORDED"
    assert accelerator["nvidia_smi_selector"] == "3"
    assert "--id=3" in observed["command"]
    assert accelerator["nvidia_smi"]["uuid"] == "GPU-SMI"


def test_job_finishing_requires_exact_successful_coverage() -> None:
    job = {
        "coverage": {
            "expected": ["a"],
            "completed": ["a"],
            "failed": [],
            "excluded": [],
        },
        "scientific_execution_prerequisites_satisfied": True,
        "scientific_evidence_blockers": [],
    }
    finish_job_metadata(job, [])
    assert job["status"] == "COMPLETED"
    assert job["exit_code"] == 0
    assert job["scientific_evidence_eligible"] is True

    incomplete = {
        "coverage": {
            "expected": ["a", "b"],
            "completed": ["a"],
            "failed": ["b"],
            "excluded": [],
        },
        "scientific_execution_prerequisites_satisfied": True,
        "scientific_evidence_blockers": [],
    }
    finish_job_metadata(incomplete, [{"task_id": "b"}])
    assert incomplete["scientific_evidence_eligible"] is False
    assert "task coverage is incomplete" in incomplete["scientific_evidence_blockers"]


def test_atomic_json_is_standard_json_and_replaces_previous_file(tmp_path) -> None:
    output = tmp_path / "job.json"
    atomic_write_json(output, {"value": float("nan"), "generation": 1})
    assert json.loads(output.read_text()) == {"generation": 1, "value": None}
    atomic_write_json(output, {"value": 2})
    assert json.loads(output.read_text()) == {"value": 2}
    assert not list(tmp_path.glob("tmp*"))


def test_scientific_dependency_lock_is_hash_pinned_and_environment_is_audited() -> None:
    resolved = resolve_run_config(ROOT)
    policy = (ROOT / "configs/dependency-lock-policy.toml").read_text()
    constraints = (ROOT / "configs/dependencies.lock").read_text()
    lock = ROOT / resolved.dependency_lock_path
    report = verify_locked_environment(
        lock, ROOT / "configs/dependency-lock-policy.toml"
    )
    assert 'status = "SCIENTIFIC-FROZEN"' in policy
    assert resolved.dependency_lock_sha256 == report["lock_sha256"]
    assert report["declared_package_count"] == 39
    assert len(report["environment_digest_sha256"]) == 64
    assert report["matches"] == (
        not report["package_mismatches"] and not report["runtime_mismatches"]
    )
    assert "not a transitive, hash-locked scientific environment" in constraints
