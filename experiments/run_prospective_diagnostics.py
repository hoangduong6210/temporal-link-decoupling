"""Run one dataset/seed of registered validation-only sampling diagnostics on Slurm."""
from __future__ import annotations

import argparse
import copy
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import random
import socket
import time
from datetime import datetime, timezone

import numpy as np
import torch
import torch.nn.functional as F

import run_prospective_pilot as pilot
from temporal_link_decoupling.modeling.bounded_prospective import BoundedProspectiveSRGNN
from temporal_link_decoupling.modeling.upstream_tgn import UpstreamTGN, checked_upstream
from temporal_link_decoupling.training_diagnostics import (
    TrainingMixture, decoder_snapshot, gradient_increment, gradient_snapshot,
    restrict_to_validation, selection_score, trace_digest,
)


def train_epoch(model, optimizer, data, train_slice, catalogue, settings, epoch, policy, interval):
    model.train()
    model.reset()
    is_tgn = isinstance(model, UpstreamTGN)
    if not is_tgn:
        model.core.set_epoch(epoch)
    sampler = TrainingMixture(catalogue, seed=settings["seed"] + epoch, policy=policy)
    trace, diagnostics = [], []
    count, skipped, total, auxiliary_sum = 0, 0, 0., 0.
    decoder_grad_squares, decoder_grad_steps = None, 0
    for ordinal, group in enumerate(pilot.timestamp_groups(data["timestamps"][train_slice])):
        src, dst = data["sources"][group], data["destinations"][group]
        timestamp = float(data["timestamps"][group.start])
        candidates, rows = sampler.sample(src, dst, timestamp, offset=group.start)
        trace.extend(rows)
        size = len(candidates.rows)
        optimizer.zero_grad(set_to_none=True)
        for begin in range(0, size, settings["query_batch_size"]):
            chunk = slice(begin, begin + settings["query_batch_size"])
            positive, negative = pilot.pair_scores(model, data, candidates.rows[chunk] + group.start, candidates.negatives[chunk])
            loss = (F.binary_cross_entropy_with_logits(positive, torch.ones_like(positive), reduction="sum") +
                    F.binary_cross_entropy_with_logits(negative, torch.zeros_like(negative), reduction="sum")) / (2 * size)
            pilot.finite([loss], "prediction loss")
            loss.backward()
            total += float(loss.detach()) * size
        measured = not is_tgn and ordinal % interval == 0
        before = gradient_snapshot(model) if measured else None
        auxiliary = pilot.observe(model, data, group, backward=not is_tgn)
        if not is_tgn:
            auxiliary_sum += float(auxiliary) * (group.stop - group.start)
            grad = model.core.existence_decoder.state_log_odds.grad
            squared = torch.zeros_like(model.core.existence_decoder.state_log_odds, dtype=torch.float64) if grad is None else grad.detach().double().square()
            decoder_grad_squares = squared if decoder_grad_squares is None else decoder_grad_squares + squared
            decoder_grad_steps += 1
        if measured:
            diagnostics.append({"group_ordinal": ordinal, "events": [group.start, group.stop],
                                "groups": gradient_increment(model, before)})
        pilot.finite((p.grad for p in model.parameters()), "gradient")
        optimizer.step()
        pilot.finite(model.parameters(), "parameter")
        pilot.finite((v for state in optimizer.state.values() for v in state.values()), "optimizer state")
        sampler.observe(src, dst, timestamp)
        count += size
        skipped += len(candidates.skipped_rows)
    return {"scored_events": count, "empty_support_events": skipped,
            "observed_events": model.observed_events,
            "prediction_loss": total / count if count else None,
            "auxiliary_loss_event_mean": None if is_tgn else auxiliary_sum / model.observed_events,
            "candidate_trace_sha256": trace_digest(trace),
            "historical_available_events": sum(row[3] >= 0 for row in trace),
            "historical_selected_events": sum(row[4] for row in trace),
            "random_only_stratum_events": sum(row[3] < 0 for row in trace),
            "gradient_diagnostics": diagnostics,
            "decoder_gradient_rms": None if is_tgn else (decoder_grad_squares / decoder_grad_steps).sqrt().tolist(),
            "decoder_gradient_steps": decoder_grad_steps}, trace


def run_cell(name, policy, seed, data, splits, catalogue, protocol, output, traces):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    settings = dict(protocol["pilot"], seed=seed)
    model = (UpstreamTGN(data, settings["hidden"], neighbors=protocol["tgn"]["neighbors"])
             if name == "tgn" else BoundedProspectiveSRGNN(data["num_nodes"], data["feat_dim"], settings["hidden"],
                                                        decoupled=name == "bounded-decoupled"))
    initial = pilot.model_digest(model)
    initial_odds = None if name == "tgn" else model.core.existence_decoder.state_log_odds.detach().clone()
    initial_decoder = None if name == "tgn" else decoder_snapshot(model)
    optimizer = torch.optim.Adam(model.parameters(), lr=settings["learning_rate"], weight_decay=settings["weight_decay"])
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=settings["epochs"])
    training_pairs = list(zip(data["sources"][splits["train"]], data["destinations"][splits["train"]]))
    seen = set(data["sources"][splits["train"]]) | set(data["destinations"][splits["train"]])
    unseen = (set(data["sources"][splits["validation"]]) | set(data["destinations"][splits["validation"]])) - seen
    epochs, best_state, best_score, best_epoch = [], None, -1., None
    started = time.perf_counter()
    for epoch in range(1, settings["epochs"] + 1):
        training, trace = train_epoch(model, optimizer, data, splits["train"], catalogue, settings, epoch,
                                      policy, protocol["diagnostics"]["gradient_group_interval"])
        trace_key = policy + ":" + str(epoch)
        if trace_key in traces:
            assert trace == traces[trace_key]
        else:
            traces[trace_key] = trace
        scheduler.step()
        decoder = None if name == "tgn" else decoder_snapshot(model, initial_odds)
        validation = pilot.evaluate(model, data, splits["validation"], catalogue, training_pairs,
                                    settings, protocol["negative_regimes"], unseen)
        score = selection_score(validation)
        if score > best_score:
            best_score, best_epoch = score, epoch
            best_state = copy.deepcopy(model.state_dict())
        epochs.append({"epoch": epoch, "training": training, "decoder": decoder,
                       "validation": validation, "selection_score": score})
        print(name, policy, seed, "epoch", epoch, "validation complete", flush=True)
    checkpoint = output / (name + "-" + policy + "-seed-" + str(seed) + ".pt")
    torch.save(best_state, checkpoint)
    return {"model": name, "training_policy": policy, "seed": seed, "initial_weights_sha256": initial,
            "initial_decoder": initial_decoder, "selected_epoch": best_epoch,
            "primary_epoch": settings["epochs"], "checkpoint_sha256": pilot.digest(checkpoint),
            "epochs": epochs, "unseen_validation_nodes": len(unseen),
            "trainable_parameters": sum(p.numel() for p in model.parameters() if p.requires_grad),
            "wall_seconds": time.perf_counter() - started}


def check_protocol(protocol):
    assert protocol["protocol_id"] == "LP-P-PROSPECTIVE-003"
    assert protocol["status"] == "DEVELOPMENT_ONLY" and not protocol["publication_eligible"]
    assert protocol["models"] == ["bounded-coupled", "bounded-decoupled", "tgn"]
    assert protocol["training_policies"] == ["random", "mixed"]
    assert protocol["negative_regimes"] == ["random", "historical", "novel-pair"]
    assert protocol["bounded_readout"]["initial_probability_margin"] == 1e-6
    assert protocol["sampling"]["historical_probability_when_available"] == .5
    assert [protocol["sampling"][key] for key in ["random_seed_offset", "historical_seed_offset", "mixture_seed_offset"]] == [0, 1000000, 2000000]
    supported = {"layers": 1, "attention_heads": 2, "dropout": 0., "memory": "gru",
                 "messages": "identity", "aggregation": "last", "node_features": "zeros"}
    assert all(protocol["tgn"][key] == value for key, value in supported.items())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, choices=["wikipedia", "mooc"])
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    if not os.environ.get("SLURM_JOB_ID", "").isdigit() or "login" in socket.gethostname().lower():
        parser.error("diagnostic execution requires Slurm compute allocation")
    if os.environ.get("PYTHONHASHSEED") != "0" or pilot.git("status", "--porcelain"):
        parser.error("requires PYTHONHASHSEED=0 and clean committed source")
    protocol_path = pilot.ROOT / "protocols/prospective_diagnostics_v3.toml"
    protocol = pilot.tomllib.loads(protocol_path.read_text())
    check_protocol(protocol)
    if args.seed not in protocol["seeds"]:
        parser.error("seed is not registered")
    settings = protocol["pilot"]
    if settings["device"] != "cpu" or not 0 < settings["torch_threads"] <= int(os.environ["SLURM_CPUS_PER_TASK"]):
        parser.error("unsupported device or insufficient allocated CPU threads")
    torch.set_num_threads(settings["torch_threads"])
    torch.use_deterministic_algorithms(True)
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=False)
    inputs = [Path(__file__), Path(pilot.__file__), protocol_path, pilot.ROOT / "resources/manifest.toml",
              pilot.ROOT / "configs/tgn-upstream.json", *sorted((pilot.ROOT / "src").rglob("*.py"))]
    report = {"schema_version": 1, "status": "STARTED", "publication_eligible": False,
              "test_evaluated": False, "protocol_id": protocol["protocol_id"],
              "source_commit": pilot.git("rev-parse", "HEAD"), "source_clean": True,
              "dataset": args.dataset, "seed": args.seed, "protocol": protocol,
              "input_sha256": {p.relative_to(pilot.ROOT).as_posix(): pilot.digest(p) for p in inputs},
              "upstream": json.loads((pilot.ROOT / "configs/tgn-upstream.json").read_text()),
              "environment": {"python": platform.python_version(), "machine": platform.machine(),
                              "torch_threads": torch.get_num_threads(),
                              "packages": {dist.metadata["Name"]: dist.version for dist in importlib.metadata.distributions()}},
              "scheduler": {key: os.environ.get(key) for key in ["SLURM_JOB_ID", "SLURM_ARRAY_JOB_ID",
                            "SLURM_ARRAY_TASK_ID", "SLURM_CPUS_PER_TASK", "SLURM_JOB_NODELIST", "SLURM_JOB_PARTITION"]},
              "started_utc": datetime.now(timezone.utc).isoformat(), "training_traces": {}, "cells": []}
    path = output / "attempt.json"
    pilot.atomic_json(path, report)
    try:
        checked_upstream()
        data = pilot.load_dataset(args.dataset)
        catalogue = np.unique(data["destinations"])
        source_events = data["num_edges"]
        cap = min(settings["max_events"], source_events)
        stop = int(np.searchsorted(data["timestamps"], data["timestamps"][cap - 1], side="right"))
        splits = pilot.chronological_splits(data["timestamps"][:stop], settings["train_ratio"], settings["validation_ratio"])
        data = restrict_to_validation(data, splits)
        report["data"] = {"source_npz_sha256": pilot.digest(pilot.ROOT / "resources/corpora" / (args.dataset + ".npz")),
                          "source_events": source_events, "prefix_events": stop, "model_events": data["num_edges"],
                          "catalogue_size": len(catalogue),
                          "splits": {key: [value.start, value.stop] for key, value in splits.items()}}
        for policy in protocol["training_policies"]:
            for name in protocol["models"]:
                report["cells"].append(run_cell(name, policy, args.seed, data, splits, catalogue, protocol, output, report["training_traces"]))
                pilot.atomic_json(path, report)
        cells = report["cells"]
        for family in ["bounded", "tgn"]:
            assert len({cell["initial_weights_sha256"] for cell in cells if cell["model"].startswith(family)}) == 1
        for regime in protocol["negative_regimes"]:
            assert len({epoch["validation"][regime]["candidate_sha256"] for cell in cells for epoch in cell["epochs"]}) == 1
            assert all(epoch["validation"][regime]["observed_events"] == data["num_edges"] for cell in cells for epoch in cell["epochs"])
        checked_upstream()
        assert pilot.git("rev-parse", "HEAD") == report["source_commit"] and not pilot.git("status", "--porcelain")
        assert all(pilot.digest(pilot.ROOT / name) == value for name, value in report["input_sha256"].items())
        report["status"] = "COMPLETED_VALIDATION_DIAGNOSTICS"
    except Exception as error:
        report["status"] = "FAILED"
        report["error"] = {"type": type(error).__name__, "message": str(error)}
        raise
    finally:
        report["finished_utc"] = datetime.now(timezone.utc).isoformat()
        pilot.atomic_json(path, report)


if __name__ == "__main__":
    main()
