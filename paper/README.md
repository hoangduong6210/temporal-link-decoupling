# Paper snapshot

`CURRENT` selects the immutable conference snapshot admitted by `PROJECT.toml`.
The selected directory contains manuscript source, rendered output, the frozen
build plan, result lock, numeric-provenance registry, and checksums.

The standalone public history does not include mutable working manuscripts,
legacy figures, or superseded snapshots. New revisions must be built with
`scripts/build_paper_snapshot.py` from a reviewed plan and a frozen evidence
release; existing snapshot directories are never edited in place.
