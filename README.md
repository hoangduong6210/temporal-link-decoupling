# Temporal Link Prediction by Decoupling

An evidence-backed research implementation for studying whether a temporal
link-prediction objective should update the temporal backbone. The repository
compares coupled end-to-end training with gradient-decoupled training under a
fixed inductive protocol.

The current scientific scope is deliberately narrow. It supports the
within-protocol coupled/decoupled comparison and its freeze-then-probe control.
It does not support state-of-the-art, external-baseline, causal,
irreversibility, or architecture-general claims. Local proxy implementations
are excluded from scientific comparisons.

## Evidence status

The active scientific result is immutable and checksum-closed. No manuscript
is currently admitted as scientific evidence:

| Record | Current artifact |
|---|---|
| Scientific claims | [`wiki/claims/Current-Claim-Language.md`](wiki/claims/Current-Claim-Language.md) |
| Evidence ledger | [`wiki/evidence/Evidence-Ledger.md`](wiki/evidence/Evidence-Ledger.md) |
| Evidence release | [`LP-REL-2026-A003-001`](results/frozen/LP-REL-2026-A003-001/) |
| Evidence-admitted paper | None; [`paper/CURRENT`](paper/CURRENT) is `UNRELEASED` |
| Scientific execution | [`LP-JOB-SLURM-A003-FINAL-RECONCILE-R2`](evidence/jobs/LP-JOB-SLURM-A003-FINAL-RECONCILE-R2.toml) |
| Reproducibility contract | [`REPRODUCIBILITY.toml`](REPRODUCIBILITY.toml) |

Every quantitative statement admitted to the wiki resolves to a claim, an
evidence selector, a registered execution job, and a checksum-locked source
artifact. A future paper must be generated from that wiki-owned claim surface
and pass the same executable gate.

## Conference manuscript

The single preserved conference manuscript is available as
[`Link_Predict.pdf`](paper/conference/Link_Predict.pdf), together with a
self-contained [`Overleaf package`](paper/conference/Link_Predict_Overleaf.zip).
This artifact applies only the requested author-block update, removal of the
specified reproducibility note, and grayscale figure rendering. It is not an
evidence-admitted snapshot because its result set is not registered in the
current frozen release.

## Journal target: JIIS

The active submission strategy is **Journal of Intelligent Information Systems
(JIIS) → Knowledge and Information Systems (KAIS) → International Journal of
Machine Learning and Cybernetics (IJMLC)**. The
[venue decision](wiki/decisions/0002-journal-target-order.md),
[checked publisher requirements](wiki/manuscript/journal-targets.toml), and
[JIIS development plan](wiki/manuscript/JIIS-Journal.md) live in the canonical
wiki. The [JIIS preparation area](paper/journal/JIIS/) follows that plan.
Venue selection is complete; manuscript preparation and scientific admission
remain open. No journal submission is claimed.

`wiki/` is the knowledge foundation: update it before deriving paper content.
No solving or heavy work runs on login nodes; submit such jobs through Slurm.

The separate [prospective pilot](wiki/methods/Prospective-Evaluation.md) implements
history-only candidate scoring and explicit sampling coverage. Its
[Slurm workflow](docs/PROSPECTIVE_PILOT.md) is for technical validation and does
not replace the admitted evidence or establish journal readiness.

The [completed pilot review](wiki/evidence/Prospective-Pilot.md) links preserved
Slurm reports and records historical-negative coverage and ranking limitations.

## Earlier DYU journal working draft

The earlier [LaTeX source and PDF](paper/journal/DYU/Latex_full/) follow the supplied DYU template and contain current result rows alongside retrospective historical analyses. The [DYU journal wiki](wiki/manuscript/DYU-Journal.md) records that draft's status; DYU is no longer the active target. [Recovered historical evidence](wiki/evidence/Recovered-Evidence.md) is organized for reconciliation and is not automatically admitted to the current release or the JIIS paper.

## Repository layout

```text
src/            installable temporal-link-decoupling package
experiments/    dataset builders, controlled runs, and invariant checks
protocols/      frozen scientific protocol and reviewed amendments
configs/        resolved runtime configuration and dependency locks
resources/      fetch-only dataset registry and checksum manifests
evidence/       execution records and release/snapshot plans
results/frozen/ immutable scientific evidence release
paper/snapshots immutable conference manuscript snapshot
paper/conference single preserved conference PDF and Overleaf package
paper/journal   JIIS preparation and the earlier DYU draft
wiki/           methods, claims, evidence, limitations, and workflow
scripts/        release, paper, provenance, and public-history gates
slurm/          scheduler entry points with site settings supplied at submit time
tests/          repository, runner, release, and safety contracts
```

## Installation

Use an isolated environment for local inspection and tests:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
```

The package metadata is suitable for development. Scientific reruns must use
the hashed dependency specification and environment procedure documented in
[`docs/RUNNER_REPRODUCIBILITY.md`](docs/RUNNER_REPRODUCIBILITY.md).

## Data

Dataset bytes are not redistributed. Reviewed URLs, raw digests, processed
digests, and builder identities are recorded in
[`resources/source_registry.json`](resources/source_registry.json). Acquisition
is explicit and fails if downloaded bytes do not match the registry:

Run acquisition, rebuild and substantial dataset checks in a Slurm allocation.

```bash
python experiments/dataset_builders/download.py wikipedia mooc \
  --output-dir resources/corpora
python experiments/dataset_builders/build_coedit.py \
  --input-dir resources/corpora --output-dir resources/corpora
python -m pytest -q tests/test_dataset_acquisition.py
```

## Verification and reproduction

Run the public repository checks from the project root inside a Slurm
allocation when running the full suite or substantial artifact/history audits:

```bash
python -m pytest -q
python scripts/audit_scientific_provenance.py --check-canonical
python scripts/verify_public_history.py
```

These commands validate contracts and frozen artifacts; they do not launch
scientific training. `--require-release` is the later submission-readiness gate
and remains blocked while `paper/CURRENT` is `UNRELEASED`. All solving and heavy
execution is scheduler-only. Site-specific account and partition values are
supplied at submission time:

```bash
sbatch -A <account> -p <partition> \
  --array=<protocol-task-range> \
  --export=ALL,LP_TASK=<protocol-task-id> \
  slurm/scientific_matrix.sbatch
```

The complete execution and reconciliation procedure is documented in
[`wiki/operations/Research-Workflow.md`](wiki/operations/Research-Workflow.md).

## Source provenance

This is a standalone projection of the Link Prediction subtree, not a copy of
the parent monorepo. The public history contains only allowlisted project files.
Original scientific commit identifiers remain in immutable evidence records;
[`evidence/export/COMMIT-EQUIVALENCE.json`](evidence/export/COMMIT-EQUIVALENCE.json)
maps them to content-equivalent public commits under the published projection
policy. The provenance tools resolve either identity and fail closed if the map
is absent, a mapped commit is unavailable, or the policy checksum changes.

## Limitations

- The admitted comparison is specific to the registered datasets, splits,
  seeds, metrics, and implementation.
- Dataset redistribution is disabled; a clean clone must acquire source bytes
  from the registered upstream locations.
- Local proxy models are diagnostics and are not external-baseline evidence.
- The study does not establish causality, state-of-the-art performance, or
  architecture-general irreversibility.

See [`wiki/LIMITATIONS.md`](wiki/LIMITATIONS.md) for the maintained scientific
boundary.

## Citation and license

Citation metadata is provided in [`CITATION.cff`](CITATION.cff).

Unless otherwise noted, project-authored software and supporting material are
licensed under the [BSD 3-Clause License](LICENSE). The exact grant and
exclusions are defined in [`LICENSE-SCOPE.md`](LICENSE-SCOPE.md).

This license does not grant rights to downloaded datasets, third-party
software, external assets, frozen evidence, or conference artifacts. Dataset
bytes are not redistributed; acquisition and rights boundaries are documented
in [`resources/source_registry.json`](resources/source_registry.json) and
[`wiki/governance/License-and-Assets.md`](wiki/governance/License-and-Assets.md).
See [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) for third-party
boundaries.
