# Paper lifecycle

> **QUARANTINED LEGACY WORKING DRAFTS:** Every file under `working/` contains
> unadmitted historical wording. It is not current evidence, permitted claim
> language, or an immutable paper snapshot. Do not submit, cite, or export it.

`working/` contains mutable Paper 1 imports. `snapshots/` is reserved for
immutable exports locked to a frozen evidence release. `CURRENT` remains
`UNRELEASED` until the export contract passes.

Existing DOCX, PDF, and ZIP files may not carry the visible source quarantine
banner and still contain unsupported scalars. Their presence is preservation,
not export permission; the workspace publication gate excludes all of `working/`.

Top-level `figs/` and project-level `figures/generated/` are exact or historical
legacy exports containing embedded numeric labels. They are also quarantined
and cannot be copied into a snapshot. A future figure must be regenerated from
locked evidence and carry a checksum-locked numeric sidecar plus its plot job.
