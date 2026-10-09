# Submission readiness report: UniReps 2026 (final review)

**Manuscript:** `paper/final_submission.pdf`, built from `paper/submission/` with `build.sh proxy`. 19 pages: main
text ends on page 9, references start on page 10, then the appendix. Rebuilt after the final readiness re-audit
(Sec. F).

## Recommendation: CONDITIONAL GO
Scientifically the paper is ready: claims, proofs, statistics and numbers are verified against raw artifacts as far as
an automated process can verify them. It is **not ready to upload as-is** because three items need a human:
1. the official `neurips_2026.sty` must replace the layout proxy, followed by a rebuild and page check;
2. the UniReps 2026 call (deadline, track, page limit, supplement rules, LLM/AI-disclosure policy) must be confirmed;
3. the authors must read and validate the proofs and claims themselves.

If any of these fails (e.g. the page limit is below 9, or AI-generated content is not allowed), the recommendation
becomes NO-GO until resolved.

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
| Anonymous supplement: 1,231 files; no git metadata; no identifiers or absolute paths | `archive` block; `supplement/bracketnet_supplement_anonymous.zip` |
| Development/test separation; review predictions committed before review runs (`2236a4b`) | `docs/EXPERIMENTAL_VERIFICATION.md` |
| Main text ≤ 9 pages in the NeurIPS 2026 layout (proxy) | references start on page 10 |
| Visual inspection | all pages in round 3; the changed theory and proof pages (4, 13–14) re-inspected |

## B. Completed but not independently verified
* **Proofs** (Props. 1–3, Cor. 1). They were re-derived line by line and checked numerically (49 unit tests in total,
  closure-flow search, theory checks on data), but only by the AI system that wrote them. No human mathematician has
  reviewed them.
* **Novelty comparison** (`docs/NOVELTY_COMPARISON.md`, appendix table). Checked by web search against listings and
  abstracts; full texts could not be fetched (arxiv.org/openreview blocked). Nine related works were added.
* **Bibliography.** Entries are standard and were checked for internal consistency, not against publisher records.
* **Simulated reviews** (`docs/REVIEWER_RISK_AUDIT.md`). Not independent peer review.

## C. Incomplete or blocked
| Item | Status |
|---|---|
| Official `neurips_2026.sty` | **blocked**: neurips.cc, Overleaf and OpenReview are unreachable from the build environment. A community copy (self-described "partial rewrite"; SHA-256 in `paper/submission/layout_proxy/PROVENANCE.md`) was used only as a layout proxy. |
| UniReps 2026 call for papers | **blocked**: unireps.org unreachable. Search results indicate an Oct 10, 2026 (AoE) deadline (extended from Oct 4) and that the 2025 call had a 9-page full-paper track and a 4-page extended-abstract track. NeurIPS 2026 guidance mentions a Sep 29 workshop notification date, which conflicts; ask the organizers. |
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
1. Download the official NeurIPS 2026 author kit, put `neurips_2026.sty` in `paper/submission/`, run
   `paper/submission/build.sh official`, and check: page count (main text ≤ the track limit), no overflow, the
   workshop option (`dblblindworkshop`) and `\workshoptitle` as the call requires.
2. Read the UniReps 2026 call. Confirm the deadline, the track (archival full paper vs. extended abstract), the page
   limit, the supplementary-material rules and the policy on AI assistance. Adjust or remove the appendix "Use of AI
   assistance" paragraph accordingly. Do not remove it to conceal material AI involvement.
3. Read and verify every proof and claim. The authors are responsible for the content.
4. Upload `supplement/bracketnet_supplement_anonymous.zip` only if the venue allows code supplements. Do not link the
   private repository.
5. Fill in OpenReview metadata yourselves. Nothing was submitted from this environment.

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

## G. GO / NO-GO
**CONDITIONAL GO.** Every remaining blocker needs a human and none can be resolved from this environment:
1. **Official style.** Download the NeurIPS 2026 author kit, put `neurips_2026.sty` into `paper/submission/`, run
   `sh paper/submission/build.sh official`, then copy `paper/submission/main_official.pdf` to the upload. Check that
   references start on page 10 or earlier and that the log has no errors. If the main text then exceeds 9 pages,
   trim it, for example by moving the Sec. 6.3 rendered-benchmark paragraph to the appendix.
2. **UniReps 2026 call.** Confirm the deadline (reported as Oct 10 AoE, which is **tomorrow**), the track, the page
   limit, supplement rules and the AI policy.
3. **Proofs.** Verify Props. 1–3 and Cor. 1 yourselves.
4. **Novelty.** Read the full texts of Painter et al. 2020, Forestano et al. 2023 and Keurti et al. 2023 to confirm
   the related-work sentences.
