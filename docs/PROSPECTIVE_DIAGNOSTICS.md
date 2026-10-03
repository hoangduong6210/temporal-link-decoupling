# Sampling and gradient diagnostics

The [wiki specification](../wiki/methods/Prospective-Diagnostics.md) and
[registered protocol](../protocols/prospective_diagnostics_v3.toml) own this study.
It uses train/validation only, retaining the prior prefix partitions and closed
destination catalogue. Test events are removed before model construction.

The matrix contains 36 fits: two datasets, three seeds, two training policies,
and bounded coupled/decoupled plus original-module TGN. Both policies score one
negative per eligible positive; the mixed policy chooses historical negatives
with probability 0.5 where support exists, and explicitly uses a random-only
stratum otherwise. The unchanged evaluation regimes never fall back.

Use the registered external TGN checkout described in
[the comparator workflow](PROSPECTIVE_DEVELOPMENT.md). Keep it clean and set
`LP_TGN_SOURCE` to its absolute local directory. Select the Python interpreter
with `LP_PYTHON`. Scientific runtime hash-locking is still an open gate; this
development runner records installed package versions.

Run checks through Slurm with the actual external checkout:

```bash
PYTHONPATH=src python3 -m pytest -q
python3 scripts/audit_scientific_provenance.py --check-canonical
```

Skipped integration tests do not satisfy the source gate. The new contracts
check candidate eligibility, explicit support strata, matched random streams,
gradient accumulation measurements, unchanged training under instrumentation,
validation-only input boundaries and the complete miniature matrix.

From an isolated, clean committed checkout with registered corpora available:

```bash
mkdir -p results/prospective-pilots
sbatch -A <account> -p <cpu-partition> --array=0-5%2 slurm/prospective_diagnostics.sbatch
```

Tasks 0–2 execute Wikipedia seeds 1–3; tasks 3–5 execute MOOC seeds 1–3.
Each task runs every registered model/policy pair and writes an atomic report
after each completed cell under
`results/prospective-pilots/diagnostics/<array>/<task>/attempt.json`.
Selected checkpoint files remain alongside those reports. Never edit the
execution checkout or overwrite an attempt during a run.

Primary comparisons use fixed-final-epoch validation scores, not the selected
checkpoint's score. The saved secondary checkpoint uses the predeclared mean
validation AP across regimes; all epoch scores remain visible. A larger
validation-selected value is not held-out performance or confirmatory evidence.

Gradient records measure the prediction gradient and the auxiliary accumulation
increment on the same training step before the optimizer update. Undefined
cosines remain null. These descriptive associations do not prove that an
auxiliary term causes better or worse generalization. Decoder snapshots retain
probabilities, sigmoid slopes, parameter displacement and actual gradient RMS;
the initialization is unchanged in this study.
