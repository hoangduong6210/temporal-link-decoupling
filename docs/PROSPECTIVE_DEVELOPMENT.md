# Prospective development matrix

The [wiki contract](../wiki/methods/Prospective-Development.md) is canonical.
This development study compares legacy and bounded probability decoders, each
coupled and detached, plus the original-module TGN comparator. The protocol
registers Wikipedia/MOOC prefixes, seeds 1/2/3 and two epochs: 30 trained cells.
Results remain non-admitted even if every cell succeeds.

Fetch the original comparator outside the public source tree and pin its commit:

```bash
git clone https://github.com/twitter-research/tgn <external-tgn-directory>
git -C <external-tgn-directory> checkout d55bbe678acabb9fc3879c408fd1f2e15919667c
export LP_TGN_SOURCE=<external-tgn-directory>
```

Use an absolute path for the environment variable. No third-party code is
vendored. Keep upstream clean; the wrapper checks the registered revision and
rejects conflicting import namespaces. Install project dependencies in the
execution environment. `LP_PYTHON` can select its interpreter.

Run the following only inside a Slurm compute allocation:

```bash
PYTHONPATH=src python3 -m pytest -q tests/test_upstream_tgn.py tests/test_bounded_prospective.py
```

Original-API score parity and query-purity integration tests must run with the
actual external checkout; skipped tests do not satisfy the comparator gate.
The bounded-head tests expose the legacy clamp's zero gradient and verify
finite log-space behavior, matched initial probabilities, checkpoint separation
and the intended query-gradient boundary.

From a clean, committed, isolated project checkout with the checksum-registered
corpora present, submit:

```bash
mkdir -p results/prospective-pilots
sbatch -A <account> -p <cpu-partition> --array=0-1 slurm/prospective_development.sbatch
```

Each dataset task executes every registered model and seed. It writes an atomic
`attempt.json` after each completed cell under
`results/prospective-pilots/development/<array>/<task>/`, plus selected checkpoints.
Failures retain completed cells and an explicit terminal error. Reruns require
new output directories; never overwrite an attempt or silently omit cells.

The runner fixes PyTorch threads explicitly, checks common evaluation candidate
hashes, coupled/decoupled initialization parity and complete history replay,
and verifies source/input/upstream identities again at completion. Do not edit
the execution checkout during a run. Preserve terminal `sacct` accounting before
archiving and interpreting results.

## Reconciliation and reproducible tables

After terminal scheduler accounting is available, run the reconciler through
Slurm from clean, committed project source with the registered corpora present:

```bash
PYTHONPATH=src python3 scripts/reconcile_prospective_development.py \
  <wikipedia-attempt.json> <mooc-attempt.json> \
  --output-dir evidence/development/<new-bundle-id>/matrix \
  --jobs <comma-separated-scheduler-job-ids>
```

Include the model array and unsuccessful attempts in the job list. The output
directory must not already exist. The reconciler verifies source/input identity,
all registered cells, initial weights, common training/evaluation candidates,
checkpoint choice, full-history observation, candidate eligibility and cohort
membership. It recomputes metrics from scored rows and refuses incomplete or
non-successful model tasks. It preserves raw reports without changing bytes.

Reproduce the archived descriptive tables, also in a Slurm allocation:

```bash
python3 scripts/render_prospective_development.py \
  --summary evidence/development/LP-P-PROSPECTIVE-002/matrix/summary.json \
  --output evidence/development/LP-P-PROSPECTIVE-002/tables.md --check
```

Omit `--check` only when creating a new table path; existing files are protected
against replacement. The [completed bundle](../evidence/development/LP-P-PROSPECTIVE-002/README.md)
retains exact execution identities, failures, checksums and quantitative results.
The [wiki review](../wiki/evidence/Prospective-Development.md) owns interpretation
and remaining full-study gates. This workflow does not admit publication claims.
