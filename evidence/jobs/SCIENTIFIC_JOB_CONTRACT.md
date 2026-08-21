# Scientific execution-job contract

The local `LP-JOB-LOCAL-*` records are structural audit records and must set
`scientific = false`. They cannot support an admitted performance claim.

A scientific job record is eligible only when it binds all of the following:

- a clean, committed source identity;
- exact protocol, resolved configuration, runner, dependency, environment, and
  dataset checksums;
- scheduler allocation, array task, attempt, seed, and upstream job identities;
- declared, completed, failed, and explicitly excluded task matrices;
- raw and aggregate result paths with checksums;
- a schema-v2 attempt ledger whose source accounting artifacts are opened,
  checksum-verified, and included in the frozen payload;
- exact accounting fields recomputed from retained scientific and quarantined
  attempts rather than trusted from declarations;
- a terminal Slurm accounting capture with exact logical/raw job coverage,
  successful states, exit codes, and timestamps for every selected task and the
  reconciliation job;
- evidence IDs, claim IDs, and numeric-occurrence IDs it supports.

Missing, failed, retried, and excluded tasks remain in the denominator. A job
record is immutable after checksum registration; corrections create a new job
record that names the record it supersedes.
