# Experiments

`run_model.py` is the coupled/decoupled runner; `run_baselines.py` owns baseline
parity; the remaining scripts are focused ablations imported from the mixed
tree. Install the package first and write mutable output only to
`results/audit/`. Heavy runs are scheduler-only.

`run_model.py` and `run_baselines.py` resolve their defaults from the tracked
protocol/configuration, use state-neutral optimizer warmup, and emit a job
envelope. See [runner reproducibility](../docs/RUNNER_REPRODUCIBILITY.md).
