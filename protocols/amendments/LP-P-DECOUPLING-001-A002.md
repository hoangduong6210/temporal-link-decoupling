# Protocol amendment LP-P-DECOUPLING-001-A002

Status: accepted before the next confirmatory execution.

## Trigger

The first current-corpus scheduler execution exposed two pre-evidence defects:

- repeated node IDs were committed with duplicate advanced-index writes, which
  do not define a portable winner across accelerator backends;
- implementations registered as external temporal baselines were simplified
  architectural proxies. In particular, the implementation registered as
  GraphMixer was a recurrent node-memory MLP, not the stateless temporal-neighbor
  MLP-Mixer described by Cong et al.

The failed GraphMixer/MOOC attempt and all otherwise completed proxy outputs are
retained in scheduler history, but none is eligible for a claim or aggregate.

## Corrective decisions

- The confirmatory matrix contains only `coupled-end-to-end`, `decoupled`, and
  `freeze-then-probe` tasks over the already frozen dataset/seed study grid.
- `temporal-baselines` remains a discoverable quarantine profile so prior jobs
  can be audited. It is explicitly ineligible for scientific matrix execution
  and publication. Executable keys carry `proxy_`, `diagnostic_`, or the honest
  internal identity `recurrent_mlp_memory`.
- A future external comparator must enter through a new amendment with an
  upstream repository, immutable upstream commit, implementation/license
  lineage, architecture checksum, and independently tested protocol adapter.
- Node-memory scoring uses one pre-batch snapshot. Candidate commits use stable
  chronological input order; for repeated IDs, the final input row wins before
  any indexed tensor assignment. The bipartite-ID invariant prohibits a node
  from occurring in both endpoint roles.
- `causal_batch` denotes replay of deterministic per-pair accumulator channels;
  it does not mean full event-by-event replay of all learned and memory state.
- Non-finite inputs, outputs, loss, gradients, parameters, optimizer state, or
  metric inputs fail the task. Values are never clamped, replaced, skipped, or
  silently omitted from coverage.

## Source comparison record

GraphMixer identity was reviewed against:

- the ICLR conference paper, `https://openreview.net/pdf?id=ayPPc0SyLv1`;
- the author implementation at commit
  `c84f1e0bee4eed848872a966b8166d741e240713`;
- the MIT-licensed DyGLib implementation at commit
  `3aacc36b94b8d2d8293d70a74fdf6d39089b4163`.

No upstream source was copied into this amendment. The author repository did
not present a license file during review; direct vendoring from it is therefore
prohibited unless the owner supplies compatible rights.

## Evidence consequence

Every pre-amendment current-corpus result is superseded. The admissible matrix
must be rerun in full from one clean post-amendment commit, then reconciled with
all failed, excluded, cancelled, and completed attempts retained. Only that
aggregate may be frozen or used to construct a conference snapshot.
