# DYU journal source package

Primary source: main.tex. Primary output: DYU_Journal_Manuscript.pdf.

The source is a standalone XeLaTeX document: the bibliography and vector diagram are embedded, so it can be compiled directly in an editor or on Overleaf. In the complete repository, run ./build.sh to verify frozen results and regenerate the result table before PDF export. Set TECTONIC to an existing executable if it is not on PATH. The script also supports XeLaTeX.

prepare.py checks the frozen matrix digest, reconstructs each result row from selected seeds, checks citation coverage and writes numeric-sources.json and source-lock.json. The map is a draft source inventory, not the full per-occurrence registry of an admitted immutable paper snapshot.

The local export uses Times New Roman and Songti TC. If these system fonts are unavailable, the source falls back to the TeX-distributed Termes and Fandol Song fonts. A fallback build can have different pagination. verification.json records the delivered export.

The current draft develops the internal conference manuscript's methodology and literature while using the admitted current shared-readout comparison. Recovered historical configurations remain separate from current results. See EDITORIAL_NOTES_VI.txt for the development record, journal-format requirements and unresolved submission items.

The working directory deliberately follows the author's requested Paper/Journal/DYU/Latex_full/ spelling. Existing immutable conference and evidence-contract paths remain under the tracked lowercase paper/ namespace; they are not renamed.

This is an editable journal draft, not a submitted article or admitted immutable snapshot.
