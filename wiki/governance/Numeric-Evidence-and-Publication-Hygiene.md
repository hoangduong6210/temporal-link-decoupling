---
title: Numeric Evidence and Publication Hygiene
status: canonical blocked gate
last_updated: 2026-08-19
paper_source: false
---

# Numeric Evidence and Publication Hygiene

Every empirical scalar in the wiki, including integers, number words, ratios,
ranges, scientific notation, and values inside code spans, must appear in a
claim record that names an Evidence ID and an execution job. A blocked claim
must say `Execution job: NONE` and may not restate a legacy scalar. Dates,
ordered-list labels, identifier suffixes, hashes, bibliographic locators, and
implementation versions are governance or structural metadata rather than
empirical claims.

The current wiki admits no paper-eligible performance scalar. Its sole validated
technical scalar is the ID-set intersection statement in `LP-C-IDFIX-001`; that
claim resolves to `LP-E-DATA-MIGRATION-001` and
`LP-JOB-LOCAL-20260819-001`. Legacy paper numbers remain under
`LP-E-LEGACY-RESULTS-001`, with no normalized job registry, and are prohibited
from release or paper export.

A conference snapshot must inventory every numeric occurrence by exact literal,
file, line, and occurrence index. Scientific, protocol, and derived entries need
Claim, Evidence, Job, source-artifact checksum, and artifact selector fields.
Structural entries need a narrow exemption. Figure labels require a sidecar
numeric inventory and a plot job. The executable gate is
`scripts/audit_scientific_provenance.py`.

Lexical scanning can detect vendor/persona names and internal-workflow markers;
it cannot determine authorship. No claim of human or AI authorship may be made
from stylometry alone. `paper/working/`, top-level `paper/figs/`,
`figures/generated/`, `results/historical/`, audit output, and the mixed parent
tree are outside the publication surface.
