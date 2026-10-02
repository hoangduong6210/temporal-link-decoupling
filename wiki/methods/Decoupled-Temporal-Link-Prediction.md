---
title: Decoupled Temporal Link Prediction
status: current implementation and historical contrast
last_updated: 2026-10-02
paper_source: false
---

# Decoupled Temporal Link Prediction

The temporal backbone combines event encoding, recurrent node memory and pair-history context. The scored readout consumes this representation. A stop-gradient preserves the forward representation and blocks the backward path at its boundary; it does not freeze deterministic event history or all auxiliary training objectives.

## Current registered comparison

Both primary profiles keep `p0_fix` off and use the registered hierarchical readout. `detach_scorepath` distinguishes the coupled and decoupled scoring paths. Positive and negative candidates receive the same gradient-boundary treatment. Data, split, seed, optimizer and non-target settings must remain fixed.

The freeze-then-probe profile is a different training procedure: the runner enables the main predictor during pretraining, selects a validation checkpoint, freezes representation parameters, reinitializes the main prediction head and trains the probe. State stores still evolve. This is neither a pure linear probe nor an intervention sufficient to establish irreversibility.

## Temporal ordering

Pair-history scoring uses pre-update context and read-only negative lookup. Deterministic pair accumulators replay repeated pairs in input order under the causal-batch option. Recurrent node memory instead uses a batch snapshot and stable last-row commit on repeated node indices. Store-level sequential agreement does not imply full-model event-by-event equivalence.

## Historical configurations

The recovered B-versus-C comparison changes design presets. The historical B-versus-K1 knob enables a separate main predictor; it is not identical to reconnecting the same scored readout. The archived scripts and result metadata preserve these differences. Claims must name the intervention actually performed. The current objective contains enabled auxiliary terms; describing the backbone as trained exclusively by a variational penalty is not an accurate specification of every active path.

## Gap semantics

The current forward path supplies source-node staleness to the pair accumulator. Pair-indexed running moments therefore summarize the supplied node gap, not necessarily an inter-arrival gap between consecutive events of that same pair. A literal fitted point-process interpretation would need a separate specification and validation.
