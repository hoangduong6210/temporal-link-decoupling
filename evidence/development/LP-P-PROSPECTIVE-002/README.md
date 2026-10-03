# Prospective readout and comparator development

**Development evidence only; not a publication release.** Canonical interpretation
lives in the [wiki review](../../../wiki/evidence/Prospective-Development.md).
The registered protocol is [LP-P-PROSPECTIVE-002](../../../protocols/prospective_development_v2.toml).

## Completed execution

All 30 cells completed: Wikipedia and MOOC, seeds 1/2/3, and legacy-coupled,
legacy-decoupled, bounded-coupled, bounded-decoupled and original-module TGN.
Each fit used the registered chronological prefix, two epochs and compact
configuration. The final source gate executed 90 tests, including all four
actual TGN integration tests with none skipped.

| Record | Identity |
|---|---|
| Model source | `be79f37` (full identity in raw reports) |
| Source validation | Slurm `7648241`, completed |
| Model execution | Slurm `7648242_0` and `7648242_1`, completed |
| Reconciler source | `2065033` (full identity in summary) |
| Reconciliation | Slurm `7648256`, completed; independent candidate/cohort/metric audit passed |
| Original TGN | `d55bbe678acabb9fc3879c408fd1f2e15919667c`, clean external checkout |
| Prior checkpoint replay | Slurm `7648211`, completed; maximum absolute logit error zero |

The prior checkpoint replay restores its original CPU thread count. This new
matrix fixes PyTorch to one thread for every model; it is a separate registered
execution, not a claim of bitwise equivalence to the earlier pilot's training.
The bounded parameterization also uses a declared interior initialization
margin where legacy effective state weights were exactly one.

## Results that constrain the paper

[Complete tables](tables.md) report means and sample standard deviations, paired
inductive differences, and deterministic controls. [The machine-readable summary](matrix/summary.json)
also contains every per-seed result and repeated/new-positive/shared-support
cohort. Means and sample SDs are descriptive, not confidence intervals.

- Wikipedia historical AP, before inductive filtering: legacy coupled
  `0.3926 ± 0.0607`, legacy detached `0.4404 ± 0.0123`, bounded coupled
  `0.3388 ± 0.0173`, bounded detached `0.3611 ± 0.0123`, TGN `0.8180 ± 0.0446`.
  Only 41 of 300 test events have historical candidate support; only 8 of 112
  inductive events do. These are small, selected cohorts.
- MOOC historical AP: legacy coupled `0.3728 ± 0.0117`, legacy detached
  `0.4074 ± 0.0208`, bounded coupled `0.4660 ± 0.0719`, bounded detached
  `0.4041 ± 0.0277`, TGN `0.3909 ± 0.0174`. Historical support is 261 of 301
  test events and 112 of 151 inductive events.
- Bounded-minus-legacy effects differ by corpus and gradient arm. In the
  bounded MOOC family, detached-minus-coupled historical AP is
  `-6.1860 ± 5.9647` percentage points over the complete supported test cohort.
  The result is not uniformly favorable across seeds; negative findings remain
  in the archive.
- Wikipedia's earlier clipped readout was a real numerical issue, but clipping
  was not the complete explanation of historical-negative failure. Retraining
  with valid bounded probabilities did not establish a general ranking repair.

Original TGN modules are evaluated under the project's adapted protocol and
compact budget. These results do not reproduce the published TGN benchmark or
establish a tuned architecture ranking. The prefixes were already inspected;
none of this matrix is independent confirmatory evidence.

## Artifact map and verification

- [Readout replay](readout/README.md): saved-checkpoint diagnosis, failed initial
  replay, checksums and scheduler states.
- [Wikipedia raw report](matrix/wikipedia-development.json) and
  [MOOC raw report](matrix/mooc-development.json): byte-preserved attempts,
  package metadata, input/candidate/checkpoint hashes and score rows.
- [Summary](matrix/summary.json) and [native accounting](matrix/slurm-accounting.tsv):
  reconstructed metrics, paired seed summaries and reconciler/source identities.
- [Validation history](validation.json) and [terminal accounting](validation-slurm-accounting.tsv):
  failed development attempts, corrections, source-gate result and completed runs.

The selected checkpoint bytes remain in local job output; their digests are
recorded in the raw reports. Dataset bytes and third-party source are fetch-only.
Public score records permit metric reconstruction without redistributing either.
The prospective environment records installed versions but still needs a complete
hash-locked runtime before full-study admission.

From the repository root, inside Slurm:

```bash
sha256sum -c evidence/development/LP-P-PROSPECTIVE-002/readout/checksums.sha256
sha256sum -c evidence/development/LP-P-PROSPECTIVE-002/matrix/checksums.sha256
sha256sum -c evidence/development/LP-P-PROSPECTIVE-002/validation-checksums.sha256
```

See the [execution/reconciliation workflow](../../../docs/PROSPECTIVE_DEVELOPMENT.md).
The frozen release `LP-REL-2026-A003-001` is untouched, `paper/CURRENT` remains
`UNRELEASED`, and this bundle does not make the JIIS submission ready.
