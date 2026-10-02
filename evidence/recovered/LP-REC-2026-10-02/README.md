# Recovered historical evidence

Recovered from the owner's SR-GNN download on 2026-10-02. This is a preservation and reconciliation bundle, not a new training run or an admitted scientific release. Original files are copied byte-for-byte. `recovery-audit.json` records source-relative paths, duplicate aliases, SHA-256 hashes, aggregate checks and comparisons with the current release. `checksums.sha256` covers the bundle.

## Coverage

- 113 distinct JSON artifacts from the link-prediction historical archive, mixed-tree experiment results, and selected frozen-probe/invariant records; 55 duplicate source aliases are recorded rather than copied again.
- Eight legacy experiment/check scripts are retained as unbound interpretation context. They were not executed and are not asserted to be the exact code that produced these results.
- All 53 entries in the historical checksum manifest match the downloaded bytes.
- All 19 files in the current frozen release match the downloaded project byte-for-byte.
- All three current processed corpora match the registered SHA-256 digests. They are restored locally to ignored `resources/corpora/`; dataset bytes are not redistributed in Git.
- 121 supported mean/sample-standard-deviation/count checks were recomputed. 117 match within absolute tolerance 1e-10; four delta summaries differ from their stored, coarsely rounded per-seed arrays. The full discrepancies remain in the audit; no source value was repaired or silently replaced.

## Conference comparison

The CoEdit five-seed B, C and proxy-TGAT summaries recover the rounded conference values 0.9876, +22.8 percentage points and +14.1 percentage points. The corrected v2 hard-negative files recover the reported rounded CoEdit +42.8/+40.5 and Wikipedia +41.6/+42.6 point contrasts. These are arithmetic matches, not provenance admission or faithful external-baseline evidence.

Freeze-then-probe files include distinct Wikipedia versions: the pooled three-seed control and the separate two-seed ID-corrected file must not be combined. PREIDFIX files and older hard-negative variants remain visible for audit. Historical B-versus-C and B-versus-K1 configurations differ from the current A003 shared-head detach contrast. They cannot replace its result matrix.

## Remaining limits

The recovered execution reconciliation explicitly says historical attempts lack exact source commits, raw-data bindings and immutable environment locks. Partial scheduler associations do not close those gaps. Some legacy JSON files contain NaN for unavailable metrics; they are preserved as originally written and must not be treated as strict JSON or finite scientific endpoints without explicit normalization into a separate derived artifact.

The archive includes pilots, failures/negative findings, obsolete variants and simplified proxies. Presence in this bundle is not permission to cite a numerical result as established. Raw prediction arrays/checkpoints and execution logs have not been comprehensively recovered. Irreversibility and a causal identity-shortcut mechanism do not follow from these arithmetic comparisons.

Run `python scripts/verify_recovered_evidence.py` to verify hashes and reconstruct the checked aggregates. The active release, claim registry and paper pointer remain unchanged. Review claim-specific source/configuration/data/scheduler bindings before proposing a new release for the journal.
