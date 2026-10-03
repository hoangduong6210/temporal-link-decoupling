"""Run the registered prospective development matrix on Slurm, never as evidence admission."""
from __future__ import annotations

import argparse
import copy
import hashlib
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


def train_epoch(model, optimizer, data, train_slice, catalogue, settings, epoch):
    model.train()
    model.reset()
    is_tgn = isinstance(model, UpstreamTGN)
    if not is_tgn:
        model.core.set_epoch(epoch)
    sampler = pilot.DestinationSampler(catalogue, seed=settings["seed"] + epoch)
    candidate_hash = hashlib.sha256()
    count, skipped, total = 0, 0, 0.
    for group in pilot.timestamp_groups(data["timestamps"][train_slice]):
        src, dst = data["sources"][group], data["destinations"][group]
        t = float(data["timestamps"][group.start])
        candidates = sampler.sample(src, dst, t, "random")
        candidate_hash.update(np.column_stack([candidates.rows + group.start, candidates.negatives]).astype("<i8").tobytes())
        size = len(candidates.rows)
        optimizer.zero_grad(set_to_none=True)
        for begin in range(0, size, settings["query_batch_size"]):
            chunk = slice(begin, begin + settings["query_batch_size"])
            pos, neg = pilot.pair_scores(model, data, candidates.rows[chunk] + group.start, candidates.negatives[chunk])
            loss = (F.binary_cross_entropy_with_logits(pos, torch.ones_like(pos), reduction="sum") +
                    F.binary_cross_entropy_with_logits(neg, torch.zeros_like(neg), reduction="sum")) / (2 * size)
            pilot.finite([loss], "prediction loss")
            loss.backward()
            total += float(loss.detach()) * size
        pilot.observe(model, data, group, backward=not is_tgn)
        pilot.finite((p.grad for p in model.parameters()), "gradient")
        optimizer.step()
        pilot.finite(model.parameters(), "parameter")
        pilot.finite((value for state in optimizer.state.values() for value in state.values()), "optimizer state")
        sampler.observe(src, dst, t)
        count += size
        skipped += len(candidates.skipped_rows)
    return {"scored_events": count, "empty_support_events": skipped, "observed_events": model.observed_events,
            "prediction_loss": total / count if count else None, "candidate_sha256": candidate_hash.hexdigest()}


def run_cell(name, seed, data, splits, catalogue, protocol, output):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    settings = dict(protocol["pilot"], seed=seed)
    if name == "tgn":
        model = UpstreamTGN(data, settings["hidden"], neighbors=protocol["tgn"]["neighbors"])
    else:
        cls = BoundedProspectiveSRGNN if name.startswith("bounded") else pilot.ProspectiveSRGNN
        model = cls(data["num_nodes"], data["feat_dim"], settings["hidden"], decoupled=name.endswith("decoupled"))
    initial = pilot.model_digest(model)
    parameters = sum(p.numel() for p in model.parameters() if p.requires_grad)
    optimizer = torch.optim.Adam(model.parameters(), lr=settings["learning_rate"], weight_decay=settings["weight_decay"])
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=settings["epochs"])
    training_pairs = list(zip(data["sources"][splits["train"]], data["destinations"][splits["train"]]))
    seen = set(data["sources"][:splits["test"].start]) | set(data["destinations"][:splits["test"].start])
    unseen = (set(data["sources"][splits["test"]]) | set(data["destinations"][splits["test"]])) - seen
    epochs, best_state, best_ap, best_epoch = [], None, -1., None
    started = time.perf_counter()
    for epoch in range(1, settings["epochs"] + 1):
        training = train_epoch(model, optimizer, data, splits["train"], catalogue, settings, epoch)
        scheduler.step()
        validation = pilot.evaluate(model, data, splits["validation"], catalogue, training_pairs,
                                    settings, ["random"], unseen)["random"]["all"]
        if validation["ap"] is None:
            raise ValueError("validation candidate support is empty")
        if validation["ap"] > best_ap:
            best_ap, best_epoch = validation["ap"], epoch
            best_state = copy.deepcopy(model.state_dict())
        epochs.append({"epoch": epoch, "training": training, "validation": validation})
        print(name, seed, "epoch", epoch, "complete", flush=True)
    model.load_state_dict(best_state)
    checkpoint = output / (name + "-seed-" + str(seed) + ".pt")
    torch.save(best_state, checkpoint)
    results = pilot.evaluate(model, data, splits["test"], catalogue, training_pairs, settings,
                             protocol["negative_regimes"], unseen)
    return {"model": name, "seed": seed, "initial_weights_sha256": initial,
            "trainable_parameters": parameters, "selected_epoch": best_epoch,
            "checkpoint_sha256": pilot.digest(checkpoint), "epochs": epochs,
            "test": results, "unseen_nodes": len(unseen), "wall_seconds": time.perf_counter() - started}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, choices=["wikipedia", "mooc"])
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    if not os.environ.get("SLURM_JOB_ID", "").isdigit() or "login" in socket.gethostname().lower():
        parser.error("development execution requires Slurm compute allocation")
    if os.environ.get("PYTHONHASHSEED") != "0" or pilot.git("status", "--porcelain"):
        parser.error("requires PYTHONHASHSEED=0 and a clean committed source tree")
    protocol_path = pilot.ROOT / "protocols/prospective_development_v2.toml"
    protocol = pilot.tomllib.loads(protocol_path.read_text())
    if protocol["status"] != "DEVELOPMENT_ONLY" or protocol["publication_eligible"]:
        parser.error("runner cannot admit scientific evidence")
    expected_models = ["legacy-coupled", "legacy-decoupled", "bounded-coupled", "bounded-decoupled", "tgn"]
    supported_tgn = {"layers": 1, "attention_heads": 2, "dropout": 0., "memory": "gru",
                     "messages": "identity", "aggregation": "last", "node_features": "zeros"}
    if protocol["models"] != expected_models or any(protocol["tgn"][key] != value for key, value in supported_tgn.items()):
        parser.error("protocol requests an unsupported model/comparator configuration")
    if protocol["bounded_readout"]["initial_probability_margin"] != 1e-6:
        parser.error("bounded initialization margin differs from implemented parameterization")
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
              "protocol_id": protocol["protocol_id"], "source_commit": pilot.git("rev-parse", "HEAD"),
              "source_clean": True, "dataset": args.dataset, "protocol": protocol,
              "input_sha256": {p.relative_to(pilot.ROOT).as_posix(): pilot.digest(p) for p in inputs},
              "upstream": json.loads((pilot.ROOT / "configs/tgn-upstream.json").read_text()),
              "environment": {"python": platform.python_version(), "machine": platform.machine(),
                              "torch_threads": torch.get_num_threads(),
                              "packages": {dist.metadata["Name"]: dist.version for dist in importlib.metadata.distributions()}},
              "scheduler": {key: os.environ.get(key) for key in ["SLURM_JOB_ID", "SLURM_ARRAY_JOB_ID",
                            "SLURM_ARRAY_TASK_ID", "SLURM_CPUS_PER_TASK", "SLURM_JOB_NODELIST", "SLURM_JOB_PARTITION"]},
              "started_utc": datetime.now(timezone.utc).isoformat(), "cells": []}
    path = output / "attempt.json"
    pilot.atomic_json(path, report)
    try:
        checked_upstream()
        data = pilot.load_dataset(args.dataset)
        catalogue = np.unique(data["destinations"])
        source_events = data["num_edges"]
        cap = min(settings["max_events"], source_events)
        stop = int(np.searchsorted(data["timestamps"], data["timestamps"][cap - 1], side="right"))
        for key in ["sources", "destinations", "timestamps", "features", "labels"]:
            data[key] = data[key][:stop]
        data["num_edges"] = stop
        splits = pilot.chronological_splits(data["timestamps"], settings["train_ratio"], settings["validation_ratio"])
        report["data"] = {"source_npz_sha256": pilot.digest(pilot.ROOT / "resources/corpora" / (args.dataset + ".npz")),
                          "source_events": source_events, "prefix_events": stop, "catalogue_size": len(catalogue),
                          "splits": {key: [value.start, value.stop] for key, value in splits.items()}}
        for seed in protocol["seeds"]:
            for name in protocol["models"]:
                report["cells"].append(run_cell(name, seed, data, splits, catalogue, protocol, output))
                pilot.atomic_json(path, report)
        cells = {(cell["model"], cell["seed"]): cell for cell in report["cells"]}
        for seed in protocol["seeds"]:
            for epoch in range(settings["epochs"]):
                assert len({cells[(name, seed)]["epochs"][epoch]["training"]["candidate_sha256"]
                            for name in protocol["models"]}) == 1
            for family in ["legacy", "bounded"]:
                a, b = [cells[(family + "-" + arm, seed)] for arm in ["coupled", "decoupled"]]
                assert a["initial_weights_sha256"] == b["initial_weights_sha256"]
        for regime in protocol["negative_regimes"]:
            assert len({cell["test"][regime]["candidate_sha256"] for cell in report["cells"]}) == 1
            assert all(cell["test"][regime]["observed_events"] == stop for cell in report["cells"])
        checked_upstream()
        assert pilot.git("rev-parse", "HEAD") == report["source_commit"] and not pilot.git("status", "--porcelain")
        for relative, expected in report["input_sha256"].items():
            assert pilot.digest(pilot.ROOT / relative) == expected
        report["status"] = "COMPLETED_DEVELOPMENT_MATRIX"
    except Exception as error:
        report["status"] = "FAILED"
        report["error"] = {"type": type(error).__name__, "message": str(error)}
        raise
    finally:
        report["finished_utc"] = datetime.now(timezone.utc).isoformat()
        pilot.atomic_json(path, report)


if __name__ == "__main__":
    main()
