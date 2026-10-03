---
title: Prospective Auxiliary and Backbone Controls
status: partially executed; paused at owner request before reconciliation
last_updated: 2026-10-03
paper_source: false
---

# Prospective Auxiliary and Backbone Controls

Execution is paused. The [resume handoff](../status/Pause-and-Resume.md) records
completed and interrupted tasks, the unvalidated reconciler and required next
checks. The protocol is unchanged; incomplete execution is not a result review.

`LP-P-PROSPECTIVE-004` owns the
[registered mechanism-control protocol](../../protocols/prospective_mechanism_v4.toml).
It follows the [sampling and gradient review](../evidence/Prospective-Diagnostics.md)
and uses the [isolated CPU runtime](Prospective-Runtime.md). Its purpose is to
distinguish auxiliary learning and backbone adaptation from the query-gradient
boundary. The study does not assume that local gradient conflict causes the
observed routing effect.

## Actual paths and intervention

The prospective query transforms past features with CSN, encodes pair state with
the ECTG context encoder, and applies deterministic DRGC message/recurrent
transforms. The routing switch detaches the resulting query representation
before the state observer and transition predictor. The bounded decoder and
the query's history-only inputs remain the same.

Observation invokes the legacy core after prediction backward, removes its
placeholder prediction loss, and differentiates the remaining auxiliary sum.
That sum includes recurrent regularization, symbolic transition/violation and
entropy terms, and continuous edge-distribution regularizers, according to the
fixed constructor. Some symbolic paths detach their backbone input internally;
other observation paths can still train the backbone. Query detachment does not
disable all auxiliary learning, and the earlier context-gradient probe did not
cover the full ECTG module.

| Arm | Query routing | Auxiliary backward | CSN/ECTG/DRGC parameters |
|---|---|---|---|
| `coupled-aux` | Coupled | Enabled | Trainable |
| `detached-aux` | Detached | Enabled | Trainable |
| `coupled-noaux` | Coupled | Disabled | Trainable |
| `detached-noaux` | Detached | Disabled | No incoming gradient; verified unchanged |
| `frozen-aux` | Detached | Enabled for remaining trainable paths | Explicitly fixed at initialization |

Disabling auxiliary backward preserves the complete observation forward,
stochastic draws, feature EMA, pair history and node-memory writes. It does not
multiply the loss by a null coefficient: doing that would create gradient
tensors and could activate Adam weight decay on otherwise disconnected
parameters. Optimizer gradients are cleared to absent tensors before each group.

The fixed-backbone arm changes only parameter trainability in CSN, full ECTG
and DRGC. It retains learned heads and evolving memory. It does not enable the
legacy `determ_only_backbone` option, which additionally bypasses learned
transforms and would change the scored representation. A fixed random
transformation with updated history is not a constant predictor.

## Registered comparisons and falsifying outcomes

Cross each arm with random and mixed training negatives, preserving the earlier
candidate budget, splits and decoder initialization. Rerun reference arms in
the same locked runtime. Match initial parameter bytes and candidate traces
across arms and policies within each seed; preserve all unsuccessful attempts.
No old-environment result is used as a paired reference.

The primary endpoint is final-epoch validation AP/AUC by negative regime and
cohort. Within each training policy, subtract the no-auxiliary routing contrast
from the auxiliary-enabled routing contrast. Also report the auxiliary effect
within each routing arm and detached-auxiliary minus fixed-backbone-auxiliary.
The full per-seed directions remain visible. Secondary selected checkpoints
use the predeclared equal-weight validation rule and cannot replace the primary
comparison after seeing outcomes.

If a routing advantage persists with auxiliary backward disabled, auxiliary
conflict is not necessary for that observed advantage under this control.
If fixed-backbone performance is similar, the need for an auxiliary-trained
backbone is weakened. Null, adverse and seed-dependent outcomes constrain the
paper equally. These are interventions on complete learning trajectories,
including head/state feedback; they cannot identify a unique local cause or
prove population equivalence from a nonsignificant difference.

## Diagnostics and admission boundary

Use disjoint, exhaustive parameter groups, including the full ECTG module.
Measure prediction gradients and auxiliary accumulation increments at fixed
probes, retaining undefined cosines. Record initial and epoch parameter hashes,
norms of movement and maximum displacement. Verify fixed parameter bytes rather
than inferring Adam updates from raw-gradient size. A synthetic integration
control must reproduce detached-noaux with an explicitly frozen noaux model.

Tests must verify reference-training equivalence to the preceding runner,
unchanged observation/RNG semantics when disabling backward, fixed backbone
bytes with dynamic memory, shared initialization/candidates and validation-only
boundaries. All tests, training and independent reconciliation run through Slurm.

These are inspected development prefixes with a closed catalogue. The study
does not evaluate test events or provide independent-source confirmation.
Full-corpus budgets, source-independent replication, uncertainty and comparator
registration remain open. The frozen release and paper pointer remain unchanged.
