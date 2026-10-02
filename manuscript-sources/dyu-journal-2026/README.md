# Da-Yeh journal author draft

This directory contains a complete English author-review manuscript with a Traditional Chinese title, abstract and keywords, prepared from the canonical wiki for the Journal of Science and Engineering Technology. It is not submitted and is not an evidence-admitted immutable paper snapshot.

## Files

- `DYU_Journal_Manuscript.docx`: editable, template-derived manuscript.
- `manuscript.txt`: auditable source; each line is a paragraph role, a tab and its text. Table cells are separated with pipes.
- `build_docx.py`: builds from the supplied journal template after conversion to DOCX, preserving unedited package parts.
- `verify_manuscript.py`: checks frozen checksums, recomputes the AP summaries, verifies every numeric token, and checks source-to-DOCX text and section geometry.
- `numeric-provenance.jsonl`, `verification.json`, `source-lock.json`: author-draft provenance and validation.
- `SUBMISSION_NOTES_VI.txt`: Vietnamese handoff, remaining author information, and submission requirements.
- `template-contract.txt`: source-template style and adaptation record.

## Scientific scope

Canonical source commit: `0603f993127f116cfc03608a36825bd327bfc8ec`.
Evidence release: `LP-REL-2026-A003-001`.
Admitted claim: `LP-C-DECOUPLING-001`.
Evidence: `LP-E-SCIENTIFIC-MATRIX-001`.
Scientific execution/reconciliation job: `LP-JOB-SLURM-A003-FINAL-RECONCILE-R2`.

Only the admitted inductive AP mean, sample SD and selected seed denominator are used as numerical performance evidence. Hyperparameters are traced to the frozen protocol. No new training was run. Historical conference numbers, hard-negative results, simplified baseline comparisons, significance claims and irreversibility claims are not imported.

The user confirmed that the conference manuscript has not been accepted or published. This is therefore a new journal manuscript based on the current evidence, not an asserted extension of a published conference paper. Submission elsewhere and coauthor approval still need author confirmation.

## Build and verify

Use the Codex bundled Python runtime with `lxml`. Convert the supplied `Template/稿件格式.doc` with the bundled LibreOffice, then run from the repository root:

```sh
python manuscript-sources/dyu-journal-2026/build_docx.py --template /absolute/path/to/converted-template.docx --output manuscript-sources/dyu-journal-2026/DYU_Journal_Manuscript.docx
python manuscript-sources/dyu-journal-2026/verify_manuscript.py
python scripts/audit_scientific_provenance.py --check-canonical
```

Render the DOCX with the Documents skill's `render_docx.py`. Font configuration must expose a Traditional Chinese font; the original MingLiU setting is retained in the DOCX and Songti TC was used as a local rendering fallback. The 9-page final render was inspected. The manuscript uses the template's A4 margins, Times New Roman sizing, body columns and line spacing. English abstract is first and Chinese translation is last, following the journal's written instructions. Instructional sample drawings and fictitious publication metadata were removed.

## Formal release boundary

`paper/CURRENT` deliberately remains `UNRELEASED`. The author-draft verifier does not replace `scripts/build_paper_snapshot.py` or `scripts/audit_scientific_provenance.py --require-release`.

The current source annotations include checksum-bound TOML protocol selectors. The formal snapshot verifier accepts only scalar JSON selectors owned by a registered scientific job. Before final admission, protocol numbers need an appropriate, reviewed, checksum-owned JSON artifact and source/export annotations in the canonical schema, followed by a registered paper-build job, results lock, immutable snapshot build and canonical release audit. Do not relabel TOML protocol values as structural exemptions or alter the frozen release in place.

The manuscript is ready for author review; journal submission additionally requires the author details and declarations listed in the handoff.

