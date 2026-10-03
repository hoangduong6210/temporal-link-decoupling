---
title: Prospective Sampling and Gradient Diagnostic Review
status: reconciled validation-only development; not admitted publication evidence
last_updated: 2026-10-03
paper_source: false
---

# Prospective Sampling and Gradient Diagnostic Review

The registered `LP-P-PROSPECTIVE-003` study completed on Slurm. Its
[development bundle](../../evidence/development/LP-P-PROSPECTIVE-003/README.md)
preserves every registered cell, training candidate trace, epoch validation
score, gradient probe, decoder snapshot and native scheduler outcome.
Independent reconciliation passed. Primary comparisons use the fixed final
epoch; validation-selected checkpoints remain separately labeled. No test
events were evaluated in this study.

## What the diagnostic establishes

Training-negative choice substantially changes historical-negative validation
ranking in these inspected prefixes. On MOOC, mixed training improves historical
AP for the bounded models and TGN, while lowering their random and novel-pair
AP. On Wikipedia, mixed training improves historical AP for the bounded models
but not TGN. This is a regime-dependent tradeoff, not a uniform model repair.

Within mixed training, bounded detachment improves mean historical AP on each
corpus, including the inductive cohort. The sampling-by-routing interaction is
positive at every registered Wikipedia seed, while its MOOC direction varies
across seeds. MOOC novel-pair interaction is adverse at every registered seed.
The interaction describes a difference between paired routing contrasts; it
does not establish superiority over TGN, population significance or general
benefit from detachment.

Historical support remains especially sparse for Wikipedia's inductive cohort.
The recency control exceeds the learned models' mean AP on that supported
cohort under mixed training. Keep this control and the repeated/new-positive
and shared-support cohorts visible. Different regime supports cannot be treated
as the same prediction population.

At the registered final-epoch probes, coupled prediction gradients reach the
shared transformations. Detachment removes those prediction gradients as
designed. Measured auxiliary increments on CSN are much smaller than the
prediction gradients; context increments are absent in the measurements and
DRGC increments are extremely small. Some CSN cosines are negative, but their
direction alone does not establish damaging interference. Probes are dependent
observations, accumulation subtraction can lose tiny increments, and Adam's
update is not determined by the current raw-gradient norm alone.

The bounded decoder has measurable gradients and parameter movement despite
near-boundary state probabilities. These observations do not establish a
vanishing-loss-gradient explanation or justify choosing a new initialization
from validation performance after the fact.

## Execution and evidence boundary

Reconciliation independently reconstructs training RNG decisions, candidate
eligibility, timestamp exclusions, validation cohorts, metrics, paired effects
and checkpoint selection. Initial parameters are matched within model family
and seed across routing and sampling policies. Actual original TGN modules
were exercised in the source gate and matrix, under the adapted project
protocol and compact training budget.

An execution encountered a storage quota failure. The partial atomic report
and native failed/cancelled states remain archived; they are excluded from the
selected matrix. Project-owned isolated worktrees and outputs were moved to
scratch, and the affected tasks were retried without changing scientific
settings or source. Successful retries are explicitly identified in the bundle.

These are already inspected prefixes, a closed destination catalogue, and
validation-only development results. The inductive definition uses endpoints
absent from training and differs from the earlier test-cohort definition.
Installed packages are recorded, but the prospective runtime is not yet
hash-locked. Training-seed variation is descriptive; neither independent-source
replication nor a held-out generalization claim follows.

## Next research decision

Retain sampling as an explicit experimental factor. Do not select mixed
training as universally preferable or promote gradient-conflict causality.
Keep the bounded decoder initialization fixed while closing reproducibility
and deciding the mechanism controls; the present measurements do not identify
initialization as the dominant bottleneck.

Before a larger study, reconcile the actual auxiliary paths and register a
matched auxiliary-disabled control and a fixed-backbone control. Separate
prediction routing, auxiliary learning and backbone adaptation; an unchanged
random backbone is a meaningful alternative explanation that must be tested.
Specify which loss terms and optimizer participation change, preserve the
history observation schedule, and use training/validation only for development.
These controls are a proposed next study, not executed evidence.

In parallel, close a portable prospective runtime lock, audit a source-independent
corpus, and measure training-only throughput through Slurm before setting
full-corpus budgets. Register data, uncertainty units, comparator/tuning budgets
and support-aware endpoints before new test inspection. The
[literature review boundary](../references/Journal-Research-Gap.md) keeps the
mechanism question distinct from established sampling and gradient-routing work.

The [journal backlog](../manuscript/JIIS-Journal.md) remains open under the
[JCR top-quartile goal](../decisions/0003-jcr-top-quartile-goal.md).
`LP-REL-2026-A003-001` and `paper/CURRENT` are unchanged.
