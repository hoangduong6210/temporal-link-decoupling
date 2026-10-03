"""Registered training mixture and observational gradient measurements for P003."""
from __future__ import annotations

import hashlib
import json

import numpy as np
import torch

from .prospective import CandidateBatch, DestinationSampler


def trace_digest(rows):
    return hashlib.sha256(json.dumps(rows, separators=(",", ":")).encode()).hexdigest()


class TrainingMixture:
    """Equal-budget random vs availability-dependent random/historical training.

    Both policies draw from all three independent RNG streams. Absent historical
    support is an explicit random-only stratum, never a historical fallback.
    """
    def __init__(self, catalogue, *, seed, policy):
        if policy not in {"random", "mixed"}:
            raise ValueError("unknown training policy")
        self.policy = policy
        self.random = DestinationSampler(catalogue, seed=seed)
        self.historical = DestinationSampler(catalogue, seed=seed + 1000000)
        self.mixture = np.random.default_rng(seed + 2000000)

    def sample(self, sources, destinations, timestamp, *, offset=0):
        base = self.random.sample(sources, destinations, timestamp, "random")
        historical = self.historical.sample(sources, destinations, timestamp, "historical")
        previous = dict(zip(historical.rows.tolist(), historical.negatives.tolist()))
        coins = self.mixture.random(len(sources))
        rows, negatives = [], []
        for index, random_negative in zip(base.rows.tolist(), base.negatives.tolist()):
            candidate = previous.get(index, -1)
            use_history = self.policy == "mixed" and candidate >= 0 and coins[index] < .5
            chosen = candidate if use_history else random_negative
            rows.append([offset + index, chosen, random_negative, candidate,
                         bool(use_history), float(coins[index])])
            negatives.append(chosen)
        return CandidateBatch(base.rows, np.asarray(negatives, dtype=np.int64), base.skipped_rows), rows

    def observe(self, sources, destinations, timestamp):
        self.random.observe(sources, destinations, timestamp)
        self.historical.observe(sources, destinations, timestamp)


GRADIENT_PREFIXES = {
    "csn": "core.csn.", "context": "core.ectg.ctx_encoder.",
    "drgc": "core.drgc.", "state_observer": "core.state_observer.",
    "transition_predictor": "core.transition_predictor.",
    "decoder": "core.existence_decoder.",
}


def gradient_snapshot(model):
    return {name: None if parameter.grad is None else parameter.grad.detach().clone()
            for name, parameter in model.named_parameters() if parameter.requires_grad}


def gradient_increment(model, prediction):
    """Measure actual accumulated gradients without changing optimizer inputs.

    Auxiliary increments are post-observation minus pre-observation gradients,
    so very small increments may be lost to floating-point cancellation.
    """
    result = {}
    parameters = dict(model.named_parameters())
    for group, prefix in GRADIENT_PREFIXES.items():
        selected = [(name, p) for name, p in parameters.items()
                    if name.startswith(prefix) and p.requires_grad]
        before, increments, connected = [], [], 0
        for name, parameter in selected:
            initial = prediction[name]
            connected += int(initial is not None)
            a = torch.zeros_like(parameter) if initial is None else initial
            b = torch.zeros_like(parameter) if parameter.grad is None else parameter.grad.detach()
            before.append(a.double().reshape(-1))
            increments.append((b.double() - a.double()).reshape(-1))
        if not selected:
            continue
        a, b = torch.cat(before), torch.cat(increments)
        na, nb, dot = float(a.norm()), float(b.norm()), float(a.dot(b))
        result[group] = {"prediction_norm": na, "auxiliary_increment_norm": nb,
                         "dot": dot, "cosine": max(-1., min(1., dot / (na * nb))) if na and nb else None,
                         "prediction_connected_parameters": connected,
                         "parameter_tensors": len(selected)}
    return result


def decoder_snapshot(model, initial=None):
    parameter = model.core.existence_decoder.state_log_odds.detach()
    probability = parameter.sigmoid()
    return {"log_odds": parameter.tolist(), "probabilities": probability.tolist(),
            "sigmoid_slopes": (probability * (1 - probability)).tolist(),
            "log_odds_displacement": (parameter - initial).tolist() if initial is not None else [0.] * len(parameter)}


def selection_score(validation):
    values = [validation[regime]["all"]["ap"] for regime in ["random", "historical", "novel-pair"]]
    if any(value is None or not np.isfinite(value) for value in values):
        raise ValueError("all registered validation regimes require finite AP for checkpoint selection")
    return float(sum(values) / len(values))


def restrict_to_validation(data, splits):
    """Remove every held-out test event before constructing an external model."""
    stop = splits["validation"].stop
    if splits["train"].start != 0 or splits["train"].stop != splits["validation"].start or stop != splits["test"].start:
        raise ValueError("expected contiguous chronological train/validation/test partitions")
    result = dict(data)
    for key in ["sources", "destinations", "timestamps", "features", "labels"]:
        result[key] = data[key][:stop].copy()
    result["num_edges"] = stop
    return result
