---
title: Prospective Development Review
status: reconciled development matrix; not admitted publication evidence
last_updated: 2026-10-03
paper_source: false
---

# Prospective Development Review

The registered `LP-P-PROSPECTIVE-002` matrix completed on Slurm from an isolated,
clean source commit. The [development bundle](../../evidence/development/LP-P-PROSPECTIVE-002/README.md)
preserves every registered cell, score row, source and data identity, descriptive
paired-seed result, and native scheduler outcome. Quantitative tables remain
non-admitted development evidence and cannot be copied into manuscript claims.

## What is closed

Checkpoint replay reproduced the earlier pilot's saved scores using its recorded
CPU thread setting. The diagnostic identifies clipping in the Wikipedia
readout, while poor MOOC historical ranking also occurs without clipping.
The [registered decoder intervention](../methods/Prospective-Development.md)
therefore repairs the probability parameterization without assuming a complete
explanation of the ranking failure.

The bounded decoder, legacy controls and [original-module TGN comparator](../methods/External-TGN-Comparator.md)
completed the paired development matrix. Integration tests exercised original
TGN APIs, gradients, chronological replay and pure queries. This establishes
an executable comparator under the adapted project protocol, not reproduction
of published benchmark results or an admitted full-study comparison.

Reconciliation checked committed dependencies, complete cells, matched
initializations within decoder families, common training and evaluation
candidates, selected checkpoints, full-history observation and timestamp ties.
It independently reconstructed candidate eligibility, omitted rows, cohorts,
AP and AUC from preserved scores. Earlier failed validation attempts remain
visible in the validation record.

## Findings and limits

The bounded decoder does not consistently improve historical-negative ranking.
On Wikipedia, its historical AP is lower than the legacy counterpart for each
gradient-routing arm when averaged over the registered seeds. TGN ranks the
available historical cohort substantially better in this development run.
Historical support is sparse, especially after inductive filtering, so this
does not establish a population-wide advantage.

On MOOC, the bounded coupled arm improves mean historical AP over the legacy
coupled arm, but the bounded detached arm does not improve over its legacy
counterpart. Detachment reduces mean historical AP within the bounded family,
while its paired direction varies across seeds. TGN's historical ranking is
also weak in this prefix. Random-negative performance alone would obscure
these differences.

Paired inductive effects also depend on corpus, decoder and negative regime.
For MOOC's bounded historical comparison, detachment lowers inductive AP at
every registered seed, even though it improves inductive random-negative AP.
Simple recurrence and recency controls remain necessary: repeated positives,
new pairs and shared candidate support describe different prediction problems.
The complete cohort results are retained even when they weaken the intended
decoupling argument. Neither a general superiority claim nor a significance
claim follows from this matrix.

These prefixes were already inspected during development. Additional training
seeds are descriptive replications within those prefixes; they do not provide
an independent dataset replication or remove model-selection bias. The compact
budget is not a tuned external benchmark. Installed-package metadata is recorded,
but the prospective runtime is not yet fully hash-locked.

## Next research decision

Keep the bounded decoder as a numerically valid experimental alternative,
retain the legacy controls, and retain original-module TGN. Do not select a
final architecture from historical test AP or replace unfavorable results.
Before scaling, specify a training/validation-only selection rule and tuning
budget, then measure training-only throughput through Slurm. Register the
full-corpus matrix, uncertainty endpoints, support/cohort reporting and an
independent-source replication dataset before inspecting new test outcomes.

The journal's defensible question remains when and under which protocol a
gradient boundary helps, rather than assuming that detachment always helps.
Close the prospective runtime lock and immutable-release contract before
admitting new evidence. Only then derive the corresponding result section from
the wiki. The [JIIS backlog](../manuscript/JIIS-Journal.md) remains open;
`LP-REL-2026-A003-001` and `paper/CURRENT` are unchanged.
