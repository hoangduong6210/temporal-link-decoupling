import importlib
from pathlib import Path

import numpy as np
import pytest
import torch

from temporal_link_decoupling.modeling.bounded_prospective import BoundedProspectiveSRGNN
from temporal_link_decoupling.modeling.mechanism_controls import (
    ARMS, BACKBONE, GROUPS, MechanismControl, gradient_increment, gradient_snapshot,
    parameter_movement, parameter_snapshot,
)
from temporal_link_decoupling.training_diagnostics import restrict_to_validation
from test_prospective import same, state
from test_training_diagnostics import stream


def runner(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "experiments"))
    return importlib.import_module("run_prospective_mechanism")


def optimizer(model):
    return torch.optim.Adam((p for p in model.parameters() if p.requires_grad), lr=.001, weight_decay=1e-5)


@pytest.mark.parametrize("policy", ["random", "mixed"])
@pytest.mark.parametrize("detached", [False, True])
def test_auxiliary_reference_training_matches_p003_exactly(monkeypatch, policy, detached):
    new = runner(monkeypatch)
    old = importlib.import_module("run_prospective_diagnostics")
    data, splits = stream()
    data = restrict_to_validation(data, splits)
    results = []
    for model_class, trainer in [(BoundedProspectiveSRGNN, old.train_epoch), (MechanismControl, new.train_epoch)]:
        torch.manual_seed(1)
        np.random.seed(1)
        model = model_class(8, 2, 8, decoupled=detached)
        report, trace = trainer(model, optimizer(model), data, splits["train"], np.array([4, 5, 6, 7]),
                                {"seed": 1, "query_batch_size": 2}, 1, policy, 2)
        results.append((new.pilot.model_digest(model), trace, state(model)))
    same(results[0][2], results[1][2])
    assert results[0][:2] == results[1][:2]


def test_disabling_auxiliary_backward_keeps_observation_and_rng_identical():
    results, gradients = [], []
    for auxiliary in [True, False]:
        torch.manual_seed(3)
        model = MechanismControl(8, 2, 8, auxiliary=auxiliary)
        model.train()
        model.core.set_epoch(1)
        src, dst, times = torch.tensor([0, 1]), torch.tensor([4, 5]), torch.tensor([1., 1.])
        model.score_candidates(src, dst, times).sum().backward()
        before = gradient_snapshot(model)
        model.observe_group(src, dst, times, torch.ones(2, 2), backward_auxiliary=True)
        results.append(state(model))
        gradients.append(gradient_increment(model, before))
    same(results[0], results[1])
    assert any(v["auxiliary_increment_norm"] > 0 for v in gradients[0].values())
    assert all(v["auxiliary_increment_norm"] == 0 for v in gradients[1].values())
    assert set(gradients[0]) == set(GROUPS)
    assert sum(v["parameter_tensors"] for v in gradients[0].values()) == len(list(model.parameters()))
    assert gradients[0]["ectg"]["parameter_tensors"] > len(list(model.core.ectg.ctx_encoder.parameters()))


def test_detached_noaux_matches_explicitly_frozen_noaux_with_weight_decay(monkeypatch):
    module = runner(monkeypatch)
    data, splits = stream()
    data = restrict_to_validation(data, splits)
    outcomes = []
    for frozen in [False, True]:
        torch.manual_seed(3)
        np.random.seed(3)
        model = MechanismControl(8, 2, 8, decoupled=True, auxiliary=False, freeze_backbone=frozen)
        initial = parameter_snapshot(model)
        opt = optimizer(model)
        for epoch in [1, 2]:
            report, _ = module.train_epoch(model, opt, data, splits["train"], np.array([4, 5, 6, 7]),
                                           {"seed": 3, "query_batch_size": 2}, epoch, "mixed", 1)
        movement = parameter_movement(model, initial)
        assert all(movement[g]["max_abs_displacement"] == 0 for g in BACKBONE)
        assert movement["existence_decoder"]["max_abs_displacement"] > 0
        outcomes.append(state(model))
    same(*outcomes)


def test_frozen_aux_keeps_parameter_bytes_but_updates_memory_and_heads(monkeypatch):
    module = runner(monkeypatch)
    data, splits = stream()
    data = restrict_to_validation(data, splits)
    torch.manual_seed(1)
    model = MechanismControl(8, 2, 8, **ARMS["frozen-aux"])
    initial = parameter_snapshot(model)
    before_memory = model.core.node_mem.memory.clone()
    report, _ = module.train_epoch(model, optimizer(model), data, splits["train"], np.array([4, 5, 6, 7]),
                                   {"seed": 1, "query_batch_size": 2}, 1, "mixed", 1)
    movement = parameter_movement(model, initial)
    assert all(movement[g]["max_abs_displacement"] == 0 and movement[g]["trainable_tensors"] == 0 for g in BACKBONE)
    assert movement["state_observer"]["max_abs_displacement"] > 0
    assert model.observed_events == 6 and not torch.equal(before_memory, model.core.node_mem.memory)
    for probe in report["gradient_diagnostics"]:
        assert all(probe["groups"][g]["post_observation_connected_tensors"] == 0 for g in BACKBONE)


def test_complete_control_matrix_preserves_candidates_initialization_and_validation_boundary(monkeypatch, tmp_path):
    module = runner(monkeypatch)
    protocol = module.pilot.tomllib.loads((module.pilot.ROOT / "protocols/prospective_mechanism_v4.toml").read_text())
    module.check_protocol(protocol)
    protocol["pilot"]["hidden"] = 8
    protocol["diagnostics"]["gradient_group_interval"] = 2
    data, splits = stream()
    data = restrict_to_validation(data, splits)
    traces, cells = {}, []
    for policy in protocol["training_policies"]:
        for arm in protocol["arms"]:
            cell = module.run_cell(arm, policy, 1, data, splits, np.array([4, 5, 6, 7]), protocol, tmp_path, traces)
            cells.append(cell)
            assert cell["intervention"] == ARMS[arm] and "test" not in cell
            assert cell["selected_epoch"] == max(cell["epochs"], key=lambda e: e["selection_score"])["epoch"]
            for epoch in cell["epochs"]:
                assert epoch["training"]["observed_events"] == 6
                for result in epoch["validation"].values():
                    assert result["observed_events"] == 9
                    assert all(6 <= row[0] < 9 for row in result["score_rows"])
    assert len({cell["initial_weights_sha256"] for cell in cells}) == 1
    for regime in protocol["negative_regimes"]:
        assert len({e["validation"][regime]["candidate_sha256"] for c in cells for e in c["epochs"]}) == 1
