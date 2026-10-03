---
title: Prospective Readout and Comparator Development
status: registered development matrix; not confirmatory evidence
last_updated: 2026-10-03
paper_source: false
---

# Prospective Readout and Comparator Development

`LP-P-PROSPECTIVE-002` owns the [development matrix](../../protocols/prospective_development_v2.toml).
Its purpose is to test the decoder's probability parameterization and establish
an executable original-module comparator under the prospective contract.
Previously inspected chronological prefixes remain development data. Additional
seeds do not convert them into an independent confirmatory study.

## Diagnosis and intervention

The [preserved checkpoint diagnosis](../../evidence/development/LP-P-PROSPECTIVE-002/readout/README.md)
contains the quantitative diagnostics, exact source/checkpoint bindings and
native scheduler outcomes, including the failed initial replay.

Replay of the saved pilot checkpoints reproduces the original scores after
restoring the recorded CPU thread count. The Wikipedia readout clips historical
candidate mixtures and collapses many distinct predictions to the upper limit;
the detached historical-negative scores all coincide. MOOC's historical scores
are poor without clipping, so this mechanism cannot explain all observed
historical-negative failure. Unclipped mixtures are diagnostic ranking values,
not valid probabilities or evidence for a repaired trained model.

The [bounded decoder](../../src/temporal_link_decoupling/modeling/bounded_prospective.py)
assigns a sigmoid probability to each latent state and mixes them using the
predicted state distribution. It evaluates the log odds through log-space sums
of present and absent mass, avoiding an upper hard clamp. Effective initial
state weights follow the original initialization with a registered interior
margin for boundary values; other parameters consume the same random draws.
This margin is necessary because the original active-state weights start on
the probability boundary. Distinct checkpoint parameter names prevent accidental
loading of a legacy decoder into the replacement.

This is a parameterization change with retraining. It is not an evaluation-only
correction and does not assume that clipping is the sole source of poor ranking.
The legacy decoder and all of its results are retained as controls.

## Mathematical and gradient boundary

Let the query transformation be \(h=Q_\theta(H_{<t},u,v,t)\), using only
observed history. The scored head combines this representation with detached
pair-history channels \(\phi_{uv}\), producing a normalized state distribution
\(q_\psi(h,\phi_{uv})\). The bounded state weights are
\(w_k=\sigma(a_k)\). Its predicted presence mass and log odds are

\[
p=\sum_k q_k w_k,
\qquad
\ell=\log\sum_k q_k\sigma(a_k)-\log\sum_k q_k\sigma(-a_k).
\]

The implementation computes these sums in log space. Finite parameter values
keep the ideal mixture strictly inside the probability interval; the log-space
form avoids rounding the final probability before calculating its log odds.
The numerical floor on state mass protects logarithms when softmax underflows.

These probabilities parameterize the sampled positive/negative classification
task. Their numerical validity does not establish calibration to a deployment
event rate. Likewise, named lifecycle states are latent model constructs with
heuristic auxiliary targets, not independently observed lifecycle annotations
or evidence that the transition restrictions are causal laws.

For coupled scoring, the head reads \(h\); for detached scoring it reads
\(\operatorname{stopgrad}(h)\). Thus, at equal parameter and history values,
the scored prediction is equal while the prediction gradient reaching
\(\theta\) is removed in the detached arm. The observation objective is the
legacy total loss minus its prediction term. Both arms preserve its routing,
including the detached observation-side scored representation. Their numeric
auxiliary gradients need not remain equal after their parameter trajectories
diverge. Persistent node and pair memories remain detached between events;
this comparison does not perform backpropagation through the whole event stream.

## Controlled comparisons

- Cross legacy/bounded decoder families with coupled/decoupled query gradients.
  Within each family and seed, initialization, candidates, auxiliary losses,
  optimizer and budget are identical; only the query detach boundary differs.
- Include the [original-module TGN comparator](External-TGN-Comparator.md),
  with an explicit compact pilot configuration and the same data/evaluation
  contract. It retains its own architecture and has no SR-GNN auxiliary loss.
- Use the protocol's fixed paired seeds and complete timestamp groups. Training
  uses random negatives. Validation random AP selects checkpoints with the
  earliest epoch on ties; historical test performance is never used for selection.
- Evaluate random, historical and novel-pair candidates with identical draws
  across every cell. Report all/inductive, repeated/new positive and shared
  support cohorts, together with recurrence and recency controls.

Negative-regime differences include changes in support. Do not pool them.
Report every registered cell, failed attempt and negative finding. Paired seed
differences and sample variation describe development stability only; no
significance, superiority, robustness or architecture-general conclusion is
admitted from this matrix.

## Execution and the next gate

The [runner](../../experiments/run_prospective_development.py) and
[Slurm entry point](../../slurm/prospective_development.sbatch) require committed,
clean source and the pinned external TGN checkout. Use an isolated checkout for
long-running jobs so subsequent wiki editing cannot change their source.
Record corpus/input/source hashes, complete installed package versions, explicit
thread count, candidates, checkpoints, selected epochs and native Slurm outcomes.
Recorded environment metadata is not yet a complete hash-locked runtime.

Before full-corpus model execution, finish the model/protocol decision using
these development records, measure training-only throughput, close the runtime
lock, register tuning/seed budgets and uncertainty endpoints, and specify an
independent-source replication dataset. A separate release contract must admit
those runs before the [JIIS article](../manuscript/JIIS-Journal.md) may cite them.
The existing frozen release and paper pointer remain unchanged.
