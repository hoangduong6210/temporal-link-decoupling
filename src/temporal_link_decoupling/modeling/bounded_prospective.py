"""Separately registered prospective decoder with bounded state probabilities."""
from __future__ import annotations

import torch
from torch import nn
import torch.nn.functional as F

from .prospective import ProspectiveSRGNN


class BoundedExistenceDecoder(nn.Module):
    """A convex mixture of sigmoid state probabilities, evaluated in log space.

    This avoids an upper hard clamp and remains differentiable even when the
    probability would round to one in floating point. The parameter name differs
    from the legacy decoder, so legacy checkpoints cannot be silently loaded.
    """
    def __init__(self, initial_weights):
        super().__init__()
        weights = initial_weights.detach().clone()
        if weights.ndim != 1 or not bool(((weights > 0) & (weights < 1)).all()):
            raise ValueError("initial state probabilities must lie strictly inside the unit interval")
        self.state_log_odds = nn.Parameter(torch.logit(weights))

    def forward(self, distribution):
        log_state = distribution.clamp_min(torch.finfo(distribution.dtype).tiny).log()
        log_present = torch.logsumexp(log_state + F.logsigmoid(self.state_log_odds), dim=-1)
        log_absent = torch.logsumexp(log_state + F.logsigmoid(-self.state_log_odds), dim=-1)
        return log_present - log_absent


class BoundedProspectiveSRGNN(ProspectiveSRGNN):
    """Same prospective backbone and observation; replace the readout parameterization."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        weights = F.softplus(self.core.existence_decoder.theta.detach())
        # correct_decoupled initializes active-state weights at exactly one.
        # Move that boundary inside the interval for finite trainable log odds.
        self.core.existence_decoder = BoundedExistenceDecoder(weights.clamp(1e-6, 1 - 1e-6))
