"""Reproduce descriptive development tables from an audited summary on Slurm."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import socket


def formatted(value, multiplier=1.):
    if value['mean'] is None:
        return 'unavailable'
    return f"{multiplier * value['mean']:.4f} ± {multiplier * value['sample_sd']:.4f}"


def render(summary):
    lines = ['# Development results — not admitted publication evidence', '',
             'Derived from `matrix/summary.json`. Entries are means ± sample standard deviations across the registered training seeds; these are descriptive quantities, not confidence intervals or significance tests.', '',
             '## Test cohort before inductive filtering', '',
             '| Dataset | Negatives | Scored / eligible | Model | AP | AUC |',
             '|---|---|---:|---|---:|---:|']
    for dataset in summary['datasets']:
        assert dataset['audit'] == 'PASS' and len(dataset['cells']) == 15
        for regime in ['random', 'historical', 'novel-pair']:
            result = dataset['aggregates'][regime]['all']
            for model in ['legacy-coupled', 'legacy-decoupled', 'bounded-coupled', 'bounded-decoupled', 'tgn']:
                value = result['models'][model]
                lines.append(f"| {dataset['dataset']} | {regime} | {result['scored_events']} / {result['eligible_events']} | {model} | {formatted(value['ap'])} | {formatted(value['auc'])} |")
    lines += ['', '## Paired inductive AP differences', '',
              'Decoupled minus coupled, in percentage points. Seed order is the registered order. Negative values are retained.', '',
              '| Dataset | Negatives | Decoder | Mean ± sample SD (pp) | Per-seed differences (pp) |',
              '|---|---|---|---:|---|']
    for dataset in summary['datasets']:
        for regime in ['random', 'historical', 'novel-pair']:
            for family in ['legacy', 'bounded']:
                value = dataset['aggregates'][regime]['inductive']['models'][family + '-paired-delta']['ap']
                values = ', '.join('unavailable' if v is None else f'{100*v:.4f}' for v in value['values'])
                lines.append(f"| {dataset['dataset']} | {regime} | {family} | {formatted(value, 100)} | {values} |")
    lines += ['', '## Deterministic history controls', '',
              'Controls use the same candidates and metric rows. See the summary for repeated/new positive and shared-support cohorts.', '',
              '| Dataset | Negatives | Cohort | Scored / eligible | Control | AP | AUC |',
              '|---|---|---|---:|---|---:|---:|']
    for dataset in summary['datasets']:
        for regime in ['random', 'historical']:
            for cohort in ['all', 'repeated-positive', 'new-pair-positive']:
                result = dataset['aggregates'][regime][cohort]
                for model in ['recurrence', 'recency']:
                    value = result['models'][model]
                    ap = 'unavailable' if value['ap'] is None else f"{value['ap']:.4f}"
                    auc = 'unavailable' if value['auc'] is None else f"{value['auc']:.4f}"
                    lines.append(f"| {dataset['dataset']} | {regime} | {cohort} | {result['scored_events']} / {result['eligible_events']} | {model} | {ap} | {auc} |")
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--check", action="store_true", help="compare without replacing the archived table")
    args = parser.parse_args()
    if not os.environ.get("SLURM_JOB_ID", "").isdigit() or "login" in socket.gethostname().lower():
        parser.error("table reproduction requires a Slurm compute allocation")
    summary = json.loads(args.summary.read_text())
    assert summary["kind"] == "reconciled-development-matrix"
    assert summary["publication_eligible"] is False
    content = render(summary)
    if args.check:
        if args.output.read_text() != content:
            parser.error("archived table differs from the audited summary")
        print("PASS: archived tables exactly reproduce the audited summary")
    else:
        with args.output.open("x") as handle:
            handle.write(content)


if __name__ == "__main__":
    main()
