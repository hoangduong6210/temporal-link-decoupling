import pytest
import torch
import torch.nn.functional as F

from temporal_link_decoupling.modeling.bounded_prospective import BoundedExistenceDecoder, BoundedProspectiveSRGNN
from temporal_link_decoupling.modeling.prospective import ProspectiveSRGNN
from temporal_link_decoupling.modeling.v33.fsm_head import ExistenceDecoder


def test_legacy_upper_clamp_loses_gradients_but_bounded_readout_retains_them():
    old = ExistenceDecoder()
    old.theta.data.fill_(2.)
    dist = torch.softmax(torch.tensor([[1., 2., 3., 4., 5.]]), -1)
    old(dist).sum().backward()
    assert not torch.count_nonzero(old.theta.grad)
    new = BoundedExistenceDecoder(torch.full((5,), .7))
    new.state_log_odds.data.fill_(40.)
    logit = new(dist)
    torch.testing.assert_close(logit, torch.tensor([40.]), atol=1e-5, rtol=0)
    logit.sum().backward()
    assert torch.isfinite(new.state_log_odds.grad).all()
    assert bool((new.state_log_odds.grad > 0).all())


def test_initial_probabilities_match_legacy_and_checkpoint_types_cannot_mix():
    old = ExistenceDecoder()
    new = BoundedExistenceDecoder(F.softplus(old.theta))
    torch.manual_seed(2)
    dist = torch.softmax(torch.randn(12, 5), -1)
    torch.testing.assert_close(new(dist), old(dist), atol=1e-6, rtol=1e-6)
    with pytest.raises(RuntimeError):
        new.load_state_dict(old.state_dict())
    with pytest.raises(ValueError):
        BoundedExistenceDecoder(torch.tensor([1.2, .3]))


def test_bounded_coupled_and_detached_queries_share_values_but_separate_backbone_gradients():
    models = []
    for detached in [False, True]:
        torch.manual_seed(5)
        model = BoundedProspectiveSRGNN(8, 2, 16, decoupled=detached)
        with torch.no_grad():
            model.observe_group(torch.tensor([0]), torch.tensor([4]), torch.tensor([1.]), torch.ones(1, 2))
        models.append(model)
    query = (torch.tensor([0, 1]), torch.tensor([5, 6]), torch.tensor([2., 2.]))
    a, b = [model.score_candidates(*query) for model in models]
    torch.testing.assert_close(a, b, rtol=0, atol=0)
    a.sum().backward()
    b.sum().backward()
    assert any(p.grad is not None and bool(torch.count_nonzero(p.grad)) for p in models[0].core.csn.parameters())
    assert all(p.grad is None or not torch.count_nonzero(p.grad) for p in models[1].core.csn.parameters())
    assert torch.count_nonzero(models[1].core.existence_decoder.state_log_odds.grad)
    # The replacement consumes no random draws and preserves other initialization.
    torch.manual_seed(5)
    legacy = ProspectiveSRGNN(8, 2, 16)
    for name, value in legacy.state_dict().items():
        if name != "core.existence_decoder.theta" and name != "core.csn.feat_ema":
            torch.testing.assert_close(value, models[0].state_dict()[name], rtol=0, atol=0)
