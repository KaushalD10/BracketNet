# Final review: record of every modification

Base: `6cbc3af` (tag `v2-final-manuscript-6cbc3af`, local; the v2 manuscript is copied to `paper/backup_v2/`). No
historical result file was modified or deleted.

## Mathematics
* New Proposition 3 (endpoint ambiguity) with proof:
  (a) chiral generators allow exact endpoint inference, transport and composition;
  (b) the true diagonal algebra cannot be exact (hairy-ball argument);
  (c) the stabilizer component of an action is not identifiable from endpoints.
  New Corollary 1 (agreement without correctness).
* Classification restated with the conjugation group explicit: three classes under SO(4), two under O(4). Added the
  K = 4 statement (no closed 4-dim span contains the true algebra).
* Implication chain (closure → class → recovery → action) restated with hypotheses; two implications shown false for SO(3).
* The BCH bound was re-derived line by line and kept (correct); its locality is stated.
* New independent checks: Pfaffian/chirality invariants (`bracketnet/so4.py`); a classification-free closure-flow
  search (200 starts); theory checks on data (`bracketnet/theory_checks.py`); tests T7–T8 and a centralizer test.
* `docs/FINAL_MATHEMATICAL_AUDIT.md`.

## Experiments (all new seeds, frozen protocol, predictions committed first)
* E2 trace (seeds 100–119, bit-identical re-runs with generator snapshots).
* E3 oracle-coefficient intervention (seeds 400–419, 80 runs).
* E4 rendered-image SO(3) benchmark (seeds 300–319, 60 runs; new `Renderer` in `bracketnet/data.py`).
* E5 transfer prediction over all 190 pairs, with oracle alignment and seed-level cluster bootstrap.
* Threshold-sensitivity robustness table (no new runs).
* Code: `oracle_actions`, snapshot support and K override in `train.py`; chiral subtype labelling extended to the
  rendered group in `structure.py` (affects only new runs); math-safe LaTeX macros.

## Statistics
* Independent recomputation of the six primary tests (`scripts/review_stats.py`); sign-flip-inverted and bootstrap
  intervals; explanation of the T² t-interval discrepancy; wording audit. `docs/FINAL_STATISTICAL_AUDIT.md`.

## Manuscript (`paper/submission/`, built to `paper/final_submission.pdf`)
* Restructured around: when do independently learned transformation representations become comparable, and why does
  closure not identify them?
* New sections and content: five levels of agreement; the mechanism (Sec. 6.2); the rendered benchmark (Sec. 6.3);
  transfer by structural agreement; the failed E5 prediction reported as such; the CKA claim corrected (CKA detects
  encoder failures but not algebra-class mismatches).
* Removed or corrected:
  * "CKA is essentially insensitive";
  * "transfer tracks correctness" (it tracks agreement);
  * implicit "closure ⇒ recovery";
  * a figure caption that described three panels for a four-panel figure.
* Moved to the appendix: SO(2) rows, the alignment table and the ablation details. Added: statistical audit table,
  threshold sensitivity, comparison of settings, AI-use paragraph.
* Built with the NeurIPS 2026 layout proxy: main text ≤ 9 pages, line numbers, 0 errors or warnings.

## Package and documents
* `supplement/bracketnet_supplement_anonymous.zip` (`scripts/build_supplement.py`).
* `scripts/verify_submission.py`.
* Documents: `FINAL_IMPROVEMENT_PLAN.md`, `FINAL_MATHEMATICAL_AUDIT.md`, `FINAL_STATISTICAL_AUDIT.md`,
  `NOVELTY_COMPARISON.md`, `EXPERIMENTAL_VERIFICATION.md`, `REVIEWER_RISK_AUDIT.md`, `SUBMISSION_READINESS.md`.

## Final readiness re-audit
No experiments were run and the protocol is unchanged.

**Theory**
* Prop. 3 hypotheses made explicit. Proof of (b) expanded.
* New Remark: continuity is essential; there is a gap for each Lipschitz class; no quantitative gap is claimed.
* Prop. 2: proof gaps closed; scope limited to exact closure.
* Corollary and implication chain condensed. (iv) is now described as unattainable for every endpoint method.

**Claims**
* Abstract, introduction, Sec. 6.2 title and text, limitations and conclusion softened ("partial explanation",
  "admits an exact rule").

**Related work**
* Nine citations added: Forestano 2023, Quessard 2020, Painter 2020, Caselles-Dupré 2019, Dang-Nhu 2026,
  de Haan & Falorsi 2018, Zhou 2019, Bouchacourt 2021, Connor & Rozell 2020.
* App. B table extended.

**AI-use statement**
* Now accurate (AI self-review is not independent verification).

**Build and verification**
* `build.sh` reruns LaTeX until the labels are stable.
* `verify_submission.py` allows the year "2023" in the comparison table.
* `docs/FINAL_MATHEMATICAL_AUDIT.md` R11; `docs/NOVELTY_COMPARISON.md` literature table.
