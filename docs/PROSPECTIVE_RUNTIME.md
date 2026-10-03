# Prospective CPU runtime

The [wiki contract](../wiki/methods/Prospective-Runtime.md) owns the scientific
boundary. This runtime is CPython 3.9.21 on Linux x86_64, with the resolver
targeting manylinux_2_28 and PyTorch 2.8.0+cpu. It is separate from the frozen
CUDA runtime. The original TGN revision remains pinned in `configs/tgn-upstream.json`.

Resolve only when deliberately creating a new lock, in Slurm:

```bash
uv pip compile configs/prospective-requirements-py39-cpu.in \
  --generate-hashes --python-version 3.9 \
  --python-platform x86_64-manylinux_2_28 --torch-backend cpu \
  --no-build --emit-index-url --output-file <new-lock-path>
```

The initial resolver is uv 0.11.28. Keep the chosen lock immutable for an
execution; do not resolve again at job startup. Review transitive changes before
registering a replacement. The generated lock includes wheel hashes, including
the CPU torch build. uv's emitted index line alone does not select that build:
**pass `--torch-backend cpu` during installation as well as resolution.**

Install into a new scratch directory in Slurm, with no ambient `PYTHONPATH`:

```bash
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
unset PYTHONPATH
uv venv --python <CPython-3.9.21-executable> <new-scratch-environment>
uv pip sync --python <new-scratch-environment>/bin/python \
  --require-hashes --no-build --torch-backend cpu \
  configs/prospective-requirements-py39-cpu.lock
uv pip check --python <new-scratch-environment>/bin/python
```

Before initial validation, use a clean committed project checkout. Supply the
clean original TGN checkout in `LP_TGN_SOURCE`. In a compute allocation:

```bash
export PYTHONPATH="$PWD/src" PYTHONHASHSEED=0
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
<environment>/bin/python scripts/check_prospective_runtime.py \
  --output <new-attestation.json>
<environment>/bin/python -m pytest -q
<environment>/bin/python scripts/audit_scientific_provenance.py --check-canonical
```

Keep native accounting and source-gate output. Hash the attestation into the
execution record. Before later jobs reuse the same installed environment:

```bash
<environment>/bin/python scripts/check_prospective_runtime.py \
  --expect <registered-attestation.json> --output <new-job-attestation.json>
```

The verification is intentionally performed on compute nodes; it hashes the
installed packages and Python payload. A successful package lock does not admit
model results or close manuscript readiness. Original TGN integration tests
must actually run, with no integration skips.
