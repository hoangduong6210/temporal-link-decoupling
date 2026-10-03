from __future__ import annotations

import copy
import importlib.util
from pathlib import Path

import numpy as np
import pytest
import torch

from temporal_link_decoupling.modeling.prospective import IndexedEverAliveStore, ProspectiveSRGNN
from temporal_link_decoupling.modeling.v33.sr_gnn_v3_3 import EverAliveStore
from temporal_link_decoupling.prospective import DestinationSampler, chronological_splits, timestamp_groups


def model(decoupled=False):
    torch.manual_seed(10)
    return ProspectiveSRGNN(8, 2, hidden=16, decoupled=decoupled)


def test_indexed_accumulator_matches_legacy_including_duplicate_and_unregistered_keys():
    original, indexed = EverAliveStore(8, torch.device("cpu")), IndexedEverAliveStore(8, torch.device("cpu"))
    for store in [original, indexed]:
        store.get(torch.tensor([0, 1]), torch.tensor([4, 5]))
        store.update(torch.tensor([0, 0, 1, 2]), torch.tensor([4, 4, 5, 6]), torch.tensor([.2, .8, .5, .9]))
        store.update(torch.tensor([0, 1]), torch.tensor([4, 5]), torch.tensor([.3, .7]))
    assert torch.equal(original.values, indexed.values)
    assert torch.equal(original.registered, indexed.registered)
    assert indexed.peek(torch.tensor([2]), torch.tensor([6])).item() == 0.


def observed(net):
    with torch.no_grad():
        net.observe_group(torch.tensor([0, 1]), torch.tensor([4, 5]),
                          torch.tensor([1., 1.], dtype=torch.float64), torch.tensor([[1., 2.], [3., 4.]]))


def state(net):
    return {"weights": {name: value.clone() for name, value in net.state_dict().items()},
            "nodes": net.core.node_mem.memory.clone(), "times": net.core.node_mem.last_t.clone(),
            "features": net.last_features.clone(), "keys": copy.deepcopy(net.core.edge_mem._key_to_idx),
            "pairs": [value.clone() for value in net.core.edge_mem._state_table],
            "ever": net.core.ever_alive.values.clone(), "registered": net.core.ever_alive.registered.clone(),
            "watermark": net.watermark, "observed": net.observed_events, "rng": torch.get_rng_state().clone()}


def same(left, right):
    if isinstance(left, torch.Tensor):
        assert torch.equal(left, right)
    elif isinstance(left, dict):
        assert left.keys() == right.keys()
        for key in left:
            same(left[key], right[key])
    elif isinstance(left, list):
        assert len(left) == len(right)
        for a, b in zip(left, right):
            same(a, b)
    else:
        assert left == right


@pytest.mark.parametrize("training", [True, False])
def test_query_is_read_only_and_candidate_order_invariant(training):
    net = model()
    observed(net)
    net.train(training)
    src, dst = torch.tensor([0, 0, 1, 0]), torch.tensor([4, 5, 6, 4])
    t = torch.full((4,), 2., dtype=torch.float64)
    before = state(net)
    scores = net.score_candidates(src, dst, t)
    same(before, state(net))
    assert torch.equal(scores[0], scores[3])  # same pair in either label position
    permutation = torch.tensor([2, 3, 0, 1])
    permuted = net.score_candidates(src[permutation], dst[permutation], t[permutation])
    torch.testing.assert_close(permuted, scores[permutation], rtol=1e-6, atol=1e-6)
    same(before, state(net))


def test_only_coupled_prediction_reaches_query_backbone():
    coupled, detached = model(), model(True)
    observed(coupled)
    observed(detached)
    query = (torch.tensor([0, 1]), torch.tensor([5, 4]), torch.tensor([2., 2.]))
    a, b = coupled.score_candidates(*query), detached.score_candidates(*query)
    torch.testing.assert_close(a, b, rtol=0, atol=0)
    a.sum().backward()
    b.sum().backward()
    for prefix in ["csn", "ectg.ctx_encoder", "drgc.msg", "drgc.gru"]:
        ca = [p.grad for name, p in coupled.core.named_parameters() if name.startswith(prefix)]
        de = [p.grad for name, p in detached.core.named_parameters() if name.startswith(prefix)]
        assert any(g is not None and torch.count_nonzero(g) for g in ca), prefix
        assert all(g is None or torch.count_nonzero(g) == 0 for g in de), prefix
    assert any(p.grad is not None and torch.count_nonzero(p.grad)
               for p in detached.core.state_observer.parameters())


def test_auxiliary_gradient_routing_is_identical_between_arms():
    a, b = model(), model(True)
    args = (torch.tensor([0]), torch.tensor([4]), torch.tensor([1.]), torch.tensor([[2., 3.]]))
    torch.manual_seed(30)
    la = a.observe_group(*args, backward_auxiliary=True)
    torch.manual_seed(30)
    lb = b.observe_group(*args, backward_auxiliary=True)
    assert la == lb
    for pa, pb in zip(a.parameters(), b.parameters()):
        if pa.grad is None:
            assert pb.grad is None
        else:
            torch.testing.assert_close(pa.grad, pb.grad, rtol=0, atol=0)
    assert any(p.grad is not None and torch.count_nonzero(p.grad) for p in a.core.ectg.parameters())


def test_query_cannot_accept_current_event_features_and_rejects_observed_time():
    net = model()
    observed(net)
    with pytest.raises(TypeError):
        net.score_candidates(torch.tensor([0]), torch.tensor([4]), torch.tensor([2.]), features=torch.ones(1, 2))
    with pytest.raises(ValueError, match="strictly after"):
        net.score_candidates(torch.tensor([0]), torch.tensor([4]), torch.tensor([1.]))
    with pytest.raises(ValueError, match="single-timestamp"):
        net.observe_group(torch.tensor([0, 1]), torch.tensor([4, 5]), torch.tensor([2., 3.]), torch.ones(2, 2))
    with pytest.raises(ValueError, match="features"):
        net.observe_group(torch.tensor([0]), torch.tensor([4]), torch.tensor([2.]), torch.full((1, 2), float("nan")))


def test_temporal_groups_and_splits_never_cut_a_tie():
    times = np.array([0., 0., 1., 2., 3., 4., 4., 4., 5., 6.])
    assert [(s.start, s.stop) for s in timestamp_groups(times)] == [(0, 2), (2, 3), (3, 4), (4, 5), (5, 8), (8, 9), (9, 10)]
    split = chronological_splits(times)
    assert split["train"].stop == 5
    assert split["validation"].stop == 8
    with pytest.raises(ValueError, match="chronological"):
        list(timestamp_groups(np.array([2., 1.])))
    with pytest.raises(ValueError, match="empty split"):
        chronological_splits(np.zeros(10))


def test_sampler_excludes_all_current_positive_destinations_and_never_wrong_role():
    sampler = DestinationSampler([4, 5, 6], seed=3)
    out = sampler.sample([0, 0], [4, 5], 1., "random")
    assert out.negatives.tolist() == [6, 6]
    assert out.rows.tolist() == [0, 1]
    assert not sampler.partners
    with pytest.raises(ValueError, match="endpoint role"):
        sampler.sample([0], [1], 1., "random")
    with pytest.raises(ValueError, match="disjoint"):
        sampler.sample([4], [5], 1., "random")
    with pytest.raises(ValueError, match="integer"):
        sampler.sample([0.5], [4], 1., "random")


def test_empty_support_is_explicit_without_rejection_retry_or_fallback():
    sampler = DestinationSampler([4, 5])
    out = sampler.sample([0, 0], [4, 5], 1., "random")
    assert not len(out.rows)
    assert out.skipped_rows.tolist() == [0, 1]
    sampler.observe([0, 0], [4, 5], 1.)
    assert sampler.partners[0] == {4, 5}
    with pytest.raises(ValueError, match="later timestamp"):
        sampler.sample([0], [4], 1., "random")


def test_historical_support_is_source_specific_and_novel_does_not_use_future_edges():
    sampler = DestinationSampler([4, 5, 6], training_pairs=[(0, 4)])
    assert not len(sampler.sample([0], [4], 1., "historical").rows)
    sampler.observe([0, 1], [4, 5], 1.)
    out = sampler.sample([0], [6], 2., "historical")
    assert out.negatives.tolist() == [4]  # not 5: that is another source's partner
    out = sampler.sample([0], [6], 2., "novel-pair")
    assert out.negatives.tolist() == [5]


def runner():
    path = Path(__file__).resolve().parents[1] / "experiments/run_prospective_pilot.py"
    spec = importlib.util.spec_from_file_location("prospective_pilot_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_evaluation_replays_all_events_and_filters_only_metric_rows():
    data = {"sources": np.array([0, 1, 0, 2]), "destinations": np.array([4, 5, 5, 4]),
            "timestamps": np.array([1., 2., 3., 3.]), "features": np.ones((4, 2), dtype=np.float32)}
    net = model()
    results = runner().evaluate(net, data, slice(2, 4), np.array([4, 5, 6]), [(0, 4)],
                                {"evaluation_seed": 7, "query_batch_size": 1},
                                ["random", "historical"], {2})
    assert results["random"]["observed_events"] == 4
    assert results["random"]["all"]["scored_events"] == 2
    assert results["random"]["inductive"]["scored_events"] == 1
    assert results["historical"]["inductive"]["scored_events"] == 0
    assert results["historical"]["inductive"]["empty_support_events"] == 1
    assert net.core.node_mem.last_t[0].item() == 3.  # non-inductive test event observed
    assert net.core.node_mem.last_t[2].item() == 3.


def test_chunk_size_does_not_change_evaluation_history_or_candidates():
    data = {"sources": np.array([0, 1, 0, 2]), "destinations": np.array([4, 5, 5, 4]),
            "timestamps": np.array([1., 2., 3., 3.]), "features": np.ones((4, 2), dtype=np.float32)}
    results = []
    for batch in [1, 8]:
        results.append(runner().evaluate(model(), data, slice(2, 4), np.array([4, 5, 6]), [],
                                         {"evaluation_seed": 7, "query_batch_size": batch}, ["random"], {2}))
    left, right = results[0]["random"], results[1]["random"]
    assert left["candidate_sha256"] == right["candidate_sha256"]
    np.testing.assert_allclose(np.asarray(left["score_rows"], float), np.asarray(right["score_rows"], float), atol=1e-6)


def test_training_backpropagates_before_tied_state_mutation():
    data = {"sources": np.array([0, 0, 1, 0]), "destinations": np.array([4, 5, 5, 4]),
            "timestamps": np.array([1., 1., 2., 3.]), "features": np.ones((4, 2), dtype=np.float32)}
    for detached in [False, True]:
        net = model(detached)
        optimizer = torch.optim.Adam(net.parameters(), lr=.001)
        result = runner().train_epoch(net, optimizer, data, slice(0, 4), np.array([4, 5, 6]),
                                      {"seed": 1, "query_batch_size": 1}, 1)
        assert result["observed_events"] == 4
        assert result["scored_events"] == 4
        assert np.isfinite(result["prediction_loss"])


def test_empty_metrics_are_unavailable_not_fabricated():
    assert runner().metrics([], 0)["status"] == "NO_ELIGIBLE_EVENTS"
    assert runner().metrics([], 3)["ap"] is None
