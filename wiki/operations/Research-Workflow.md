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

Heavy training is scheduler-only. Failed and superseded attempts remain visible.
No mutable artifact is copied directly into a paper snapshot.

## Recovery before rerunning

Locate historical records, verify preservation hashes, reconstruct aggregates, compare configurations, and inspect source/data/execution bindings before deciding which experiments need rerunning. Preserve discrepancies as evidence. No new training was launched during recovery; archived scripts require adaptation and protocol review before use.
