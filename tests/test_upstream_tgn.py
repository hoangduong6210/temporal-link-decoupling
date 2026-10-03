import copy
import os
import importlib
from pathlib import Path

import numpy as np
import pytest
import torch

from temporal_link_decoupling.modeling.upstream_tgn import UpstreamTGN


@pytest.fixture
def data():
    if not os.environ.get("LP_TGN_SOURCE"):
        pytest.skip("external TGN integration requires the registered checkout")
    return {"sources": np.array([0, 1, 0, 2]), "destinations": np.array([4, 5, 5, 4]),
            "timestamps": np.array([1., 1., 2., 3.]),
            "features": np.array([[1., 2.], [3., 4.], [5., 6.], [7., 8.]], dtype=np.float32),
            "feat_dim": 2, "num_nodes": 8}


def observe(net, data, group):
    return net.observe_group(torch.tensor(data["sources"][group]), torch.tensor(data["destinations"][group]),
                             torch.tensor(data["timestamps"][group]), torch.tensor(data["features"][group]))


def test_query_matches_original_tgn_and_does_not_mutate_memory(data):
    torch.manual_seed(7)
    net = UpstreamTGN(data, hidden=8, neighbors=2).eval()
    observe(net, data, slice(0, 2))
    original = copy.deepcopy(net.core)
    before = net.core.memory.backup_memory()
    rng = torch.get_rng_state().clone()
    src, dst, t = torch.tensor([0, 0]), torch.tensor([5, 6]), torch.tensor([2., 2.], dtype=torch.float64)
    scores = net.score_candidates(src, dst, t)
    pos, neg = original.compute_edge_probabilities(np.array([1]), np.array([6]), np.array([7]),
                                                   np.array([2.]), np.array([3]), n_neighbors=2)
    torch.testing.assert_close(scores.sigmoid(), torch.cat([pos.reshape(-1), neg.reshape(-1)]), atol=1e-6, rtol=1e-6)
    after = net.core.memory.backup_memory()
    torch.testing.assert_close(before[0], after[0], rtol=0, atol=0)
    torch.testing.assert_close(before[1], after[1], rtol=0, atol=0)
    assert before[2].keys() == after[2].keys()
    for key, values in before[2].items():
        assert len(values) == len(after[2][key])
        for a, b in zip(values, after[2][key]):
            torch.testing.assert_close(a[0], b[0], rtol=0, atol=0)
            torch.testing.assert_close(a[1], b[1], rtol=0, atol=0)
    assert torch.equal(rng, torch.get_rng_state())
    torch.testing.assert_close(net.score_candidates(src.flip(0), dst.flip(0), t.flip(0)), scores.flip(0))
    torch.testing.assert_close(torch.cat([net.score_candidates(src[i:i+1], dst[i:i+1], t[i:i+1]) for i in range(2)]), scores)


def test_current_and_future_attributes_cannot_affect_query(data):
    changed = copy.deepcopy(data)
    changed["features"][2:] = 999.
    models = []
    for stream in [data, changed]:
        torch.manual_seed(4)
        net = UpstreamTGN(stream, hidden=8, neighbors=2).eval()
        observe(net, stream, slice(0, 2))
        models.append(net)
    query = (torch.tensor([0, 0]), torch.tensor([5, 6]), torch.tensor([2., 2.], dtype=torch.float64))
    torch.testing.assert_close(models[0].score_candidates(*query), models[1].score_candidates(*query), rtol=0, atol=0)
    with pytest.raises(ValueError, match="chronological"):
        observe(models[0], data, slice(3, 4))


def test_tgn_query_trains_original_attention_memory_and_readout(data):
    torch.manual_seed(9)
    net = UpstreamTGN(data, hidden=8, neighbors=2)
    observe(net, data, slice(0, 2))
    scores = net.score_candidates(torch.tensor([0, 0]), torch.tensor([5, 6]), torch.tensor([2., 2.]))
    torch.nn.functional.binary_cross_entropy_with_logits(scores, torch.tensor([1., 0.])).backward()
    for module in [net.core.memory_updater, net.core.embedding_module, net.core.affinity_score]:
        assert any(p.grad is not None and bool(torch.count_nonzero(p.grad)) for p in module.parameters())
    observe(net, data, slice(2, 3))
    assert net.observed_events == 3
    net.reset()
    assert net.observed_events == 0 and not net.core.memory.messages


def test_training_and_inductive_evaluation_replay_all_events(data, monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "experiments"))
    runner = importlib.import_module("run_prospective_development")
    model = UpstreamTGN(data, hidden=8, neighbors=2)
    optimizer = torch.optim.Adam(model.parameters(), lr=.001)
    settings = {"seed": 1, "evaluation_seed": 1729, "query_batch_size": 1}
    training = runner.train_epoch(model, optimizer, data, slice(0, 3), np.array([4, 5, 6]), settings, 1)
    assert training["observed_events"] == 3 and np.isfinite(training["prediction_loss"])
    evaluation = runner.pilot.evaluate(model, data, slice(3, 4), np.array([4, 5, 6]), [],
                                       settings, ["random", "historical"], {2})
    assert evaluation["random"]["observed_events"] == 4
    assert evaluation["random"]["inductive"]["scored_events"] == 1
    assert evaluation["historical"]["inductive"]["empty_support_events"] == 1
