# Resume after local cleanup

Research remains **paused** until the owner requests continuation. The
[canonical wiki handoff](../wiki/status/Pause-and-Resume.md) owns the objective,
scientific boundary and continuation order. This document records the practical
fresh-clone route after the owner requested deletion of the local checkout and
its project symlinks. No old working directory or private Git metadata is required.

## Retrieve the preserved project

```bash
rtk git clone https://github.com/hoangduong6210/temporal-link-decoupling.git
cd temporal-link-decoupling
rtk git status --short --branch
```

Use the full history: past model, runtime and reconciler source commits are
referenced by the evidence. Read `wiki/status/Pause-and-Resume.md` before work.
Commit identity remains `Hoangduong6210 <Hoangduong4316@icloud.com>`; obtain push
authentication separately when needed. No credential is stored in the project.

Git preserves source, wiki, protocols, dependency locks, original runtime
attestations, public raw reports and frozen evidence. It does **not** include
dataset bytes, the original TGN checkout, installed environments, `.pt`
checkpoints, ignored run directories or the former private backup archives.
Cloning restores the research record and code, not a ready-to-run environment.
The earlier backup digests in `pause/pause.json` are historical metadata.
Any scratch remnants outside the deleted checkout are optional, expiring copies;
the route below does not rely on them.

## Prepare only after the owner resumes research

All dependency installation, dataset acquisition, hashing, tests, analysis and
training must run through Slurm. Supply current site account/partition settings
and new scratch paths; do not reconstruct private paths from old chat messages.

1. In a compute allocation, check the public archive with
   `sha256sum -c evidence/development/LP-P-PROSPECTIVE-004/pause/checksums.sha256`.
   Run the canonical provenance and public-history gates from the README.
2. Follow the README data workflow to fetch and checksum Wikipedia and MOOC
   through `experiments/dataset_builders/download.py`. Fetch the clean original
   TGN revision pinned in `configs/tgn-upstream.json`, following
   [the comparator workflow](PROSPECTIVE_DEVELOPMENT.md), and set `LP_TGN_SOURCE`.
3. Follow [the CPU runtime workflow](PROSPECTIVE_RUNTIME.md) with the existing
   hashed lock, CPython 3.9.21 and explicit CPU torch backend. Do not resolve a
   replacement lock merely because the old environment was deleted. If that
   interpreter/platform cannot be reproduced, document the required change
   before registering the replacement condition.
4. Generate and retain a **new** runtime attestation. A new installation prefix
   can change its digest even with identical wheels. Preserve
   `evidence/development/LP-RUNTIME-CPU-001/` unchanged. Register the new attestation
   in a distinct bundle and document a runtime-only amendment in wiki and the
   development protocol before committing the new execution source. The current
   runner reads `protocols/prospective_mechanism_v4.toml` and enforces
   `[runtime].attestation`; merely setting `LP_PYTHON` will not replace that
   historical binding. Do not bypass the verifier or overwrite the old attestation.
5. Run the complete test suite with actual original-TGN integration, including
   `tests/test_mechanism_reconciliation.py`, from clean committed source in Slurm.
   Retain the source commit, complete output, new runtime attestation and native
   accounting. The later reconciler source gate was cancelled before starting;
   its earlier model-source gate does not establish that these tests pass.
6. Preserve the P004 model and scientific design while registering the runtime
   amendment. Start the full `--array=0-11` matrix through
   `slurm/prospective_mechanism.sbatch` in a new output directory, using the new
   verified `LP_PYTHON`. This repeats all 60 fits, including the 10 earlier
   completed fits, rather than relying on missing historical checkpoints or
   mixing runtime conditions. Do not copy partial cells into new attempts.
7. Independently reconcile all new task reports, runtime sidecars and selected
   checkpoints using [the mechanism workflow](PROSPECTIVE_MECHANISM.md).
   Preserve the old reports and cancellations as history. Admit no result until
   the new complete matrix passes its checks, then update wiki interpretation.

The historical model source is
`0fd12eb190577de99314531bb62afc8624f89c8d`; the unvalidated-at-pause reconciler
source is `396704119f44fecfdfbaa4e66dff0425c103c837`. A fresh runtime binding
requires a new committed execution source; do not relabel it as the old run.
Frozen release artifacts and `paper/CURRENT = UNRELEASED` remain unchanged.

The next research goal is still journal readiness under the owner's JCR / Web
of Science JIF Q1 criterion, with metric year and relevant category verified.
Venue eligibility, independent-source evidence, the full study and the
wiki-derived manuscript remain unfinished. These instructions do not resume
the goal or claim a successful new execution.
