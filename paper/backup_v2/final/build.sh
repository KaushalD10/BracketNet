#!/usr/bin/env sh
# Clean build of the final manuscript; fails on the first LaTeX error.
set -e
cd "$(dirname "$0")"
rm -f main.aux main.bbl main.blg main.log main.out main.pdf
pdflatex -interaction=nonstopmode -halt-on-error main.tex > /dev/null
bibtex main > /dev/null
pdflatex -interaction=nonstopmode -halt-on-error main.tex > /dev/null
pdflatex -interaction=nonstopmode -halt-on-error main.tex > /dev/null
echo "errors: $(grep -c '^!' main.log)  warnings: $(grep -c 'Warning' main.log)  overfull: $(grep -c 'Overfull' main.log)  pages: $(pdfinfo main.pdf | awk '/Pages/{print $2}')"
