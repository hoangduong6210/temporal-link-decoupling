"""Reconstruct pilot metrics and audit candidates against the full prefix history.

Run on a Slurm compute node with the registered corpora available. Derived
recurrence/recency controls are exploratory diagnostics, never admitted claims.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
import math
import os
from pathlib import Path
import socket
import subprocess

import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score

from temporal_link_decoupling.datasets import load_dataset

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "evidence/development/LP-P-PROSPECTIVE-001"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def metrics(rows):
    if not rows:
        return {"events": 0, "ap": None, "auc": None}
    scores = np.asarray(rows, dtype=float).reshape(-1)
    assert np.isfinite(scores).all()
    labels = np.tile([1, 0], len(rows))
    return {"events": len(rows), "ap": float(average_precision_score(labels, scores)),
            "auc": float(roc_auc_score(labels, scores))}


def review(path):
    report = json.loads(path.read_text())
    assert report["status"] == "COMPLETED_TECHNICAL_PILOT"
    assert report["publication_eligible"] is False and report["source_clean"] is True
    for relative, expected in report["input_sha256"].items():
        source = subprocess.check_output(["git", "show", report["source_commit"] + ":" + relative], cwd=ROOT)
        assert hashlib.sha256(source).hexdigest() == expected, relative
    data = load_dataset(report["dataset"])
    assert sha(ROOT / "resources/corpora" / (report["dataset"] + ".npz")) == report["data"]["source_npz_sha256"]
    stop = report["data"]["prefix_events"]
    assert len(data["sources"]) == report["data"]["source_events"]
    catalogue = set(map(int, data["destinations"]))
    assert len(catalogue) == report["data"]["catalogue_size"]
    times = data["timestamps"][:stop]
    src, dst = data["sources"][:stop], data["destinations"][:stop]
    train_stop = report["data"]["splits"]["train"][1]
    start, test_stop = report["data"]["splits"]["test"]
    assert test_stop == stop
    assert report["data"]["splits"] == {"train": [0, train_stop],
        "validation": [train_stop, start], "test": [start, stop]}
    for boundary in [train_stop, start, stop]:
        if boundary < len(data["timestamps"]):
            assert data["timestamps"][boundary - 1] < data["timestamps"][boundary]
    training = defaultdict(set)
    for s, d in zip(src[:train_stop], dst[:train_stop]):
        training[int(s)].add(int(d))
    seen_nodes = set(src[:start]) | set(dst[:start])
    unseen = (set(src[start:]) | set(dst[start:])) - seen_nodes
    inductive = {i for i in range(start, stop) if src[i] in unseen or dst[i] in unseen}
    left, right = report["arms"]
    assert [left["arm"], right["arm"]] == ["coupled", "decoupled"]
    assert left["initial_weights_sha256"] == right["initial_weights_sha256"]
    regimes = ["random", "historical", "novel-pair"]
    maps = {}
    for arm in report["arms"]:
        maps[arm["arm"]] = {}
        assert arm["unseen_nodes"] == len(unseen)
        for regime in regimes:
            result = arm["test"][regime]
            rows = result["score_rows"]
            maps[arm["arm"]][regime] = {row[0]: row for row in rows}
            assert len(maps[arm["arm"]][regime]) == len(rows)
            assert all(start <= row[0] < stop and row[4] == (row[0] in inductive) for row in rows)
            assert result["observed_events"] == stop
            candidate_hash = hashlib.sha256(json.dumps([[r[0], r[1]] for r in rows]).encode()).hexdigest()
            assert candidate_hash == result["candidate_sha256"] == left["test"][regime]["candidate_sha256"]
            for cohort, selected, eligible in [
                ("all", rows, stop - start),
                ("inductive", [r for r in rows if r[4]], len(inductive)),
            ]:
                actual = metrics([r[2:4] for r in selected])
                recorded = result[cohort]
                assert recorded["eligible_events"] == eligible
                assert recorded["scored_events"] == actual["events"]
                assert recorded["empty_support_events"] == eligible - actual["events"]
                for key in ["ap", "auc"]:
                    if actual[key] is None:
                        assert recorded[key] is None
                    else:
                        assert math.isclose(actual[key], recorded[key], rel_tol=0, abs_tol=1e-12)
    previous = defaultdict(dict)
    repeated, controls = set(), {regime: {} for regime in regimes}
    # Independent history audit: inspect each whole timestamp before updating it.
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
                               catalogue - training[s] if regime == "novel-pair" else catalogue)
                    support = support - positives[s]
                    row = maps["coupled"][regime].get(i)
                    assert (row is not None) == bool(support), (regime, i, "support mismatch")
                    if row is None:
                        continue
                    assert row[1] in support, (regime, i, "invalid negative")
                    assert maps["decoupled"][regime][i][1] == row[1]
                    pair = [d, row[1]]
                    controls[regime][i] = {
                        "recurrence": [float(node in history) for node in pair],
                        # Never-observed pairs rank below every observed pair at this query time.
                        "recency": [history.get(node, float(times[0]) - 1.) - t for node in pair],
                    }
        for i in range(begin, end):
            previous[int(src[i])][int(dst[i])] = float(times[i])
    shared = set.intersection(*(set(maps["coupled"][regime]) for regime in regimes))
    cohorts = {"all": set(range(start, stop)), "inductive": inductive,
               "repeated-positive": repeated, "new-pair-positive": set(range(start, stop)) - repeated,
               "shared-regime-support": shared}
    diagnostics = {}
    for regime in regimes:
        diagnostics[regime] = {}
        for cohort, members in cohorts.items():
            indices = sorted(members & set(controls[regime]))
            models = {arm: metrics([maps[arm][regime][i][2:4] for i in indices])
                      for arm in maps}
            models.update({name: metrics([controls[regime][i][name] for i in indices])
                           for name in ["recurrence", "recency"]})
            diagnostics[regime][cohort] = {"eligible_events": len(members), "models": models}
    return {"dataset": report["dataset"], "pilot_sha256": sha(path),
            "source_commit": report["source_commit"], "audit": "PASS",
            "diagnostics": diagnostics}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="write a new derived report; never overwrite")
    args = parser.parse_args()
    if not os.environ.get("SLURM_JOB_ID", "").isdigit() or "login" in socket.gethostname().lower():
        parser.error("review requires a Slurm compute-node allocation")
    for line in (BUNDLE / "checksums.sha256").read_text().splitlines():
        expected, relative = line.split(maxsplit=1)
        path = (ROOT / relative).resolve()
        assert path.is_relative_to(ROOT) and sha(path) == expected, relative
    result = {"kind": "exploratory-pilot-review", "publication_eligible": False,
              "review_script_sha256": sha(Path(__file__)), "job_id": os.environ["SLURM_JOB_ID"],
              "recency_definition": "last observed pair timestamp minus query time; unseen uses first stream timestamp minus one",
              "datasets": [review(BUNDLE / (name + "-pilot.json")) for name in ["wikipedia", "mooc"]]}
    if args.output:
        with args.output.open("x") as stream:
            stream.write(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
    for dataset in result["datasets"]:
        print(dataset["dataset"], dataset["audit"])
        for regime in ["random", "historical"]:
            for cohort in ["all", "repeated-positive", "new-pair-positive"]:
                print(regime, cohort, dataset["diagnostics"][regime][cohort])


if __name__ == "__main__":
    main()
