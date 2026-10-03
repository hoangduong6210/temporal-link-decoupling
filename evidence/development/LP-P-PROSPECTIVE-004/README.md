# Paused auxiliary/backbone control study

**Paused at the owner's request; incomplete and not independently reconciled.**
The canonical [resume handoff](../../../wiki/status/Pause-and-Resume.md) records
the continuation order. Do not interpret this archive as a complete experiment.

| Item | State at pause |
|---|---|
| Protocol | `LP-P-PROSPECTIVE-004`, 60 planned fits |
| Model source | `0fd12eb190577de99314531bb62afc8624f89c8d` |
| Model source gate | Slurm `7651476`: 109 tests passed, none skipped; runtime, canonical and public-history checks passed |
| Completed tasks | `7651485_0` and `7651485_1`: Wikipedia seed 1, random and mixed training, 5 arms each |
| Fits in completed tasks | 10 of 60; these still require independent reconciliation |
| Interrupted tasks | `7651485_2` and `7651485_3`: each atomic report records 2 cells and still says `STARTED`; native state is cancelled |
| Never-started tasks | Array indices 4–11, cancelled while pending |
| Reconciler source | `396704119f44fecfdfbaa4e66dff0425c103c837` |
| Reconciler validation | `7651509`, cancelled before start; new reconciler tests have not run |
| Actual-result preflight | `7651514`, cancelled before start |
| Pause archive | `7651532`, completed; archival work only, no training or result analysis |

The [pause record](pause/pause.json) binds every retained report, task status,
source and private-backup digest. The [native accounting](pause/slurm-accounting.tsv)
retains cancellation states and exit codes. The [model-source log](pause/model-source-validation.txt)
proves the earlier gate, not the later unexecuted reconciler gate.

Raw successful and partial reports were copied byte-for-byte into `pause/`,
alongside task runtime attestations. Selected checkpoints and all task outputs
are also backed up privately in a persistent archive. A separate private archive
preserves the installed CPU environment; restore instructions are in this
checkout's Git metadata. Raw data and third-party source remain fetch-only.
The private backups are local, not uploaded as part of this public Git archive.

On resumption, validate the reconciler first and audit completed tasks 0–1.
Then rerun indices 2–11 from the pinned model source into a **new** array directory.
The 4 cells in partial tasks are retained for history, not spliced into a
complete task or silently resumed. If the runtime cannot be restored and
reverified, register the changed condition and rerun matched references.

After all tasks complete, reconcile the original successful task reports with
the successful retry reports, retaining the full cancellation history. Do not
overwrite any original attempt. No aggregate, performance claim or manuscript
result is admitted from the current partial study.

Handoff integrity can be checked through Slurm:

```bash
sha256sum -c evidence/development/LP-P-PROSPECTIVE-004/pause/checksums.sha256
```

The earlier frozen release and `paper/CURRENT = UNRELEASED` are unchanged.
