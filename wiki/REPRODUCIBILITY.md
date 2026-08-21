---
title: Reproducibility Contract
status: canonical contract
last_updated: 2026-08-20
paper_source: false
---

# Reproducibility Contract

A release must pin source commit, protocol/config hashes, dependency lock,
dataset manifest and checksums, complete seed/task coverage, failures,
aggregation code, result checksums, and claim mappings. Mutable work goes to
`results/audit/`; immutable releases go to `results/frozen/<release-id>/` and
must never be edited. `results/CURRENT`, `PROJECT.toml`, the evidence ledger,
and a paper `results.lock.yaml` must agree before export.

The machine-readable assessment is `REPRODUCIBILITY.toml`. It is currently
`BLOCKED` only at the execution/release layer: the project has a committed
baseline, but still needs a fresh scheduler matrix, a frozen evidence release,
and an immutable paper snapshot.

The first fresh execution was not admitted. It exposed duplicate node-memory
commits and a temporal comparator registry containing simplified proxies. The
corrective protocol amendment now defines stable last-row memory commits,
fail-closed finite checks, and removes proxy tasks from the publication matrix.
All affected outputs remain in scheduler history as excluded attempts; every
registered SR-GNN task profile must run again from the corrective commit.

The foundation is now fail-closed. Upstream raw bytes and processed corpora are
checksum-pinned; acquisition is explicit and deterministic; data rights use a
fetch-only/no-redistribution policy where no redistribution grant was found.
The runner consumes a checksum-owned protocol, configuration, task profile, and
hashed transitive dependency lock. It restores model, optimizer, temporal
store, and random state after warmup. Scheduler output records the source,
submission script, CUDA runtime, accelerator UUID, PCI identity, driver,
environment digest, task coverage, and failures.

The active dataset loader is fail-closed: it neither downloads nor preprocesses
implicitly, rejects non-finite or non-chronological arrays and overlapping
bipartite IDs, and rejects bytes that disagree with `resources/manifest.toml`.
The explicit builders have also reproduced all current corpus bytes from the
registered raw inputs in a clean staging tree.

`scripts/reconcile_scientific_matrix.py` retains retry/failure/exclusion history,
requires a successful final attempt for every protocol cell, and reconstructs
all aggregates from retained per-seed rows using sample standard deviation.
`scripts/freeze_evidence_release.py` and `scripts/build_paper_snapshot.py` refuse
partial matrices, stale hashes, mutable artifacts, and unclassified numeric
occurrences.

Run `python scripts/audit_scientific_provenance.py --check-canonical` to verify
the current fail-closed state. Use `--require-release` only in a publication
pipeline; it must fail while release readiness is blocked.
