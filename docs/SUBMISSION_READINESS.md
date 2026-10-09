# Submission readiness report: UniReps 2026 (official style applied, 2026-10-09)

**Manuscript to upload:** `paper/final_submission.pdf`, built from `paper/submission/` with `build.sh official` using
the official `neurips_2026.sty` (v2026-01-29, SHA-256 c3fc2894…a4555a) supplied by the authors, on top of the
Sec. F re-audit content. 18 pages: main text ends on page 9 (the reference list starts partway down page 9), then
references (29 entries) and appendices A–G. Option `dblblindworkshop`: anonymous author block, line numbers, standard
"Submitted to … Do not distribute" notice. Applying the style changed no research content, claim or number.

**Venue requirements (UniReps 2026 call, read directly on 2026-10-09 at unireps.org/2026/call-for-papers):**
deadline **Oct 10, 2026 AoE** on OpenReview; Full Paper (archival) ≤ 9 pages main text excluding references and
appendix; Extended Abstract (non-archival) ≤ 4 pages; NeurIPS template; both tracks anonymized; the NeurIPS paper
checklist "doesn't need to be included" (it is not included). The call states no supplementary-material rules and no
LLM/AI policy.

## Recommendation: GO for the Full Paper (archival) track, conditional only on the authors' own read-through
Formatting, page limit, anonymity, references, figures and the reproducibility checks all pass with the official
style. What automation cannot discharge is in Sec. G: the authors must verify the proofs and the related-work
sentences. The paper does **not** fit the 4-page Extended Abstract track.

## A. Completed and verified (automated)
| Item | Evidence |
|---|---|
| All 49 tests pass (re-run after the final re-audit) | `results/review/test_results.txt` (pytest) |
| Bit-identical re-runs: main-evaluation SO(3) and T² runs, an oracle run and a rendered run, all from scratch | `results/review/verification_submission.json` → `reruns` |
| Every table and number macro regenerates identically from raw run files | same file → `recompute.identical = true` |
| Every manuscript macro defined (102 used); every literal number justified or recomputed | `macros`, `theory_literals` |
| Six primary tests independently recomputed; all match | `results/review/statistical_audit.json` |
| PDF: 0 LaTeX errors, 0 warnings, 0 undefined references or citations, 0 overfull boxes, no Type-3 fonts | `pdf` block |
| Anonymity: author block anonymous; PDF metadata empty; no names, e-mail, repository URL or "NeurReps"; no date | `pdf.identifying = []`, `pdf_author = ""` |
| Anonymous supplement (rebuilt 2026-10-09, byte-identical to the Sec. F build): 1,231 files; no git metadata; no identifiers or absolute paths | `archive` block; `supplement/bracketnet_supplement_anonymous.zip` |
| Development/test separation; review predictions committed before review runs (`2236a4b`) | `docs/EXPERIMENTAL_VERIFICATION.md` |
| Main text ≤ 9 pages, **official** NeurIPS 2026 style | references start on page 9; `pdf.main_text_within_9_pages = true` |
| All 5 figures embedded; 29/29 bibliography entries cited and resolved; 0 undefined references; 0 missing files | `.build_official/main.log`; `pdf` block |
| Fonts: Type 1 + embedded TrueType (matplotlib DejaVu) only, no Type 3; US Letter | `pdffonts`, `pdfinfo` |
| Visual inspection | all 18 pages of the official-style PDF (2026-10-09): no overflow; figures and tables legible |

## B. Completed but not independently verified
* **Proofs** (Props. 1–3, Cor. 1). They were re-derived line by line and checked numerically (49 unit tests in total,
  closure-flow search, theory checks on data), but only by the AI system that wrote them. No human mathematician has
  reviewed them.
* **Novelty comparison** (`docs/NOVELTY_COMPARISON.md`, appendix table). Checked by web search against listings and
  abstracts; full texts could not be fetched (arxiv.org/openreview blocked). Nine related works were added.
* **Bibliography.** Entries are standard and were checked for internal consistency, not against publisher records.
* **Simulated reviews** (`docs/REVIEWER_RISK_AUDIT.md`). Not independent peer review.

## C. Previously blocked items and other gaps
| Item | Status |
|---|---|
| Official `neurips_2026.sty` | **resolved 2026-10-09**: supplied by the authors; `paper/final_submission.pdf` is built from it. The community proxy is kept for history only (`layout_proxy/PROVENANCE.md`). |
| UniReps 2026 call for papers | **resolved 2026-10-09**: read directly (see top). NeurIPS checklist not required, so the supplied `checklist.tex` is deliberately not included. |
| Branch `unireps-final-review` | The first push returned HTTP 403 but had created the remote branch; a later push succeeded. The final work is on **both** `unireps-final-review` and `claude/eager-franklin-y9zaho` (same commit). The v2 backup is preserved in history (`6cbc3af`) and in `paper/backup_v2/`. |
| External published baselines (LieGAN, LaLiGAN, HAE) | **not run**. Supervision differs; the oracle-coefficient variant is the action-supervised analogue. Stated in the paper. |
| Natural-image benchmark | **not done**. The rendered benchmark is synthetic. Stated. |

## D. Remaining scientific limitations (all stated in the paper)
* Synthetic, low-dimensional benchmarks; known K; compact orthogonal actions.
* SO(3) results: closure produces wrong (chiral) closed algebras in 8/20 runs on the synthetic map and in 7/20 (all
  closed runs) on rendered images. The correct-closed improvement (5 → 8/20) is not significant.
* No transport improvement anywhere; a small transport cost on rendered images.
* T² effects are concentrated in a few seeds.
* The mechanism proposition is qualitative and holds at the ground-truth embedding. The oracle intervention supports
  but does not isolate it; the strongest trace diagnostic (AUC 0.94) is post hoc.
* One pre-registered prediction failed: structure did not beat CKA at predicting transfer failure.
* The closure-weight rule needed an amendment (committed before any fresh run).

## E. Human confirmation required before upload
Superseded by Sec. G below (items 1–2 of the earlier list were resolved on 2026-10-09).

## F. Final readiness re-audit (no new experiments, protocol unchanged)
**AI self-review is not independent human verification.** Everything below was checked by the AI system that drafted
the paper.

**Corrected in the manuscript:**
1. **Prop. 3(b).** It was overstated as "the objective favours the chiral algebra". It now states its hypotheses
   (continuity, a full orbit sphere, all ε-small triangles) and says it rules out only an *exact* zero. A
   discontinuous rule can be exact off a null set. A new Remark proves a positive gap for each fixed Lipschitz
   class and states that no quantitative gap is known. Abstract, introduction, Sec. 6.2 and the conclusion were
   softened to match.
2. **Prop. 2.** Two proof gaps closed (the graph-conjugacy step, the 4-dim case). Its scope is now limited to exactly
   closed spans.
3. **Novelty.** Closure losses are prior work (Forestano et al. 2023). Unsupervised action estimation is prior work
   (Painter et al. 2020). Prop. 3(b) is now framed as a known type of topological obstruction. Nine citations
   were added.
4. **AI-use statement.** The false sentence "the authors … have checked the claims, proofs and results" was replaced
   with the true one: AI self-check plus automated tests, which are not independent verification. **Authors:** once
   you have verified the proofs yourselves, you may say so there.

**Verification after the changes:**
* `pytest` 49/49.
* `verify_submission.py`: all hard checks pass.
  * 4/4 bit-identical from-scratch re-runs.
  * Recomputation identical.
  * 102 macros defined.
  * 0 LaTeX errors, warnings or overfull boxes.
  * No Type-3 fonts.
  * Empty author metadata; no identifiers.
  * Archive: 1,231 files, no hits, no git.

**Official resources (still blocked).** Re-tried media.neurips.cc, neurips.cc, unireps.org, overleaf.com and ctan:
all are refused by the egress proxy. Web search reports these, **all unconfirmed**:
* a UniReps 2026 deadline of **Oct 10, 2026 AoE**, extended from Oct 4 (organizers' X account);
* the workshop on Dec 12, 2026;
* 2025 rules: 9-page full papers, 4-page extended abstracts, NeurIPS template, anonymized;
* the workshop options `\usepackage[dblblindworkshop]{neurips_2026}` and `\workshoptitle{...}`, which `main.tex`
  already uses.

## G. GO / NO-GO (2026-10-09, official style)
**GO for the Full Paper (archival) track**, once the authors have done the following (none can be done from this
environment):
1. **Proofs.** Verify Props. 1–3, the Remark and Cor. 1 yourselves. If you have, you may say so in Appendix G.
2. **Novelty.** Read the full texts of Painter et al. 2020, Forestano et al. 2023 and Keurti et al. 2023 to confirm
   the related-work sentences.
3. **Submit** `paper/final_submission.pdf` to the Full Paper track on OpenReview before **Oct 10, 2026 AoE**, and fill
   in the metadata yourselves. Nothing was submitted from this environment.
4. **Supplement.** Upload `supplement/bracketnet_supplement_anonymous.zip` only if OpenReview offers a supplementary
   field (the call does not mention one). Do not link the private repository.
5. **AI-use statement** (Appendix G): keep it. The call has no AI policy, and the paragraph must not be removed to
   conceal material AI involvement.

Superseded: the earlier conditional-GO list (official style, call confirmation) is resolved.
