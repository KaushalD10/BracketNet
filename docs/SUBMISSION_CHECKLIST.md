# UniReps 2026 submission checklist

## Venue requirements: what could and could not be verified
Network policy in the build environment blocked unireps.org, openreview.net, neurips.cc, overleaf.com, ctan.org
and x.com. Only web-search snippets were available, so **every venue rule below is UNVERIFIED** and must be checked
by the authors on the official call before submission.

| Item | Best available information | Source quality | Status |
|---|---|---|---|
| Venue | UniReps 2026 workshop at NeurIPS 2026; a "UniReps 2026 Workshop" OpenReview venue is listed as open | search snippet of the OpenReview venue list | unverified |
| Deadline | **October 10, 2026 (AoE)**, extended from October 4 | search snippet attributing posts to the UniReps account | unverified |
| Workshop date | December 12, 2026 (Paris) | search snippet | unverified |
| NeurIPS 2026 workshop timeline | suggested contribution deadline Aug 29, 2026; mandatory accept/reject notification Sep 29, 2026 | search snippet of the NeurIPS workshop guidance | **conflicts** with an Oct 10 deadline; check with the organizers |
| Tracks | 2025 edition: full paper (proceedings) ≤ 9 pages, extended abstract (non-archival) ≤ 4 pages, both excluding references and appendix | 2025/2023 calls via search snippets | 2026 rules unverified |
| Template | NeurIPS LaTeX template (2025 and 2023 calls) | search snippets | `neurips_2026.sty` could not be downloaded; see below |
| Anonymity | double-blind; anonymized submissions | 2025/2023 calls | applied (see below) |
| Code / supplementary | not determined | none | provide an anonymized code archive, not this repository URL |

## Manuscript status (`paper/final/main.pdf`)
| Check | Result |
|---|---|
| Clean build (pdflatex → bibtex → pdflatex ×2, `-halt-on-error`) | 0 errors, 0 warnings, 0 overfull boxes (see `results/final/verification.json`) |
| Undefined references or citations | none |
| Main text length (stand-in geometry: 5.5 in × 9 in text block, 10 pt Times, as in the NeurIPS style) | ends on page 9, before the references; within a 9-page full-paper limit **if** the 2026 limit is 9 and the official style produces the same layout |
| Official style file | **NOT applied**: `neurips_2026.sty` could not be downloaded. `main.tex` uses it automatically if the file is placed in `paper/final/`; recompile and re-check the page count. The official style adds line numbers and may shift pages. |
| Fonts | all embedded; no Type 3 fonts (figures use TrueType) |
| Anonymity | author block "Anonymous Author(s)"; PDF Author/Creator metadata empty; no date; text scanned for names, e-mail, GitHub, repository URL and "NeurReps" (none found); the paper refers only to "anonymized supplementary code" |
| Venue identifiers | no NeurReps identifiers; the footer line of the original submission was dropped |
| Numbers | every number in the text is a LaTeX macro generated from raw results, except protocol constants and seven literals that `scripts/verify_final.py` recomputes |

## Before submitting (author actions)
1. Read the official UniReps 2026 call for papers: deadline, track, page limit, template, supplementary rules.
2. Download the official `neurips_2026.sty` into `paper/final/`, recompile, and re-check the page count and that
   no text overflows.
3. Choose the track (full paper vs. extended abstract). The current main text (≈ 9 pages) fits only a 9-page track.
4. Build an anonymized code archive (strip git history and author metadata). Do not link this repository.
5. Fill in OpenReview metadata yourselves. Nothing has been submitted from this environment.
