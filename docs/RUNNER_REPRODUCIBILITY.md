# Runner reproducibility

The link-prediction runners consume `configs/default.toml` and
`protocols/link_prediction_v1.toml`; CLI values are explicit overrides recorded
in the output job envelope. Dataset and seed subsets are scheduler tasks within
the protocol. Training, optimizer, or determinism overrides mark the execution
as protocol-deviating.

Scientific scheduler jobs must set process-start determinism before Python is
launched:

```bash
uv pip sync configs/scientific-requirements-py39-cu128.lock
python -m pip install --no-deps -e .
export PYTHONHASHSEED=0
export CUBLAS_WORKSPACE_CONFIG=:4096:8
export LP_JOB_ID=LP-JOB-<REGISTERED-ID>
python experiments/run_model.py --config configs/default.toml \
  --protocol protocols/link_prediction_v1.toml --task-id decoupled \
  --design correct_decoupled --p0_fix off --fsm_arch v3 --fsm_decode hier \
  --decol_hier_v2 --causal_batch --hier_causal_policy \
  --lambda_edge_trans 0.5
```

The protocol owns three publication-matrix profiles: `coupled-end-to-end`,
`decoupled`, and `freeze-then-probe`. Main-arm profiles validate every
model-semantic flag exactly. The discoverable `temporal-baselines` profile is a
quarantine registry for simplified proxies and aborts before scientific
execution; it cannot support a baseline or paper claim. Dataset and seed subsets remain valid
scheduler-array decomposition. Missing or mismatched `--task-id` is recorded as
a startup blocker; a registered scientific scheduler job persists the failure
and exits before training when any startup blocker exists.

The warmup is a real forward/backward/optimizer pass for kernel initialization,
but model parameters and buffers, optimizer slots, RNG streams, and temporal
stores are restored afterward. It therefore contributes no hidden training
epoch.

Stateful models score a mini-batch from one pre-batch snapshot. Repeated node
IDs are reduced in stable chronological input order before indexed assignment,
with the final row providing the committed candidate. This is batch-snapshot
semantics, not full event-by-event replay. Inputs, outputs, losses, gradients,
parameters, optimizer slots, and metric inputs are finite-checked; any violation
fails the task without value replacement or task omission.

Every output JSON contains resolved file hashes, CLI arguments, source state,
scheduler identity, deterministic settings, environment versions, expected and
observed task coverage, and failure records. This metadata is necessary but not
sufficient for evidence admission.

CUDA jobs also record the visible device index, accelerator name and compute
capability, memory and processor topology, UUID, PCI bus identity, driver,
runtime, and cuDNN version. A scientific scheduler job exits before training if
that accelerator record cannot be completed.

`configs/dependencies.lock` remains a bootstrap constraint set and is never used
as scientific proof. The config and protocol instead pin the reviewed
`scientific-requirements-py39-cu128.lock` by SHA-256. At startup the runner
compares every locked distribution version plus Python ABI, platform and
PyTorch/CUDA stack with the active environment and records a canonical
environment digest. A registered scheduler run fails before training when that
exact comparison does not close.

Submit the reviewed scheduler arrays through `slurm/scientific_matrix.sbatch`.
After all attempts terminate, run `slurm/reconcile_scientific_matrix.sbatch`
with an `afterany` dependency on every array. The reconciler retains all attempts,
requires a successful final attempt for each protocol cell, verifies every
parent source/input/environment/accelerator binding, and reconstructs means and
sample standard deviations from the per-seed rows. Only its complete scheduler
result and attempt ledger may feed the evidence freeze gate.
