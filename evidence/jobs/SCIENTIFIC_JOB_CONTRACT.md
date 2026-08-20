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
- evidence IDs, claim IDs, and numeric-occurrence IDs it supports.

Missing, failed, retried, and excluded tasks remain in the denominator. A job
record is immutable after checksum registration; corrections create a new job
record that names the record it supersedes.
