# Project scripts

The provenance pipeline is fail-closed:

- `audit_scientific_provenance.py` audits canonical wiki, claim/evidence/job,
  pointer, disclosure, and snapshot contracts.
- `reconcile_scientific_matrix.py` validates every scheduler cell and retained
  attempt before reconstructing the per-seed aggregate.
- `freeze_evidence_release.py` materializes a checksum-closed immutable release
  from a reviewed plan.
- `build_paper_snapshot.py` admits only committed manuscript sources and frozen
  release artifacts, with occurrence-level provenance for every numeric token.

The freeze and snapshot tools update pointers only when `--activate` is supplied
and all prerequisites pass. They stage atomically and refuse overwrites.
