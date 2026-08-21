# Paper snapshot

`CURRENT` selects the immutable conference snapshot admitted by `PROJECT.toml`.
The selected directory contains manuscript source, rendered output, the frozen
build plan, result lock, numeric-provenance registry, and checksums.

The standalone public history excludes mutable working manuscripts and legacy
figures. Earlier immutable snapshots remain available after they are
superseded. New revisions must be built with `scripts/build_paper_snapshot.py`
from a reviewed plan and a frozen evidence release; existing snapshot
directories are never edited in place.
