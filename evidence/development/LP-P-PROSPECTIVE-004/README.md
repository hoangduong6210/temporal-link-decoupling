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
alongside task runtime attestations. At the original pause, selected checkpoints,
task outputs and the installed CPU environment were backed up inside private
Git metadata. The owner's later local-cleanup request includes those private
archives. They were never uploaded to GitHub. Raw data and third-party source
remain fetch-only. The checksum-closed `pause.json` is an immutable record of
the earlier pause, not a statement of current private-backup availability.

The default [fresh-clone workflow](../../../docs/RESUME_FROM_CLONE.md) now
rebuilds and registers the runtime, validates the reconciler and reruns all
12 tasks / 60 fits into a **new** array directory. The earlier 10 fits and
4 partial-task cells remain historical reports; they are not spliced into a
new-runtime matrix. Old checkpoint hashes do not reconstruct checkpoint bytes.

After all new tasks complete, reconcile their matched-runtime reports and
checkpoints, retaining the original pause and cancellation history separately.
Do not overwrite any original attempt. No aggregate, performance claim or
manuscript result is admitted from the current partial study.

Handoff integrity can be checked through Slurm:

```bash
sha256sum -c evidence/development/LP-P-PROSPECTIVE-004/pause/checksums.sha256
```

The earlier frozen release and `paper/CURRENT = UNRELEASED` are unchanged.
