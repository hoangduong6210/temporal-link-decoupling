---
title: Negative Sampling
status: current implementation and historical context
last_updated: 2026-10-02
paper_source: false
---

# Negative Sampling

The current admitted regime is fair-random-destination. The evaluator retains the positive source and samples a replacement destination from the seen or unseen pool corresponding to the true destination. It rejects the identical destination, not all contemporaneous positive pairs. Pools are not restricted to the destination endpoint type of bipartite corpora. Results are conditional on this candidate construction.

Inductive nodes are test nodes absent from training and validation. The test stream is filtered before the inductive evaluator executes; omitted test events do not update memory in that run. Training and validation are replayed for warmup. This differs from maintaining state on the complete test stream and only filtering scored outputs.

## Recovered harder-negative runs

Historical and inductive hard-negative records exist in the restored history. Preserve original and corrected variants separately. The retained field `indpool_from_train` has a legacy name; in corrected code it indicates availability of the test-only-pair pool. Interpret it with the corresponding code, not by its label alone. Paired candidate draws, target availability and pool support need explicit checks before historical claims can be admitted.
