"""Reproduce P003 descriptive validation tables from a reconciled summary on Slurm."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import socket
import statistics


def formatted(value, scale=1.):
    if value["mean"] is None:
        return "unavailable"
    return f"{scale * value['mean']:.4f} ± {scale * value['sample_sd']:.4f}"


def render(summary):
    assert summary["kind"] == "reconciled-validation-diagnostics"
    assert summary["publication_eligible"] is False and summary["test_evaluated"] is False
    lines = ["# Validation-only diagnostic results", "",
             "Development records only. No test events are evaluated. Primary values use the fixed final epoch. Means ± sample SD describe the registered training seeds, not confidence intervals. Selected-checkpoint results remain separately labeled in the JSON summary.", ""]
    for cohort in ["all", "inductive"]:
        lines += ["## Final-epoch validation: " + cohort, "",
                  "| Dataset | Negatives | Scored / eligible | Training | Model | AP | AUC |",
                  "|---|---|---:|---|---|---:|---:|"]
        for dataset in summary["datasets"]:
            assert dataset["audit"] == "PASS" and len(dataset["cells"]) == 18
            for regime in ["random", "historical", "novel-pair"]:
                result = dataset["aggregates"][regime][cohort]
                for policy in ["random", "mixed"]:
                    for model in ["bounded-coupled", "bounded-decoupled", "tgn"]:
                        values = result["primary"][model + "/" + policy]
                        lines.append(f"| {dataset['dataset']} | {regime} | {result['scored_events']} / {result['eligible_events']} | {policy} | {model} | {formatted(values['ap'])} | {formatted(values['auc'])} |")
        lines.append("")
    lines += ["## Paired routing and sampling interaction", "",
              "Routing is decoupled minus coupled; interaction is mixed routing minus random routing. Values are AP percentage points, paired within seed. The interaction does not by itself show that either model improves in absolute terms.", "",
              "| Dataset | Negatives | Cohort | Random routing Δ | Mixed routing Δ | Interaction | Interaction by seed |",
              "|---|---|---|---:|---:|---:|---|"]
    for dataset in summary["datasets"]:
        for regime in ["random", "historical", "novel-pair"]:
            for cohort in ["all", "inductive"]:
                result = dataset["aggregates"][regime][cohort]["contrasts"]
                values = result["sampling-by-routing-ap"]
                per_seed = ", ".join("unavailable" if v is None else f"{100 * v:.4f}" for v in values["values"])
                lines.append(f"| {dataset['dataset']} | {regime} | {cohort} | {formatted(result['random-routing-ap'], 100)} | {formatted(result['mixed-routing-ap'], 100)} | {formatted(values, 100)} | {per_seed} |")
    lines += ["", "## Final-epoch shared-transformation gradient probes", "",
              "Norms are means over the registered probes pooled across training seeds. The negative-cosine fraction uses only probes with both norms nonzero. These are descriptive accumulation increments, with floating-point subtraction limits; no causal interpretation or independent-sample inference is made.", "",
              "| Dataset | Training | Model | Module | Mean prediction norm | Mean auxiliary increment norm | Defined cosine probes | Negative cosine fraction |",
              "|---|---|---|---|---:|---:|---:|---:|"]
    for dataset in summary["datasets"]:
        for policy in ["random", "mixed"]:
            for model in ["bounded-coupled", "bounded-decoupled"]:
                cells = [c for c in dataset["cells"] if c["policy"] == policy and c["model"] == model]
                for group in ["csn", "context", "drgc"]:
                    values = [p["groups"][group] for cell in cells for p in cell["final_training"]["gradient_diagnostics"]]
                    cosines = [v["cosine"] for v in values if v["cosine"] is not None]
                    fraction = f"{sum(v < 0 for v in cosines) / len(cosines):.4f}" if cosines else "undefined"
                    lines.append(f"| {dataset['dataset']} | {policy} | {model} | {group} | {statistics.mean(v['prediction_norm'] for v in values):.6g} | {statistics.mean(v['auxiliary_increment_norm'] for v in values):.6g} | {len(cosines)} / {len(values)} | {fraction} |")
    lines += ["", "## Decoder movement and sensitivity", "",
              "Each row is a trained cell. These measurements describe the unchanged bounded initialization; they do not test an alternative initialization or prove saturation caused poor ranking.", "",
              "| Dataset | Training | Model | Seed | Max absolute log-odds displacement | Min final sigmoid slope | Max decoder gradient RMS |",
              "|---|---|---|---:|---:|---:|---:|"]
    for dataset in summary["datasets"]:
        for cell in dataset["cells"]:
            if cell["final_decoder"] is not None:
                decoder = cell["final_decoder"]
                lines.append(f"| {dataset['dataset']} | {cell['policy']} | {cell['model']} | {cell['seed']} | {max(abs(v) for v in decoder['log_odds_displacement']):.6g} | {min(decoder['sigmoid_slopes']):.6g} | {max(cell['final_training']['decoder_gradient_rms']):.6g} |")
    lines += ["", "## Deterministic controls", "",
              "Repeated/new-positive and shared-support controls are also available in the summary.", "",
              "| Dataset | Negatives | Cohort | Control | AP | AUC |",
              "|---|---|---|---|---:|---:|"]
    for dataset in summary["datasets"]:
        for regime in ["random", "historical", "novel-pair"]:
            for cohort in ["all", "inductive"]:
                for name, result in dataset["aggregates"][regime][cohort]["controls"].items():
                    ap = "unavailable" if result["ap"] is None else f"{result['ap']:.4f}"
                    auc = "unavailable" if result["auc"] is None else f"{result['auc']:.4f}"
                    lines.append(f"| {dataset['dataset']} | {regime} | {cohort} | {name} | {ap} | {auc} |")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if not os.environ.get("SLURM_JOB_ID", "").isdigit() or "login" in socket.gethostname().lower():
        parser.error("table reproduction requires Slurm compute allocation")
    content = render(json.loads(args.summary.read_text()))
    if args.check:
        if args.output.read_text() != content:
            parser.error("archived tables differ from the audited summary")
        print("PASS: diagnostic tables exactly reproduce the audited summary")
    else:
        with args.output.open("x") as handle:
            handle.write(content)


if __name__ == "__main__":
    main()
