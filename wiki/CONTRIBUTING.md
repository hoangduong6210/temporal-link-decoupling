---
title: Contributing
status: canonical governance
last_updated: 2026-10-02
paper_source: false
---

# Contributing

Read [Start Here](START-HERE.md), the project status, claim language, and
evidence ledger before changes. Keep reusable implementation under `src/`, thin
study entry points under `experiments/`, and authoritative parameters under
`configs/` or `protocols/`. Do not import from a sibling project. Update
[Project Status](status/Project-Status.md) when blockers or scientific state
change. New wiki pages require front matter and an [Index](INDEX.md) entry.

## Authoring and compute rules

The canonical `wiki/` is the knowledge foundation. Update methods, interpretation,
evidence and claim status here before deriving paper content. The active journal
sequence is JIIS → KAIS → IJMLC; use the
[JIIS development plan](manuscript/JIIS-Journal.md).

No solving or heavy execution on login nodes. Submit training, evaluation,
dataset rebuilds, substantial validation and rendering through Slurm. Login
nodes are for editing, lightweight inspection, Git and scheduler operations.
Never put credentials or machine-specific absolute paths into public files.

## Working with recovered material

Use `scripts/verify_recovered_evidence.py` after moving or inspecting historical files. Preserve original bytes, duplicate aliases, older variants and known discrepancies. Record a derived correction separately; do not rewrite a recovered result to match manuscript text. Current scientific runs continue to use the registered runner and scheduler.
