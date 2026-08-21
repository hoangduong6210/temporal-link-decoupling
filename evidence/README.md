# Evidence records

This directory contains the execution identities used by current claims and
the plans that assembled the active evidence release and paper snapshot. Each
job record is checksum-registered in `jobs/checksums.sha256`.

Scientific status requires `scientific = true` and every field in
`jobs/SCIENTIFIC_JOB_CONTRACT.md`. Local records can document acquisition,
accounting, or paper assembly, but they cannot create a performance claim.

`export/` records the policy and commit-equivalence map used to create this
standalone public history without making parent-monorepo objects reachable.
