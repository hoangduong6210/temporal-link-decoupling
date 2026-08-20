---
title: Evidence Ledger
status: canonical evidence ledger
last_updated: 2026-08-20
paper_source: false
---

# Evidence Ledger

Current evidence release: `UNRELEASED`. No entry below is frozen scientific evidence.

## LP-E-DATA-MIGRATION-001

- **Scientific purpose:** Verify local corpus identities and disjoint bipartite ID
  namespaces after migration.
- **Lifecycle:** VALIDATED for local migration integrity; not ADMITTED.
- **Source commit:** UNKNOWN; the split tree has no frozen release commit.
- **Protocol, configuration, and data hashes:** Dataset and upstream raw-file
  hashes are owned by `resources/manifest.toml`, `resources/checksums.sha256`,
  and `resources/source_registry.json`.
- **Execution identity:** `LP-JOB-LOCAL-20260819-001`, recorded at
  `evidence/jobs/LP-JOB-LOCAL-20260819-001.toml`; local execution, not a scheduler
  or frozen-release job.
- **Artifact path or release URI:** `resources/manifest.toml`,
  `resources/checksums.sha256`, and local ignored files under `resources/corpora/`.
- **Artifact checksum:** Dataset bytes are declared in `resources/checksums.sha256`;
  the execution record is pinned by `evidence/jobs/checksums.sha256`. No frozen-
  release checksum manifest exists.
- **Coverage and failures:** Current corpora were rebuilt deterministically from
  registered raw inputs in clean staging and matched their declared digests.
- **Acceptance-gate outcome:** Schema/hash/ID-disjointness, upstream digest, and
  clean-acquisition gates PASS; evidence release remains BLOCKED.
- **Supported claim IDs:** `LP-C-IDFIX-001` at VALIDATED technical status only.
- **Rejected claim IDs:** none.
- **Scientific-use boundary:** Dataset migration integrity only; no performance or
  paper-eligible conclusion.

## LP-E-RUNTIME-MIGRATION-001

- **Scientific purpose:** Detect drift in the copied runtime closure.
- **Lifecycle:** VALIDATED for local code-copy integrity; not ADMITTED.
- **Source commit:** UNKNOWN; no frozen release commit.
- **Protocol, configuration, and data hashes:** Runtime files are owned by
  `configs/shared-runtime.sha256`; the frozen protocol, resolved configuration,
  dataset manifests, and scientific dependency lock are checksum-bound.
- **Execution identity:** `LP-JOB-LOCAL-20260819-001`, recorded at
  `evidence/jobs/LP-JOB-LOCAL-20260819-001.toml`; local execution, not a scheduler
  or frozen-release job.
- **Artifact path or release URI:** `src/` and `configs/shared-runtime.sha256`.
- **Artifact checksum:** Per-file SHA-256 values are in
  `configs/shared-runtime.sha256`; the execution record is pinned by
  `evidence/jobs/checksums.sha256`. No release-level checksum exists.
- **Coverage and failures:** Runtime files, exact transitive environment, task
  profiles, state-neutral warmup, and fail-closed scheduler metadata were tested.
- **Acceptance-gate outcome:** Runtime and runner contract gates PASS; fresh
  scheduler execution and frozen-release gates remain BLOCKED.
- **Supported claim IDs:** none.
- **Rejected claim IDs:** none.
- **Scientific-use boundary:** Code-copy integrity only.

## LP-E-LEGACY-RESULTS-001

- **Scientific purpose:** Preserve pre-split result artifacts for future audit.
- **Lifecycle:** QUARANTINED.
- **Source commit:** UNKNOWN.
- **Protocol, configuration, and data hashes:** Historical bindings are incomplete
  and cannot be reconciled to the current data/protocol chain.
- **Execution identity:** Surviving scheduler identities, artifacts, retries,
  terminal failures, and unknown fields are normalized in
  `results/historical/legacy_import/execution_reconciliation.json`.
- **Artifact path or release URI:** `results/historical/legacy_import/`.
- **Artifact checksum:** Local preservation hashes are in
  `results/historical/legacy_import/checksums.sha256`; no frozen release checksum.
- **Coverage and failures:** The retained legacy attempt matrix records completed,
  failed, timed-out, cancelled, inferred, and missing states without inventing
  absent evidence.
- **Acceptance-gate outcome:** REJECTED for current scientific use; no historical
  performance artifact closes source/data/environment provenance.
- **Supported claim IDs:** none at ADMITTED status.
- **Rejected claim IDs:** none registered; unaudited artifacts do not reject claims.
- **Scientific-use boundary:** Audit input only; not current or paper evidence.

## LP-E-LEGACY-PAPER-001

- **Scientific purpose:** Preserve the pre-split link-prediction working paper.
- **Lifecycle:** QUARANTINED.
- **Source commit:** UNKNOWN.
- **Protocol, configuration, and data hashes:** UNKNOWN; no results lock exists.
- **Execution identity:** not applicable.
- **Artifact path or release URI:** `paper/working/`.
- **Artifact checksum:** Local preservation hashes are in
  `paper/working/checksums.sha256`; no immutable paper snapshot hash exists.
- **Coverage and failures:** Scientific, baseline-parity, and citation audits are incomplete.
- **Acceptance-gate outcome:** Paper-export gate BLOCKED.
- **Supported claim IDs:** none.
- **Rejected claim IDs:** none.
- **Scientific-use boundary:** Editorial history only; strong wording inside these
  files is not permitted current claim language.

## LP-E-PROVENANCE-AUDIT-001

- **Scientific purpose:** Check canonical numeric provenance, pointer agreement,
  snapshot absence/closure, reproducibility status, and active-surface disclosure hygiene.
- **Lifecycle:** VALIDATED for local governance only; not ADMITTED.
- **Source commit:** UNKNOWN; the project tree is uncommitted.
- **Protocol, configuration, and data hashes:** Structural manifests are checked;
  scientific execution closure remains BLOCKED in `REPRODUCIBILITY.toml`.
- **Execution identity:** `LP-JOB-LOCAL-20260819-002`, recorded at
  `evidence/jobs/LP-JOB-LOCAL-20260819-002.toml`; local audit only.
- **Artifact path or release URI:** `REPRODUCIBILITY.toml`,
  `scripts/audit_scientific_provenance.py`, and the repository contract tests.
- **Artifact checksum:** The execution record is pinned by
  `evidence/jobs/checksums.sha256`; there is no frozen audit release.
- **Coverage and failures:** Canonical wiki/current-pointer/snapshot and active
  text surfaces are checked; image semantics and authorship are not inferred.
- **Acceptance-gate outcome:** Canonical consistency PASS; scientific release
  readiness BLOCKED.
- **Supported claim IDs:** none.
- **Rejected claim IDs:** none.
- **Scientific-use boundary:** Governance validation only; it supports no metric,
  performance, generalization, or conference-paper claim.
