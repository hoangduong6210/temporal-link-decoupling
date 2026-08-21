# Frozen results

`CURRENT` selects the immutable scientific evidence release admitted by
`PROJECT.toml`. The selected release includes checksum-locked protocol,
configuration, data identities, scheduler records, per-task results, attempt
accounting, and aggregate reconstruction.

Mutable run output and legacy imports are intentionally absent from the public
history. A new result must pass the release-plan contract and be frozen under a
new release identifier; existing release bytes are never edited in place.
