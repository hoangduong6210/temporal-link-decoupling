---
title: Prospective Sampling and Gradient Diagnostics
status: completed and reconciled validation-only development study
last_updated: 2026-10-03
paper_source: false
---

# Prospective Sampling and Gradient Diagnostics

`LP-P-PROSPECTIVE-003` owns the [registered diagnostic protocol](../../protocols/prospective_diagnostics_v3.toml).
It follows the [development review](../evidence/Prospective-Development.md).
The [completed diagnostic review](../evidence/Prospective-Diagnostics.md) owns
the interpretation and next research decision.
The question is whether the observed benefit of detachment depends on training
negative sampling, and whether decoder or auxiliary-gradient behavior helps
interpret that dependence. These are hypotheses, not established explanations.

## Scope and endpoints

Cross the bounded coupled/decoupled arms with random and mixed training
negatives. Run the pinned original-module TGN comparator under the same training
policies. Preserve the earlier legacy controls as historical development records;
this stage is not a new matched comparison of decoder families.

Use the registered train/validation partitions of the already inspected
prefixes. Remove held-out test events and attributes before constructing any
model. The external destination catalogue remains the declared closed-catalogue
assumption; its identities are not inferred to be available prospectively.
Inductive validation rows contain an endpoint absent from training; all events
remain in history replay. This differs from the prior test cohort's definition.

The primary descriptive endpoint is final-epoch validation performance by
regime and cohort. Report the within-seed detached-minus-coupled contrast under
each sampling policy, then the difference between those contrasts. This avoids
letting checkpoint selection determine the primary interaction. Save a secondary
checkpoint selected by equal-weight mean validation AP over the registered
regimes, with the earliest epoch winning ties. Empty regime support is an error;
do not silently alter the selection criterion. Retain every epoch's score rows.
Validation-selected performance is descriptive and optimistically selected;
neither it nor final-epoch development performance is held-out test evidence.

## Explicit availability-dependent training mixture

Generate the same base random candidate for each supported event in every
policy. Independently draw a historical candidate from the source's strictly
earlier partners, excluding all current positives of that source. Where
historical support exists, the registered mixing probability decides which
component supplies the training negative. Where it is absent, the mixture
explicitly has a random-only stratum. Record availability and chosen component
for every row; never label the random-only stratum as historical sampling.

The random arm consumes the same candidate and mixture random streams while
always selecting the random component. Training event support and negative
budget are therefore matched across policies. No model receives extra negatives.
Sampling decisions do not use target novelty, event attributes or future events.
Observe complete timestamp groups after scoring and update historical support
only then. Evaluation retains typed regimes, explicit omitted rows and no
fallback. The adaptive training mixture is not an implementation of an external
benchmark's historical sampler.

## Diagnostic measurements

At protocol-fixed training groups, record prediction-gradient norms before
observation and the auxiliary gradient accumulation increment before the
optimizer step. Group shared transformations and prediction heads separately.
Record their dot product and cosine where defined; absent gradients are visible,
not replaced with an apparent alignment. Increment subtraction is subject to
floating-point cancellation. Detached prediction gradients on the query backbone
are expected to vanish; this alone is not evidence of harmful gradient conflict.

Record initial and epoch decoder log odds, effective state probabilities,
sigmoid slopes, parameter displacement and gradient magnitude. Near-boundary
initialization can affect sensitivity, but small sigmoid slope alone does not
prove a vanishing end-to-end loss gradient. Do not tune initialization or remove
auxiliary terms in this matrix. Any follow-up intervention requires its own
registration and train/validation selection rule.

Retain recurrence/recency controls and repeated/new-positive/shared-support
cohorts. Gradient associations and improved validation scores cannot identify
causality, deployment calibration, general superiority or population uncertainty.

## Execution and decision gate

Commit the protocol and implementation before Slurm execution. Bind source,
corpora, original TGN revision, package versions, candidates, checkpoints and
native scheduler outcomes. Test mixture eligibility and parity, gradient
measurement, validation-only boundaries and TGN integration before the matrix.
Reconcile every cell and unfavorable result before updating the wiki review.

Use the resulting measurements to decide whether a targeted initialization or
auxiliary intervention is justified. Only after that decision should the project
register full-corpus budgets, independent-source replication, prospective
runtime lock and uncertainty endpoints. The frozen release and `paper/CURRENT`
remain unchanged; the [JIIS readiness gate](../manuscript/JIIS-Journal.md) stays open.
