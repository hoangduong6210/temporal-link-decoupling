---
title: Current Claim Registry
status: canonical claim registry
last_updated: 2026-08-21
paper_source: false
---

# Current Claim Registry

## Admitted claims

None until the validated scientific matrix is copied into an immutable evidence
release. Validation does not by itself authorize paper export.

## Validated claims pending evidence-release activation

### LP-C-DECOUPLING-001

- **Exact permitted statement:** Under the registered current-corpus protocol,
  the observed decoupled SR-GNN arm has higher mean inductive average precision
  than the coupled end-to-end arm on each registered corpus. This is a
  within-protocol arm comparison, not a baseline, state-of-the-art,
  architecture-general, or causal claim.
- **Lifecycle status:** VALIDATED; release activation pending.
- **Scope and population:** The exact task, seed, attempt, and failure population
  recorded by the scientific matrix and its attempt ledger.
- **Dataset and fidelity:** `LP-D-COEDIT-002`, `LP-D-MOOC-003`, and
  `LP-D-WIKIPEDIA-003`, with their checksum-owned registered topology.
- **Metric and uncertainty unit:** Inductive average precision, reported as mean
  and sample standard deviation across the selected seeds. Values below use
  round-half-even to four decimal places from the named JSON selectors.
- **Evidence IDs:** `LP-E-SCIENTIFIC-MATRIX-001`.
- **Execution job:** `LP-JOB-SLURM-A003-FINAL-RECONCILE-R2`.
- **Artifact:** `results/audit/scientific-matrix.json`, SHA-256
  `09bbd7563be8e95c58e12fce38a45eae1c542cf5cc4179647289f44c611d2cea`.

| Profile | Dataset | Inductive AP mean | Sample SD | Selected seeds | JSON selectors |
|---|---|---:|---:|---:|---|
| coupled end-to-end | CoEdit | 0.9787 | 0.0021 | 3 | `$.summary[0].ind_ap_mean`; `$.summary[0].ind_ap_std`; `$.summary[0].n_seeds` |
| coupled end-to-end | MOOC | 0.9910 | 0.0047 | 3 | `$.summary[1].ind_ap_mean`; `$.summary[1].ind_ap_std`; `$.summary[1].n_seeds` |
| coupled end-to-end | Wikipedia | 0.9967 | 0.0003 | 3 | `$.summary[2].ind_ap_mean`; `$.summary[2].ind_ap_std`; `$.summary[2].n_seeds` |
| decoupled | CoEdit | 0.9891 | 0.0016 | 3 | `$.summary[3].ind_ap_mean`; `$.summary[3].ind_ap_std`; `$.summary[3].n_seeds` |
| decoupled | MOOC | 0.9947 | 0.0007 | 3 | `$.summary[4].ind_ap_mean`; `$.summary[4].ind_ap_std`; `$.summary[4].n_seeds` |
| decoupled | Wikipedia | 0.9983 | 0.0003 | 3 | `$.summary[5].ind_ap_mean`; `$.summary[5].ind_ap_std`; `$.summary[5].n_seeds` |
| freeze then probe | CoEdit | 0.8381 | 0.0484 | 3 | `$.summary[6].ind_ap_mean`; `$.summary[6].ind_ap_std`; `$.summary[6].n_seeds` |
| freeze then probe | MOOC | 0.9862 | 0.0009 | 3 | `$.summary[7].ind_ap_mean`; `$.summary[7].ind_ap_std`; `$.summary[7].n_seeds` |
| freeze then probe | Wikipedia | 0.9623 | 0.0128 | 3 | `$.summary[8].ind_ap_mean`; `$.summary[8].ind_ap_std`; `$.summary[8].n_seeds` |

- **Attempt-accounting artifact:**
  `results/audit/scientific-matrix-attempts.json`, SHA-256
  `c27226eb2e035f3f3dca67da7e07eca2c31cdc7293cc53bb2c47a4f3adfb94d2`.

| Accounting field | Value | JSON selector |
|---|---:|---|
| expected scientific tasks | 27 | `$.accounting.scientific_expected` |
| selected completed tasks | 27 | `$.accounting.scientific_completed` |
| scientific attempts retained | 162 | `$.accounting.scientific_attempt_total` |
| failed scientific attempts retained | 57 | `$.accounting.scientific_failed` |
| cancelled scientific attempts retained | 48 | `$.accounting.scientific_cancelled` |
| inadmissible scientific attempts retained | 135 | `$.accounting.scientific_inadmissible` |
| quarantined attempts retained | 167 | `$.accounting.quarantined_attempt_total` |
| failed quarantined attempts retained | 38 | `$.accounting.quarantined_failed` |
| cancelled quarantined attempts retained | 49 | `$.accounting.quarantined_cancelled` |

- **Required qualifiers:** Observed, current-corpus, within-protocol,
  checksum-bound, and sample standard deviation.
- **Known limitations:** No faithful external temporal baseline is admitted; the
  registered negative-sampling regime is the only evaluated regime; the
  freeze-then-probe rows do not establish irreversibility.
- **Paper eligibility:** false until `LP-REL-2026-A003-001` is FROZEN and the
  artifact paths above are rebound to its payload.
- **Last review date:** 2026-08-21.

## Validated artifacts that are not admitted claims

### LP-C-IDFIX-001

- **Exact permitted statement:** In the locally retained current Wikipedia and
  MOOC NPZ files, observed source and destination node-ID sets are disjoint.
- **Lifecycle status:** VALIDATED (technical migration property only).
- **Scope and population:** The two local current NPZ identities named by
  `resources/manifest.toml`; no performance conclusion.
- **Dataset and fidelity:** `LP-D-WIKIPEDIA-003` and `LP-D-MOOC-003`; exact
  checksum-pinned clean-acquisition builds, not frozen-release evidence.
- **Metric and uncertainty unit:** Set-intersection cardinality equals zero;
  uncertainty not applicable.
- **Evidence IDs:** `LP-E-DATA-MIGRATION-001`.
- **Execution job:** `LP-JOB-LOCAL-20260820-001` (local structural check only).
- **Required qualifiers:** Say "checksum-pinned local builds" and "observed node-ID
  sets"; do not imply a dataset redistribution grant or performance conclusion.
- **Known limitations:** Fetch-only rights policy; scientific execution and frozen
  release closure remain separate gates.
- **Paper eligibility:** false.
- **Last review date:** 2026-08-21.

## Blocked or proposed claims

### LP-C-IRREVERSIBILITY-001

- **Exact permitted statement:** Freeze-then-probe measurements are retained as
  an observed protocol arm; no irreversibility claim is admitted.
- **Lifecycle status:** BLOCKED.
- **Scope and population:** Current registered model instances and corpora only;
  no architecture-general conclusion.
- **Dataset and fidelity:** Current checksum-owned corpus identities.
- **Metric and uncertainty unit:** The observed inductive AP rows are registered
  under `LP-C-DECOUPLING-001`; they do not identify an irreversible mechanism.
- **Evidence IDs:** `LP-E-SCIENTIFIC-MATRIX-001`.
- **Execution job:** `LP-JOB-SLURM-A003-FINAL-RECONCILE-R2`; execution exists,
  but the proposed inference remains blocked.
- **Required qualifiers:** Use "observed freeze-then-probe arm" and do not call
  the effect irreversible.
- **Known limitations:** Comparator parity, intervention sufficiency, and
  architecture-general scope are not established.
- **Paper eligibility:** false.
- **Last review date:** 2026-08-21.

## Rejected positive claims

None registered. Absence of an admitted claim is not evidence of rejection.

## Prohibited wording

Do not call a legacy JSON current evidence, mix `PREIDFIX` and ID-fixed cells,
state a seed count not present in the artifact, promote quarantined manuscript
language, or describe the proxy implementations as external baselines.
