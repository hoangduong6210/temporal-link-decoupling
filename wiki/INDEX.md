---
title: Exhaustive Wiki Index
status: canonical index
last_updated: 2026-08-21
paper_source: false
---

# Exhaustive Wiki Index

## Maintained pages and semantic owners

- [Wiki authority](README.md)
- [Start Here](START-HERE.md)
- [Exhaustive Wiki Index](INDEX.md)
- [Glossary](GLOSSARY.md)
- [Contributing](CONTRIBUTING.md)
- [Limitations](LIMITATIONS.md)
- [Reproducibility](REPRODUCIBILITY.md)
- [Research System Map](architecture/Research-System-Map.md)
- [Research Questions](questions/Research-Questions.md)
- [Current Claim Language](claims/Current-Claim-Language.md)
- [Historical Claim Ledger](claims/Historical-Claim-Ledger.md)
- [Dataset Registry](datasets/Dataset-Registry.md)
- [Data and Target Contract](datasets/Data-and-Target-Contract.md)
- [Split Decision](decisions/0001-separate-link-prediction-and-lifecycle-readout.md)
- [Evidence Ledger](evidence/Evidence-Ledger.md)
- [License and Assets](governance/License-and-Assets.md)
- [Numeric Evidence and Publication Hygiene](governance/Numeric-Evidence-and-Publication-Hygiene.md)
- [Paper Export Contract](manuscript/Paper-Export-Contract.md)
- [Decoupling Method](methods/Decoupled-Temporal-Link-Prediction.md)
- [Negative Sampling](methods/Negative-Sampling.md)
- [Research Workflow](operations/Research-Workflow.md)
- [Technical Source Map](references/Technical-Source-Map.md)
- [Inductive Decoupling Benchmark](results/Inductive-Decoupling-Benchmark.md)
- [Project Status](status/Project-Status.md)
- [Live Execution](status/Live-Execution.md)

## Identifier index

| Kind | Identifier | Semantic owner |
|---|---|---|
| Research question | `LP-RQ-DECOUPLING-001` | [Research Questions](questions/Research-Questions.md) |
| Research question | `LP-RQ-IRREVERSIBILITY-001` | [Research Questions](questions/Research-Questions.md) |
| Research question | `LP-RQ-HARDNEG-001` | [Research Questions](questions/Research-Questions.md) |
| Dataset | `LP-D-COEDIT-002` | [Dataset Registry](datasets/Dataset-Registry.md) |
| Dataset | `LP-D-WIKIPEDIA-003` | [Dataset Registry](datasets/Dataset-Registry.md) |
| Dataset | `LP-D-MOOC-003` | [Dataset Registry](datasets/Dataset-Registry.md) |
| Dataset | `LP-D-COEDIT-001` | [Dataset Registry](datasets/Dataset-Registry.md) |
| Dataset | `LP-D-WIKIPEDIA-002` | [Dataset Registry](datasets/Dataset-Registry.md) |
| Dataset | `LP-D-MOOC-002` | [Dataset Registry](datasets/Dataset-Registry.md) |
| Dataset | `LP-D-WIKIPEDIA-001` | [Dataset Registry](datasets/Dataset-Registry.md) |
| Dataset | `LP-D-MOOC-001` | [Dataset Registry](datasets/Dataset-Registry.md) |
| Protocol | `LP-P-DECOUPLING-001` | [Protocol](../protocols/link_prediction_v1.toml) |
| Protocol amendment | `LP-P-DECOUPLING-001-A001` | [Amendment](../protocols/amendments/LP-P-DECOUPLING-001-A001.md) |
| Protocol amendment | `LP-P-DECOUPLING-001-A002` | [Corrective amendment](../protocols/amendments/LP-P-DECOUPLING-001-A002.md) |
| Protocol amendment | `LP-P-DECOUPLING-001-A003` | [Dataset-topology amendment](../protocols/amendments/LP-P-DECOUPLING-001-A003.md) |
| Evidence | `LP-E-DATA-MIGRATION-001` | [Evidence Ledger](evidence/Evidence-Ledger.md) |
| Evidence | `LP-E-RUNTIME-MIGRATION-001` | [Evidence Ledger](evidence/Evidence-Ledger.md) |
| Evidence | `LP-E-LEGACY-RESULTS-001` | [Evidence Ledger](evidence/Evidence-Ledger.md) |
| Evidence | `LP-E-LEGACY-PAPER-001` | [Evidence Ledger](evidence/Evidence-Ledger.md) |
| Evidence | `LP-E-PROVENANCE-AUDIT-001` | [Evidence Ledger](evidence/Evidence-Ledger.md) |
| Evidence | `LP-E-SCHEDULER-HISTORY-001` | [Evidence Ledger](evidence/Evidence-Ledger.md) |
| Execution job | `LP-JOB-LOCAL-20260819-001` | [Job record](../evidence/jobs/LP-JOB-LOCAL-20260819-001.toml) |
| Execution job | `LP-JOB-LOCAL-20260819-002` | [Provenance-audit job](../evidence/jobs/LP-JOB-LOCAL-20260819-002.toml) |
| Execution job | `LP-JOB-LOCAL-20260820-002` | [Scheduler-accounting job](../evidence/jobs/LP-JOB-LOCAL-20260820-002.toml) |
| Current claim | `LP-C-IDFIX-001` | [Current Claim Language](claims/Current-Claim-Language.md) |
| Current claim | `LP-C-DECOUPLING-001` | [Current Claim Language](claims/Current-Claim-Language.md) |
| Current claim | `LP-C-IRREVERSIBILITY-001` | [Current Claim Language](claims/Current-Claim-Language.md) |
| Historical claim | `LP-H-MIXED-001` | [Historical Claim Ledger](claims/Historical-Claim-Ledger.md) |
| Decision | `DEC-0001` | [Split Decision](decisions/0001-separate-link-prediction-and-lifecycle-readout.md) |

## Paper snapshot index

None. `paper/CURRENT` and `PROJECT.toml` both declare `UNRELEASED`.

Identifier namespaces are project-local: questions `LP-RQ-*`, datasets `LP-D-*`,
protocols `LP-P-*`, evidence `LP-E-*`, claims `LP-C-*`, and historical claims
`LP-H-*`. Decision IDs use `DEC-*` within this project.
