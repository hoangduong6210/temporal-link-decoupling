"""Matched auxiliary and parameter-freezing interventions for prospective P004."""
from __future__ import annotations

import hashlib

import torch

from .bounded_prospective import BoundedProspectiveSRGNN


BACKBONE = ("csn", "ectg", "drgc")
GROUPS = ("csn", "ectg", "drgc", "state_observer", "transition_predictor", "existence_decoder", "other")
ARMS = {
    "coupled-aux": {"decoupled": False, "auxiliary": True, "freeze_backbone": False},
    "detached-aux": {"decoupled": True, "auxiliary": True, "freeze_backbone": False},
    "coupled-noaux": {"decoupled": False, "auxiliary": False, "freeze_backbone": False},
    "detached-noaux": {"decoupled": True, "auxiliary": False, "freeze_backbone": False},
    "frozen-aux": {"decoupled": True, "auxiliary": True, "freeze_backbone": True},
}


class MechanismControl(BoundedProspectiveSRGNN):
    def __init__(self, *args, auxiliary=True, freeze_backbone=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.auxiliary_enabled = auxiliary
        self.backbone_frozen = freeze_backbone
        if freeze_backbone:
            for name in BACKBONE:
                for parameter in getattr(self.core, name).parameters():
                    parameter.requires_grad_(False)

    def observe_group(self, *args, backward_auxiliary=False, **kwargs):
        # The full observation forward, RNG use, EMA and memory writes remain.
        # Skip the auxiliary backward entirely: multiplying its loss by zero
        # would create zero .grad tensors and activate Adam weight decay.
        return super().observe_group(*args, backward_auxiliary=(backward_auxiliary and self.auxiliary_enabled), **kwargs)


def parameter_group(name):
    for group in GROUPS[:-1]:
        if name.startswith("core." + group + "."):
            return group
    return "other"


def parameter_snapshot(model):
    return {name: parameter.detach().clone() for name, parameter in model.named_parameters()}


def parameter_movement(model, initial):
    result = {}
    for group in GROUPS:
        selected = [(name, p) for name, p in model.named_parameters() if parameter_group(name) == group]
        differences = [(p.detach().double() - initial[name].double()).reshape(-1) for name, p in selected]
        values = torch.cat(differences) if differences else torch.zeros(0, dtype=torch.float64)
        digest = hashlib.sha256()
        for name, parameter in selected:
            digest.update(name.encode())
            digest.update(parameter.detach().cpu().contiguous().numpy().tobytes())
        result[group] = {"l2_displacement": float(values.norm()),
                         "max_abs_displacement": float(values.abs().max()) if values.numel() else 0.,
                         "parameter_tensors": len(selected), "trainable_tensors": sum(p.requires_grad for _, p in selected),
                         "parameters": sum(p.numel() for _, p in selected), "weights_sha256": digest.hexdigest()}
    return result


def gradient_snapshot(model):
    return {name: None if p.grad is None else p.grad.detach().clone() for name, p in model.named_parameters()}


def gradient_increment(model, prediction):
    result = {}
    for group in GROUPS:
        selected = [(name, p) for name, p in model.named_parameters() if parameter_group(name) == group]
        before, increments = [], []
        for name, parameter in selected:
            a = torch.zeros_like(parameter) if prediction[name] is None else prediction[name]
            b = torch.zeros_like(parameter) if parameter.grad is None else parameter.grad.detach()
            before.append(a.double().reshape(-1))
            increments.append((b.double() - a.double()).reshape(-1))
        a = torch.cat(before) if before else torch.zeros(0, dtype=torch.float64)
        b = torch.cat(increments) if increments else torch.zeros(0, dtype=torch.float64)
        na, nb, dot = float(a.norm()), float(b.norm()), float(a.dot(b))
        result[group] = {"prediction_norm": na, "auxiliary_increment_norm": nb, "dot": dot,
                         "cosine": max(-1., min(1., dot / (na * nb))) if na and nb else None,
                         "prediction_connected_tensors": sum(prediction[name] is not None for name, _ in selected),
                         "post_observation_connected_tensors": sum(p.grad is not None for _, p in selected),
                         "parameter_tensors": len(selected), "trainable_tensors": sum(p.requires_grad for _, p in selected)}
    return result
