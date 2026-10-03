import importlib
import os
from pathlib import Path

import numpy as np
import pytest
import torch
from torch import nn

from temporal_link_decoupling.training_diagnostics import (
    TrainingMixture, gradient_increment, gradient_snapshot, restrict_to_validation,
    selection_score, trace_digest,
)


def test_mixture_preserves_base_draws_and_explicit_history_availability():
    samplers = [TrainingMixture([4, 5, 6], seed=7, policy=policy) for policy in ["random", "mixed"]]
    for sampler in samplers:
        first, trace = sampler.sample([0, 0], [4, 5], 1.)
        assert first.negatives.tolist() == [6, 6]
        assert all(row[3] == -1 and row[4] is False for row in trace)
        assert not sampler.historical.partners
        sampler.observe([0, 0], [4, 5], 1.)
    sources, destinations = [0] * 100 + [1], [5] * 100 + [4]
    draws = [s.sample(sources, destinations, 2., offset=2) for s in samplers]
    a, b = [trace for _, trace in draws]
    assert len(a) == len(b) == 101
    assert [[r[0], r[2], r[3], r[5]] for r in a] == [[r[0], r[2], r[3], r[5]] for r in b]
    assert all(r[1] == r[2] and not r[4] for r in a)
    assert all(r[3] == 4 and r[1] != 5 for r in b[:-1])
    assert 0 < sum(r[4] for r in b) < 100
    assert b[-1][3] == -1 and b[-1][1] == b[-1][2] and not b[-1][4]
    assert all(r[4] == (r[3] >= 0 and r[5] < .5) for r in b)
    assert trace_digest(a) != trace_digest(b)


def test_mixture_respects_ties_and_never_invents_empty_support():
    sampler = TrainingMixture([4, 5], seed=1, policy="mixed")
    out, trace = sampler.sample([0, 0], [4, 5], 1.)
    assert out.skipped_rows.tolist() == [0, 1] and not trace
    sampler.observe([0, 0], [4, 5], 1.)
    with pytest.raises(ValueError, match="later timestamp"):
        sampler.sample([0], [5], 1.)
    with pytest.raises(ValueError, match="policy"):
        TrainingMixture([4, 5], seed=1, policy="unknown")


def test_gradient_increment_exposes_opposition_without_changing_gradients():
    model = nn.Module()
    model.core = nn.Module()
    model.core.csn = nn.Linear(2, 1, bias=False)
    weight = model.core.csn.weight
    weight.sum().backward()
    before = gradient_snapshot(model)
    (-2 * weight.sum()).backward()
    actual = weight.grad.clone()
    value = gradient_increment(model, before)["csn"]
    assert value["cosine"] == pytest.approx(-1.)
    assert value["prediction_norm"] == pytest.approx(2 ** .5)
    assert value["auxiliary_increment_norm"] == pytest.approx(2 * 2 ** .5)
    assert torch.equal(weight.grad, actual)
    model.zero_grad(set_to_none=True)
    before = gradient_snapshot(model)
    weight.sum().backward()
    value = gradient_increment(model, before)["csn"]
    assert value["prediction_norm"] == 0 and value["cosine"] is None
    assert value["prediction_connected_parameters"] == 0


def test_secondary_selection_does_not_silently_drop_empty_regimes():
    result = {regime: {"all": {"ap": value}} for regime, value in
              zip(["random", "historical", "novel-pair"], [.9, .3, .6])}
    assert selection_score(result) == pytest.approx(.6)
    result["historical"]["all"]["ap"] = None
    with pytest.raises(ValueError, match="finite AP"):
        selection_score(result)


def stream():
    data = {"sources": np.array([0, 0, 1, 0, 1, 0, 0, 2, 1, 3]),
            "destinations": np.array([4, 5, 4, 6, 5, 4, 5, 6, 6, 7]),
            "timestamps": np.arange(1., 11.), "features": np.ones((10, 2), dtype=np.float32),
            "labels": np.ones(10), "num_edges": 10, "num_nodes": 8, "feat_dim": 2}
    data["features"][-1] = np.nan
    return data, {"train": slice(0, 6), "validation": slice(6, 9), "test": slice(9, 10)}


def test_test_events_are_removed_and_validation_arrays_are_independent():
    data, splits = stream()
    result = restrict_to_validation(data, splits)
    assert result["num_edges"] == 9
    assert np.isfinite(result["features"]).all()
    for key in ["sources", "destinations", "timestamps", "features", "labels"]:
        assert len(result[key]) == 9 and not np.shares_memory(data[key], result[key])
    with pytest.raises(ValueError, match="contiguous"):
        restrict_to_validation(data, dict(splits, validation=slice(7, 9)))


def diagnostic_runner(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "experiments"))
    return importlib.import_module("run_prospective_diagnostics")


def test_observational_diagnostics_leave_actual_training_unchanged(monkeypatch):
    runner = diagnostic_runner(monkeypatch)
    data, splits = stream()
    data = restrict_to_validation(data, splits)
    outcomes = []
    for interval in [1, 1000]:
        torch.manual_seed(1)
        np.random.seed(1)
        model = runner.BoundedProspectiveSRGNN(8, 2, 8)
        optimizer = torch.optim.Adam(model.parameters(), lr=.001)
        report, trace = runner.train_epoch(model, optimizer, data, splits["train"], np.array([4, 5, 6, 7]),
                                          {"seed": 1, "query_batch_size": 2}, 1, "mixed", interval)
        outcomes.append((runner.pilot.model_digest(model), trace, report))
    assert outcomes[0][:2] == outcomes[1][:2]
    assert len(outcomes[0][2]["gradient_diagnostics"]) > len(outcomes[1][2]["gradient_diagnostics"])


def test_complete_mini_matrix_has_paired_initialization_sampling_and_no_test(monkeypatch, tmp_path):
    if not os.environ.get("LP_TGN_SOURCE"):
        pytest.skip("actual TGN checkout is required for the diagnostic matrix integration")
    runner = diagnostic_runner(monkeypatch)
    protocol = runner.pilot.tomllib.loads((runner.pilot.ROOT / "protocols/prospective_diagnostics_v3.toml").read_text())
    runner.check_protocol(protocol)
    protocol["pilot"]["hidden"] = 8
    protocol["tgn"]["neighbors"] = 2
    protocol["diagnostics"]["gradient_group_interval"] = 2
    data, splits = stream()
    data = restrict_to_validation(data, splits)
    traces, cells = {}, []
    for policy in protocol["training_policies"]:
        for name in protocol["models"]:
            cell = runner.run_cell(name, policy, 1, data, splits, np.array([4, 5, 6, 7]), protocol, tmp_path, traces)
            cells.append(cell)
            assert "test" not in cell and cell["primary_epoch"] == 2
            assert cell["unseen_validation_nodes"] == 1
            assert cell["selected_epoch"] == max(cell["epochs"], key=lambda e: e["selection_score"])["epoch"]
            for epoch in cell["epochs"]:
                assert epoch["training"]["observed_events"] == 6
                for result in epoch["validation"].values():
                    assert result["observed_events"] == 9
                    assert all(6 <= row[0] < 9 for row in result["score_rows"])
                if name == "bounded-decoupled":
                    for probe in epoch["training"]["gradient_diagnostics"]:
                        assert all(probe["groups"][group]["prediction_norm"] == 0 for group in ["csn", "context", "drgc"])
    for family in ["bounded", "tgn"]:
        assert len({c["initial_weights_sha256"] for c in cells if c["model"].startswith(family)}) == 1
    for regime in protocol["negative_regimes"]:
        assert len({e["validation"][regime]["candidate_sha256"] for c in cells for e in c["epochs"]}) == 1
