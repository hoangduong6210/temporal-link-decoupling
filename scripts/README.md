# Project scripts

The provenance pipeline is fail-closed:

- `audit_scientific_provenance.py` audits canonical wiki, claim/evidence/job,
  pointer, disclosure, and snapshot contracts.
- `reconcile_scientific_matrix.py` validates every scheduler cell and retained
  attempt before reconstructing the per-seed aggregate.
- `freeze_evidence_release.py` materializes a checksum-closed immutable release
  from a reviewed plan. It verifies ledger source artifacts by bytes, recomputes
  exact attempt accounting, requires terminal Slurm coverage, reconstructs
  aggregates, and copies all of those inputs into the release.
- `build_paper_snapshot.py` admits only committed manuscript sources and frozen
  release artifacts, with occurrence-level provenance for every numeric token.
  Each scientific literal is recomputed from a strict JSON selector and exact or
  declared half-even-rounded value assertion; declared checksums alone are not
  accepted.
- `numeric_evidence.py` is the shared strict selector, finite-decimal, transform,
  rounding, and ambiguous-number validator used by both the builder and the
  independent canonical auditor.

The freeze and snapshot tools update pointers only when `--activate` is supplied
and all prerequisites pass. They stage atomically and refuse overwrites.

The current conference manuscript is preserved under `paper/conference/` but is
not evidence-admitted. Continuous integration therefore runs the canonical
consistency audit; the stricter release gate remains blocked until a future
wiki-derived manuscript has complete numeric provenance.
