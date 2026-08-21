# Protocol amendment LP-P-DECOUPLING-001-A003

Status: accepted before replacement confirmatory execution.

## Trigger

Campaign `LP-CAM-A002-20260820` revealed that the disjoint bipartite namespace
contract had been applied to every corpus. The first three CoEdit cells failed
closed; the remaining cells and reconciliation job were cancelled. Their native
scheduler states and exact source/protocol/data/environment bindings remain in
the checksum-bound scheduler history and are ineligible for aggregation.

The parent SR-GNN preprocessing source and the current deterministic builders
show two distinct dataset topologies: JODIE Wikipedia/MOOC are user-to-item
bipartite streams whose independent namespaces must be disjoint after remapping;
CoEdit is intentionally a user-to-user graph in one shared node namespace.

## Corrective decisions

- Dataset topology is now an explicit checksum-owned protocol and resource-
  manifest field, not a global boolean.
- Wikipedia and MOOC must have no node ID occurring in both endpoint roles.
- CoEdit must have valid node bounds and a non-empty source/destination overlap,
  which confirms use of the registered shared node space.
- A mismatch between protocol topology and the current resource manifest fails
  configuration resolution before training.
- All A002 campaign outputs remain `INADMISSIBLE`, including any cell whose
  scheduler state is `COMPLETED`, `FAILED`, or `CANCELLED`.
- The complete scientific matrix must be rerun from one clean post-amendment
  commit. No A002 attempt may be selected for an aggregate.

## Evidence consequence

This amendment changes validation scope only; it does not change corpus bytes,
study datasets, seeds, splits, model arms, optimization, metrics, or selection
rules. A frozen evidence release and conference snapshot remain blocked until
the replacement matrix and full attempt ledger pass the release gates.
