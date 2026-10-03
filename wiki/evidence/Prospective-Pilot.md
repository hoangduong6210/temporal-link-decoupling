---
title: Prospective Pilot Review
status: technical pilot completed; not admitted performance evidence
last_updated: 2026-10-02
paper_source: false
---

# Prospective Pilot Review

The Wikipedia and MOOC executions of `LP-P-PROSPECTIVE-001` completed on Slurm
from committed, clean source. The [development bundle](../../evidence/development/LP-P-PROSPECTIVE-001/README.md)
preserves the original reports, source and dataset hashes, scored rows, candidate
identities, coverage, native scheduler outcomes and validation history.
Its quantitative diagnostics are explicitly non-admitted and must not be
copied into the manuscript's performance claims.

## What the pilot establishes

The [prospective adapter](../methods/Prospective-Evaluation.md) can train and
evaluate with scoring before observation. Paired arms start with identical
weights and receive identical evaluation candidates. Contract tests cover
candidate symmetry, gradient separation, pure scoring, temporal ties and full
history replay. Reported metrics were reconstructed from preserved score rows;
coverage accounting and committed input hashes were independently checked.
An additional replay audit checked every candidate and omitted row against
actual source history, current timestamp exclusions and the destination role.
It reconstructed repeated/new positive cohorts and shared regime support, and
computed deterministic recurrence and recency controls from earlier events.

The archive includes earlier failed validation attempts and their corrections.
The recovered-evidence verifier passed under the recorded Python environment;
an exact historical-aggregate equality check failed under another interpreter.
Historical artifacts were not rewritten to erase that discrepancy. See the
bundle's validation record for the precise interpreter and job identities.

## Findings that constrain the next study

Historical-negative support is sparse in the Wikipedia prefix, especially for
the inductive cohort. Historical-negative ranking is poor in the available
cohorts despite strong random-negative scores. Consequently, high random scores
cannot support a general robustness claim. Coverage and ranking quality must
be considered together; omitted rows must remain visible.

The paired direction is not uniformly favorable to decoupling across all
cohorts and regimes. A short chronological-prefix pilot cannot establish
superiority or uncertainty. The mechanism behind the historical-negative
failure is unresolved: neither a causal shortcut explanation nor a proposed
repair follows from these results alone.

The exploratory controls show that repeated positives dominate the Wikipedia
random-negative cohort and are easily separated by recurrence alone. Ranking
previously unseen positive pairs is substantially harder. Under historical
negatives, recency outperforms the adapter on the repeated-positive cohorts.
These observations justify retaining simple history controls in the full study;
they do not establish a causal explanation for model behavior. The controls
were added after inspecting pilot results and are not confirmatory comparisons.

## Next execution gate

Before committing a confirmatory matrix:

- Carry forward the audited historical support, repeated/new positive cohorts
  and shared-cohort comparisons; register their full-study reporting rules.
- Register the recurrence and recency controls prospectively. Review why the
  adapter ranks new positive pairs poorly against historical candidates before
  selecting a new model or claiming robustness. Preserve negative findings.
- Review an original external comparator and bind its source, features, query
  timing, candidates, tuning allowance and selection rule to the same task.
- Register complete-corpus budgets, paired seeds, uncertainty analysis and
  independent-source replication before observing their test results.
- Lock the execution environment and define a new attempt/reconciliation and
  immutable-release contract. Pilot provenance does not substitute for this.

These gates refine the [JIIS backlog](../manuscript/JIIS-Journal.md). They do not
alter `LP-REL-2026-A003-001`, admit a new claim, or advance `paper/CURRENT`.
The paper must continue to be derived from reviewed wiki knowledge.
