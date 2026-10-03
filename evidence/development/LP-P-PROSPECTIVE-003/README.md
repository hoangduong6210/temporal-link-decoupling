# Validation-only sampling and gradient diagnostics

**Development evidence only; not a publication release.** The
[wiki review](../../../wiki/evidence/Prospective-Diagnostics.md) owns the
interpretation. The registered protocol is
[LP-P-PROSPECTIVE-003](../../../protocols/prospective_diagnostics_v3.toml).

## Completed execution and audit

All 36 fits completed: Wikipedia/MOOC × seeds 1/2/3 × random/mixed training
negatives × bounded-coupled/bounded-decoupled/original-module TGN. Each fit uses
2 epochs of the registered prefix. Test events and attributes are removed
before constructing models. The primary endpoint is final-epoch validation;
the validation-selected checkpoint is a separately labeled secondary result.

| Record | Identity |
|---|---|
| Model/protocol source | `3852ac236372dac864b624869db97e55b43aae74` |
| Model source gate | Slurm `7650663`: 97 tests passed, none skipped; canonical and public-history checks passed |
| Selected Wikipedia tasks | `7650669_0`, `7650669_1`, `7650669_2`: completed, exit `0:0` |
| Selected MOOC retries | `7651259_3`, `7651259_4`, `7651259_5`: completed, exit `0:0` |
| Reconciler source | `dd34c73aa5a22b70836bc05f5195128cfaf82fcd` |
| Reconciler source gate | `7651262`: 98 tests passed, none skipped; canonical check passed |
| Independent Wikipedia preflight | `7651319`: 18 cells passed |
| Complete reconciliation | `7651272`: completed; all registered cells passed |
| Table/validation archive | `7651292`: completed |
| Original TGN revision | `d55bbe678acabb9fc3879c408fd1f2e15919667c` |

The auditor reconstructs every training candidate/RNG trace, evaluation
candidate exclusion, cohort, AP/AUC and paired comparison. It verifies matched
initial parameters across routing and policy within each model family and seed,
shared candidate traces, secondary checkpoint selection, diagnostic consistency,
committed dependencies and successful terminal accounting for selected tasks.

## Results and limits

[Complete tables](tables.md) are rendered from the
[audited summary](matrix/summary.json). Values below are final-epoch validation
means ± sample SD over the 3 registered training seeds, not confidence intervals.

- MOOC historical AP over the supported cohort rises with mixed training:
  bounded coupled `0.4690 ± 0.0630` → `0.8596 ± 0.0029`, bounded detached
  `0.4253 ± 0.0178` → `0.8697 ± 0.0053`, TGN `0.3990 ± 0.0100` →
  `0.6907 ± 0.0237`. All these models lose mean AP on random and novel-pair
  evaluation under mixed training. This is a sampling-dependent tradeoff.
- Wikipedia historical AP rises for the bounded models: coupled
  `0.3524 ± 0.0297` → `0.5690 ± 0.1162`, detached `0.3338 ± 0.0046` →
  `0.6717 ± 0.1317`; TGN changes from `0.7050 ± 0.0084` to
  `0.6787 ± 0.0501`. Sparse support prevents a broad superiority conclusion.
- Historical candidate support is `54 / 300` Wikipedia validation events and
  `20 / 171` inductive events; MOOC support is `264 / 300` and `108 / 144`.
  Random and novel-pair regimes cover all eligible events. Inductive here means
  an endpoint absent from training, unlike P002's test definition.
- The AP sampling-by-routing interaction, in percentage points, is
  `12.1253 ± 3.4815` on Wikipedia's complete historical support and
  `5.3753 ± 6.5921` on MOOC's. Wikipedia interactions are positive at all
  seeds, including inductive filtering; MOOC's historical direction varies by
  seed. MOOC novel-pair interactions are negative at all seeds. The complete
  per-seed contrasts and secondary selected-checkpoint results remain visible.
- On Wikipedia inductive historical evaluation, recency AP is `0.5908`, above
  mixed-training learned-model means: coupled `0.4842`, detached `0.5563`,
  TGN `0.4431`. This control constrains the interpretation of the sparse cohort.
- At final-epoch coupled CSN probes, mean prediction norms range from about
  `0.016` to `0.020`, versus auxiliary increments about `0.000038` to
  `0.000131`. Defined CSN cosines are sometimes negative. Measured context
  increments are zero and DRGC increments are extremely small. These dependent
  observations, subject to floating-point subtraction and Adam dynamics, do not
  identify harmful gradient conflict. Detached prediction-backbone gradients
  are zero by construction, not evidence of a beneficial mechanism.
- Every bounded fit records nonzero decoder gradient RMS and log-odds movement.
  Small final sigmoid slopes alone therefore cannot establish a vanishing
  end-to-end loss gradient or justify a selected initialization change.

The prefixes were already inspected. Final-epoch validation is development
evidence even though it avoids checkpoint selection for the primary contrast.
The closed destination catalogue, compact budget, adapted TGN protocol and
unlocked prospective runtime remain limitations. Training seeds are not
independent datasets or independent temporal observations. No test evidence,
significance, deployment calibration or architecture-general claim is admitted.

## Preserved storage failure and retry chain

Original MOOC task `7650669_3` failed with `OSError: [Errno 122] Disk quota
exceeded` while writing its temporary report. Its last atomic report still says
`STARTED`; [that partial report](failed/mooc-seed-1-partial.json) is preserved
byte-for-byte and excluded from the matrix. The original private log contains
site paths; its digest, rather than those paths, is public in
[validation.json](validation.json).

Original tasks `7650669_4` and `7650669_5` and validation job `7651228` ended
with native `FAILED` / `0:53` states. No successful fit or source check is inferred
from them. Dependent jobs `7651229` and `7651241` were cancelled. Slurm job
`7651253` relocated only project-owned isolated worktrees and outputs to scratch,
repaired worktree metadata and retained old path aliases. The successful MOOC
retry used the same source, data and scientific settings. Full states appear in
[terminal validation accounting](validation-slurm-accounting.tsv) and
[matrix accounting](matrix/slurm-accounting.tsv).

## Artifact verification

- `matrix/{dataset}-seed-{seed}.json`: successful byte-preserved raw reports,
  all epoch scores, negative traces, diagnostic probes, package metadata and
  checkpoint/input hashes.
- [Summary](matrix/summary.json): independent reconstruction, all supported
  cohorts and paired routing/sampling contrasts.
- [Validation history](validation.json), [model source log](model-source-validation.txt)
  and [reconciler source log](reconciler-source-validation.txt): source gates and
  failed/selected attempt boundaries.

Checkpoint bytes remain in local scratch job output; hashes are in raw reports.
Data and original TGN source remain fetch-only. Run verification in Slurm:

```bash
sha256sum -c evidence/development/LP-P-PROSPECTIVE-003/matrix/checksums.sha256
sha256sum -c evidence/development/LP-P-PROSPECTIVE-003/validation-checksums.sha256
python3 scripts/render_prospective_diagnostics.py \
  --summary evidence/development/LP-P-PROSPECTIVE-003/matrix/summary.json \
  --output evidence/development/LP-P-PROSPECTIVE-003/tables.md --check
```

The [workflow](../../../docs/PROSPECTIVE_DIAGNOSTICS.md) explains repeat execution.
The frozen release `LP-REL-2026-A003-001` and `paper/CURRENT = UNRELEASED` remain
unchanged. This archive does not make the journal submission ready.
