---
title: Decoupled Temporal Link Prediction
status: migration method record
last_updated: 2026-08-19
paper_source: false
---

# Decoupled Temporal Link Prediction

The controlled factor is whether the link loss has a gradient path to the
temporal backbone. The decoupled arm trains the scored readout on detached
features; the coupled arm enables an end-to-end predictor. A valid comparison
must hold data, split, negative draws, optimizer, seed, and non-target settings
fixed. Current source is under `src/temporal_link_decoupling/modeling/v33/`.
