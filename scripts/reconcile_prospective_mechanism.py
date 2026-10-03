"""Audit P004 candidates, scores, intervention invariants and selected checkpoints."""
from __future__ import annotations

import argparse
from collections import defaultdict
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import socket
import subprocess

import numpy as np
import torch

from reconcile_prospective_development import metrics, mean_sd, sha
from reconcile_prospective_diagnostics import audit_training_traces
from temporal_link_decoupling.datasets import load_dataset
from temporal_link_decoupling.modeling.mechanism_controls import (
    ARMS, BACKBONE, GROUPS, MechanismControl, parameter_movement, parameter_snapshot,
)
from temporal_link_decoupling.prospective import chronological_splits, timestamp_groups
from temporal_link_decoupling.training_diagnostics import trace_digest

ROOT = Path(__file__).resolve().parents[1]


def evaluation_contract(data, splits, catalogue, protocol):
    """Independent support and RNG reconstruction; no training sampler calls."""
    start, stop = splits["validation"].start, splits["validation"].stop
    src, dst, times = [data[key][:stop] for key in ["sources", "destinations", "timestamps"]]
    seen = set(src[:start]) | set(dst[:start])
    unseen = (set(src[start:]) | set(dst[start:])) - seen
    inductive = {i for i in range(start, stop) if src[i] in unseen or dst[i] in unseen}
    training_partners, history = defaultdict(set), defaultdict(dict)
    for s, d in zip(src[:start], dst[:start]):
        training_partners[int(s)].add(int(d))
    regimes = protocol["negative_regimes"]
    rngs = {r: np.random.default_rng(protocol["pilot"]["evaluation_seed"] + j) for j, r in enumerate(regimes)}
    candidates, controls, repeated = {r: [] for r in regimes}, {r: {} for r in regimes}, set()
    for group in timestamp_groups(times):
        current = defaultdict(set)
        for s, d in zip(src[group], dst[group]):
            current[int(s)].add(int(d))
        if group.start >= start:
            for i in range(group.start, group.stop):
                s, d = int(src[i]), int(dst[i])
                if d in history[s]:
                    repeated.add(i)
                for regime in regimes:
                    support = ((set(history[s]) if regime == "historical" else
                                catalogue - training_partners[s] if regime == "novel-pair" else catalogue)
                               - current[s])
                    if not support:
                        continue
                    negative = int(rngs[regime].choice(sorted(support)))
                    candidates[regime].append([i, negative, i in inductive])
                    controls[regime][i] = {
                        "recurrence": [float(node in history[s]) for node in [d, negative]],
                        "recency": [history[s].get(node, float(times[0]) - 1.) - float(times[i]) for node in [d, negative]],
                    }
        for i in range(group.start, group.stop):
            history[int(src[i])][int(dst[i])] = float(times[i])
    cohorts = {"all": set(range(start, stop)), "inductive": inductive,
               "repeated-positive": repeated, "new-pair-positive": set(range(start, stop)) - repeated,
               "shared-regime-support": set.intersection(*(set(r[0] for r in candidates[g]) for g in regimes))}
    return candidates, cohorts, controls, unseen


def compare_movement(actual, expected):
    assert set(actual) == set(expected) == set(GROUPS)
    for group in GROUPS:
        for key in ["weights_sha256", "parameter_tensors", "trainable_tensors", "parameters"]:
            assert actual[group][key] == expected[group][key], "checkpoint/group identity mismatch"
        for key in ["l2_displacement", "max_abs_displacement"]:
            assert math.isclose(actual[group][key], expected[group][key], rel_tol=1e-10, abs_tol=1e-12)


def audit_checkpoint(cell, report, attempt_path, data):
    # This model family has no node-indexed trainable parameters. A small node
    # catalogue recreates every parameter without allocating full replay stores.
    torch.manual_seed(report["seed"])
    template = MechanismControl(4, data["feat_dim"], report["protocol"]["pilot"]["hidden"], **ARMS[cell["arm"]])
    initial = parameter_snapshot(template)
    compare_movement(cell["initial_groups"], parameter_movement(template, initial))
    assert cell["trainable_parameters"] == sum(p.numel() for p in template.parameters() if p.requires_grad)
    checkpoint = attempt_path.parent / (cell["arm"] + "-" + report["training_policy"] + "-seed-" + str(report["seed"]) + ".pt")
    assert sha(checkpoint) == cell["checkpoint_sha256"], "selected checkpoint byte mismatch"
    weights = torch.load(checkpoint, map_location="cpu", weights_only=True)
    with torch.no_grad():
        for name, parameter in template.named_parameters():
            assert weights[name].shape == parameter.shape and torch.isfinite(weights[name]).all()
            parameter.copy_(weights[name])
    selected = cell["epochs"][cell["selected_epoch"] - 1]
    compare_movement(selected["movement"], parameter_movement(template, initial))


def audit_intervention(cell, epoch, groups, interval):
    intervention = ARMS[cell["arm"]]
    training = epoch["training"]
    assert cell["intervention"] == intervention
    assert training["auxiliary_backward_enabled"] == intervention["auxiliary"]
    assert math.isfinite(training["auxiliary_forward_value_event_mean"])
    for group, movement in epoch["movement"].items():
        initial = cell["initial_groups"][group]
        assert movement["parameters"] == initial["parameters"] and movement["parameter_tensors"] == initial["parameter_tensors"]
        assert movement["trainable_tensors"] == initial["trainable_tensors"]
        assert math.isfinite(movement["l2_displacement"]) and movement["l2_displacement"] >= 0
        assert 0 <= movement["max_abs_displacement"] <= movement["l2_displacement"] + 1e-12
        if group in BACKBONE and cell["arm"] in {"detached-noaux", "frozen-aux"}:
            assert movement["weights_sha256"] == initial["weights_sha256"]
            assert movement["l2_displacement"] == movement["max_abs_displacement"] == 0
    probes = training["gradient_diagnostics"]
    assert [p["group_ordinal"] for p in probes] == list(range(0, len(groups), interval))
    for probe in probes:
        group = groups[probe["group_ordinal"]]
        assert probe["events"] == [group.start, group.stop] and set(probe["groups"]) == set(GROUPS)
        for name, value in probe["groups"].items():
            a, b, dot, cosine = [value[k] for k in ["prediction_norm", "auxiliary_increment_norm", "dot", "cosine"]]
            assert all(math.isfinite(v) for v in [a, b, dot]) and a >= 0 and b >= 0
            assert abs(dot) <= a * b + 1e-10
            assert value["parameter_tensors"] == cell["initial_groups"][name]["parameter_tensors"]
            assert value["trainable_tensors"] == cell["initial_groups"][name]["trainable_tensors"]
            assert 0 <= value["prediction_connected_tensors"] <= value["trainable_tensors"]
            assert 0 <= value["post_observation_connected_tensors"] <= value["trainable_tensors"]
            if a and b:
                assert math.isclose(cosine, dot / (a * b), rel_tol=1e-9, abs_tol=1e-9)
            else:
                assert cosine is None
            if not intervention["auxiliary"]:
                assert b == 0 and value["prediction_connected_tensors"] == value["post_observation_connected_tensors"]
            if intervention["decoupled"] and name in BACKBONE:
                assert a == 0 and value["prediction_connected_tensors"] == 0
            if intervention["freeze_backbone"] and name in BACKBONE:
                assert a == b == value["post_observation_connected_tensors"] == value["trainable_tensors"] == 0


def audit_dataset(reports, paths, *, complete=True):
    reference = reports[0]
    protocol = reference["protocol"]
    data = load_dataset(reference["dataset"])
    catalogue = set(map(int, data["destinations"]))
    meta = reference["data"]
    assert sha(ROOT / "resources/corpora" / (reference["dataset"] + ".npz")) == meta["source_npz_sha256"]
    assert data["num_edges"] == meta["source_events"] and len(catalogue) == meta["catalogue_size"]
    cap = min(protocol["pilot"]["max_events"], meta["source_events"])
    stop = int(np.searchsorted(data["timestamps"], data["timestamps"][cap - 1], side="right"))
    splits = chronological_splits(data["timestamps"][:stop], protocol["pilot"]["train_ratio"], protocol["pilot"]["validation_ratio"])
    assert meta["splits"] == {key: [value.start, value.stop] for key, value in splits.items()}
    assert meta["prefix_events"] == stop and meta["model_events"] == splits["validation"].stop
    candidates, cohorts, controls, unseen = evaluation_contract(data, splits, catalogue, protocol)
    regimes = protocol["negative_regimes"]
    rows_out = []
    for report, path in zip(reports, paths):
        assert report["data"] == meta and report["status"] == "COMPLETED_VALIDATION_MECHANISM"
        assert report["test_evaluated"] is False and report["publication_eligible"] is False and report["source_clean"] is True
        assert len(report["cells"]) == len(ARMS) and {c["arm"] for c in report["cells"]} == set(ARMS)
        traces = copy.deepcopy({key: report[key] for key in ["seed", "protocol", "training_traces"]})
        traces["protocol"]["training_policies"] = [report["training_policy"]]
        groups = audit_training_traces(traces, data, splits["train"].stop, catalogue)
        assert len({c["initial_weights_sha256"] for c in report["cells"]}) == 1
        runtime_path = path.parent / "runtime.json"
        assert sha(runtime_path) == report["runtime_attestation_sha256"]
        runtime = json.loads(runtime_path.read_text())
        assert runtime["runtime"] == report["runtime"] and runtime["source_clean"] and runtime["source_commit"] == report["source_commit"]
        for cell in report["cells"]:
            assert cell["seed"] == report["seed"] and cell["training_policy"] == report["training_policy"] and "test" not in cell
            assert cell["unseen_validation_nodes"] == len(unseen) and cell["primary_epoch"] == protocol["pilot"]["epochs"]
            assert [e["epoch"] for e in cell["epochs"]] == list(range(1, cell["primary_epoch"] + 1))
            evaluated = {}
            for epoch in cell["epochs"]:
                trace = report["training_traces"][report["training_policy"] + ":" + str(epoch["epoch"])]
                training = epoch["training"]
                assert training["candidate_trace_sha256"] == trace_digest(trace) and training["scored_events"] == len(trace)
                assert training["scored_events"] + training["empty_support_events"] == training["observed_events"] == splits["train"].stop
                assert training["historical_available_events"] == sum(r[3] >= 0 for r in trace)
                assert training["historical_selected_events"] == sum(r[4] for r in trace)
                audit_intervention(cell, epoch, groups, protocol["diagnostics"]["gradient_group_interval"])
                results = {}
                for regime in regimes:
                    recorded = epoch["validation"][regime]
                    rows = recorded["score_rows"]
                    assert [[r[0], r[1], r[4]] for r in rows] == candidates[regime], "evaluation support or RNG mismatch"
                    assert recorded["observed_events"] == splits["validation"].stop
                    assert recorded["candidate_sha256"] == hashlib.sha256(json.dumps([[r[0], r[1]] for r in rows]).encode()).hexdigest()
                    results[regime] = {}
                    for cohort, members in cohorts.items():
                        value = metrics([r[2:4] for r in rows if r[0] in members])
                        value["eligible_events"] = len(members)
                        results[regime][cohort] = value
                        if cohort in {"all", "inductive"}:
                            original = recorded[cohort]
                            assert original["scored_events"] == value["events"] and original["eligible_events"] == len(members)
                            assert original["empty_support_events"] == len(members) - value["events"]
                            for metric in ["ap", "auc"]:
                                assert (value[metric] is None and original[metric] is None) or math.isclose(value[metric], original[metric], abs_tol=1e-12, rel_tol=0)
                assert math.isclose(epoch["selection_score"], sum(results[r]["all"]["ap"] for r in regimes) / len(regimes), abs_tol=1e-12, rel_tol=0)
                evaluated[epoch["epoch"]] = results
            assert cell["selected_epoch"] == max(cell["epochs"], key=lambda e: e["selection_score"])["epoch"]
            audit_checkpoint(cell, report, path, data)
            rows_out.append({"arm": cell["arm"], "policy": report["training_policy"], "seed": report["seed"],
                             "selected_checkpoint_verified": True,
                             "primary": evaluated[cell["primary_epoch"]], "selected_secondary": evaluated[cell["selected_epoch"]],
                             "final_movement": cell["epochs"][-1]["movement"], "final_training": cell["epochs"][-1]["training"],
                             "selected_epoch": cell["selected_epoch"]})
    if not complete:
        return {"audit": "PASS", "cells": len(rows_out), "boundary": "subset audit only; no complete-matrix summary"}
    assert {(r["seed"], r["training_policy"]) for r in reports} == {(s, p) for s in protocol["seeds"] for p in protocol["training_policies"]}
    for seed in protocol["seeds"]:
        assert len({c["initial_weights_sha256"] for r in reports if r["seed"] == seed for c in r["cells"]}) == 1
    index = {(r["arm"], r["policy"], r["seed"]): r for r in rows_out}
    contrasts = {"routing-aux": ("detached-aux", "coupled-aux"),
                 "routing-noaux": ("detached-noaux", "coupled-noaux"),
                 "auxiliary-coupled": ("coupled-aux", "coupled-noaux"),
                 "auxiliary-detached": ("detached-aux", "detached-noaux"),
                 "backbone-adaptation": ("detached-aux", "frozen-aux")}
    aggregates = {}
    for regime in regimes:
        aggregates[regime] = {}
        support = set(r[0] for r in candidates[regime])
        for cohort, members in cohorts.items():
            value = {"eligible_events": len(members), "scored_events": len(members & support), "policies": {}, "controls": {}}
            for policy in protocol["training_policies"]:
                item = {"primary": {}, "selected_secondary": {}, "contrasts": {}}
                for endpoint in ["primary", "selected_secondary"]:
                    for arm in ARMS:
                        item[endpoint][arm] = {metric: mean_sd([index[(arm, policy, seed)][endpoint][regime][cohort][metric]
                                                               for seed in protocol["seeds"]]) for metric in ["ap", "auc"]}
                for metric in ["ap", "auc"]:
                    for name, (left, right) in contrasts.items():
                        pairs = [(index[(left, policy, s)]["primary"][regime][cohort][metric],
                                  index[(right, policy, s)]["primary"][regime][cohort][metric]) for s in protocol["seeds"]]
                        item["contrasts"][name + "-" + metric] = mean_sd([None if a is None or b is None else a - b for a, b in pairs])
                    a, b = [item["contrasts"][name + "-" + metric]["values"] for name in ["routing-aux", "routing-noaux"]]
                    item["contrasts"]["auxiliary-by-routing-" + metric] = mean_sd([None if x is None or y is None else x - y for x, y in zip(a, b)])
                value["policies"][policy] = item
            for control in ["recurrence", "recency"]:
                value["controls"][control] = metrics([controls[regime][i][control] for i in sorted(members & support)])
            aggregates[regime][cohort] = value
    return {"dataset": reference["dataset"], "audit": "PASS", "cells": rows_out, "aggregates": aggregates}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("attempts", nargs=12, type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--jobs", required=True)
    args = parser.parse_args()
    assert os.environ.get("SLURM_JOB_ID", "").isdigit() and "login" not in socket.gethostname().lower()
    torch.set_num_threads(1)
    assert not subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip()
    source = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    output = args.output_dir.resolve()
    assert output.is_relative_to(ROOT) and not output.exists()
    reports = [json.loads(path.read_text()) for path in args.attempts]
    reference = reports[0]
    protocol = reference["protocol"]
    assert protocol["protocol_id"] == "LP-P-PROSPECTIVE-004" and protocol["arms"] == list(ARMS)
    assert {(r["dataset"], r["seed"], r["training_policy"]) for r in reports} == {(d, s, p) for d in protocol["datasets"] for s in protocol["seeds"] for p in protocol["training_policies"]}
    for report in reports:
        assert all(report[key] == reference[key] for key in ["source_commit", "input_sha256", "protocol", "runtime"])
        assert report["execution"]["torch_threads"] == 1 and report["execution"]["deterministic_algorithms"]
    for relative, expected in reference["input_sha256"].items():
        blob = subprocess.check_output(["git", "show", reference["source_commit"] + ":" + relative], cwd=ROOT)
        assert hashlib.sha256(blob).hexdigest() == sha(ROOT / relative) == expected
    try:
        import tomllib
    except ModuleNotFoundError:
        import tomli as tomllib
    assert tomllib.loads((ROOT / "protocols/prospective_mechanism_v4.toml").read_text()) == protocol
    assert json.loads((ROOT / protocol["runtime"]["attestation"]).read_text())["runtime"] == reference["runtime"]
    accounting = subprocess.check_output(["sacct", "-j", args.jobs, "--format=JobID,State,ExitCode,Elapsed,AllocCPUS,NodeList,MaxRSS", "-P"], text=True)
    states = {line.split("|")[0]: line.split("|")[1:3] for line in accounting.splitlines()[1:]}
    for report in reports:
        job = report["scheduler"]["SLURM_ARRAY_JOB_ID"] + "_" + report["scheduler"]["SLURM_ARRAY_TASK_ID"]
        assert states[job] == ["COMPLETED", "0:0"]
    inputs = {p.name: sha(p) for p in [Path(__file__), ROOT / "scripts/reconcile_prospective_diagnostics.py", ROOT / "scripts/reconcile_prospective_development.py"]}
    summary = {"kind": "reconciled-validation-mechanism", "protocol_id": protocol["protocol_id"],
               "publication_eligible": False, "test_evaluated": False, "source_commit": reference["source_commit"],
               "reconciler_source_commit": source, "reconciler_sha256": inputs, "job_id": os.environ["SLURM_JOB_ID"],
               "input_reports": {str(i): sha(p) for i, p in enumerate(args.attempts)}, "datasets": []}
    for dataset in protocol["datasets"]:
        selected = [(r, p) for r, p in zip(reports, args.attempts) if r["dataset"] == dataset]
        summary["datasets"].append(audit_dataset([r for r, _ in selected], [p for _, p in selected]))
    assert source == subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    assert all(sha(ROOT / "scripts" / name) == value for name, value in inputs.items())
    output.mkdir(parents=True, exist_ok=False)
    for report, path in zip(reports, args.attempts):
        name = report["dataset"] + "-seed-" + str(report["seed"]) + "-" + report["training_policy"]
        shutil.copyfile(path, output / (name + ".json"))
        shutil.copyfile(path.parent / "runtime.json", output / (name + "-runtime.json"))
    (output / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n")
    (output / "slurm-accounting.tsv").write_text(accounting)
    files = sorted(output.iterdir())
    (output / "checksums.sha256").write_text("".join(sha(p) + "  " + p.relative_to(ROOT).as_posix() + "\n" for p in files))
    print("PASS: complete P004 matrix, independent candidate RNG, cohorts, metrics, interventions and selected checkpoints")


if __name__ == "__main__":
    main()
