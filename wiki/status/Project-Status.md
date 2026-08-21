---
title: Project Status
status: active migration status
last_updated: 2026-08-21
paper_source: false
---

# Project Status

## Current state

The project root, package namespace, corpus registry, legacy result partition,
paper working tree, and canonical wiki are separated. Evidence and paper pointers
remain `UNRELEASED`. The original mixed tree remains a read-only migration source
because it contains dirty changes and pre-ID-fix provenance. No scientific
conclusion changed during the split.

## Verification state

The local repository, import-boundary, checksum-manifest, JSON, wiki-link,
frontmatter, artifact-hygiene, and dataset-schema/ID contracts passed on
2026-08-19 (`LP-E-DATA-MIGRATION-001`, `LP-E-RUNTIME-MIGRATION-001`,
job `LP-JOB-LOCAL-20260819-001`). This is a local structural result, not a
frozen evidence release.
The numeric/pointer/snapshot/disclosure gate also passes in its canonical
unreleased mode (`LP-E-PROVENANCE-AUDIT-001`, job
`LP-JOB-LOCAL-20260819-002`). Release readiness remains BLOCKED.
Current corpus bytes were deterministically rebuilt from checksum-pinned raw
inputs in a clean staging tree. They remain ignored and are not redistributed;
clean acquisition uses the reviewed source registry and explicit builders.

## Active blockers

- The scoped project has a committed baseline identity. Every fresh scheduler
  envelope must still capture the exact clean execution commit.
- A fresh current-corpus scheduler matrix has not yet completed, so accelerator
  records and current performance aggregates are not admitted.
- The initial fresh attempts are preserved by `LP-E-SCHEDULER-HISTORY-001` and
  job `LP-JOB-LOCAL-20260820-002`. Native scheduler outcomes remain unchanged;
  scientific admissibility is recorded separately. Bootstrap root-cause wording
  is UNVERIFIED, the retry exposed ambiguous node-memory collision semantics,
  and all temporal comparator implementations were adjudicated as simplified
  proxies rather than faithful external baselines.
- The subsequent A002 campaign is also preserved and inadmissible. CoEdit failed
  closed under a wrongly global bipartite-ID invariant; queued work and the
  reconciliation job were cancelled. Amendment `LP-P-DECOUPLING-001-A003`
  restores the registered homogeneous CoEdit topology while retaining disjoint
  user/item namespaces for Wikipedia and MOOC.
- The initial A003 submission-directory attempt failed before runner startup and
  its dependent reconciliation was cancelled. Its exact native accounting is
  retained in the same scheduler-history evidence; replacement execution must
  originate from the project root.
- A later A003 campaign was stopped after the release gate exposed the stale
  pre-freeze configuration lifecycle label. Completed and cancelled cells remain
  inadmissible. The resolved configuration is now explicitly
  `SCIENTIFIC-FROZEN` before replacement execution.
- No frozen evidence release, admitted performance claim, results lock, or
  immutable paper snapshot exists.
- Strong numerical and generalization wording in `paper/working/` remains QUARANTINED.
- Historical execution attempts are reconciled where surviving artifacts allow,
  including retries and terminal failures, but remain ineligible because they
  lack the current source/data/environment chain. The preserved DOCX and ZIP lack
  visible quarantine banners; legacy figures remain outside the publication path.

## Next stage

Run the frozen scheduler matrix from a clean commit, reconcile every attempt,
and freeze the checksum-closed evidence release. Then generate the new
paper only from admitted release artifacts and build the immutable conference
snapshot. Paper export remains blocked until those gates pass.
