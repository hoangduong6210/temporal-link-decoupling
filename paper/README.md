# Paper

The active journal target is **JIIS**, with **KAIS** and **IJMLC** as the ordered
fallbacks. The [canonical wiki plan](../wiki/manuscript/JIIS-Journal.md) owns
manuscript positioning, sources and the readiness backlog.

- `journal/JIIS/`: preparation area linked to the wiki; no completed manuscript yet.
- `journal/DYU/`: earlier editable journal draft and exports, preserved for reference.
- `conference/`: author-preserved conference source, rendered PDF, self-contained
  Overleaf package and checksums.

The conference manuscript is not evidence-admitted because its complete result
set is not registered in the current frozen release. Accordingly,
`paper/CURRENT` is `UNRELEASED`; this is a scientific status, not a missing-file
condition.

Manuscript revisions must be written from the canonical wiki claim and evidence
surfaces, then admitted with `scripts/build_paper_snapshot.py`. Editable journal
drafts are permitted; they are not immutable scientific snapshots. Historical
numerical tables in the DYU draft need separate claim admission before reuse.
Run heavy compilation and rendering through Slurm.
