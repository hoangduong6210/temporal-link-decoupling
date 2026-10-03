---
title: Original TGN Comparator Contract
status: integration and development matrix passed; no admitted comparison
last_updated: 2026-10-03
paper_source: false
---

# Original TGN Comparator Contract

The comparator loads the original modules from the authors' [TGN repository](https://github.com/twitter-research/tgn),
bound by [the source register](../../configs/tgn-upstream.json), which also links
the primary paper, Temporal Graph Networks for Deep Learning on Dynamic Graphs.
The external checkout is fetched separately, kept clean and checked against the
registered commit. It is not vendored or replaced with a simplified local proxy.
Upstream retains its Apache license; see [third-party notices](../../THIRD_PARTY_NOTICES.md).

## Original modules and adapted protocol

The [wrapper](../../src/temporal_link_decoupling/modeling/upstream_tgn.py) retains
upstream attention, time encoding, pending-message aggregation, recurrent memory
and affinity readout. Queries compute pending memory updates without committing
them, then call the original embedding and affinity modules. Observation invokes
the original temporal-embedding API after scoring, stores actual event messages
and detaches persistent memory. No SR-GNN auxiliary loss is assigned to TGN.

The upstream evaluator uses batch-level metric averaging and its own sampling
and inductive replay. Those procedures are not used for a protocol-matched
comparison. The project wrapper instead shares the prospective splits, typed
negative candidates, full-stream replay, pooled metrics and timestamp groups.
This is original TGN modules under an adapted evaluation protocol, not a claim
to reproduce the published benchmark results.

| Concern | Project comparator contract |
|---|---|
| Node identities | Shift registered identities to preserve upstream's reserved padding identity; no learned node-identity features |
| Features | Constant node attributes and the registered event attributes; current attributes enter only observation |
| Temporal neighbors | Original recent-neighbor finder with strict timestamp cutoff; reject queries that skip unobserved earlier events |
| Timestamp ties | Query the complete group before observation; preserve upstream last-message aggregation for later queries |
| Pure query | Do not change memory, pending messages, parameters or random state; compare logits with an original API call on a cloned state |
| Inductive reporting | Select metric rows while observing the complete stream; never condition negative eligibility on the true destination's novelty |
| Pilot budget | Explicit compact dimensions, neighborhood budget and disabled dropout; not the paper's tuned configuration |
| Evaluation | Same candidates and checkpoint-selection rule as the prospective adapter; report support and paired query ordering |

The graph-attention embedding does not use the optional time-projection
normalization arguments. The wrapper therefore does not estimate normalization
statistics from the test stream. Queries still use original attention time
encoding and message time gaps.

## Validation and admission

Integration tests require the actual external checkout. They check original-API
score parity, query state/RNG purity, permutation/chunk invariance, exclusion of
current/future attributes, chronological observation and gradients reaching the
original attention, memory updater and readout. A skipped integration test is
not evidence that the comparator is validated.

Modern-runtime integration and the registered development matrix completed;
the [development review](../evidence/Prospective-Development.md) preserves their
scope and findings. Full-dataset settings, tuning
budgets, paired seeds and environment locks remain a separate registration.
Review this contract with the [prospective specification](Prospective-Evaluation.md)
before admitting any result to the journal evidence.
