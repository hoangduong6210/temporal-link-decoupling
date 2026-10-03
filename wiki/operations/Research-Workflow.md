---
title: Research Workflow
status: canonical operations
last_updated: 2026-10-02
paper_source: false
---

# Research Workflow

```text
question -> frozen protocol -> scheduler execution -> complete attempts
-> schema/seed/failure audit -> immutable release -> evidence entry
-> scoped claim review -> paper snapshot
```

All solving and heavy work is Slurm-only: training, evaluation, dataset rebuilds,
parameter searches, substantial analysis/tests and document rendering. Do not
execute these on a login node. Editing, lightweight metadata checks, Git and
scheduler operations may run there. Supply account, partition and environment
at submission time and retain the job identity and terminal accounting.

Failed and superseded attempts remain visible. No mutable artifact is copied
directly into a paper snapshot. A validation job does not create scientific
evidence or substitute for the registered scientific runner.

## Journal work

The active target is JIIS, followed by KAIS and IJMLC. Start with the
[JIIS plan](../manuscript/JIIS-Journal.md). Revise canonical wiki knowledge before
paper content; preserve `LP-REL-2026-A003-001` and register any new scientific
release separately. Do not submit a new training matrix solely because the
venue changed: first resolve the question, comparator and protocol amendment.

## Recovery before rerunning

Locate historical records, verify preservation hashes, reconstruct aggregates, compare configurations, and inspect source/data/execution bindings before deciding which experiments need rerunning. Preserve discrepancies as evidence. No new training was launched during recovery; archived scripts require adaptation and protocol review before use.
