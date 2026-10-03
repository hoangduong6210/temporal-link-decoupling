---
title: Prospective Evaluation
status: pilot specification; no admitted performance claim
last_updated: 2026-10-02
paper_source: false
---

# Prospective Evaluation

`LP-P-PROSPECTIVE-001` is a separate pilot protocol for the JIIS readiness work.
Its [executable settings](../../protocols/prospective_v1.toml) do not amend the
frozen historical comparison. No pilot result belongs to `LP-C-DECOUPLING-001`.

## Target and event availability

Predict an interaction at a supplied query time using strictly earlier observed
events. This is timestamp-conditioned link ranking, not prediction of the next
event time. The candidate API accepts source, destination and query time only;
the current event attributes and positive label cannot enter the scorer.

Use Wikipedia and MOOC with their registered disjoint endpoint identities.
CoEdit is excluded from this pilot because its midpoint-indexed attributes are
retrospective. Its original corpus and results are preserved.

The destination catalogue consists of the corpus's destination-role identities.
The pilot assumes this catalogue is externally available before evaluation;
this closed-catalogue assumption must be disclosed. It reveals candidate
identities, not their event history or attributes. Future catalogue availability
is not established by the benchmark. Negatives are not selected by the true
destination's seen/unseen status.

## Score, then observe

All events at an identical timestamp form an indivisible group. Score every
candidate from the state before that timestamp, complete prediction backprop,
then observe all real events in stable input order. Update parameters only
after that group's observation losses have been differentiated. Tied events
do not see each other's attributes when scored. Observation order within a tie
remains a declared stable-order approximation for later timestamps.

Train/validation/test boundaries never divide a timestamp group. Evaluation
replays the full preceding history and observes every real test event. Inductive
membership only selects reported rows; it does not filter memory updates.
Inductive nodes are absent from both training and validation. Test-time
observation updates state but never model parameters.

## Prospective adapter and gradient boundary

The adapter reuses the existing residual event encoder, pair-state context
encoder, recurrent message/GRU modules and state-transition existence readout.
For a query, it combines stored endpoint memories, each endpoint's last observed
attributes, pre-event pair state and query-time gaps. The same deterministic
candidate transformation is applied to every candidate without committing a
hypothetical event. Encoder running statistics are read-only during scoring.

Coupled and decoupled arms differ only in detachment of this query representation
before the shared scored readout. Both positive and negative candidates use the
same boundary. Scoring gradients cannot pass through detached persistent
memory; they reach the trainable query transformation in the coupled arm.
This is not backpropagation through the full event stream.

After scoring, the existing event forward path performs observation updates
with the actual attributes. Its original prediction loss is subtracted from
the auxiliary objective and its observation-side scored representation remains
detached in both arms. Thus the prospective prediction loss is the only
arm-dependent gradient switch; legacy auxiliary routing is held fixed.
Observation-side scores are never used as reported predictions.

This changes the query representation, scoring order and primary prediction
weighting relative to the original protocol. It is a prospective adapter study,
not an exact rerun or proof that fixing evaluation alone explains old results.
The paired pilot uses identical initial weights, candidate draws and budgets.
The adapter updates the ever-active max accumulator only at touched pair keys;
a parity test checks equivalence with the original full-array update, including
duplicate and unregistered keys. The original implementation remains intact.

## Candidates and coverage

- Random: sample uniformly from valid destination identities after exclusions.
- Historical: sample from the source's actual partners observed strictly before
  the query time, after exclusions. It is not a marginal destination multiset.
- Novel-pair: sample from the catalogue excluding that source's training partners
  and current positives. It does not inspect future test-only positive edges.

Exclude all known positive destinations for the same source at the current
timestamp when constructing evaluation negatives. This is evaluator filtering,
not information supplied to the model. Do not exclude future positives.
Deduplicate support before sampling. If eligible support is empty, omit that
row from the affected ranking metric, record the reason and coverage, and still
observe the real event. Never silently fall back to an easier regime or accept
an invalid negative after exhausting retries. Compare regimes on their declared
coverage; coverage differences preclude naive metric pooling.

## Pilot admission boundary

The pilot uses a declared chronological prefix to check correctness, finite
training, gradient routing, state evolution and runtime. Empty inductive or
historical subsets are reported as unavailable, not replaced by another cohort.
It cannot establish accuracy, superiority, significance or journal readiness.
Full-corpus paired runs, faithful external comparators, independent-source
replication and a new immutable evidence release remain subsequent work.

Submit execution through Slurm. Record clean source identity, settings and
dataset hashes, environment, candidate/coverage records and scheduler identity.
Keep failed attempts as failed artifacts. Update this page and the
[JIIS plan](../manuscript/JIIS-Journal.md) before changing the scientific scope.

The initial execution is complete. See the [pilot review](../evidence/Prospective-Pilot.md)
for retained development records, coverage limitations and the next study gate.

## Readout diagnosis

The inherited existence decoder mixes state probabilities with positive,
unbounded learned weights, then clips the mixture before converting to a logit.
The weights therefore do not guarantee a valid probability mixture. The
[checkpoint replay diagnostic](../../experiments/diagnose_prospective_readout.py)
will verify reproduction of saved scores and measure clipping by candidate role
and repeated/new positive cohorts. Ranking the unclipped mixture is a diagnostic
only, not a repaired probability estimate or retrained model. Diagnose this
numerical boundary before attributing historical-negative failure to gradient
decoupling. Any replacement parameterization requires a separate development
protocol and paired execution; the original pilot remains preserved.
