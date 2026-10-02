# DYU journal source package

Primary source: `main.tex`. Primary output: `DYU_Journal_Manuscript.pdf`.

The standalone XeLaTeX document embeds its bibliography and vector diagram. Upload `DYU_Overleaf.zip`, select XeLaTeX and compile `main.tex`; no external image, bibliography download or research dataset is required. The canonical repository path is `paper/journal/DYU/Latex_full/`.

## Verification and regeneration

In the complete repository, run `python prepare.py` and `python check_editorial.py`, then `./build.sh`. Set `TECTONIC` to an existing executable if it is not on PATH; the build script also supports XeLaTeX. Python 3 and NumPy are needed for the dataset check. `prepare.py` verifies the frozen matrix, reconstructs primary means and sample deviations, runs `prepare_historical.py` for the additional tables, checks citation coverage and writes source maps. `prepare_statistics.py` verifies corpus checksums and reconstructs every corpus/split count in Table 1. The numerical inventories are source maps, not a substitute for a complete immutable paper-snapshot registry.

The delivered PDF uses Times New Roman and MingLiU. On macOS, the source can use the existing MingLiU font installed with Microsoft Word. Otherwise it tries Songti TC and finally the TeX-distributed Termes/Fandol fallback. Overleaf may therefore paginate differently. The archive does not redistribute proprietary fonts. `verification.json` records the delivered export and its limits.

## Word exports

Provide an existing Pandoc executable through `PANDOC` or PATH and install python-docx and Pillow. Run `python render_word_figure.py`, then `python export_word.py`. On systems other than macOS, set `FIGURE_FONT` to a Times New Roman TTF. The exporter uses `../Word/template.docx`, native Office Math and editable tables. Figure 1 is embedded at 600 dpi; the editable SVG is retained in `../Word/figures/`.

Word uses 9-point body text and true 1.5-line spacing (`w:line=360`, `w:lineRule=auto`), including references. Authors are 10-point bold; English affiliation/address lines are italic; captions are 9-point bold. Equations are left aligned with right-aligned numbers and a blank-line equivalent above and below. Chinese text specifies MingLiU. Use LibreOffice's MS Word 97 filter for the legacy DOC and inspect that export separately. A headless renderer must be configured to see the installed CJK and math fonts; absent fonts caused missing Chinese glyphs and a different page count during QA. With those fonts available, both Word exports rendered to 10 pages. Native Microsoft Word pagination may differ.

## Editorial constraints

Prioritize method, results and interpretation over literature volume; every reference must support text in the article. The current selection contains 40 sources. Do not fabricate data or erase the limitations of earlier experiments. Keep the same-readout gradient comparison distinct from predictor changes and frozen probes. The model is specified as part of this study, without its internal implementation name. Source checks and visual review do not certify human-only authorship, plagiarism clearance, evidence-snapshot admission or journal acceptance.
