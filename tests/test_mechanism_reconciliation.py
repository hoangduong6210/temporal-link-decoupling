import copy
import importlib
from pathlib import Path

import numpy as np
import pytest

from test_mechanism_controls import runner
from test_training_diagnostics import stream
from temporal_link_decoupling.prospective import timestamp_groups
from temporal_link_decoupling.training_diagnostics import restrict_to_validation


def auditor(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "scripts"))
    return importlib.import_module("reconcile_prospective_mechanism")


@pytest.fixture
def cell(monkeypatch, tmp_path):
    module = runner(monkeypatch)
    protocol = module.pilot.tomllib.loads((module.pilot.ROOT / "protocols/prospective_mechanism_v4.toml").read_text())
    protocol["pilot"]["hidden"] = 8
    protocol["diagnostics"]["gradient_group_interval"] = 2
    full, splits = stream()
    data = restrict_to_validation(full, splits)
    result = module.run_cell("detached-noaux", "mixed", 1, data, splits, np.array([4, 5, 6, 7]), protocol, tmp_path, {})
    report = {"seed": 1, "training_policy": "mixed", "protocol": protocol}
    return result, report, data, splits, tmp_path / "attempt.json"


def test_independent_evaluation_rng_matches_all_retained_score_rows(monkeypatch, cell):
    result, report, data, splits, _ = cell
    candidates, cohorts, controls, unseen = auditor(monkeypatch).evaluation_contract(data, splits, {4, 5, 6, 7}, report["protocol"])
    assert unseen == {2} and cohorts["inductive"] == {7}
    for epoch in result["epochs"]:
        for regime, scores in epoch["validation"].items():
            assert [[r[0], r[1], r[4]] for r in scores["score_rows"]] == candidates[regime]
            assert set(controls[regime]) == {r[0] for r in candidates[regime]}


def test_checkpoint_audit_reconstructs_parameters_and_rejects_bytes_or_group_tampering(monkeypatch, cell):
    result, report, data, _, path = cell
    module = auditor(monkeypatch)
    module.audit_checkpoint(result, report, path, data)
    changed = copy.deepcopy(result)
    changed["epochs"][changed["selected_epoch"] - 1]["movement"]["csn"]["weights_sha256"] = "0" * 64
    with pytest.raises(AssertionError, match="identity"):
        module.audit_checkpoint(changed, report, path, data)
    checkpoint = path.parent / "detached-noaux-mixed-seed-1.pt"
    checkpoint.write_bytes(checkpoint.read_bytes() + b"changed")
    with pytest.raises(AssertionError, match="checkpoint byte"):
        module.audit_checkpoint(result, report, path, data)


def test_intervention_audit_rejects_invented_auxiliary_gradient(monkeypatch, cell):
    result, report, data, splits, _ = cell
    module = auditor(monkeypatch)
    groups = list(timestamp_groups(data["timestamps"][splits["train"]]))
    epoch = result["epochs"][0]
    module.audit_intervention(result, epoch, groups, 2)
    changed = copy.deepcopy(epoch)
    changed["training"]["gradient_diagnostics"][0]["groups"]["csn"]["auxiliary_increment_norm"] = 1.
    with pytest.raises(AssertionError):
        module.audit_intervention(result, changed, groups, 2)
