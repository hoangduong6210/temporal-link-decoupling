---
title: Research System Map
status: canonical architecture
last_updated: 2026-10-02
paper_source: false
---

# Research System Map

```text
corpus manifest -> chronological split -> coupled/decoupled training
                -> paired negative evaluation -> per-seed artifacts
                -> completeness audit -> frozen release
                -> evidence ledger -> reviewed claim -> paper snapshot
```

The v3.3 implementation closure is internal to this project. Historical
lifecycle machinery inside the pinned model is an implementation dependency,
not a second research claim or a sibling-project dependency.

## Historical and current execution paths

Current executable code remains under `src/` and current experiment entry points under `experiments/`. Recovered result bytes live under `results/recovered/`. The scripts under `evidence/source-archives/legacy-v33/` are interpretation context with old imports; they are not active replacements for the registered runners. Recovery metadata lives under `evidence/recovered/`.
