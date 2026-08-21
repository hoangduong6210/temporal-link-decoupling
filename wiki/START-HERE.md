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
`split-migration-audit`. Current evidence release: `UNRELEASED`. Current paper
snapshot: `UNRELEASED`.

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

## Unsupported or blocked now

- No quantitative performance, irreversibility, hard-negative, baseline, or
  generalization claim is admitted.
- The scoped project has a committed baseline identity; scientific jobs must
  bind their exact clean execution commit.
- The fresh current-corpus scheduler matrix and its reconciliation are pending.
- No frozen evidence release or immutable conference snapshot exists.

## Running work and ownership

No training or scheduler job is currently admitted. Dataset redistribution is
disabled under the conservative rights policy. The evidence reviewer must close
fresh execution coverage and comparator parity; the claim reviewer may approve
wording only after a frozen release exists.

## Next actions

1. Run and reconcile the frozen protocol scheduler matrix from a clean commit.
2. Freeze the initial `LP-*` evidence release.
3. Author and snapshot only the
   claim language supported by that release.

## Safe first checks and task routes

Run `python -m pytest -q` for local structural contracts; it does not run heavy
training or create scientific evidence. Contributors start with [Project Status](status/Project-Status.md).
Claim reviewers read [Claim Registry](claims/Current-Claim-Language.md),
[Evidence Ledger](evidence/Evidence-Ledger.md), and [Limitations](LIMITATIONS.md).
Dataset reviewers read [Dataset Registry](datasets/Dataset-Registry.md) and
[Source Map](references/Technical-Source-Map.md). Paper editors read the
[Paper Export Contract](manuscript/Paper-Export-Contract.md).
