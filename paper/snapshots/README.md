# Immutable conference-paper snapshots

The active snapshot is `LP-SNAP-2026-CONFERENCE-003`. Earlier snapshots remain
immutable and may be superseded only by advancing the pointer through a reviewed
snapshot plan.

Each future `<snapshot-id>/` must contain `snapshot.toml`,
`results.lock.yaml`, `numeric-provenance.jsonl`, `checksums.sha256`, all declared
source files, and every rendered export. The manifest must bind the snapshot to
one frozen result release, a clean source/wiki commit, and a paper-build job.

`numeric-provenance.jsonl` inventories every numeric occurrence in every paper
source. Scientific, protocol, and derived values require a claim ID, evidence
ID, execution-job ID, artifact checksum, and artifact selector. Structural
tokens require one narrow documented exemption. Numeric figure labels require
a checksum-locked sidecar inventory and the plot job that generated the figure.

Snapshots cannot import from `paper/working/`, top-level `paper/figs/`,
`figures/generated/`, `results/audit/`, or `results/historical/`.
