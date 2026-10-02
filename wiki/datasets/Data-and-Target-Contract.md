---
title: Data and Target Contract
status: canonical contract
last_updated: 2026-10-02
paper_source: false
---

# Data and Target Contract

Each NPZ must contain sources, destinations, timestamps, labels, features,
num_nodes, num_edges, and feat_dim. Event arrays share length `num_edges`;
features have shape `(num_edges, feat_dim)`; node IDs are in range; timestamps
are nondecreasing. The loader sanitizes non-finite raw Wikipedia feature values.
Wikipedia and MOOC require disjoint source and destination ID namespaces.

## Interpretation for the journal

CoEdit is derived from the Wikipedia source stream and therefore is not an independent source replication. Wikipedia and MOOC use separate endpoint namespaces; CoEdit uses a shared contributor namespace. Scoring currently receives event features, so any forecasting interpretation must specify whether those features are available at decision time. The candidate sampler is also part of the target definition.

## Constructed-event availability

CoEdit uses the midpoint of the contributing edit timestamps and averages their attributes. The later edit must be observed before the derived interaction can be constructed. Chronological splitting of this midpoint-indexed stream alone does not establish prospective input availability. The journal reports this limitation explicitly.
