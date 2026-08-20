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

    assert len(matrix) == 108
    assert len(set(matrix)) == len(matrix)
    assert {item["task_profile"] for item in matrix.values()} == {
        "coupled-end-to-end",
        "decoupled",
        "freeze-then-probe",
        "temporal-baselines",
    }
    assert {item["seed"] for item in matrix.values()} == {1, 7, 42}
    assert {item["dataset"] for item in matrix.values()} == {
        "coedit", "wikipedia", "mooc"
    }


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
