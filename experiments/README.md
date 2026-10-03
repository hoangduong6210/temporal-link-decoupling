# Experiments

`run_model.py` is the coupled/decoupled runner; `run_baselines.py` owns baseline
parity; the remaining scripts are focused ablations imported from the mixed
tree. Install the package first and write mutable output only to
`results/audit/`. Heavy runs are scheduler-only.

`run_prospective_pilot.py` is the separate JIIS protocol-development runner.
It implements pre-event candidate scoring, typed destination sampling and full
history replay under `protocols/prospective_v1.toml`. Its ignored outputs live
under `results/prospective-pilots/`, are explicitly non-publication pilots, and
cannot enter the A003 scientific matrix. See [pilot operations](../docs/PROSPECTIVE_PILOT.md)
and the [canonical specification](../wiki/methods/Prospective-Evaluation.md).

`run_model.py` and `run_baselines.py` resolve their defaults from the tracked
protocol/configuration, use state-neutral optimizer warmup, and emit a job
envelope. See [runner reproducibility](../docs/RUNNER_REPRODUCIBILITY.md).
