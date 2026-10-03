"""Audit complete development attempts and preserve descriptive, non-admitted results."""
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
import statistics
import subprocess

import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

from temporal_link_decoupling.datasets import load_dataset

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def metrics(pairs):
    if not pairs:
        return {"events": 0, "ap": None, "auc": None}
    scores = np.asarray(pairs, dtype=float).reshape(-1)
    assert np.isfinite(scores).all()
    labels = np.tile([1, 0], len(pairs))
    return {"events": len(pairs), "ap": float(average_precision_score(labels, scores)),
            "auc": float(roc_auc_score(labels, scores))}


def mean_sd(values):
    if any(value is None for value in values):
        return {"n": len(values), "mean": None, "sample_sd": None, "values": values}
    return {"n": len(values), "mean": statistics.mean(values),
            "sample_sd": statistics.stdev(values) if len(values) > 1 else None, "values": values}


def audit(report):
    assert report["status"] == "COMPLETED_DEVELOPMENT_MATRIX"
    assert report["publication_eligible"] is False and report["source_clean"] is True
    for relative, expected in report["input_sha256"].items():
        content = subprocess.check_output(["git", "show", report["source_commit"] + ":" + relative], cwd=ROOT)
        assert hashlib.sha256(content).hexdigest() == expected
        if relative == "protocols/prospective_development_v2.toml":
            assert tomllib.loads(content.decode()) == report["protocol"]
        elif relative == "configs/tgn-upstream.json":
            assert json.loads(content) == report["upstream"]
    protocol = report["protocol"]
    models, seeds, regimes = protocol["models"], protocol["seeds"], protocol["negative_regimes"]
    cells = {(cell["model"], cell["seed"]): cell for cell in report["cells"]}
    assert len(cells) == len(report["cells"]) == len(models) * len(seeds)
    assert set(cells) == {(name, seed) for name in models for seed in seeds}
    for seed in seeds:
        for family in ["legacy", "bounded"]:
            assert cells[(family + "-coupled", seed)]["initial_weights_sha256"] == cells[(family + "-decoupled", seed)]["initial_weights_sha256"]
        for epoch in range(protocol["pilot"]["epochs"]):
            assert len({cells[(name, seed)]["epochs"][epoch]["training"]["candidate_sha256"] for name in models}) == 1
    data = load_dataset(report["dataset"])
    assert sha(ROOT / "resources/corpora" / (report["dataset"] + ".npz")) == report["data"]["source_npz_sha256"]
    assert len(data["sources"]) == report["data"]["source_events"]
    stop = report["data"]["prefix_events"]
    cap = min(protocol["pilot"]["max_events"], report["data"]["source_events"])
    assert stop == int(np.searchsorted(data["timestamps"], data["timestamps"][cap - 1], side="right"))
    train_stop = report["data"]["splits"]["train"][1]
    start, test_stop = report["data"]["splits"]["test"]
    assert test_stop == stop
    assert report["data"]["splits"] == {"train": [0, train_stop], "validation": [train_stop, start], "test": [start, stop]}
    for boundary in [train_stop, start, stop]:
        if boundary < len(data["timestamps"]):
            assert data["timestamps"][boundary - 1] < data["timestamps"][boundary]
    src, dst, times = [data[key][:stop] for key in ["sources", "destinations", "timestamps"]]
    catalogue = set(map(int, data["destinations"]))
    assert len(catalogue) == report["data"]["catalogue_size"]
    seen = set(src[:start]) | set(dst[:start])
    unseen = (set(src[start:]) | set(dst[start:])) - seen
    inductive = {i for i in range(start, stop) if src[i] in unseen or dst[i] in unseen}
    reference = report["cells"][0]
    maps = {regime: {r[0]: r for r in reference["test"][regime]["score_rows"]} for regime in regimes}
    train_partners, previous = defaultdict(set), defaultdict(dict)
    for s, d in zip(src[:train_stop], dst[:train_stop]):
        train_partners[int(s)].add(int(d))
    repeated, controls = set(), {regime: {} for regime in regimes}
    boundaries = np.r_[0, np.flatnonzero(np.diff(times) != 0) + 1, stop]
    for begin, end in zip(boundaries[:-1], boundaries[1:]):
        positives = defaultdict(set)
        for i in range(begin, end):
            positives[int(src[i])].add(int(dst[i]))
        if begin >= start:
            for i in range(begin, end):
                s, d, t = int(src[i]), int(dst[i]), float(times[i])
                history = previous[s]
                if d in history:
                    repeated.add(i)
                for regime in regimes:
                    support = (set(history) if regime == "historical" else
                               catalogue - train_partners[s] if regime == "novel-pair" else catalogue) - positives[s]
                    row = maps[regime].get(i)
                    assert bool(support) == (row is not None)
                    if row is not None:
                        assert row[1] in support
                        controls[regime][i] = {"recurrence": [float(node in history) for node in [d, row[1]]],
                            "recency": [history.get(node, float(times[0]) - 1.) - t for node in [d, row[1]]]}
        for i in range(begin, end):
            previous[int(src[i])][int(dst[i])] = float(times[i])
    cohorts = {"all": set(range(start, stop)), "inductive": inductive, "repeated-positive": repeated,
               "new-pair-positive": set(range(start, stop)) - repeated,
               "shared-regime-support": set.intersection(*(set(maps[regime]) for regime in regimes))}
    cell_metrics = []
    for cell in report["cells"]:
        assert cell["unseen_nodes"] == len(unseen)
        assert len(cell["epochs"]) == protocol["pilot"]["epochs"]
        best = max(cell["epochs"], key=lambda item: item["validation"]["ap"])
        assert cell["selected_epoch"] == best["epoch"]
        for epoch in cell["epochs"]:
            assert epoch["training"]["observed_events"] == train_stop
            assert epoch["training"]["scored_events"] + epoch["training"]["empty_support_events"] == train_stop
        results = {}
        for regime in regimes:
            result, rows = cell["test"][regime], cell["test"][regime]["score_rows"]
            assert result["observed_events"] == stop
            assert len({r[0] for r in rows}) == len(rows)
            assert [[r[0], r[1], r[4]] for r in rows] == [[r[0], r[1], r[4]] for r in reference["test"][regime]["score_rows"]]
            assert all(start <= r[0] < stop and r[4] == (r[0] in inductive) for r in rows)
            expected = hashlib.sha256(json.dumps([[r[0], r[1]] for r in rows]).encode()).hexdigest()
            assert expected == result["candidate_sha256"]
            results[regime] = {}
            for cohort, members in cohorts.items():
                selected = [r for r in rows if r[0] in members]
                value = metrics([r[2:4] for r in selected])
                value["eligible_events"] = len(members)
                value["empty_support_events"] = len(members) - len(selected)
                results[regime][cohort] = value
                if cohort in ["all", "inductive"]:
                    recorded = result[cohort]
                    assert recorded["scored_events"] == value["events"]
                    assert recorded["eligible_events"] == value["eligible_events"]
                    assert recorded["empty_support_events"] == value["empty_support_events"]
                    for metric in ["ap", "auc"]:
                        assert (recorded[metric] is None and value[metric] is None) or math.isclose(recorded[metric], value[metric], rel_tol=0, abs_tol=1e-12)
        cell_metrics.append({"model": cell["model"], "seed": cell["seed"], "metrics": results})
    indexed = {(cell["model"], cell["seed"]): cell["metrics"] for cell in cell_metrics}
    aggregates = {}
    for regime in regimes:
        aggregates[regime] = {}
        for cohort, members in cohorts.items():
            summary = {name: {metric: mean_sd([indexed[(name, seed)][regime][cohort][metric] for seed in seeds])
                              for metric in ["ap", "auc"]} for name in models}
            for family in ["legacy", "bounded"]:
                paired = {}
                for metric in ["ap", "auc"]:
                    left = [indexed[(family + "-coupled", seed)][regime][cohort][metric] for seed in seeds]
                    right = [indexed[(family + "-decoupled", seed)][regime][cohort][metric] for seed in seeds]
                    paired[metric] = mean_sd([None if a is None or b is None else b - a for a, b in zip(left, right)])
                summary[family + "-paired-delta"] = paired
            selected = sorted(set(controls[regime]) & members)
            for control in ["recurrence", "recency"]:
                summary[control] = metrics([controls[regime][i][control] for i in selected])
            aggregates[regime][cohort] = {"eligible_events": len(members), "scored_events": len(selected), "models": summary}
    return {"dataset": report["dataset"], "audit": "PASS", "cells": cell_metrics, "aggregates": aggregates}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("attempts", nargs=2, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--jobs", required=True, help="all relevant attempts, including failures, for native sacct preservation")
    args = parser.parse_args()
    if not os.environ.get("SLURM_JOB_ID", "").isdigit() or "login" in socket.gethostname().lower():
        parser.error("reconciliation requires Slurm compute allocation")
    reports = [json.loads(path.read_text()) for path in args.attempts]
    assert {r["dataset"] for r in reports} == {"wikipedia", "mooc"}
    assert len({r["source_commit"] for r in reports}) == 1
    assert all(r["protocol"] == reports[0]["protocol"] and r["upstream"] == reports[0]["upstream"] for r in reports)
    accounting = subprocess.check_output(["sacct", "-j", args.jobs, "--format=JobID,State,ExitCode,Elapsed,AllocCPUS,NodeList,MaxRSS", "-P"], text=True)
    records = {row.split("|")[0]: row.split("|") for row in accounting.splitlines()[1:]}
    for report in reports:
        key = report["scheduler"]["SLURM_ARRAY_JOB_ID"] + "_" + report["scheduler"]["SLURM_ARRAY_TASK_ID"]
        assert records[key][1:3] == ["COMPLETED", "0:0"]
    summary = {"kind": "reconciled-development-matrix", "publication_eligible": False,
               "interpretation": "descriptive paired seed variation on previously inspected prefixes; no significance or confirmatory claim",
               "job_id": os.environ["SLURM_JOB_ID"], "reconciler_sha256": sha(Path(__file__)),
               "source_commit": reports[0]["source_commit"],
               "input_reports": {r["dataset"]: sha(p) for r, p in zip(reports, args.attempts)},
               "datasets": [audit(report) for report in reports]}
    args.output_dir.mkdir(parents=True, exist_ok=False)
    for report, path in zip(reports, args.attempts):
        shutil.copyfile(path, args.output_dir / (report["dataset"] + "-development.json"))
    (args.output_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n")
    (args.output_dir / "slurm-accounting.tsv").write_text(accounting)
    files = sorted(args.output_dir.iterdir())
    (args.output_dir / "checksums.sha256").write_text("".join(sha(path) + "  " + path.relative_to(ROOT).as_posix() + "\n" for path in files))
    print("PASS: complete matrix, source identities, candidates, coverage, metrics and paired seed summaries; no evidence admission.")
    for dataset in summary["datasets"]:
        for regime in ["random", "historical"]:
            print(dataset["dataset"], regime, json.dumps(dataset["aggregates"][regime]["all"]))


if __name__ == "__main__":
    main()
