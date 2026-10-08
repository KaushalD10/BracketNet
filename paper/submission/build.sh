#!/usr/bin/env sh
# Clean build. Usage: build.sh official | proxy | fallback   (default: proxy)
#   official : requires the OFFICIAL neurips_2026.sty in this directory (download from neurips.cc)
#   proxy    : uses layout_proxy/neurips_2026_COMMUNITY_COPY_NOT_OFFICIAL.sty in a temporary directory
#   fallback : plain article stand-in with NeurIPS-like geometry
set -e
MODE=${1:-proxy}
HERE="$(cd "$(dirname "$0")" && pwd)"
B="$HERE/.build_$MODE"
rm -rf "$B"; mkdir -p "$B/sections"
cp "$HERE"/main.tex "$HERE"/refs.bib "$B"/; cp "$HERE"/sections/*.tex "$B"/sections/
case "$MODE" in
  official) test -f "$HERE/neurips_2026.sty" || { echo "official neurips_2026.sty missing"; exit 2; }; cp "$HERE/neurips_2026.sty" "$B"/ ;;
  proxy) cp "$HERE/layout_proxy/neurips_2026_COMMUNITY_COPY_NOT_OFFICIAL.sty" "$B/neurips_2026.sty" ;;
  fallback) ;;
esac
# relative paths in main.tex are written for paper/submission/; the build dir is one level deeper
sed -i 's#\.\./\.\./#../../../#g' "$B/main.tex" "$B"/sections/*.tex
cd "$B"
pdflatex -interaction=nonstopmode -halt-on-error main.tex > /dev/null
bibtex main > /dev/null
pdflatex -interaction=nonstopmode -halt-on-error main.tex > /dev/null
pdflatex -interaction=nonstopmode -halt-on-error main.tex > /dev/null
cp main.pdf "$HERE/main_$MODE.pdf"
echo "[$MODE] errors: $(grep -c '^!' main.log)  warnings: $(grep -c 'Warning' main.log)  overfull: $(grep -c 'Overfull' main.log)  pages: $(pdfinfo main.pdf | awk '/Pages/{print $2}')"
grep 'Warning' main.log | sort | uniq -c | head -20 || true
