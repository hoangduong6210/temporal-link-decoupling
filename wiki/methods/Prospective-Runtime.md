---
title: Isolated Prospective CPU Runtime
status: hash-installed candidate; committed-source verification pending
last_updated: 2026-10-03
paper_source: false
---

# Isolated Prospective CPU Runtime

The prospective study now has a separate generated
[CPU dependency lock](../../configs/prospective-requirements-py39-cpu.lock).
It does not modify the frozen release's accelerator lock or relabel earlier
development runs as hash-locked execution.

The [direct inputs](../../configs/prospective-requirements-py39-cpu.in) retain
the established scientific-library versions, select an explicit CPU tensor
library build, and include the test and rendering dependencies. The resolver
pins transitive versions and artifact hashes for the recorded Python ABI and
platform. Install from the hashed lock into an isolated environment without
system or user site-packages; the abstract input is not an installation lock.
The [workflow](../../docs/PROSPECTIVE_RUNTIME.md) owns exact operational commands.

## Verification contract

Require the registered interpreter patch version, CPU platform and package set.
The runtime verifier checks installed distribution RECORD hashes, records an
installed-payload digest, and binds the base interpreter, Python shared library
and standard-library payload. It also records the C-library version. Full
tests with the pinned original TGN implementation must pass from committed
source before using the environment for new science.

Subsequent jobs compare their runtime attestation against the registered
installation before execution. The attestation binds the particular installed
environment, including generated entry-point scripts. A fresh installation at
another location needs its own verified attestation; it is not expected to have
an identical digest merely because it uses the same wheel lock.

This is a package lock and environment attestation, not a container image or a
guarantee of bitwise equality across CPU hardware. Preserve host, thread count,
determinism settings and native scheduler metadata per run. All installation,
runtime hashing, tests and execution go through Slurm on scratch storage.

## Scientific boundary

Changing from the earlier mixed system environment to an isolated CPU build is
a new runtime condition. Rerun matched reference arms alongside new controls;
do not subtract old-environment scores as if they were paired controls. Preserve
the earlier packages, raw scores and limitations in their original bundles.
The existing immutable release and paper pointer remain unchanged.
