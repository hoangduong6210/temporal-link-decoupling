---
title: Research System Map
status: canonical architecture
last_updated: 2026-08-19
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
