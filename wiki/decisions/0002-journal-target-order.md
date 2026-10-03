---
title: Journal Target Order
status: accepted venue decision
last_updated: 2026-10-02
paper_source: false
---

# DEC-0002: JIIS primary, KAIS and IJMLC next

## Context

The repository owner selected Journal of Intelligent Information Systems (JIIS)
as the primary journal, followed by Knowledge and Information Systems (KAIS)
and International Journal of Machine Learning and Cybernetics (IJMLC). This
decision replaces DYU as the active target. The existing DYU package remains
an earlier editable draft and a record of prior editorial work.

## Decision

Prepare for **JIIS → KAIS → IJMLC**, in that order. Target selection is complete;
manuscript preparation and evidence admission remain in progress. No journal
submission has been made by this change.

The [venue register](../manuscript/journal-targets.toml) owns the machine-readable
order, publisher identities, checked instructions and preparation status.
[JIIS Journal Development](../manuscript/JIIS-Journal.md) owns the writing plan
and readiness backlog. [Journal Targets](../manuscript/Journal-Targets.md)
explains fit and venue-specific adaptation.

## Rationale and alternatives

JIIS is the owner's selected target. Our editorial fit assessment is to frame
the work as a design and evaluation study of gradient routing in a stateful
temporal information system. Its scope includes intelligent-system design,
knowledge discovery and interpreted experiments motivated by applications.
This is an assessment of fit, not an editorial decision or acceptance forecast.
See the [publisher's JIIS scope](https://link.springer.com/journal/10844/aims-and-scope).

KAIS retains the knowledge-discovery and evaluation angle. IJMLC retains the
representation-learning and learning-system angle. Neither fallback reduces
the evidence standard. DYU remains available as prior work but is outside the
active submission sequence.

## Hard rules

- `wiki/` is the repository's knowledge foundation. The existing lowercase
  directory implements the owner's Wiki requirement; do not create a competing
  `Wiki/` tree. Establish interpretation, sources and claim status here before
  deriving manuscript text or tables.
- No solving, training, evaluation, dataset rebuilding, parameter search or
  other heavy job on a login node. Submit heavy work through Slurm, including
  substantial validation or document-rendering jobs. Login-node work is limited
  to editing, lightweight inspection, Git and scheduler operations.
- Preserve frozen evidence and the current claim boundaries. Venue choice does
  not admit historical results or establish new performance claims.

## Switching venues

Finish the current venue's consideration through a decision or confirmed
withdrawal before submitting elsewhere. Record the outcome and adaptation in
the wiki, refresh that venue's instructions, and update the active target in
the venue register. A scope rejection prompts reframing; an evidence criticism
requires an evidence response before resubmission. Do not prepare concurrent
submissions or treat a venue change as a way around unresolved scientific gaps.

## Evidence and affected IDs

`LP-C-DECOUPLING-001` and `LP-E-SCIENTIFIC-MATRIX-001` remain the current claim
and evidence basis. `LP-REL-2026-A003-001` is unchanged. `paper/CURRENT` remains
`UNRELEASED` until the [export contract](../manuscript/Paper-Export-Contract.md)
is satisfied.

## Supersedes / superseded by

Supersedes the active DYU target in [DYU Journal Development](../manuscript/DYU-Journal.md).
Does not supersede the scientific protocol, prior artifacts or `DEC-0001`.
No later venue decision is registered.
