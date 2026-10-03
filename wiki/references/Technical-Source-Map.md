---
title: Technical Source Map
status: verified provenance map
last_updated: 2026-10-03
paper_source: false
---

# Technical Source Map

The machine-readable source identity for current data is
`resources/source_registry.json`; `resources/manifest.toml` owns the processed
identities. Quarantined manuscript citations do not become current sources by
proximity.

| Topic/source owner | Intended use | Primary source identity | Verification state | Admission boundary |
|---|---|---|---|---|
| Wikipedia and MOOC raw streams | Dataset provenance and acquisition | Exact SNAP JODIE HTTPS objects and response metadata in `resources/source_registry.json` | Raw and processed digests verified by `LP-JOB-LOCAL-20260820-001` | Fetch-only; no redistribution grant asserted |
| CoEdit construction | Population, event definition, exclusions, and units | Registered Wikipedia parent plus `experiments/dataset_builders/build_coedit.py` and checksum-owned parameters | Deterministic clean rebuild verified by `LP-JOB-LOCAL-20260820-001` | Project-built derivative; no source-independence claim |
| Average precision | Current endpoint computation | Runner implementation bound by the scientific source commit and resolved protocol | Aggregate recomputation verified by `LP-JOB-SLURM-A003-FINAL-RECONCILE-R2` | Within-protocol claim only |
| Registered negative sampling | Evaluation protocol | `protocols/link_prediction_v1.toml` and checksum-owned resolved task profiles | Current scientific matrix complete | No hard-negative generalization claim |
| Temporal comparator families | Comparator scope and parity | Simplified local proxies are explicitly quarantined | Not admitted as external baselines | No state-of-the-art or protocol-parity claim |
| Original Temporal Graph Networks | External comparator under the prospective project protocol | Authors' repository and primary paper bound by [the pinned source register](../../configs/tgn-upstream.json) | [Original-module integration](../methods/External-TGN-Comparator.md) and development matrix passed | Adapted evaluation and compact budget; no reproduction of published benchmark results or admitted full-study ranking |
| Freeze then probe | Observed protocol arm | Current runner and resolved freeze task profile | Measurements retained by `LP-E-SCIENTIFIC-MATRIX-001` | No causal or irreversibility claim |

Any future external comparison must add an exact primary source, stable official
implementation identity, proposition supported, parity audit, and reviewer
decision before claim admission.

## Journal bibliography and archival sources

The journal retains the conference literature on temporal models, point-process features, online statistics, variational objectives and gradient separation. Primary publication records should supply bibliographic metadata. The recovered result archive is an internal research source; it is not an external benchmark publication or independent corroboration.
