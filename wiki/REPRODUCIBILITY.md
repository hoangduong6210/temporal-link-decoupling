---
title: Reproducibility Contract
status: canonical contract
last_updated: 2026-08-21
paper_source: false
---

# Reproducibility Contract

A release must pin source commit, protocol/config hashes, dependency lock,
dataset manifest and checksums, complete seed/task coverage, failures,
aggregation code, result checksums, and claim mappings. Mutable work goes to
`results/audit/`; immutable releases go to `results/frozen/<release-id>/` and
must never be edited. `results/CURRENT`, `PROJECT.toml`, the evidence ledger,
and a paper `results.lock.yaml` must agree before export.

The machine-readable assessment is `REPRODUCIBILITY.toml`. The fresh scheduler
matrix, attempt reconciliation, and frozen evidence release are complete. Paper
release readiness is blocked while `paper/CURRENT` is `UNRELEASED`. The
canonical audit reopens the scientific gate if any pointer, checksum, job
ownership, wiki commit, numeric selector, or rounded literal drifts.

The first fresh execution was not admitted. It exposed duplicate node-memory
commits and a temporal comparator registry containing simplified proxies. The
corrective protocol amendment now defines stable last-row memory commits,
fail-closed finite checks, and removes proxy tasks from the publication matrix.
All affected outputs retain native scheduler state while scientific
admissibility and aggregate selection are recorded separately; every registered
SR-GNN task profile must run again from the corrective commit.

The next campaign also remains inadmissible. It failed closed because a global
bipartite-ID invariant was incorrectly applied to the intentionally homogeneous
CoEdit graph; pending work was cancelled once the defect was isolated. Amendment
`LP-P-DECOUPLING-001-A003` replaces that boolean with checksum-owned per-dataset
topology classes. Native scheduler outcomes remain in
`LP-E-SCHEDULER-HISTORY-001`; no affected output can be selected.

The resolved default configuration carried `SCIENTIFIC-FROZEN` before the
replacement execution. The pre-freeze campaign was stopped and retained as
inadmissible rather than changing configuration metadata after seeing a final
matrix. The terminal current campaign binds its clean source commit, resolved
protocol/configuration, task profile, datasets, dependency lock, accelerator
environment, selected parent results, and native Slurm accounting.

The foundation is now fail-closed. Upstream raw bytes and processed corpora are
checksum-pinned; acquisition is explicit and deterministic; data rights use a
fetch-only/no-redistribution policy where no redistribution grant was found.
The runner consumes a checksum-owned protocol, configuration, task profile, and
hashed transitive dependency lock. It restores model, optimizer, temporal
store, and random state after warmup. Scheduler output records the source,
submission script, CUDA runtime, accelerator UUID, PCI identity, driver,
environment digest, task coverage, and failures.

The active dataset loader is fail-closed: it neither downloads nor preprocesses
implicitly, rejects non-finite or non-chronological arrays, enforces the
registered per-dataset topology, and rejects bytes that disagree with
`resources/manifest.toml`.
The explicit builders have also reproduced all current corpus bytes from the
registered raw inputs in a clean staging tree.

`scripts/reconcile_scientific_matrix.py` retains failed, cancelled, completed,
and quarantined attempts; checksum-binds an explicit selected attempt per
protocol cell; and reconstructs all aggregates from retained per-seed rows using
sample standard deviation. `LP-E-SCIENTIFIC-MATRIX-001` records the complete
result and `LP-JOB-SLURM-A003-FINAL-RECONCILE-R2` owns its execution identity.
`scripts/freeze_evidence_release.py` and `scripts/build_paper_snapshot.py` refuse
partial matrices, stale hashes, mutable artifacts, and unclassified numeric
occurrences.

Run `python scripts/audit_scientific_provenance.py --check-canonical` to verify
the current fail-closed state. Publication pipelines use `--require-release`,
which additionally requires the reproducible status and immutable pointers.
