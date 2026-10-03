# DYU journal manuscript package

This is the earlier DYU package. The active target is now **JIIS**, followed by
KAIS and IJMLC; follow the [wiki development plan](../../../wiki/manuscript/JIIS-Journal.md).
The files below remain a record of earlier editorial work and are not a JIIS
submission package or an admitted scientific snapshot.

The canonical editable manuscript is `Latex_full/main.tex`. Its bibliography and vector diagram are embedded, so the article compiles independently of the research repository.

- `Latex_full/`: editable LaTeX, PDF, numerical checks, reference audit and export scripts.
- `DYU_Overleaf.zip`: uploadable source package; select XeLaTeX and `main.tex`.
- `Word/DYU_Journal_Manuscript.docx`: editable Word version with native Office Math.
- `Word/DYU_Journal_Manuscript.doc`: legacy Word 97–2003 export.
- `Word/template.docx`: retained conversion of the supplied journal template.
- `EDITORIAL_AUDIT_VI.txt`: revision summary and validation limits.

The 2026-10-03 exports contain 8 tables, 1 figure, 8 numbered equations and 40 cited references. All 46 reported AP/SD pairs are preserved. The LaTeX PDF has 10 pages; DOCX and DOC each render to 10 pages with Times New Roman, MingLiU and the installed Word math fonts. Font substitution can change pagination; the final Word files have not been paginated in Microsoft Word itself. See `Latex_full/verification.json` for checks and hashes.

The content describes the model, training and evaluation directly, with internal configuration codes replaced by descriptive names. The English and Chinese front matter occupy consecutive pages before the Introduction, as requested by the author. No journal submission or formal evidence-snapshot admission is implied.
