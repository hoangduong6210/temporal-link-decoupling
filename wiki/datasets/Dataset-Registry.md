---
title: Dataset Registry
status: canonical dataset registry
last_updated: 2026-08-21
paper_source: false
---

# Dataset Registry

## LP-D-COEDIT-002

- **Version and lifecycle:** current clean-acquisition derivative; candidate for a
  future frozen release.
- **Source and provenance:** Deterministically derived from `LP-D-WIKIPEDIA-003` by
  the checksum-pinned builder and parameters in `resources/source_registry.json`.
- **License and redistribution:** Fetch/build locally; dataset bytes are excluded
  from source releases under the project rights policy.
- **Checksum:** Owned by `resources/manifest.toml` and `resources/checksums.sha256`.
- **Population and geometry:** Homogeneous contributor co-edit event graph using
  a shared node namespace for both endpoint roles.
- **Inputs, targets, units, and fidelity:** NPZ schema is owned by
  [Data and Target Contract](Data-and-Target-Contract.md); the exact raw parent and
  transformation identity are machine-readable.
- **Inclusion, exclusion, and quality gates:** Builder settings, stable ordering,
  output digest, schema, finite-value, node-bound, and shared-space overlap
  checks are mandatory.
- **Split and leakage controls:** Owned by `LP-P-DECOUPLING-001`; execution-specific
  split and negative-pool identities must be captured by each scientific job.
- **Known defects:** No dataset redistribution grant is asserted.
- **Compatible claims:** none admitted until fresh current-corpus runs freeze.

## LP-D-WIKIPEDIA-003

- **Version and lifecycle:** current full upstream clean-acquisition identity;
  candidate for a future frozen release.
- **Source and provenance:** Exact HTTPS source, raw digest, retrieval metadata,
  builder mode, and processed digest are pinned in `resources/source_registry.json`.
- **License and redistribution:** Fetch-only from the registered public endpoint;
  dataset bytes are not redistributed.
- **Checksum:** Owned by `resources/manifest.toml` and `resources/checksums.sha256`.
- **Population and geometry:** Bipartite user/item stream with disjoint stored node
  namespaces.
- **Inputs, targets, units, and fidelity:** NPZ schema is owned by the data contract;
  event ordering and non-finite feature handling are explicit builder behavior.
- **Inclusion, exclusion, and quality gates:** Raw and processed digest, schema,
  finite-value, ID-range, namespace-disjointness, and chronological-order checks.
- **Split and leakage controls:** Owned by `LP-P-DECOUPLING-001` and captured by
  scientific job metadata.
- **Known defects:** No upstream redistribution license grant was identified.
- **Compatible claims:** technical ID-namespace validation; performance awaits fresh runs.

## LP-D-MOOC-003

- **Version and lifecycle:** current full upstream clean-acquisition identity;
  candidate for a future frozen release.
- **Source and provenance:** Exact HTTPS source, raw digest, retrieval metadata,
  builder mode, and processed digest are pinned in `resources/source_registry.json`.
- **License and redistribution:** Fetch-only from the registered public endpoint;
  dataset bytes are not redistributed.
- **Checksum:** Owned by `resources/manifest.toml` and `resources/checksums.sha256`.
- **Population and geometry:** Bipartite user/item stream with disjoint stored node
  namespaces.
- **Inputs, targets, units, and fidelity:** NPZ schema is owned by the data contract;
  event ordering and non-finite feature handling are explicit builder behavior.
- **Inclusion, exclusion, and quality gates:** Raw and processed digest, schema,
  finite-value, ID-range, namespace-disjointness, and chronological-order checks.
- **Split and leakage controls:** Owned by `LP-P-DECOUPLING-001` and captured by
  scientific job metadata.
- **Known defects:** No upstream redistribution license grant was identified.
- **Compatible claims:** technical ID-namespace validation; performance awaits fresh runs.

## Quarantined migration identities

`LP-D-COEDIT-001`, `LP-D-WIKIPEDIA-002`, and `LP-D-MOOC-002` are retained under
`resources/corpora/legacy_migration/`. They are the exact result-era processed
identities, but they are not interchangeable with the current clean-acquisition
corpora. Legacy AP artifacts cannot support claims about current corpora.

## LP-D-WIKIPEDIA-001

- **Version and lifecycle:** QUARANTINED pre-ID-fix local copy.
- **Source and provenance:** Historical predecessor of `LP-D-WIKIPEDIA-002`;
  exact upstream raw identity is UNKNOWN/BLOCKED.
- **License and redistribution:** UNKNOWN/BLOCKED.
- **Checksum:** Owned by `resources/manifest.toml` and `resources/checksums.sha256`.
- **Population and geometry:** Historical bipartite data with overlapping numeric
  user/item namespaces in the stored node IDs.
- **Inputs, targets, units, and fidelity:** Historical NPZ; units UNKNOWN.
- **Inclusion, exclusion, and quality gates:** Retained for migration audit only.
- **Split and leakage controls:** Not commensurable with ID-fixed cells.
- **Known defects:** Node-ID namespace defect plus unresolved provenance.
- **Compatible claims:** none; not current evidence.

## LP-D-MOOC-001

- **Version and lifecycle:** QUARANTINED pre-ID-fix local copy.
- **Source and provenance:** Historical predecessor of `LP-D-MOOC-002`; exact
  upstream raw identity is UNKNOWN/BLOCKED.
- **License and redistribution:** UNKNOWN/BLOCKED.
- **Checksum:** Owned by `resources/manifest.toml` and `resources/checksums.sha256`.
- **Population and geometry:** Historical bipartite data with overlapping numeric
  user/item namespaces in the stored node IDs.
- **Inputs, targets, units, and fidelity:** Historical NPZ; units UNKNOWN.
- **Inclusion, exclusion, and quality gates:** Retained for migration audit only.
- **Split and leakage controls:** Not commensurable with ID-fixed cells.
- **Known defects:** Node-ID namespace defect plus unresolved provenance.
- **Compatible claims:** none; not current evidence.

Pre-ID-fix identities remain quarantined under their original registry IDs. A
dataset can enter frozen evidence only through a scientific job that binds the
current source registry, processed checksum, resolved split, negative pools, and
complete environment record.
