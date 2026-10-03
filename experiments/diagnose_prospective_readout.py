"""Replay saved pilot checkpoints and measure clipping without retraining."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import socket

import numpy as np
import torch
import torch.nn.functional as F

import run_prospective_pilot as pilot


@torch.no_grad()
def diagnose(dataset, original, checkpoint_root):
    # CPU reduction order depends on thread count, especially near the logit
    # clamp. Reproduce the recorded execution instead of loosening score checks.
    threads = int(original["scheduler"]["SLURM_CPUS_PER_TASK"])
    if threads > int(os.environ.get("SLURM_CPUS_PER_TASK", "1")):
        raise RuntimeError("allocation cannot reproduce the pilot thread count")
    torch.set_num_threads(threads)
    data = pilot.load_dataset(dataset)
    assert pilot.digest(pilot.ROOT / "resources/corpora" / (dataset + ".npz")) == original["data"]["source_npz_sha256"]
    stop = original["data"]["prefix_events"]
    start = original["data"]["splits"]["test"][0]
    out = []
    for arm in original["arms"]:
        checkpoint = checkpoint_root / (arm["arm"] + "-checkpoint.pt")
        assert pilot.digest(checkpoint) == arm["checkpoint_sha256"]
        net = pilot.ProspectiveSRGNN(data["num_nodes"], data["feat_dim"],
                                   original["settings"]["hidden"], decoupled=arm["arm"] == "decoupled")
        net.load_state_dict(torch.load(checkpoint, map_location="cpu", weights_only=True))
        net.eval()
        net.core.set_epoch(original["settings"]["epochs"])
        net.reset()
        weights = F.softplus(net.core.existence_decoder.theta).cpu().tolist()
        maps = {regime: {row[0]: row for row in result["score_rows"]}
                for regime, result in arm["test"].items()}
        records = {regime: [] for regime in maps}
        history = set()
        maximum_error = 0.
        for group in pilot.timestamp_groups(data["timestamps"][:stop]):
            if group.start >= start:
                for regime, saved in maps.items():
                    indices = np.array([i for i in range(group.start, group.stop) if i in saved], dtype=np.int64)
                    if not len(indices):
                        continue
                    captured = []
                    def capture(module, inputs, output):
                        dist = inputs[0]
                        raw = (F.softplus(module.theta).unsqueeze(0) * dist).sum(-1)
                        captured.append((raw.cpu(), dist.cpu()))
                    handle = net.core.existence_decoder.register_forward_hook(capture)
                    try:
                        pos, neg = pilot.pair_scores(net, data, indices, np.array([saved[i][1] for i in indices]))
                    finally:
                        handle.remove()
                    assert len(captured) == 1
                    raw, dist = captured[0]
                    size = len(indices)
                    for k, i in enumerate(indices):
                        error = max(abs(pos[k].item() - saved[i][2]), abs(neg[k].item() - saved[i][3]))
                        maximum_error = max(maximum_error, error)
                        assert error <= 2e-5, (dataset, arm["arm"], regime, i, error)
                        records[regime].append({
                            "event": int(i), "repeated": (int(data["sources"][i]), int(data["destinations"][i])) in history,
                            "inductive": saved[i][4], "served": [float(pos[k]), float(neg[k])],
                            "raw": [float(raw[k]), float(raw[size + k])],
                            "state": [dist[k].tolist(), dist[size + k].tolist()],
                        })
            pilot.observe(net, data, group)
            history.update(zip(map(int, data["sources"][group]), map(int, data["destinations"][group])))
        regimes = {}
        for regime, rows in records.items():
            regimes[regime] = {}
            for cohort in ["all", "repeated-positive", "new-pair-positive", "inductive"]:
                selected = [r for r in rows if cohort == "all" or
                            (cohort == "repeated-positive" and r["repeated"]) or
                            (cohort == "new-pair-positive" and not r["repeated"]) or
                            (cohort == "inductive" and r["inductive"])]
                measures = {}
                for name in ["served", "raw"]:
                    converted = [[r["event"], 0, *r[name], r["inductive"]] for r in selected]
                    measures[name] = pilot.metrics(converted, len(selected))
                for side, index in [("positive", 0), ("negative", 1)]:
                    values = [r["raw"][index] for r in selected]
                    measures[side] = {"upper_clipped": sum(v >= 1 - 1e-6 for v in values),
                                      "lower_clipped": sum(v <= 1e-6 for v in values),
                                      "unique_served": len({r["served"][index] for r in selected}),
                                      "raw_min": min(values) if values else None,
                                      "raw_max": max(values) if values else None}
                regimes[regime][cohort] = measures
        out.append({"arm": arm["arm"], "checkpoint_sha256": arm["checkpoint_sha256"],
                    "decoder_weights": weights, "replay_max_abs_error": maximum_error,
                    "observed_events": net.observed_events, "regimes": regimes})
    return {"dataset": dataset, "torch_threads": threads, "arms": out}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint-root", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    if not os.environ.get("SLURM_JOB_ID", "").isdigit() or "login" in socket.gethostname().lower():
        parser.error("diagnosis requires Slurm compute allocation")
    if os.environ.get("PYTHONHASHSEED") != "0" or pilot.git("status", "--porcelain"):
        parser.error("requires PYTHONHASHSEED=0 and a clean committed tree")
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    args.output_dir.mkdir(parents=True, exist_ok=False)
    report = {"kind": "readout-clipping-diagnosis", "status": "STARTED", "publication_eligible": False,
              "source_commit": pilot.git("rev-parse", "HEAD"),
              "script_sha256": pilot.digest(Path(__file__)), "job_id": os.environ["SLURM_JOB_ID"],
              "interpretation": "raw mixture is a ranking diagnostic, not a probability or retrained model",
              "datasets": []}
    output = args.output_dir / "diagnosis.json"
    pilot.atomic_json(output, report)
    try:
        for task, dataset in enumerate(["wikipedia", "mooc"]):
            path = pilot.ROOT / "evidence/development/LP-P-PROSPECTIVE-001" / (dataset + "-pilot.json")
            original = json.loads(path.read_text())
            result = diagnose(dataset, original, args.checkpoint_root / str(task))
            result["original_report_sha256"] = pilot.digest(path)
            report["datasets"].append(result)
            print(dataset, json.dumps(result), flush=True)
            pilot.atomic_json(output, report)
        assert pilot.git("rev-parse", "HEAD") == report["source_commit"] and not pilot.git("status", "--porcelain")
        report["status"] = "COMPLETED_DIAGNOSTIC"
    except Exception as error:
        report["status"] = "FAILED"
        report["error"] = {"type": type(error).__name__, "message": str(error)}
        raise
    finally:
        pilot.atomic_json(output, report)


if __name__ == "__main__":
    main()
