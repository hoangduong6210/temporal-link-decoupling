#!/usr/bin/env bash
set -euo pipefail
source_dir="$(cd "$(dirname "$0")" && pwd)"
cd "$source_dir"
python3 prepare.py
mkdir -p build
if [[ -n "$(printenv TECTONIC || true)" ]]; then
  "$TECTONIC" --keep-logs --outdir build main.tex
elif command -v tectonic >/dev/null 2>&1; then
  tectonic --keep-logs --outdir build main.tex
elif command -v xelatex >/dev/null 2>&1; then
  xelatex -interaction=nonstopmode -halt-on-error -output-directory=build main.tex
  xelatex -interaction=nonstopmode -halt-on-error -output-directory=build main.tex
else
  echo "Set TECTONIC to an existing Tectonic executable, or use XeLaTeX." >&2
  exit 1
fi
cp build/main.pdf DYU_Journal_Manuscript.pdf
