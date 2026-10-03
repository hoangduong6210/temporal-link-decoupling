"""Run registered P004 auxiliary/backbone controls, with validation-only scoring."""
from __future__ import annotations

import argparse
import copy
import json
import os
from pathlib import Path
import platform
import random
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone

import numpy as np
import torch
import torch.nn.functional as F

import run_prospective_pilot as pilot
from temporal_link_decoupling.modeling.mechanism_controls import (
    ARMS, BACKBONE, GROUPS, MechanismControl, gradient_increment, gradient_snapshot,
    parameter_movement, parameter_snapshot,
)
from temporal_link_decoupling.training_diagnostics import (
    TrainingMixture, decoder_snapshot, restrict_to_validation, selection_score, trace_digest,
)


def train_epoch(model, optimizer, data, train_slice, catalogue, settings, epoch, policy, interval):
    model.train()
    model.reset()
    model.core.set_epoch(epoch)
    sampler = TrainingMixture(catalogue, seed=settings["seed"] + epoch, policy=policy)
    trace, probes = [], []
    count, skipped, total, auxiliary_sum = 0, 0, 0., 0.
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
        before = gradient_snapshot(model) if ordinal % interval == 0 else None
        auxiliary = pilot.observe(model, data, group, backward=True)
        auxiliary_sum += float(auxiliary) * (group.stop - group.start)
        if before is not None:
            diagnostic = gradient_increment(model, before)
            if not model.auxiliary_enabled:
                assert all(value["auxiliary_increment_norm"] == 0 for value in diagnostic.values())
            probes.append({"group_ordinal": ordinal, "events": [group.start, group.stop], "groups": diagnostic})
        pilot.finite((p.grad for p in model.parameters()), "gradient")
        optimizer.step()
        pilot.finite(model.parameters(), "parameter")
        pilot.finite((v for state in optimizer.state.values() for v in state.values()), "optimizer state")
        sampler.observe(src, dst, timestamp)
        count += size
        skipped += len(candidates.skipped_rows)
    return {"scored_events": count, "empty_support_events": skipped, "observed_events": model.observed_events,
            "prediction_loss": total / count if count else None,
            "auxiliary_forward_value_event_mean": auxiliary_sum / model.observed_events,
            "auxiliary_backward_enabled": model.auxiliary_enabled,
            "candidate_trace_sha256": trace_digest(trace),
            "historical_available_events": sum(row[3] >= 0 for row in trace),
            "historical_selected_events": sum(row[4] for row in trace),
            "gradient_diagnostics": probes}, trace


def run_cell(arm, policy, seed, data, splits, catalogue, protocol, output, traces):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    settings = dict(protocol["pilot"], seed=seed)
    model = MechanismControl(data["num_nodes"], data["feat_dim"], settings["hidden"], **ARMS[arm])
    initial_digest = pilot.model_digest(model)
    initial = parameter_snapshot(model)
    initial_groups = parameter_movement(model, initial)
    initial_odds = model.core.existence_decoder.state_log_odds.detach().clone()
    initial_decoder = decoder_snapshot(model)
    optimizer = torch.optim.Adam((p for p in model.parameters() if p.requires_grad),
                                 lr=settings["learning_rate"], weight_decay=settings["weight_decay"])
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=settings["epochs"])
    training_pairs = list(zip(data["sources"][splits["train"]], data["destinations"][splits["train"]]))
    seen = set(data["sources"][splits["train"]]) | set(data["destinations"][splits["train"]])
    unseen = (set(data["sources"][splits["validation"]]) | set(data["destinations"][splits["validation"]])) - seen
    epochs, best_state, best_score, best_epoch = [], None, -1., None
    started = time.perf_counter()
    for epoch in range(1, settings["epochs"] + 1):
        training, trace = train_epoch(model, optimizer, data, splits["train"], catalogue, settings, epoch,
                                      policy, protocol["diagnostics"]["gradient_group_interval"])
        key = policy + ":" + str(epoch)
        if key in traces:
            assert trace == traces[key]
        else:
            traces[key] = trace
        scheduler.step()
        movement = parameter_movement(model, initial)
        if arm in {"detached-noaux", "frozen-aux"}:
            assert all(movement[g]["weights_sha256"] == initial_groups[g]["weights_sha256"] for g in BACKBONE)
            assert all(movement[g]["max_abs_displacement"] == 0 for g in BACKBONE)
        validation = pilot.evaluate(model, data, splits["validation"], catalogue, training_pairs,
                                    settings, protocol["negative_regimes"], unseen)
        score = selection_score(validation)
        if score > best_score:
            best_score, best_epoch = score, epoch
            best_state = copy.deepcopy(model.state_dict())
        epochs.append({"epoch": epoch, "training": training, "movement": movement,
                       "decoder": decoder_snapshot(model, initial_odds),
                       "validation": validation, "selection_score": score})
        print(arm, policy, seed, "epoch", epoch, "validation complete", flush=True)
    checkpoint = output / (arm + "-" + policy + "-seed-" + str(seed) + ".pt")
    torch.save(best_state, checkpoint)
    return {"arm": arm, "intervention": ARMS[arm], "training_policy": policy, "seed": seed,
            "initial_weights_sha256": initial_digest, "initial_groups": initial_groups,
            "initial_decoder": initial_decoder, "selected_epoch": best_epoch,
            "primary_epoch": settings["epochs"], "checkpoint_sha256": pilot.digest(checkpoint),
            "epochs": epochs, "unseen_validation_nodes": len(unseen),
            "trainable_parameters": sum(p.numel() for p in model.parameters() if p.requires_grad),
            "wall_seconds": time.perf_counter() - started}


def check_protocol(protocol):
    assert protocol["protocol_id"] == "LP-P-PROSPECTIVE-004"
    assert protocol["status"] == "DEVELOPMENT_ONLY" and not protocol["publication_eligible"]
    assert protocol["arms"] == list(ARMS)
    assert protocol["training_policies"] == ["random", "mixed"]
    assert protocol["negative_regimes"] == ["random", "historical", "novel-pair"]
    assert protocol["diagnostics"]["groups"] == list(GROUPS)
    assert protocol["sampling"]["historical_probability_when_available"] == .5
    assert [protocol["sampling"][key] for key in ["random_seed_offset", "historical_seed_offset", "mixture_seed_offset"]] == [0, 1000000, 2000000]
    assert protocol["interventions"]["backbone"] == ["core." + name for name in BACKBONE]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, choices=["wikipedia", "mooc"])
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--policy", required=True, choices=["random", "mixed"])
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    if not os.environ.get("SLURM_JOB_ID", "").isdigit() or "login" in socket.gethostname().lower():
        parser.error("mechanism execution requires Slurm compute allocation")
    if os.environ.get("PYTHONHASHSEED") != "0" or pilot.git("status", "--porcelain"):
        parser.error("requires PYTHONHASHSEED=0 and clean committed source")
    protocol_path = pilot.ROOT / "protocols/prospective_mechanism_v4.toml"
    protocol = pilot.tomllib.loads(protocol_path.read_text())
    check_protocol(protocol)
    if args.seed not in protocol["seeds"]:
        parser.error("unregistered seed")
    settings = protocol["pilot"]
    if settings["device"] != "cpu" or not 0 < settings["torch_threads"] <= int(os.environ["SLURM_CPUS_PER_TASK"]):
        parser.error("unsupported device or insufficient CPU allocation")
    torch.set_num_threads(settings["torch_threads"])
    torch.use_deterministic_algorithms(True)
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=False)
    verifier = pilot.ROOT / "scripts/check_prospective_runtime.py"
    runtime_record = output / "runtime.json"
    subprocess.run([sys.executable, str(verifier), "--expect", str(pilot.ROOT / protocol["runtime"]["attestation"]),
                    "--output", str(runtime_record)], check=True)
    inputs = [Path(__file__), Path(pilot.__file__), protocol_path, verifier,
              pilot.ROOT / "resources/manifest.toml", pilot.ROOT / protocol["runtime"]["lock"],
              pilot.ROOT / protocol["runtime"]["attestation"], *sorted((pilot.ROOT / "src").rglob("*.py"))]
    report = {"schema_version": 1, "status": "STARTED", "publication_eligible": False,
              "test_evaluated": False, "protocol_id": protocol["protocol_id"],
              "source_commit": pilot.git("rev-parse", "HEAD"), "source_clean": True,
              "dataset": args.dataset, "seed": args.seed, "training_policy": args.policy,
              "protocol": protocol, "input_sha256": {p.relative_to(pilot.ROOT).as_posix(): pilot.digest(p) for p in inputs},
              "runtime": json.loads(runtime_record.read_text())["runtime"],
              "runtime_attestation_sha256": pilot.digest(runtime_record),
              "execution": {"torch_threads": torch.get_num_threads(), "deterministic_algorithms": torch.are_deterministic_algorithms_enabled(),
                            "kernel": platform.release(), "cpu": platform.processor()},
              "scheduler": {key: os.environ.get(key) for key in ["SLURM_JOB_ID", "SLURM_ARRAY_JOB_ID",
                            "SLURM_ARRAY_TASK_ID", "SLURM_CPUS_PER_TASK", "SLURM_JOB_NODELIST", "SLURM_JOB_PARTITION"]},
              "started_utc": datetime.now(timezone.utc).isoformat(), "training_traces": {}, "cells": []}
    path = output / "attempt.json"
    pilot.atomic_json(path, report)
    try:
        data = pilot.load_dataset(args.dataset)
        catalogue = np.unique(data["destinations"])
        source_events = data["num_edges"]
        cap = min(settings["max_events"], source_events)
        stop = int(np.searchsorted(data["timestamps"], data["timestamps"][cap - 1], side="right"))
        splits = pilot.chronological_splits(data["timestamps"][:stop], settings["train_ratio"], settings["validation_ratio"])
        data = restrict_to_validation(data, splits)
        report["data"] = {"source_npz_sha256": pilot.digest(pilot.ROOT / "resources/corpora" / (args.dataset + ".npz")),
                          "source_events": source_events, "prefix_events": stop, "model_events": data["num_edges"],
                          "catalogue_size": len(catalogue), "splits": {key: [value.start, value.stop] for key, value in splits.items()}}
        for arm in protocol["arms"]:
            report["cells"].append(run_cell(arm, args.policy, args.seed, data, splits, catalogue, protocol, output, report["training_traces"]))
            pilot.atomic_json(path, report)
        assert len({cell["initial_weights_sha256"] for cell in report["cells"]}) == 1
        for regime in protocol["negative_regimes"]:
            assert len({e["validation"][regime]["candidate_sha256"] for c in report["cells"] for e in c["epochs"]}) == 1
            assert all(e["validation"][regime]["observed_events"] == data["num_edges"] for c in report["cells"] for e in c["epochs"])
        subprocess.run([sys.executable, str(verifier), "--expect", str(runtime_record)], check=True)
        assert pilot.git("rev-parse", "HEAD") == report["source_commit"] and not pilot.git("status", "--porcelain")
        assert all(pilot.digest(pilot.ROOT / name) == value for name, value in report["input_sha256"].items())
        report["status"] = "COMPLETED_VALIDATION_MECHANISM"
    except Exception as error:
        report["status"] = "FAILED"
        report["error"] = {"type": type(error).__name__, "message": str(error)}
        raise
    finally:
        report["finished_utc"] = datetime.now(timezone.utc).isoformat()
        pilot.atomic_json(path, report)


if __name__ == "__main__":
    main()
