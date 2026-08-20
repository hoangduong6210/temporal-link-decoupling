---
title: Paper Export Contract
status: canonical contract
last_updated: 2026-08-19
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

The export allowlist excludes `paper/working/`, top-level `paper/figs/`,
`figures/generated/`, mutable audit results, and historical results. Current
DOCX/ZIP working exports lack visible quarantine text and are unsafe to submit.
`paper/CURRENT` must remain `UNRELEASED` until
`python scripts/audit_scientific_provenance.py --require-release` succeeds.
