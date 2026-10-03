---
title: JIIS Journal Development
status: active preparation; not submission ready
last_updated: 2026-10-02
paper_source: false
---

# JIIS Journal Development

Target: **Journal of Intelligent Information Systems**. KAIS and IJMLC remain
the ordered alternatives in [Journal Targets](Journal-Targets.md).
This page is the canonical editorial brief and readiness backlog. It does not
admit a new claim or represent a completed JIIS manuscript.

## Positioning and contribution

Working title: **Gradient Routing in Stateful Temporal Link Prediction:
A Controlled Inductive Study**.

Lead with the information-system problem: interaction histories evolve, and
a temporal predictor must coordinate persistent state with a scored readout.
Explain why the location of the training gradient boundary is a design choice
worth testing. Use the registered interaction corpora to motivate potential
applications without claiming deployed-system or prospective performance.

The contribution is the integrated temporal model and an auditable comparison
of gradient-routing procedures under a fixed protocol. Describe established
components with attribution. The admitted result is the bounded observed
coupled/decoupled comparison in `LP-C-DECOUPLING-001`; the freeze-then-probe arm
is a control with distinct training semantics. It does not identify irreversible
damage, causal effects or architecture-general superiority.

Do not describe detachment as removing only the link loss if auxiliary terms
reuse the detached state distribution. Describe the actual scoring and update
order before interpreting performance. Any fuller mathematical account must
first be reconciled with implementation and added to the method wiki.

## Manuscript derived from wiki

| Manuscript part | Canonical source | Writing and verification requirement |
|---|---|---|
| Motivation and contribution | [Research Questions](../questions/Research-Questions.md), this brief, [Current Claims](../claims/Current-Claim-Language.md) | Explain the system-design question and bounded contribution; avoid a leaderboard claim |
| Related work | [Technical Source Map](../references/Technical-Source-Map.md) | Audit original references for temporal memory, representation learning, gradient routing and evaluation before citing |
| Method and model diagram | [Decoupling Method](../methods/Decoupled-Temporal-Link-Prediction.md) | Specify the scored readout, auxiliary gradient paths, pre-update pair history and batch-level recurrent memory |
| Data and protocol | [Data Contract](../datasets/Data-and-Target-Contract.md), [Dataset Registry](../datasets/Dataset-Registry.md), [Negative Sampling](../methods/Negative-Sampling.md) | Explain inductive splits, namespace topology, candidate availability, negative sampling and checkpoint selection |
| Results and control | [Current Claims](../claims/Current-Claim-Language.md), [Evidence Ledger](../evidence/Evidence-Ledger.md), [Benchmark](../results/Inductive-Decoupling-Benchmark.md) | Derive displayed values from the frozen selectors and retain the registered uncertainty unit; do not transcribe historical DYU tables |
| Discussion and validity | [Limitations](../LIMITATIONS.md), [Historical Claims](../claims/Historical-Claim-Ledger.md) | Distinguish current evidence, retrospective context and untested hypotheses |
| Reproducibility and availability | [Reproducibility](../REPRODUCIBILITY.md), [Research Workflow](../operations/Research-Workflow.md), [License and Assets](../governance/License-and-Assets.md) | Bind source and artifacts, explain fetch-only data, and record Slurm execution |
| Declarations and final package | [Journal Targets](Journal-Targets.md), [Export Contract](Paper-Export-Contract.md) | Obtain accurate author declarations, check current venue formatting and admit an immutable snapshot |

The earlier [DYU source](../../paper/journal/DYU/Latex_full/) can help locate
material to review. It is not the scientific source of truth. Its retrospective
tables cannot enter the JIIS result section until their own release and claim
bindings close. A venue change alone must not relabel those tables as admitted.

## Readiness backlog

These are project preparation priorities, not claims that the journal explicitly
requires a particular experiment. Complete the editorial work from existing
evidence first; register protocol changes before commissioning new execution.

| Priority | Work item | Completion evidence / current state |
|---|---|---|
| Required | Venue order and official-instruction register | Completed by the venue decision and linked register |
| Required | Wiki method reconciliation | Open: verify every score, auxiliary gradient path, update rule and temporal assumption against code; resolve omissions in the wiki before drafting equations |
| Required | Current-evidence manuscript | Open: develop the outline above into an English LaTeX article; bind each quantitative occurrence to admitted evidence |
| Required | Event-conditioning and temporal leakage review | Open: document what event attributes are available at scoring time, source staleness and batch ordering; either validate the intended prediction setting or narrow its interpretation explicitly |
| High | Faithful external comparator | Open: select a maintained original implementation through source review; freeze split, candidate pool, features, tuning and compute budget; retain unsuccessful attempts. Existing proxies cannot satisfy this item |
| High | Negative-sampling robustness | Open: preregister historical or hard-negative regimes, eligibility rules and collision handling; compare under matched settings without altering the existing release |
| High | Interpretation of uncertainty and practical relevance | Open: review paired-seed behavior and variation; assess efficiency or case-study measurements only if supported by registered execution; avoid unsupported significance or efficiency claims |
| Conditional | Historical ablations | Open: reconcile source, data and execution identity per claim or leave the numerical tables out of the submission; arithmetic recovery is insufficient |
| Required | JIIS template and compiled layout | Open: resolve the guideline template ambiguity, enforce the recorded page/abstract/keyword limits and inspect the rendered PDF |
| Required | Author and publication declarations | Open: verify metadata, contributions, interests, funding, data availability, prior-publication status and assistance disclosure |
| Required | Evidence-bound submission snapshot | Open: record wiki commit, build job, numeric registry, bibliography/figure hashes and results lock; pass the release audit before advancing the paper pointer |

At the scientific review checkpoint, explicitly decide which proposed extensions
are necessary for the paper's claims and convincing venue fit. A decision to
defer them must retain the corresponding limitations. Do not silently mark
unexecuted comparator or robustness work as completed.

## Execution and handoff

The [prospective evaluation specification](../methods/Prospective-Evaluation.md)
and `LP-P-PROSPECTIVE-001` implement the initial protocol-development work.
The adapter separates scoring from observation, uses typed candidate support,
and retains all events when reporting inductive metrics. It is a distinct pilot
study; its changed representation and objective must not be presented as an
unchanged rerun of the current admitted model. Full-scale comparator evidence
and manuscript admission remain open.

All solving and heavy work goes through Slurm. This includes training,
evaluation, dataset rebuilding, large analysis, substantial test runs and
document rendering. On the login node, edit, inspect lightweight metadata,
manage Git, and submit or inspect jobs. Supply account and partition at submit
time; keep machine-specific paths and credentials outside the public tree.

New science follows the [Research Workflow](../operations/Research-Workflow.md):
review protocol/configuration, commit the source, submit, preserve attempts and
scheduler accounting, reconcile, freeze a new release, then update claims and
derive the paper. The existing frozen release is never overwritten.

The [JIIS work area](../../paper/journal/JIIS/README.md) points back to this brief.
`paper/CURRENT` remains `UNRELEASED`. A preparation commit is not a submission,
an acceptance, or a new scientific execution.
