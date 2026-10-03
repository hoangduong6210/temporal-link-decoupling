# Auxiliary and backbone controls

The [wiki specification](../wiki/methods/Prospective-Mechanism-Controls.md) and
[P004 protocol](../protocols/prospective_mechanism_v4.toml) own this study.
It contains 60 fits: 2 datasets × 3 seeds × 2 negative-training policies × 5 arms.
Only the registered train/validation prefixes enter the model. The primary
endpoint is fixed-final-epoch validation; checkpoints selected by mean validation
AP remain secondary. Do not select an architecture from these scores as though
they were held-out results.

The [verified CPU runtime](PROSPECTIVE_RUNTIME.md) is mandatory. Set `LP_PYTHON`
to its interpreter. Before any matrix execution, run the complete test suite
with the actual pinned original TGN checkout available. The mechanism tests
exercise unchanged P003 reference training, observation/RNG parity, explicit
freezing, the noaux equivalence invariant and the complete miniature matrix.

Use an isolated clean checkout on scratch, with the registered corpora accessible
through `resources/corpora`. Check inode and byte quota as well as scheduler
resources. Commit the protocol and source before submission:

```bash
mkdir -p results/prospective-pilots
sbatch -A <account> -p <cpu-partition> --array=0-11%2 \
  slurm/prospective_mechanism.sbatch
```

Tasks 0–5 run Wikipedia, tasks 6–11 MOOC; each adjacent task pair runs random/mixed
training at the same seed. Each task runs all 5 arms and atomically records each
completed cell. Attempts and checkpoints are under
`results/prospective-pilots/mechanism/<array>/<task>/`.
Runtime payload is reverified before and after each task. Fixed parameters are
checked by byte hashes at every epoch, while state history still evolves.

Preserve every attempt, checkpoint hash, runtime record and native scheduler
outcome. The matrix is not complete until independent reconciliation reconstructs
all candidates, validation metrics, support/cohorts, checkpoint selection,
paired effects and intervention invariants. Raw reports contain all score rows;
quantitative review belongs under `evidence/development/`, with qualitative
interpretation in wiki before any manuscript derivation.

From a clean committed checkout in Slurm, reconcile all 12 original attempt
directories after terminal successful accounting is available:

```bash
PYTHONPATH=src <environment>/bin/python scripts/reconcile_prospective_mechanism.py \
  <task-0-attempt.json> <task-1-attempt.json> <remaining-task-attempts> \
  --output-dir evidence/development/<new-bundle>/matrix \
  --jobs <source-gate-and-array-job-ids>
```

Keep the selected `.pt` checkpoints and each task's `runtime.json` alongside
the original attempts during reconciliation. The auditor verifies checkpoint
bytes and independently rebuilds the initial parameter groups using a small
node catalogue (this model has no node-indexed trainable parameters), then
recomputes the selected epoch's parameter displacement from the checkpoint.
It reconstructs evaluation candidates from support and independent RNG streams,
not only from agreement between model reports. Public score archives permit
metric reconstruction; repeating the full checkpoint audit also requires the
locally retained checkpoint bytes or a faithful rerun.
