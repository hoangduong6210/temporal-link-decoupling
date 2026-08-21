---
title: Start Here
status: canonical onboarding
last_updated: 2026-08-21
paper_source: false
---

# Start Here

## Objective and stage

The project tests decoupling-by-construction against coupled end-to-end training
for inductive temporal link prediction. The current stage is
`immutable-release-assembly`. Current evidence release: `UNRELEASED`. Current
paper snapshot: `UNRELEASED`.

## Supported now

- The projects have independent package, data, result, wiki, and paper roots.
- Current and quarantined corpora have distinct stable manifest identities.
- Raw acquisition and deterministic clean rebuilds are checksum-pinned.
- The scientific runner, dependency lock, accelerator record, attempt reconciler,
  evidence freezer, and paper snapshot builder are fail-closed.
- Legacy execution attempts and claims are retained for audit without admission.
- Failed and superseded fresh attempts are retained in checksum-bound scheduler
  history; the corrected publication matrix excludes simplified model proxies.
- Dataset topology is checksum-owned per corpus: CoEdit uses a homogeneous
  shared node space, while Wikipedia and MOOC use disjoint bipartite namespaces.
- The complete current scientific task matrix, terminal accounting, and
  reconstructed aggregates are validated by `LP-E-SCIENTIFIC-MATRIX-001` and
  `LP-JOB-SLURM-A003-FINAL-RECONCILE-R2`.

## Unsupported or blocked now

- Quantitative wording is validated only inside `LP-C-DECOUPLING-001`; paper
  admission waits for the frozen release.
- Irreversibility, hard-negative, external-baseline, state-of-the-art, causal,
  and architecture-general claims remain blocked.
- No frozen evidence release or immutable conference snapshot exists.

## Running work and ownership

No training or scheduler job is currently running. Dataset redistribution is
disabled under the conservative rights policy. The evidence reviewer must
verify immutable release closure; the claim reviewer may approve paper wording
only after that release exists.

## Next actions

1. Freeze the declared `LP-*` evidence release.
2. Author only the claim language supported by that release.
3. Build and audit the immutable conference snapshot.

## Safe first checks and task routes

Run `python -m pytest -q` for local structural contracts; it does not run heavy
training or create scientific evidence. Contributors start with [Project Status](status/Project-Status.md).
Claim reviewers read [Claim Registry](claims/Current-Claim-Language.md),
[Evidence Ledger](evidence/Evidence-Ledger.md), and [Limitations](LIMITATIONS.md).
Dataset reviewers read [Dataset Registry](datasets/Dataset-Registry.md) and
[Source Map](references/Technical-Source-Map.md). Paper editors read the
[Paper Export Contract](manuscript/Paper-Export-Contract.md).
