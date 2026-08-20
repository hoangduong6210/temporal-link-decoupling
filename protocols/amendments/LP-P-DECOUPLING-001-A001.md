# Protocol amendment LP-P-DECOUPLING-001-A001

Status: accepted for the next confirmatory execution.

## Reason

The migration corpora cannot be reproduced from a reviewed raw identity. The
Wikipedia migration stream is truncated, while other migration artifacts also
differ semantically from deterministic clean-acquisition builds. Legacy result
values therefore remain quarantined and cannot be relabeled as current evidence.

## Changes

- Replace result-era datasets with the current identities in
  `resources/manifest.toml` and bind raw acquisition through
  `resources/source_registry.json`.
- Require the checksum-locked resolved configuration, task profile, dependency
  environment, strict determinism record, scheduler identity, and clean source
  commit before training.
- Define the allowed coupled, decoupled, freeze-then-probe, and temporal-baseline
  task profiles in the protocol.
- Count training epochs only after state-neutral warmup restoration.
- Require complete seed/task/attempt/failure coverage; preserve unsuccessful
  attempts and prohibit silent exclusions.

## Evidence consequence

No pre-amendment performance artifact is eligible for the next release. The
conference snapshot must be generated only from fresh current-corpus jobs and
their frozen aggregate sidecars.
