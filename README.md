# Temporal Link Prediction by Decoupling

This project studies whether preventing the link-prediction loss from shaping
the temporal backbone improves inductive link prediction. Its scope includes
the controlled coupled/decoupled contrast, freeze-then-probe, hard negatives,
and split/leakage controls across CoEdit, Wikipedia, and MOOC. Simplified
temporal-model proxies are quarantined and provide no external-baseline claim.

The repository is independent from the lifecycle-readout project: it owns its
source snapshot, corpora manifests, result history, paper working tree, wiki,
and claim/evidence namespace (`LP-*`). There are no sibling imports.

## Start here

1. Read [wiki/START-HERE.md](wiki/START-HERE.md).
2. Inspect [PROJECT.toml](PROJECT.toml) for release pointers.
3. Install with `python -m pip install -e .` in an isolated environment.
4. Run `python -m pytest -q` for repository contracts.
5. Run `python scripts/audit_scientific_provenance.py --check-canonical` for
   Claim → Evidence → Job, numeric, pointer, snapshot, and disclosure gates.
6. Inspect `LP-E-SCIENTIFIC-MATRIX-001` and the checksum-registered terminal
   reconciliation job for the completed current matrix.
7. Freeze only a reviewed release plan with
   `scripts/freeze_evidence_release.py`; build a paper snapshot only from that
   release with `scripts/build_paper_snapshot.py`.

Scientific execution closure is complete. Publication readiness remains
`BLOCKED` only until the frozen evidence release and checksum-locked paper
snapshot both exist; see `REPRODUCIBILITY.toml`.

Historical binaries are present locally under `resources/corpora/`,
`results/historical/legacy_import/`, and `paper/working/`; their presence does
not make them frozen or paper-eligible. Heavy training must run through an
approved scheduler workflow, not on a login node.

License selection is pending owner review; see
[wiki/governance/License-and-Assets.md](wiki/governance/License-and-Assets.md).
