"""Slurm-only prospective protocol pilot; outputs are never publication evidence."""
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
import subprocess
import sys
import time
from datetime import datetime, timezone

import numpy as np
import torch
import torch.nn.functional as F
from sklearn.metrics import average_precision_score, roc_auc_score

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

from temporal_link_decoupling.datasets import load_dataset
from temporal_link_decoupling.modeling.prospective import ProspectiveSRGNN
from temporal_link_decoupling.prospective import DestinationSampler, chronological_splits, timestamp_groups

ROOT = Path(__file__).resolve().parents[1]


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def atomic_json(path: Path, content) -> None:
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(content, indent=2, sort_keys=True, allow_nan=False) + "\n")
    temporary.replace(path)


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def tensor(values, *, ids=False):
    return torch.as_tensor(values, dtype=torch.long if ids else torch.float64)


def finite(values, context: str):
    for value in values:
        if isinstance(value, torch.Tensor) and not bool(torch.isfinite(value).all()):
            raise FloatingPointError(f"non-finite {context}")


def observe(model, data, group, *, backward=False):
    return model.observe_group(tensor(data["sources"][group], ids=True),
                               tensor(data["destinations"][group], ids=True),
                               tensor(data["timestamps"][group]),
                               torch.as_tensor(data["features"][group], dtype=torch.float32),
                               backward_auxiliary=backward)


def pair_scores(model, data, indices, negative):
    source = tensor(data["sources"][indices], ids=True)
    positive = tensor(data["destinations"][indices], ids=True)
    timestamp = tensor(data["timestamps"][indices])
    # A single label-free call makes both sides follow exactly the same path.
    scores = model.score_candidates(torch.cat([source, source]),
                                    torch.cat([positive, tensor(negative, ids=True)]),
                                    torch.cat([timestamp, timestamp]))
    finite([scores], "query scores")
    return scores[:len(indices)], scores[len(indices):]


def train_epoch(model, optimizer, data, train_slice, catalogue, settings, epoch):
    model.train()
    model.reset()
    model.core.set_epoch(epoch)
    sampler = DestinationSampler(catalogue, seed=settings["seed"] + epoch)
    n_scored, n_skipped, loss_sum = 0, 0, 0.
    for group in timestamp_groups(data["timestamps"][train_slice]):
        src, dst = data["sources"][group], data["destinations"][group]
        timestamp = float(data["timestamps"][group.start])
        candidates = sampler.sample(src, dst, timestamp, "random")
        optimizer.zero_grad(set_to_none=True)
        size = len(candidates.rows)
        batch_size = settings["query_batch_size"]
        for start in range(0, size, batch_size):
            chunk = slice(start, start + batch_size)
            indices = candidates.rows[chunk] + group.start
            pos, neg = pair_scores(model, data, indices, candidates.negatives[chunk])
            loss = (F.binary_cross_entropy_with_logits(pos, torch.ones_like(pos), reduction="sum")
                    + F.binary_cross_entropy_with_logits(neg, torch.zeros_like(neg), reduction="sum")) / (2 * size)
            finite([loss], "prediction loss")
            loss.backward()
            loss_sum += float(loss.detach()) * size
        observe(model, data, group, backward=True)
        finite((p.grad for p in model.parameters()), "gradient")
        optimizer.step()
        finite(model.parameters(), "parameter")
        finite((value for state in optimizer.state.values() for value in state.values()), "optimizer state")
        sampler.observe(src, dst, timestamp)
        n_scored += size
        n_skipped += len(candidates.skipped_rows)
    return {"scored_events": n_scored, "empty_support_events": n_skipped,
            "observed_events": model.observed_events,
            "prediction_loss": loss_sum / n_scored if n_scored else None}


def metrics(rows, eligible: int):
    if not rows:
        return {"ap": None, "auc": None, "eligible_events": eligible,
                "scored_events": 0, "empty_support_events": eligible,
                "status": "NO_ELIGIBLE_EVENTS" if not eligible else "EMPTY_NEGATIVE_SUPPORT"}
    positive = np.asarray([row[2] for row in rows])
    negative = np.asarray([row[3] for row in rows])
    labels = np.r_[np.ones(len(rows)), np.zeros(len(rows))]
    scores = np.r_[positive, negative]
    return {"ap": float(average_precision_score(labels, scores)),
            "auc": float(roc_auc_score(labels, scores)), "eligible_events": eligible,
            "scored_events": len(rows), "empty_support_events": eligible - len(rows),
            "status": "AVAILABLE"}


@torch.no_grad()
def evaluate(model, data, selected, catalogue, training_pairs, settings, regimes, unseen):
    """Replay all history; filter metric rows only, including for inductive scores."""
    model.eval()
    model.reset()
    samplers = {regime: DestinationSampler(catalogue, training_pairs=training_pairs,
                                          seed=settings["evaluation_seed"] + index)
                for index, regime in enumerate(regimes)}
    records = {regime: [] for regime in regimes}
    inductive_eligible = 0
    for group in timestamp_groups(data["timestamps"][:selected.stop]):
        src, dst = data["sources"][group], data["destinations"][group]
        timestamp = float(data["timestamps"][group.start])
        if group.start >= selected.start:
            inductive_eligible += sum(int(s) in unseen or int(d) in unseen for s, d in zip(src, dst))
            for regime, sampler in samplers.items():
                candidates = sampler.sample(src, dst, timestamp, regime)
                for start in range(0, len(candidates.rows), settings["query_batch_size"]):
                    chunk = slice(start, start + settings["query_batch_size"])
                    indices = candidates.rows[chunk] + group.start
                    negatives = candidates.negatives[chunk]
                    pos, neg = pair_scores(model, data, indices, negatives)
                    for index, nd, p, n in zip(indices, negatives, pos.tolist(), neg.tolist()):
                        is_ind = int(data["sources"][index]) in unseen or int(data["destinations"][index]) in unseen
                        records[regime].append([int(index), int(nd), p, n, bool(is_ind)])
        observe(model, data, group)
        for sampler in samplers.values():
            sampler.observe(src, dst, timestamp)
    results = {}
    for regime, rows in records.items():
        candidates = [[row[0], row[1]] for row in rows]
        results[regime] = {
            "all": metrics(rows, selected.stop - selected.start),
            "inductive": metrics([row for row in rows if row[4]], inductive_eligible),
            "candidate_sha256": hashlib.sha256(json.dumps(candidates).encode()).hexdigest(),
            "observed_events": model.observed_events,
            "score_rows": rows,
        }
    return results


def model_digest(model) -> str:
    h = hashlib.sha256()
    for name, value in sorted(model.state_dict().items()):
        h.update(name.encode())
        h.update(value.detach().cpu().contiguous().numpy().tobytes())
    return h.hexdigest()


def run_arm(arm, data, splits, catalogue, settings, regimes, output):
    seed = settings["seed"]
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    model = ProspectiveSRGNN(data["num_nodes"], data["feat_dim"], settings["hidden"],
                             decoupled=arm == "decoupled")
    initial = model_digest(model)
    optimizer = torch.optim.Adam(model.parameters(), lr=settings["learning_rate"],
                                 weight_decay=settings["weight_decay"])
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=settings["epochs"])
    training_pairs = list(zip(data["sources"][splits["train"]], data["destinations"][splits["train"]]))
    seen = set(data["sources"][:splits["test"].start]) | set(data["destinations"][:splits["test"].start])
    unseen = (set(data["sources"][splits["test"]]) | set(data["destinations"][splits["test"]])) - seen
    epochs, best_state, best_ap, best_epoch = [], None, -1., None
    started = time.perf_counter()
    for epoch in range(1, settings["epochs"] + 1):
        training = train_epoch(model, optimizer, data, splits["train"], catalogue, settings, epoch)
        scheduler.step()
        validation = evaluate(model, data, splits["validation"], catalogue, training_pairs,
                              settings, ["random"], unseen)["random"]["all"]
        ap = validation["ap"]
        if ap is None:
            raise ValueError("validation has no valid candidate support; checkpoint selection unavailable")
        epochs.append({"epoch": epoch, "training": training, "validation": validation})
        if ap > best_ap:
            best_ap, best_epoch = ap, epoch
            best_state = copy.deepcopy(model.state_dict())
        print(f"{arm}: epoch {epoch} complete; observed {training['observed_events']} training events", flush=True)
    model.load_state_dict(best_state)
    torch.save(best_state, output / f"{arm}-checkpoint.pt")
    test = evaluate(model, data, splits["test"], catalogue, training_pairs, settings, regimes, unseen)
    return {"arm": arm, "initial_weights_sha256": initial,
            "checkpoint_sha256": digest(output / f"{arm}-checkpoint.pt"),
            "selected_epoch": best_epoch, "epochs": epochs, "test": test,
            "unseen_nodes": len(unseen), "wall_seconds": time.perf_counter() - started}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, choices=["wikipedia", "mooc"])
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    if not os.environ.get("SLURM_JOB_ID", "").isdigit() or "login" in socket.gethostname().lower():
        parser.error("pilot execution requires a Slurm compute-node allocation")
    if os.environ.get("PYTHONHASHSEED") != "0":
        parser.error("set PYTHONHASHSEED=0 before starting Python")
    if git("status", "--porcelain", "--untracked-files=normal"):
        parser.error("pilot requires a clean committed source tree")
    protocol_path = ROOT / "protocols/prospective_v1.toml"
    protocol = tomllib.loads(protocol_path.read_text())
    if protocol["status"] != "PILOT_ONLY" or protocol["publication_eligible"]:
        parser.error("this runner only implements the non-publication pilot protocol")
    settings = protocol["pilot"]
    if settings["device"] != "cpu":
        parser.error("this deterministic pilot runner is registered for CPU")
    torch.set_num_threads(int(os.environ.get("SLURM_CPUS_PER_TASK", "1")))
    torch.use_deterministic_algorithms(True)
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=False)
    inputs = [protocol_path, Path(__file__).resolve(), ROOT / "resources/manifest.toml",
              *sorted((ROOT / "src").rglob("*.py"))]
    report = {
        "schema_version": 1, "status": "STARTED", "publication_eligible": False,
        "protocol_id": protocol["protocol_id"], "source_commit": git("rev-parse", "HEAD"),
        "source_clean": True, "dataset": args.dataset, "settings": settings,
        "input_sha256": {path.relative_to(ROOT).as_posix(): digest(path) for path in inputs},
        "environment": {"python": platform.python_version(), "machine": platform.machine(),
                        **{name: importlib.metadata.version(name) for name in
                           ["torch", "numpy", "scikit-learn", "pandas"]}},
        "scheduler": {key: os.environ.get(key) for key in
                      ["SLURM_JOB_ID", "SLURM_ARRAY_JOB_ID", "SLURM_ARRAY_TASK_ID",
                       "SLURM_JOB_PARTITION", "SLURM_CPUS_PER_TASK", "SLURM_JOB_NODELIST"]},
        "started_utc": datetime.now(timezone.utc).isoformat(), "arms": [],
        "limitations": ["chronological-prefix technical pilot, not performance evidence",
                        "closed destination catalogue assumed available",
                        "stable observation order within timestamp ties",
                        "prospective adapter differs from the frozen A003 model objective"],
    }
    path = output / "attempt.json"
    atomic_json(path, report)
    try:
        data = load_dataset(args.dataset)
        catalogue = np.unique(data["destinations"])
        original_count = data["num_edges"]
        cap = min(settings["max_events"], original_count)
        stop = int(np.searchsorted(data["timestamps"], data["timestamps"][cap - 1], side="right"))
        for key in ["sources", "destinations", "timestamps", "features", "labels"]:
            data[key] = data[key][:stop]
        data["num_edges"] = stop
        splits = chronological_splits(data["timestamps"], settings["train_ratio"], settings["validation_ratio"])
        report["data"] = {"source_npz_sha256": digest(ROOT / "resources/corpora" / f"{args.dataset}.npz"),
                          "source_events": original_count, "prefix_events": stop,
                          "catalogue_size": len(catalogue),
                          "splits": {key: [value.start, value.stop] for key, value in splits.items()}}
        for arm in protocol["arms"]:
            report["arms"].append(run_arm(arm, data, splits, catalogue, settings,
                                           protocol["negative_regimes"], output))
            atomic_json(path, report)
        left, right = report["arms"]
        if left["initial_weights_sha256"] != right["initial_weights_sha256"]:
            raise AssertionError("paired arms did not start with identical weights")
        for regime in protocol["negative_regimes"]:
            if left["test"][regime]["candidate_sha256"] != right["test"][regime]["candidate_sha256"]:
                raise AssertionError("paired arms did not receive identical evaluation candidates")
        if git("rev-parse", "HEAD") != report["source_commit"] or git("status", "--porcelain", "--untracked-files=normal"):
            raise RuntimeError("source tree changed during execution")
        for relative, expected in report["input_sha256"].items():
            if digest(ROOT / relative) != expected:
                raise RuntimeError(f"input changed during execution: {relative}")
        report["status"] = "COMPLETED_TECHNICAL_PILOT"
    except Exception as error:
        report["status"] = "FAILED"
        report["error"] = {"type": type(error).__name__, "message": str(error)}
        raise
    finally:
        report["finished_utc"] = datetime.now(timezone.utc).isoformat()
        atomic_json(path, report)
    print(f"Completed technical pilot for {args.dataset}; no performance claim admitted.", flush=True)


if __name__ == "__main__":
    main()
