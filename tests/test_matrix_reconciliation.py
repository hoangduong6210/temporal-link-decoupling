from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/reconcile_scientific_matrix.py"


def _module():
    spec = importlib.util.spec_from_file_location("matrix_reconciliation", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_protocol_matrix_is_exact_and_unique() -> None:
    module = _module()
    protocol = module._load_toml(ROOT / "protocols/link_prediction_v1.toml")
    matrix = module.expected_matrix(protocol)

    assert len(matrix) == 27
    assert len(set(matrix)) == len(matrix)
    assert {item["task_profile"] for item in matrix.values()} == {
        "coupled-end-to-end",
        "decoupled",
        "freeze-then-probe",
    }
    assert {item["seed"] for item in matrix.values()} == {1, 7, 42}
    assert {item["dataset"] for item in matrix.values()} == {
        "coedit", "wikipedia", "mooc"
    }


def test_scheduler_history_expands_every_main_attempt_without_state_laundering() -> None:
    module = _module()
    protocol = module._load_toml(ROOT / "protocols/link_prediction_v1.toml")
    matrix = module.expected_matrix(protocol)
    attempts, audit_attempts = module._external_attempts(
        ROOT,
        ROOT / "evidence/execution/LP-SCHEDULER-HISTORY-20260820.json",
        protocol,
        matrix,
    )

    assert len(attempts) == 81
    assert {item["task_id"] for item in attempts} == set(matrix)
    assert {item["scheduler_state"] for item in attempts} == {
        "FAILED", "COMPLETED", "CANCELLED"
    }
    assert {item["admissibility"] for item in attempts} == {"INADMISSIBLE"}
    assert not any(item["selected_for_aggregate"] for item in attempts)
    assert {item["source_commit"] for item in attempts} == {
        "61d3839ad9c5b896f8f20634d9d9a08da5bf957a",
        "3da5159246c2f94cf9cc2bd5a969e1d68dfaa9a1",
        "0ca0fd59e36bcadd8246d8c03ee9b0ecd7af7148",
    }
    assert all(item["array_job_id"] in {
        "6907586", "6907587", "6907588", "6907662", "6907663", "6907664",
        "6915240", "6915241", "6915242"
    } for item in attempts)
    assert len({item["attempt_id"] for item in attempts}) == 81
    assert sum(item["scheduler_state"] == "FAILED" for item in attempts) == 30
    assert sum(item["scheduler_state"] == "COMPLETED" for item in attempts) == 27
    assert sum(item["scheduler_state"] == "CANCELLED" for item in attempts) == 24

    assert len(audit_attempts) == 165
    assert sum(item["scheduler_state"] == "COMPLETED" for item in audit_attempts) == 80
    assert sum(item["scheduler_state"] == "FAILED" for item in audit_attempts) == 38
    assert sum(item["scheduler_state"] == "CANCELLED" for item in audit_attempts) == 47
    assert all(item["admissibility"] == "INADMISSIBLE" for item in audit_attempts)
    assert not any(item["selected_for_aggregate"] for item in audit_attempts)


def test_raw_sacct_capture_has_unique_complete_array_tuples() -> None:
    module = _module()
    rows = module._sacct_rows(
        ROOT / "evidence/execution/raw/LP-SACCT-20260820.psv"
    )

    assert len(rows) == 218
    assert rows[("6907589", 35)]["scheduler_state"] == "FAILED"
    assert rows[("6907589", 36)]["scheduler_state"] == "CANCELLED"
    assert rows[("6907665", 43)]["scheduler_state"] == "FAILED"
    assert rows[("6907665", 44)]["scheduler_state"] == "COMPLETED"
    assert rows[("6907590", None)]["scheduler_state"] == "CANCELLED"
    assert rows[("6907666", None)]["scheduler_state"] == "FAILED"

    a002_rows = module._sacct_rows(
        ROOT / "evidence/execution/raw/LP-SACCT-20260821-A002.psv"
    )
    assert len(a002_rows) == 28
    assert a002_rows[("6915240", 2)]["scheduler_state"] == "FAILED"
    assert a002_rows[("6915240", 3)]["scheduler_state"] == "CANCELLED"
    assert a002_rows[("6915242", 8)]["scheduler_state"] == "CANCELLED"
    assert a002_rows[("6915243", None)]["scheduler_state"] == "CANCELLED"


def test_reconciled_summary_uses_sample_standard_deviation() -> None:
    module = _module()
    rows = []
    for seed, value in ((1, 0.1), (7, 0.2), (42, 0.3)):
        rows.append({
            "task_profile": "decoupled",
            "model": "srgnn-v3-3",
            "dataset": "coedit",
            "seed": seed,
            "trans_ap": value,
            "trans_auc": value,
            "ind_ap": value,
            "ind_auc": value,
        })

    summary = module._summary(rows)

    assert len(summary) == 1
    assert summary[0]["n_seeds"] == 3
    assert summary[0]["seeds"] == [1, 7, 42]
    assert summary[0]["ind_ap_mean"] == pytest.approx(0.2)
    assert summary[0]["ind_ap_std"] == pytest.approx(0.1)


def test_reconciled_summary_rejects_duplicate_seed() -> None:
    module = _module()
    row = {
        "task_profile": "decoupled",
        "model": "srgnn-v3-3",
        "dataset": "coedit",
        "seed": 1,
        "trans_ap": 0.1,
        "trans_auc": 0.1,
        "ind_ap": 0.1,
        "ind_auc": 0.1,
    }
    with pytest.raises(module.MatrixError, match="duplicate seed"):
        module._summary([row, dict(row)])
