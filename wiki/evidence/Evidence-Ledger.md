---
title: Evidence Ledger
status: canonical evidence ledger
last_updated: 2026-08-21
paper_source: false
---

# Evidence Ledger

Current evidence release: `UNRELEASED`. The complete current scientific matrix is
validated below and awaits atomic copy into its declared frozen release.

## LP-E-SCIENTIFIC-MATRIX-001

- **Scientific purpose:** Preserve the current-corpus coupled, decoupled, and
  freeze-then-probe protocol arms with complete attempt accounting.
- **Lifecycle:** VALIDATED scientific evidence; FROZEN activation pending.
- **Source commit:** `ed227ad1cbc8143ff23e78aee476f01b7c9028de`, captured as a
  clean source identity by every selected runner envelope.
- **Protocol, configuration, and data hashes:** Bound in
  `LP-JOB-SLURM-A003-FINAL-RECONCILE-R2` to the frozen protocol, resolved
  configuration, data manifest, data checksum registry, hashed transitive
  dependency lock, and deterministic accelerator environment digest.
- **Execution identity:** `LP-JOB-SLURM-A003-FINAL-RECONCILE-R2`; native array
  identities and the successful reconciliation identity are preserved in the
  final Slurm accounting capture.
- **Artifact path or release URI:** `results/audit/scientific-matrix.json` and
  `results/audit/scientific-matrix-attempts.json`; the release plan is
  `evidence/release-plans/LP-REL-2026-A003-001.json`.
- **Artifact checksum:** The matrix, ledger, source captures, terminal Slurm
  accounting, failed reconciliation accounting, and job record are individually
  checksum-bound by the release plan or the job registry.
- **Coverage and failures:** The selected matrix is complete. Every scientific
  and quarantined attempt is retained with native terminal state,
  admissibility, selection identity, parent-result checksum, and failure reason.
- **Acceptance-gate outcome:** PASS for source, protocol, configuration, corpus,
  dependency, accelerator, attempt-selection, failure-accounting, and aggregate
  reconstruction gates. Frozen-copy and immutable-paper gates are pending.
- **Supported claim IDs:** `LP-C-DECOUPLING-001` at VALIDATED status.
- **Rejected claim IDs:** none. `LP-C-IRREVERSIBILITY-001` remains BLOCKED because
  the observed protocol contrast does not identify an irreversible mechanism.
- **Scientific-use boundary:** Within-protocol SR-GNN arm comparison only. No
  external-baseline, state-of-the-art, hard-negative, causal, or
  architecture-general conclusion.

## LP-E-SCHEDULER-HISTORY-001

- **Scientific purpose:** Preserve the complete scheduler history that triggered
  the collision-semantics and comparator-identity correction.
- **Lifecycle:** VALIDATED accounting evidence; not ADMITTED performance evidence.
- **Source commit:** The queried attempts retain their submitted commit identity
  in `evidence/execution/LP-SCHEDULER-HISTORY-20260820.json`.
- **Protocol, configuration, and data hashes:** Parent runner outputs retain their
  original bindings; amendments `LP-P-DECOUPLING-001-A002` and
  `LP-P-DECOUPLING-001-A003` supersede the affected campaigns.
- **Execution identity:** `LP-JOB-LOCAL-20260820-002`, checksum-registered under
  `evidence/jobs/`; the underlying Slurm array and reconciliation IDs are in the
  scheduler-history artifact.
- **Artifact path or release URI:**
  `evidence/execution/LP-SCHEDULER-HISTORY-20260820.json`, which checksum-binds
  the raw pipe-delimited `sacct` capture under `evidence/execution/raw/`.
- **Artifact checksum:** Bound by the local job record and incorporated as a
  required input to the matrix reconciler.
- **Coverage and failures:** The artifact retains failed bootstrap arrays,
  dependency cancellation, superseded successful main-arm attempts, the
  non-finite recurrent-memory proxy failure, the failed reconciliation, and the
  failed/cancelled dataset-topology, submission-directory, and pre-freeze
  configuration campaigns.
- **Acceptance-gate outcome:** PASS for native scheduler-state preservation;
  INADMISSIBLE for numerical claims and aggregate reuse.
- **Supported claim IDs:** none.
- **Rejected claim IDs:** none; affected result artifacts retain their native
  FAILED, CANCELLED, or COMPLETED state but are scientifically inadmissible.
- **Scientific-use boundary:** Scheduler accounting and adjudication only.

## LP-E-DATA-MIGRATION-001

- **Scientific purpose:** Verify local corpus identities and their registered
  homogeneous or disjoint-bipartite topology after migration.
- **Lifecycle:** VALIDATED for local migration integrity; not ADMITTED.
- **Source commit:** The clean acquisition run used the committed source identity
  named by `REPRODUCIBILITY.toml`.
- **Protocol, configuration, and data hashes:** Dataset and upstream raw-file
  hashes are owned by `resources/manifest.toml`, `resources/checksums.sha256`,
  and `resources/source_registry.json`.
- **Execution identity:** `LP-JOB-LOCAL-20260820-001`, recorded at
  `evidence/jobs/LP-JOB-LOCAL-20260820-001.toml`; clean-archive acquisition and
  deterministic rebuild, not a scientific scheduler job.
- **Artifact path or release URI:** `resources/manifest.toml`,
  `resources/checksums.sha256`, and local ignored files under `resources/corpora/`.
- **Artifact checksum:** Raw and processed bytes are declared in the source/data
  registries; the execution record is pinned by `evidence/jobs/checksums.sha256`.
  The pending scientific release plan checksum-binds the same registries.
- **Coverage and failures:** Current corpora were rebuilt deterministically from
  registered raw inputs in clean staging and matched their declared digests.
- **Acceptance-gate outcome:** Schema/hash/dataset-topology, upstream digest, and
  clean-acquisition gates PASS; immutable release copy is pending.
- **Supported claim IDs:** `LP-C-IDFIX-001` at VALIDATED technical status only.
- **Rejected claim IDs:** none.
- **Scientific-use boundary:** Dataset migration integrity only; no performance or
  paper-eligible conclusion.

## LP-E-RUNTIME-MIGRATION-001

- **Scientific purpose:** Detect drift in the copied runtime closure.
- **Lifecycle:** VALIDATED for local code-copy integrity; not ADMITTED.
- **Source commit:** The scientific runner source is the clean commit recorded by
  `REPRODUCIBILITY.toml` and the current scientific job.
- **Protocol, configuration, and data hashes:** Runtime files are owned by
  `configs/shared-runtime.sha256`; the frozen protocol, resolved configuration,
  dataset manifests, and scientific dependency lock are checksum-bound.
- **Execution identity:** `LP-JOB-LOCAL-20260820-001`, recorded at
  `evidence/jobs/LP-JOB-LOCAL-20260820-001.toml`; local execution, not a scheduler
  or frozen-release job.
- **Artifact path or release URI:** `src/` and `configs/shared-runtime.sha256`.
- **Artifact checksum:** Per-file SHA-256 values are in
  `configs/shared-runtime.sha256`; the execution record is pinned by
  `evidence/jobs/checksums.sha256`. No release-level checksum exists.
- **Coverage and failures:** Runtime files, exact transitive environment, task
  profiles, state-neutral warmup, and fail-closed scheduler metadata were tested.
- **Acceptance-gate outcome:** Runtime, runner, and fresh scheduler execution
  gates PASS; frozen-copy and immutable-paper gates remain pending.
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
- **Source commit:** The audit implementation is committed; the final audit
  evidence will bind the post-snapshot audit commit.
- **Protocol, configuration, and data hashes:** Structural manifests and the
  validated scientific chain are checked; frozen-copy closure is still pending.
- **Execution identity:** `LP-JOB-LOCAL-20260819-002`, recorded at
  `evidence/jobs/LP-JOB-LOCAL-20260819-002.toml`; local audit only.
- **Artifact path or release URI:** `REPRODUCIBILITY.toml`,
  `scripts/audit_scientific_provenance.py`, and the repository contract tests.
- **Artifact checksum:** The execution record is pinned by
  `evidence/jobs/checksums.sha256`; there is no frozen audit release.
- **Coverage and failures:** Canonical wiki/current-pointer/snapshot and active
  text surfaces are checked; image semantics and authorship are not inferred.
- **Acceptance-gate outcome:** Canonical consistency PASS; immutable release and
  paper pointers are still pending.
- **Supported claim IDs:** none.
- **Rejected claim IDs:** none.
- **Scientific-use boundary:** Governance validation only; it supports no metric,
  performance, generalization, or conference-paper claim.
