# Link Prediction submission package

This directory preserves the uploaded 10-page manuscript and applies only the
author-requested presentation changes:

1. add Duong Viet Huy to the author block, using the affiliation format from
   the Life Cycle Readout paper;
2. remove the specified reproducibility-note paragraph; and
3. render the three included figures in grayscale for black-and-white output.

No other manuscript prose, number, table, equation, citation, or claim was
rewritten. `Link_Predict.pdf` is the compiled paper. The `overleaf/` directory
and `Link_Predict_Overleaf.zip` contain the self-contained LaTeX package.

This is the sole conference manuscript retained in the current tree. It is not
evidence-admitted, and `paper/CURRENT` is therefore `UNRELEASED`. Keeping that
boundary avoids presenting results that are not registered in the current
frozen release as current evidence, while leaving the requested paper text
untouched.

## Build

Upload the ZIP file to Overleaf and select `main.tex`, or build locally with:

```sh
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
```

The packaged `IEEEtran.cls` retains its upstream notice and is distributed
under the LaTeX Project Public License, version 1.3. The manuscript, figures,
and rendered PDF are not covered by the repository's software license unless a
separate grant is stated by the rights holders.

`checksums.sha256` records every distributed artifact. The checksum file itself
is intentionally omitted from its own inventory.
