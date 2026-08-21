---
title: Paper Export Contract
status: canonical contract
last_updated: 2026-08-21
paper_source: false
---

# Paper Export Contract

`paper/working/` is mutable and non-canonical. Export requires an admitted claim
set, current frozen evidence release, source wiki commit, figure hashes,
bibliography hash, toolchain identity, and `results.lock.yaml`. The resulting
`paper/snapshots/<snapshot-id>/` is immutable and `paper/CURRENT` is advanced
only after consistency tests pass.

Every snapshot must satisfy `paper/snapshots/README.md` and include a manifest,
results lock, checksum manifest, paper-build job, and complete per-occurrence
numeric registry. Every scientific value in prose, equations, tables, captions,
appendices, and figure labels must resolve to a Claim ID, Evidence ID, Job ID,
artifact checksum, and artifact selector. Structural numbers require an explicit
narrow exemption; omission is not an exemption.

The selector must resolve to a finite scalar inside a checksum-owned artifact
that belongs to the declared scientific job. The registry must declare exact
equality or an explicit decimal precision and rounding rule. Both the snapshot
builder and canonical auditor independently recompute the assertion; neither
trusts builder-authored audit fields.

The export allowlist excludes `paper/working/`, top-level `paper/figs/`,
`figures/generated/`, mutable audit results, and historical results. Current
working exports remain unsafe to submit. A submission package must use the
checksum-bound PDF and self-contained Overleaf archive inside the active
snapshot. The active pointer is `LP-SNAP-2026-CONFERENCE-005`; it remains
publishable only while
`python scripts/audit_scientific_provenance.py --require-release` succeeds.
