# Prospective technical pilot — not publication evidence

The canonical [pilot review](../../../wiki/evidence/Prospective-Pilot.md) owns
interpretation; the [method specification](../../../wiki/methods/Prospective-Evaluation.md)
and [protocol](../../../protocols/prospective_v1.toml) define execution.
This bundle does not enter the frozen A003 release or any admitted claim.

## Preserved execution

- `wikipedia-pilot.json` and `mooc-pilot.json` are byte-for-byte copies of the
  completed attempt reports from Slurm array `7647918`, tasks `0` and `1`.
  Each binds the clean source commit, input and corpus hashes, installed
  package versions, paired initialization/candidates, selected epochs, scores,
  coverage and scheduler identity. Checkpoints remain local, with hashes in
  these reports; they are not redistributed in this bundle.
- `validation.json` records 14 prospective tests and 69 other passing tests,
  canonical/recovery/source audits, earlier failed attempts and corrections.
  The historical verifier passed under Python 3.11; its exact aggregate
  comparison failed under Python 3.9. The numerical source artifacts were
  unchanged. The cause of the interpreter-dependent discrepancy is not closed.
- `slurm-accounting.tsv` preserves pipe-delimited native `sacct` fields for
  dataset preparation, validation attempts, source audit and pilot jobs.
- `checksums.sha256` covers the original reports and validation/accounting
  records. Archival job `7647966` verified source inputs against the recorded
  Git commit, paired initialization, candidate hashes, coverage, and AP/AUC
  reconstruction from score rows before creating this bundle.

The source commit is `6a0f015` (full identity in each report). Runtime settings
were seed 1, two epochs, hidden dimension 32 and CPU execution. The Wikipedia
prefix contains 2,000 events; MOOC contains 2,001 because the final timestamp
group is preserved. These budgets and prefixes are not a full benchmark.
Package versions were recorded, but a complete confirmatory dependency lock
has not been established.

## Diagnostic results

AP and AUC below are rounded from the original reports. All rows refer to the
test cohort before inductive filtering. They are development diagnostics only.

| Dataset | Negative regime | Scored / eligible events | Coupled AP | Decoupled AP | Coupled AUC | Decoupled AUC |
|---|---|---:|---:|---:|---:|---:|
| Wikipedia | Random | 300 / 300 | 0.9839 | 0.9846 | 0.9804 | 0.9815 |
| Wikipedia | Historical | 41 / 300 | 0.3584 | 0.4285 | 0.2246 | 0.3537 |
| Wikipedia | Novel-pair | 300 / 300 | 0.9840 | 0.9849 | 0.9806 | 0.9820 |
| MOOC | Random | 301 / 301 | 0.8713 | 0.8877 | 0.9159 | 0.9270 |
| MOOC | Historical | 261 / 301 | 0.3680 | 0.3856 | 0.2354 | 0.3036 |
| MOOC | Novel-pair | 301 / 301 | 0.9295 | 0.9527 | 0.9527 | 0.9623 |

Historical inductive support is only 8 / 112 events for Wikipedia and
112 / 151 for MOOC. In these historical inductive rows, detached AP is lower
than coupled AP on both datasets. The direction is not uniform across cohorts,
and no seed-level uncertainty can be estimated from this pilot. Random and
historical metrics must not be pooled or compared as if their cohorts matched.

## Exploratory history controls

`exploratory-review.json`, produced by Slurm job `7648014`, records an independent
candidate/history audit and cohort analysis. Both datasets passed: every saved
candidate belongs to its specified support, and every omitted event has empty
support for that regime. No fallback negatives were found. Source/input hashes,
full-stream observation counts, cohort flags and AP/AUC reconstruction passed.
`review-slurm-accounting.tsv` records this job and archival job `7647966`;
`review-checksums.sha256` binds the derived report, accounting and review script.

In the Wikipedia random-negative test cohort, 245 / 300 positive pairs had
appeared earlier. Both adapter arms and a binary recurrence control obtain
AUC 1.0 on those repeated-positive rows. On the remaining 55 new-positive rows,
coupled/decoupled AUC is 0.6213 / 0.6468. The overall random score therefore
conceals substantially different tasks.

For historical negatives on repeated-positive rows, recency AUC is 0.9501 on
Wikipedia and 0.6213 on MOOC, versus adapter AUC 0.3823 / 0.5000 and
0.4869 / 0.5583 respectively (coupled / decoupled). On new-positive historical
rows, both Wikipedia arms have AUC 0.0; MOOC has 0.1020 / 0.1414. These small,
post-hoc cohorts motivate diagnosis and prospective registration of controls;
they do not demonstrate a universal failure mechanism or statistical significance.

Recurrence scores whether a pair was previously observed. Recency scores the
last observed pair timestamp minus query time; an unobserved pair uses the
first stream timestamp minus one before subtracting query time. Controls are
evaluated on exactly the saved candidates and cohort rows. Neither sees the
current event before scoring. The report includes comparisons on the common
event support across all negative regimes; regime scores are not pooled.

## Reconstruct and inspect

With the registered corpora and repository dependencies available, run inside a
Slurm compute allocation from the repository root:

```bash
PYTHONPATH=src python3 scripts/review_prospective_pilot.py
sha256sum -c evidence/development/LP-P-PROSPECTIVE-001/review-checksums.sha256
```

The review checks preserved hashes and source identities, reconstructs metrics,
audits candidate membership and omitted rows against strictly earlier history,
then reports repeated/new positive cohorts and shared regime support. Recurrence
and recency controls are deterministic, exploratory diagnostics added after
inspecting the pilot. They are not preregistered comparator evidence. Use
`--output <new-path>` to preserve a derived report without overwriting an earlier
attempt. This script does not train or change either model.

The raw score-row schema is `[event_index, negative_destination, positive_logit,
negative_logit, is_inductive]`; indices refer to the registered chronological
prefix. Data bytes are fetched through the corpus registry, not redistributed.

Full-corpus paired execution, faithful external baselines, independent-source
replication, locked execution provenance and manuscript admission remain open.
