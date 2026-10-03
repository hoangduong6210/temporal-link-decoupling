# Prospective protocol pilot

The [wiki specification](../wiki/methods/Prospective-Evaluation.md) is authoritative.
The [pilot protocol](../protocols/prospective_v1.toml) fixes settings and scope.
This entry point produces technical pilot artifacts, never admitted performance
evidence. It leaves the A003 source, protocol, runtime manifest and release intact.

The adapter reuses the existing model modules, replacing the scored event
representation with a symmetric history-only query transform. Its observation
path retains the legacy auxiliary objective with the legacy prediction term
removed. The scored representation is the only arm-dependent detach boundary.
This is an explicitly changed protocol/model interface, not a metric correction
that can be applied to old result rows.

## Prepare and execute on Slurm

Acquire the checksum-registered Wikipedia and MOOC corpora through the existing
dataset builder in a compute allocation. Install the repository dependencies in
the execution environment. The pilot records installed versions, but does not
claim equivalence to the frozen scientific environment or full dependency-lock
closure; those are required before confirmatory execution.

Commit the source before running. Submit from the repository root:

```bash
mkdir -p results/prospective-pilots
sbatch -A <account> -p <cpu-partition> --array=0-1 slurm/prospective_pilot.sbatch
```

The script uses `python3`, or the interpreter supplied through `LP_PYTHON`.
Each array task runs both coupled and decoupled arms for its dataset. The CPU
pilot is deliberately bounded; its chronological prefix is extended to include
the entire final timestamp group. Split boundaries also preserve timestamp ties.
The complete destination catalogue is treated as externally available metadata.

Outputs go to the ignored `results/prospective-pilots/<array-job>/<task>/`:

- `attempt.json`: source/input/data identities, environment, scheduler fields,
  resolved settings, progress, terminal status and errors if any.
- Arm checkpoints: validation-selected parameters, with hashes in the report.
- Per-regime scores, exact candidate hashes, eligible/scored/skipped counts and
  full-stream observation counts, embedded in the report.

An existing output directory is rejected. Preserve failed attempts and native
`sacct` records; submit a new attempt instead of overwriting. The runner fails
if source or input identities change during execution. Pin the working tree
for the lifetime of the job; do not edit it while the pilot is running.

## Checks and interpretation

Run tests in a Slurm allocation:

```bash
python3 -m pytest -q tests/test_prospective.py
python3 -m pytest -q
python3 scripts/audit_scientific_provenance.py --check-canonical
```

Tests cover pure scoring, candidate permutation/chunk invariance, paired forward
values, separated prediction gradients, identical auxiliary gradients, temporal
ties, valid candidate roles, source-specific historical partners, empty support,
and full-history replay with metric-only inductive filtering.

`COMPLETED_TECHNICAL_PILOT` requires identical initial weights and evaluation
candidates across arms, finite execution and unchanged inputs. The report's
`publication_eligible` stays false. Missing cohorts produce null metrics and an
explicit reason. A successful pilot does not establish superiority, confirm
statistical power or make the manuscript submission-ready.

Before a full run, review pilot diagnostics and cost, then register the full
study, exact runtime lock, comparator implementations, tuning/seed budgets and
independent-source dataset. The old scientific reconciler does not admit this
new protocol; its future release needs its own reviewed execution contract.

The initial execution is preserved in the [development bundle](../evidence/development/LP-P-PROSPECTIVE-001/README.md).
Follow the [canonical pilot review](../wiki/evidence/Prospective-Pilot.md) for its
findings and the next study gate. Run `scripts/review_prospective_pilot.py` on a
Slurm compute node to reconstruct metrics and inspect candidate history,
repeated/new positive cohorts and exploratory recurrence/recency controls.
