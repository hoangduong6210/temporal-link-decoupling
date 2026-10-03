"""Independently audit P003 traces, validation scores and descriptive interactions."""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import socket
import subprocess

import numpy as np

from reconcile_prospective_development import metrics, mean_sd, sha
from temporal_link_decoupling.datasets import load_dataset
from temporal_link_decoupling.prospective import timestamp_groups, chronological_splits
from temporal_link_decoupling.training_diagnostics import GRADIENT_PREFIXES, trace_digest

ROOT = Path(__file__).resolve().parents[1]


def audit_training_traces(report, data, train_stop, catalogue):
    epochs = report["protocol"]["pilot"]["epochs"]
    policies = report["protocol"]["training_policies"]
    assert set(report["training_traces"]) == {policy + ":" + str(epoch) for policy in policies for epoch in range(1, epochs + 1)}
    groups = list(timestamp_groups(data["timestamps"][:train_stop]))
    for epoch in range(1, epochs + 1):
        references = []
        for policy in policies:
            trace = report["training_traces"][policy + ":" + str(epoch)]
            assert len({row[0] for row in trace}) == len(trace)
            observed, expected_rows, position = defaultdict(set), [], 0
            random_rng = np.random.default_rng(report["seed"] + epoch)
            history_rng = np.random.default_rng(report["seed"] + epoch + 1000000)
            mixture_rng = np.random.default_rng(report["seed"] + epoch + 2000000)
            for group in groups:
                positive = defaultdict(set)
                for s, d in zip(data["sources"][group], data["destinations"][group]):
                    positive[int(s)].add(int(d))
                coins = mixture_rng.random(group.stop - group.start)
                for i in range(group.start, group.stop):
                    source = int(data["sources"][i])
                    random_support = sorted(catalogue - positive[source])
                    history_support = sorted(observed[source] - positive[source])
                    random_candidate = int(random_rng.choice(random_support)) if random_support else None
                    history_candidate = int(history_rng.choice(history_support)) if history_support else -1
                    if random_candidate is None:
                        continue
                    use_history = policy == "mixed" and history_candidate >= 0 and coins[i - group.start] < .5
                    expected = [i, history_candidate if use_history else random_candidate,
                                random_candidate, history_candidate, bool(use_history), float(coins[i - group.start])]
                    assert trace[position] == expected, "training trace violates support, timestamp exclusions, RNG or policy"
                    expected_rows.append(i)
                    position += 1
                for source, destinations in positive.items():
                    observed[source].update(destinations)
            assert position == len(trace)
            assert [row[0] for row in trace] == expected_rows
            references.append([[r[0], r[2], r[3], r[5]] for r in trace])
        assert all(reference == references[0] for reference in references), "base draws differ across training policies"
    return groups


def audit_gradient_and_decoder(cell, epoch, groups, interval):
    training = epoch["training"]
    if cell["model"] == "tgn":
        assert training["gradient_diagnostics"] == [] and training["decoder_gradient_steps"] == 0
        assert training["decoder_gradient_rms"] is None and epoch["decoder"] is None and cell["initial_decoder"] is None
        return
    assert training["decoder_gradient_steps"] == len(groups)
    assert len(training["decoder_gradient_rms"]) == 5
    assert all(math.isfinite(value) and value >= 0 for value in training["decoder_gradient_rms"])
    initial, decoder = cell["initial_decoder"], epoch["decoder"]
    for snapshot in [initial, decoder]:
        odds = np.asarray(snapshot["log_odds"])
        probabilities = np.asarray(snapshot["probabilities"])
        assert len(odds) == 5 and np.isfinite(odds).all()
        np.testing.assert_allclose(probabilities, 1 / (1 + np.exp(-odds)), atol=1e-7, rtol=1e-6)
        np.testing.assert_allclose(snapshot["sigmoid_slopes"], probabilities * (1 - probabilities), atol=1e-8, rtol=1e-6)
    np.testing.assert_allclose(decoder["log_odds_displacement"], np.asarray(decoder["log_odds"]) - initial["log_odds"], atol=1e-7, rtol=1e-6)
    probes = training["gradient_diagnostics"]
    assert [p["group_ordinal"] for p in probes] == list(range(0, len(groups), interval))
    for probe in probes:
        group = groups[probe["group_ordinal"]]
        assert probe["events"] == [group.start, group.stop]
        assert set(probe["groups"]) == set(GRADIENT_PREFIXES)
        for name, value in probe["groups"].items():
            a, b, dot, cosine = [value[k] for k in ["prediction_norm", "auxiliary_increment_norm", "dot", "cosine"]]
            assert math.isfinite(a) and math.isfinite(b) and math.isfinite(dot) and a >= 0 and b >= 0
            assert abs(dot) <= a * b + 1e-10
            assert 0 <= value["prediction_connected_parameters"] <= value["parameter_tensors"]
            if a and b:
                assert math.isclose(cosine, dot / (a * b), rel_tol=1e-9, abs_tol=1e-9)
            else:
                assert cosine is None
            if cell["model"] == "bounded-decoupled" and name in {"csn", "context", "drgc"}:
                assert a == 0 and value["prediction_connected_parameters"] == 0


def audit_dataset(reports):
    reference = reports[0]
    protocol = reference["protocol"]
    data = load_dataset(reference["dataset"])
    catalogue = set(map(int, data["destinations"]))
    meta = reference["data"]
    assert sha(ROOT / "resources/corpora" / (reference["dataset"] + ".npz")) == meta["source_npz_sha256"]
    assert len(data["sources"]) == meta["source_events"] and len(catalogue) == meta["catalogue_size"]
    cap = min(protocol["pilot"]["max_events"], meta["source_events"])
    stop = int(np.searchsorted(data["timestamps"], data["timestamps"][cap - 1], side="right"))
    splits = chronological_splits(data["timestamps"][:stop], protocol["pilot"]["train_ratio"], protocol["pilot"]["validation_ratio"])
    assert meta["splits"] == {key: [value.start, value.stop] for key, value in splits.items()}
    train_stop, validation_stop = splits["train"].stop, splits["validation"].stop
    assert meta["prefix_events"] == stop and meta["model_events"] == validation_stop
    for boundary in [train_stop, validation_stop, stop]:
        if boundary < len(data["timestamps"]):
            assert data["timestamps"][boundary - 1] < data["timestamps"][boundary]
    src, dst, times = [data[key][:validation_stop] for key in ["sources", "destinations", "timestamps"]]
    seen = set(src[:train_stop]) | set(dst[:train_stop])
    unseen = (set(src[train_stop:]) | set(dst[train_stop:])) - seen
    inductive = {i for i in range(train_stop, validation_stop) if src[i] in unseen or dst[i] in unseen}
    regimes = protocol["negative_regimes"]
    first_results = reference["cells"][0]["epochs"][0]["validation"]
    maps = {regime: {row[0]: row for row in first_results[regime]["score_rows"]} for regime in regimes}
    prior, training_partners = defaultdict(dict), defaultdict(set)
    for s, d in zip(src[:train_stop], dst[:train_stop]):
        training_partners[int(s)].add(int(d))
    repeated, controls = set(), {regime: {} for regime in regimes}
    for group in timestamp_groups(times):
        positive = defaultdict(set)
        for s, d in zip(src[group], dst[group]):
            positive[int(s)].add(int(d))
        if group.start >= train_stop:
            for i in range(group.start, group.stop):
                source, destination, timestamp = int(src[i]), int(dst[i]), float(times[i])
                history = prior[source]
                if destination in history:
                    repeated.add(i)
                for regime in regimes:
                    support = (set(history) if regime == "historical" else
                               catalogue - training_partners[source] if regime == "novel-pair" else catalogue) - positive[source]
                    row = maps[regime].get(i)
                    assert bool(support) == (row is not None)
                    if row is not None:
                        assert row[1] in support
                        controls[regime][i] = {
                            "recurrence": [float(node in history) for node in [destination, row[1]]],
                            "recency": [history.get(node, float(times[0]) - 1.) - timestamp for node in [destination, row[1]]]}
        for i in range(group.start, group.stop):
            prior[int(src[i])][int(dst[i])] = float(times[i])
    cohorts = {"all": set(range(train_stop, validation_stop)), "inductive": inductive,
               "repeated-positive": repeated, "new-pair-positive": set(range(train_stop, validation_stop)) - repeated,
               "shared-regime-support": set.intersection(*(set(maps[regime]) for regime in regimes))}
    rows_out = []
    for report in reports:
        assert report["data"] == meta
        assert report["status"] == "COMPLETED_VALIDATION_DIAGNOSTICS" and report["test_evaluated"] is False
        assert report["publication_eligible"] is False and report["source_clean"] is True
        cells = report["cells"]
        assert len(cells) == len(protocol["models"]) * len(protocol["training_policies"])
        assert {(c["model"], c["training_policy"]) for c in cells} == {(m, p) for m in protocol["models"] for p in protocol["training_policies"]}
        groups = audit_training_traces(report, data, train_stop, catalogue)
        for family in ["bounded", "tgn"]:
            assert len({c["initial_weights_sha256"] for c in cells if c["model"].startswith(family)}) == 1
        for cell in cells:
            assert cell["seed"] == report["seed"] and "test" not in cell
            assert cell["unseen_validation_nodes"] == len(unseen)
            assert cell["primary_epoch"] == protocol["pilot"]["epochs"]
            assert [epoch["epoch"] for epoch in cell["epochs"]] == list(range(1, cell["primary_epoch"] + 1))
            evaluated = {}
            for epoch in cell["epochs"]:
                training = epoch["training"]
                trace = report["training_traces"][cell["training_policy"] + ":" + str(epoch["epoch"])]
                assert training["candidate_trace_sha256"] == trace_digest(trace)
                assert training["scored_events"] == len(trace)
                assert training["scored_events"] + training["empty_support_events"] == training["observed_events"] == train_stop
                assert training["historical_available_events"] == sum(row[3] >= 0 for row in trace)
                assert training["random_only_stratum_events"] == sum(row[3] < 0 for row in trace)
                assert training["historical_selected_events"] == sum(row[4] for row in trace)
                audit_gradient_and_decoder(cell, epoch, groups, protocol["diagnostics"]["gradient_group_interval"])
                results = {}
                for regime in regimes:
                    recorded = epoch["validation"][regime]
                    rows = recorded["score_rows"]
                    assert len({row[0] for row in rows}) == len(rows)
                    assert [[r[0], r[1], r[4]] for r in rows] == [[r[0], r[1], r[4]] for r in first_results[regime]["score_rows"]]
                    assert all(train_stop <= r[0] < validation_stop and r[4] == (r[0] in inductive) for r in rows)
                    assert recorded["observed_events"] == validation_stop
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
                score = sum(results[regime]["all"]["ap"] for regime in regimes) / len(regimes)
                assert math.isclose(score, epoch["selection_score"], rel_tol=0, abs_tol=1e-12)
                evaluated[epoch["epoch"]] = results
            assert cell["selected_epoch"] == max(cell["epochs"], key=lambda e: e["selection_score"])["epoch"]
            rows_out.append({"model": cell["model"], "policy": cell["training_policy"], "seed": cell["seed"],
                             "primary": evaluated[cell["primary_epoch"]], "selected": evaluated[cell["selected_epoch"]],
                             "selected_epoch": cell["selected_epoch"], "initial_decoder": cell["initial_decoder"],
                             "final_decoder": cell["epochs"][-1]["decoder"],
                             "final_training": cell["epochs"][-1]["training"]})
    index = {(r["model"], r["policy"], r["seed"]): r for r in rows_out}
    aggregates = {}
    for regime in regimes:
        aggregates[regime] = {}
        for cohort, members in cohorts.items():
            item = {"eligible_events": len(members), "scored_events": len(set(maps[regime]) & members),
                    "primary": {}, "selected_secondary": {}, "contrasts": {}, "controls": {}}
            for model in protocol["models"]:
                for policy in protocol["training_policies"]:
                    for endpoint, destination in [("primary", "primary"), ("selected", "selected_secondary")]:
                        item[destination][model + "/" + policy] = {
                            metric: mean_sd([index[(model, policy, seed)][endpoint][regime][cohort][metric] for seed in protocol["seeds"]])
                            for metric in ["ap", "auc"]}
            for metric in ["ap", "auc"]:
                deltas = {}
                for policy in protocol["training_policies"]:
                    paired = []
                    for seed in protocol["seeds"]:
                        a = index[("bounded-coupled", policy, seed)]["primary"][regime][cohort][metric]
                        b = index[("bounded-decoupled", policy, seed)]["primary"][regime][cohort][metric]
                        paired.append(None if a is None or b is None else b - a)
                    deltas[policy] = paired
                    item["contrasts"][policy + "-routing-" + metric] = mean_sd(paired)
                interaction = [None if a is None or b is None else b - a for a, b in zip(deltas["random"], deltas["mixed"])]
                item["contrasts"]["sampling-by-routing-" + metric] = mean_sd(interaction)
                for model in protocol["models"]:
                    values = []
                    for seed in protocol["seeds"]:
                        a = index[(model, "random", seed)]["primary"][regime][cohort][metric]
                        b = index[(model, "mixed", seed)]["primary"][regime][cohort][metric]
                        values.append(None if a is None or b is None else b - a)
                    item["contrasts"][model + "-sampling-" + metric] = mean_sd(values)
            for control in ["recurrence", "recency"]:
                item["controls"][control] = metrics([controls[regime][i][control] for i in sorted(set(controls[regime]) & members)])
            aggregates[regime][cohort] = item
    return {"dataset": reference["dataset"], "audit": "PASS", "aggregates": aggregates, "cells": rows_out,
            "training_support": {str(r["seed"]): {key: {"events": len(trace), "historical_available": sum(row[3] >= 0 for row in trace),
                                    "historical_selected": sum(row[4] for row in trace)} for key, trace in r["training_traces"].items()} for r in reports}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("attempts", nargs=6, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--jobs", required=True)
    args = parser.parse_args()
    if not os.environ.get("SLURM_JOB_ID", "").isdigit() or "login" in socket.gethostname().lower():
        parser.error("reconciliation requires Slurm compute allocation")
    output = args.output_dir.resolve()
    if not output.is_relative_to(ROOT) or output.exists():
        parser.error("output must be a new directory inside the project")
    source = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip():
        parser.error("reconciler requires clean committed source")
    reports = [json.loads(path.read_text()) for path in args.attempts]
    reference = reports[0]
    protocol = reference["protocol"]
    assert protocol["protocol_id"] == "LP-P-PROSPECTIVE-003"
    assert {(r["dataset"], r["seed"]) for r in reports} == {(d, s) for d in protocol["datasets"] for s in protocol["seeds"]}
    for report in reports:
        assert all(report[key] == reference[key] for key in ["source_commit", "input_sha256", "protocol", "upstream", "environment"])
    for relative, expected in reference["input_sha256"].items():
        content = subprocess.check_output(["git", "show", reference["source_commit"] + ":" + relative], cwd=ROOT)
        assert hashlib.sha256(content).hexdigest() == sha(ROOT / relative) == expected
    # The parsed protocol/source register must match the content bound by the run.
    try:
        import tomllib
    except ModuleNotFoundError:
        import tomli as tomllib
    assert tomllib.loads((ROOT / "protocols/prospective_diagnostics_v3.toml").read_text()) == protocol
    assert json.loads((ROOT / "configs/tgn-upstream.json").read_text()) == reference["upstream"]
    accounting = subprocess.check_output(["sacct", "-j", args.jobs, "--format=JobID,State,ExitCode,Elapsed,AllocCPUS,NodeList,MaxRSS", "-P"], text=True)
    states = {row.split("|")[0]: row.split("|")[1:3] for row in accounting.splitlines()[1:]}
    for report in reports:
        key = report["scheduler"]["SLURM_ARRAY_JOB_ID"] + "_" + report["scheduler"]["SLURM_ARRAY_TASK_ID"]
        assert states[key] == ["COMPLETED", "0:0"]
    reconciliation_inputs = {path.name: sha(path) for path in [Path(__file__), ROOT / "scripts/reconcile_prospective_development.py"]}
    summary = {"kind": "reconciled-validation-diagnostics", "protocol_id": protocol["protocol_id"],
               "publication_eligible": False, "test_evaluated": False,
               "interpretation": "descriptive development validation; no independent test or significance inference",
               "source_commit": reference["source_commit"], "reconciler_source_commit": source,
               "reconciler_source_clean": True, "reconciler_sha256": reconciliation_inputs,
               "job_id": os.environ["SLURM_JOB_ID"],
               "input_reports": {r["dataset"] + "-" + str(r["seed"]): sha(p) for r, p in zip(reports, args.attempts)},
               "datasets": [audit_dataset(sorted([r for r in reports if r["dataset"] == dataset], key=lambda r: r["seed"])) for dataset in protocol["datasets"]]}
    assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == source
    assert all(sha(ROOT / "scripts" / name) == value for name, value in reconciliation_inputs.items())
    output.mkdir(parents=True, exist_ok=False)
    for report, path in zip(reports, args.attempts):
        shutil.copyfile(path, output / (report["dataset"] + "-seed-" + str(report["seed"]) + ".json"))
    (output / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n")
    (output / "slurm-accounting.tsv").write_text(accounting)
    files = sorted(output.iterdir())
    (output / "checksums.sha256").write_text("".join(sha(path) + "  " + path.relative_to(ROOT).as_posix() + "\n" for path in files))
    print("PASS: complete validation-only matrix, independent training traces, cohorts, metrics, gradient records and paired interactions.")
    for dataset in summary["datasets"]:
        for regime in protocol["negative_regimes"]:
            result = dataset["aggregates"][regime]["inductive"]
            print(dataset["dataset"], regime, "inductive support", result["scored_events"], "/", result["eligible_events"],
                  "AP interaction", result["contrasts"]["sampling-by-routing-ap"])


if __name__ == "__main__":
    main()
