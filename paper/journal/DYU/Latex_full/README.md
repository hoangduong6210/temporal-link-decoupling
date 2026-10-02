# DYU journal source package

Primary source: main.tex. Primary output: DYU_Journal_Manuscript.pdf.

The source is a standalone XeLaTeX document: the bibliography and vector diagram are embedded, so it can be compiled directly in an editor or on Overleaf. In the complete repository, run ./build.sh to verify frozen results and regenerate the result table before PDF export. Set TECTONIC to an existing executable if it is not on PATH. The script also supports XeLaTeX.

prepare.py checks the frozen matrix digest, reconstructs each result row from selected seeds, checks citation coverage and writes numeric-sources.json and source-lock.json. The map is a draft source inventory, not the full per-occurrence registry of an admitted immutable paper snapshot.

The local export uses Times New Roman and Songti TC. If these system fonts are unavailable, the source falls back to the TeX-distributed Termes and Fandol Song fonts. A fallback build can have different pagination. verification.json records the delivered export.

The current draft develops the internal conference manuscript's methodology and literature while using the admitted current shared-readout comparison. Recovered historical configurations remain separate from current results. See EDITORIAL_NOTES_VI.txt for the development record, journal-format requirements and unresolved submission items.

The canonical path is paper/journal/DYU/Latex_full/. Existing conference and frozen evidence files are unchanged.

This is an editable journal draft, not a submitted article or admitted immutable snapshot.

## Overleaf and Word

Upload DYU_Overleaf.zip and choose XeLaTeX with main.tex as the main document. All article content, bibliography and the vector diagram are embedded. The 72-reference list is checked by prepare.py; no BibTeX download is required. Running prepare.py requires the full research repository, but compiling main.tex does not.

To regenerate Word, install python-docx and provide an existing Pandoc executable via PANDOC or PATH, then run python export_word.py. The complete repository includes ../Word/template.docx. The export uses editable native Office Math and reconstructed tables. Use LibreOffice's MS Word 97 export filter for the legacy .doc, then visually inspect that export. Word conversion dependencies are separate from LaTeX/Overleaf compilation.
