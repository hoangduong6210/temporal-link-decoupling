---
title: Decision 0001 - Separate link prediction and lifecycle readout
status: accepted
date: 2026-08-19
paper_source: false
---

# DEC-0001 — Separate link prediction and lifecycle readout

## Context

Independent paper scopes shared a mutable implementation and evidence tree.
That prevented project-local namespaces, pointers, and claim admission rules.

## Options considered

1. Keep the mixed tree and distinguish studies only by documentation.
2. Share a mutable sibling runtime between the project roots.
3. Create independent roots with temporarily duplicated, checksum-listed runtime
   closures while preserving the mixed source as migration history.

## Decision

Adopt the independent-root option. Create a link-prediction root with a copied,
checksum-listable runtime closure. Do not import or symlink a sibling project.
Preserve the mixed source tree until parity and evidence audits complete.

## Scientific consequences

- The split changes artifact ownership, not a scientific conclusion.
- Legacy numerical artifacts and paper prose remain QUARANTINED.
- A new result requires `LP-P-DECOUPLING-001`, complete execution accounting, a
  frozen evidence release, and explicit claim review.
- Temporary runtime duplication creates drift risk controlled by manifests and tests.

## Evidence and affected IDs

- Runtime migration record: `LP-E-RUNTIME-MIGRATION-001`.
- Data migration record: `LP-E-DATA-MIGRATION-001`.
- Quarantined legacy records: `LP-E-LEGACY-RESULTS-001` and
  `LP-E-LEGACY-PAPER-001`.
- All `LP-RQ-*`, `LP-D-*`, `LP-P-*`, and `LP-C-*` objects are project-local.

## Supersedes / superseded by

Supersedes no earlier link-prediction decision record. Superseded by: none.
A later change must create a new decision and link both records; this accepted
record is not edited to rewrite the historical choice.
