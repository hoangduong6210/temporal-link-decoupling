from __future__ import annotations

import numpy as np
import pytest
import torch

from temporal_link_decoupling import training
from temporal_link_decoupling.metrics import RunningMetrics
from temporal_link_decoupling.modeling.baseline.sr_gnn import (
    NodeMemoryStore as BaselineNodeMemoryStore,
)
from temporal_link_decoupling.modeling.v33.sr_gnn import (
    NodeMemoryStore as V33NodeMemoryStore,
)


@pytest.mark.parametrize("store_type", [BaselineNodeMemoryStore, V33NodeMemoryStore])
def test_node_memory_duplicate_commit_is_stable_last_row_wins(store_type) -> None:
    store = store_type(4, 2, torch.device("cpu"))
    indices = torch.tensor([2, 1, 2, 1], dtype=torch.long)
    values = torch.tensor([[2.0, 2.0], [1.0, 1.0], [20.0, 20.0], [10.0, 10.0]])
    times = torch.tensor([2.0, 1.0, 20.0, 10.0])

    for _ in range(3):
        store.reset()
        store.set(indices, values)
        store.update_time(indices, times)
        assert torch.equal(store.memory[2], values[2])
        assert torch.equal(store.memory[1], values[3])
        assert store.last_t[2].item() == 20.0
        assert store.last_t[1].item() == 10.0


def _split(*, nonfinite_feature: bool = False) -> dict[str, np.ndarray]:
    features = np.ones((10, 1), dtype=np.float32)
    if nonfinite_feature:
        features[4, 0] = np.nan
    return {
        "sources": np.arange(10, dtype=np.int64) % 2,
        "destinations": (np.arange(10, dtype=np.int64) % 2) + 2,
        "timestamps": np.arange(10, dtype=np.float32),
        "features": features,
    }


class _NaNOutputModel(torch.nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.weight = torch.nn.Parameter(torch.tensor(1.0))

    def forward(self, src, dst, t, feat, neg_dst):
        pos = self.weight * torch.ones_like(t)
        neg = self.weight * torch.zeros_like(t)
        return {"pos_score": pos, "neg_score": neg, "loss": pos.sum() * torch.nan}


class _CountingModel(torch.nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.weight = torch.nn.Parameter(torch.tensor(1.0))
        self.calls = 0

    def forward(self, src, dst, t, feat, neg_dst):
        self.calls += 1
        pos = self.weight * torch.ones_like(t)
        neg = self.weight * torch.zeros_like(t)
        return {"pos_score": pos, "neg_score": neg, "loss": (pos - 1).square().mean()}


class _NaNDiagnosticModel(_CountingModel):
    def forward(self, src, dst, t, feat, neg_dst):
        out = super().forward(src, dst, t, feat, neg_dst)
        out["diagnostic"] = torch.tensor(float("nan"))
        return out


def test_nonfinite_model_output_fails_before_optimizer_step(monkeypatch) -> None:
    monkeypatch.setattr(training, "DEVICE", torch.device("cpu"))
    model = _NaNOutputModel()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.1)
    before = model.weight.detach().clone()

    with pytest.raises(training.NonFiniteExecutionError, match="output:loss"):
        training.run_epoch(
            model, _split(), num_nodes=4, batch_size=10,
            optimizer=optimizer, desc="finite-guard-test",
        )

    assert torch.equal(model.weight.detach(), before)
    assert optimizer.state == {}


def test_nonfinite_input_fails_before_model_call(monkeypatch) -> None:
    monkeypatch.setattr(training, "DEVICE", torch.device("cpu"))
    model = _CountingModel()

    with pytest.raises(training.NonFiniteExecutionError, match="input:features"):
        training.run_epoch(
            model, _split(nonfinite_feature=True), num_nodes=4,
            batch_size=10, desc="input-guard-test",
        )

    assert model.calls == 0


def test_nonfinite_auxiliary_output_also_fails(monkeypatch) -> None:
    monkeypatch.setattr(training, "DEVICE", torch.device("cpu"))
    with pytest.raises(training.NonFiniteExecutionError, match="output:diagnostic"):
        training.run_epoch(
            _NaNDiagnosticModel(), _split(), num_nodes=4,
            batch_size=10, desc="diagnostic-guard-test",
        )


def test_running_metrics_rejects_nonfinite_values() -> None:
    metrics = RunningMetrics()
    with pytest.raises(ValueError, match="non-finite"):
        metrics.update(np.array([np.nan]), np.array([0.0]), 0.0)
