# Decoupled Temporal Link Prediction with SR-GNN

## Abstract

This study asks whether preventing the link-prediction objective from shaping a temporal backbone improves inductive link prediction. We compare a coupled end-to-end arm with a decoupled arm under the checksum-owned protocol, identical current corpora, and an explicitly reconciled task matrix. The observed decoupled mean is higher on each registered corpus. The result is a bounded within-protocol comparison and does not establish external-baseline superiority, causality, or architecture-general behavior.

## Research design

The coupled arm allows prediction gradients to shape the temporal representation. The decoupled arm blocks that score path while retaining the same registered data, split policy, negative-sampling regime, training schedule, and evaluation endpoint. Every selected run binds a clean source commit, resolved configuration, dataset digests, a hashed dependency environment, deterministic accelerator metadata, and a terminal scheduler identity.

## Results

The primary endpoint is inductive average precision. Uncertainty is the sample standard deviation across the selected seeds. All displayed values are rounded half-even from the frozen aggregate artifact.

| Training arm | Corpus | Inductive AP mean | Sample SD | Selected seeds |
|---|---|---:|---:|---:|
| coupled end-to-end | CoEdit | 0.9787 | 0.0021 | 3 |
| decoupled | CoEdit | 0.9891 | 0.0016 | 3 |
| coupled end-to-end | MOOC | 0.9910 | 0.0047 | 3 |
| decoupled | MOOC | 0.9947 | 0.0007 | 3 |
| coupled end-to-end | Wikipedia | 0.9967 | 0.0003 | 3 |
| decoupled | Wikipedia | 0.9983 | 0.0003 | 3 |

The observed ordering is consistent across the registered corpora in this protocol. The comparison is descriptive: it does not isolate a universal mechanism and it does not authorize claims about unregistered models, datasets, or negative-sampling regimes.

## Reproducibility and evidence

The paper snapshot is assembled only from an immutable evidence release. Numeric provenance is occurrence-level: each table value resolves through a strict selector to a finite scalar in the checksum-owned aggregate artifact, and an independent audit recomputes the declared rounding. Failed, cancelled, superseded, and quarantined attempts remain in the attempt ledger and cannot be selected silently.

## Limitations

Simplified temporal comparators are excluded because they have not passed external implementation-parity review. The current evidence supports only the registered SR-GNN arm comparison. It does not support state-of-the-art, hard-negative robustness, causal, physical-world, lifecycle-readout, or architecture-general irreversibility claims.

## Conclusion

Within the registered protocol, separating representation learning from the link-prediction score path is associated with higher observed mean inductive average precision on each current corpus. The immutable snapshot preserves the narrower evidentiary boundary together with the values.
