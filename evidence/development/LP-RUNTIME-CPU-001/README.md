# Isolated prospective CPU runtime validation

The [wiki runtime contract](../../../wiki/methods/Prospective-Runtime.md) owns
the interpretation. This is environment validation, not model performance.

- CPython 3.9.21, Linux x86_64, PyTorch 2.8.0+cpu; 36 exact dependency pins
  installed with required artifact hashes and no source builds.
- Installer Slurm `7651441` completed. Source gate `7651454` tested commit
  `091ae8e1cb136190a077bde12776e5a31a9fa704`: **101 passed, none skipped**,
  including original TGN integration. Canonical and public-history audits passed.
- Slurm `7651458` archived the [runtime attestation](runtime.json),
  [source-gate log](source-validation.txt), [validation record](validation.json)
  and [native accounting](slurm-accounting.tsv).
- Earlier install attempt `7651436` failed because the installer lacked the
  explicit CPU-backend flag; verifier attempt `7651446` failed on duplicate
  physical-directory aliases. Both are preserved in the validation record.
  Diagnostic job `7651452` identified the lib/lib64 alias; the corrected verifier
  deduplicates resolved directories while retaining detection of distinct installs.

The installation digest binds this environment, including entry-point scripts.
A different installation location has its own attestation. The package lock is
portable within the stated ABI/platform constraints; it is not a container or
a guarantee of identical floating-point results across CPU hardware.

Verify through Slurm from the repository root:

```bash
sha256sum -c evidence/development/LP-RUNTIME-CPU-001/checksums.sha256
<environment>/bin/python scripts/check_prospective_runtime.py \
  --expect evidence/development/LP-RUNTIME-CPU-001/runtime.json
```

The [operational workflow](../../../docs/PROSPECTIVE_RUNTIME.md) documents clean
installation and validation. Earlier development runs retain their recorded
runtime limitations; matched reference arms must be rerun in this environment.
