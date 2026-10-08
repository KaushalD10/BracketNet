# Final improvement plan (branch `unireps-final-review`)

Starting point: commit `6cbc3af` (tag `v2-final-manuscript-6cbc3af`). The manuscript is backed up in
`paper/backup_v2/`. Baseline verification (`results/review/baseline_verification.txt`): 43 tests pass,
recomputation identical, 0 undefined macros, 0 LaTeX errors.

Weaknesses are ranked by severity (S: 3 = could invalidate a claim, 1 = presentation), cost (C: hours of work
including compute) and reviewer impact (I: 3 = likely decisive).

| # | Weakness | S | C | I | Action |
|---|---|---|---|---|---|
| 1 | No mechanism for the chiral failure: "closure is not recovery" is shown but not explained | 3 | 3 | 3 | Prove an endpoint-ambiguity / zero-loss-chiral proposition; test it with existing checkpoints (composition error by class) and with a pre-registered intervention (oracle action coefficients) on fresh seeds; trace the span chirality before the closure ramp |
| 2 | Implication chain closure → class → recovery → action stated loosely; action inference is not identifiable even for correct models | 3 | 1 | 3 | Prove that the stabilizer component of an SO(3) action is invisible to endpoint-based inference; restate the chain with precise hypotheses |
| 3 | The SO(4) vs O(4) conjugacy distinction ("two chiral classes") | 2 | 0.5 | 2 | Make the conjugation group explicit everywhere; add an independent Pfaffian-based chirality invariant and an optimization-based search for closed 3-dim subspaces that does not use the classification |
| 4 | Prop. 2 explicit-constant proof not independently re-derived | 3 | 1 | 2 | Re-derive line by line (FINAL_MATHEMATICAL_AUDIT.md); keep it if correct, otherwise weaken |
| 5 | T² H1: sign-flip p is small but the t-interval includes 0 | 2 | 1 | 2 | Explain (heavy-tailed, all-same-sign differences); report sign-flip-inverted intervals matched to the primary test |
| 6 | Transfer analysis is descriptive; CKA's blindness is asserted from means | 2 | 2 | 3 | All 190 pairs per method; pre-specified failure definition; AUC of CKA vs label-free structural distance for predicting held-out transfer failure, with seed-level cluster bootstrap; oracle (ground-truth) alignment check |
| 7 | Synthetic, mildly nonlinear observations only | 2 | 3 | 3 | Rendered-image benchmark (SO(3) acting on a 3-D light/blob position; 24×24 images), frozen protocol unchanged, fresh seeds |
| 8 | No external baseline | 2 | 3 | 2 | HAE requires action labels, LieGAN/LaLiGAN use distributional signals: no direct comparison is fair. Instead, an action-supervised (HAE-style) variant as the oracle intervention in #1; a conceptual comparison table |
| 9 | Official NeurIPS 2026 style not applied; venue rules unverified | 3 | ? | 3 | Retry retrieval; if blocked, document as a human action (P0 blocker) |
| 10 | Writing: the intellectual centre is not explicit; the negative finding reads as failure | 2 | 2 | 3 | Restructure around "when do independently learned transformation representations become comparable, and why does closure not identify them" |
| 11 | Figures: no geometric explanation of diagonal vs chiral | 1 | 1 | 2 | so(4) = L ⊕ R schematic; mechanism figure |
| 12 | Anonymous supplementary archive and AI-use disclosure | 3 | 0.5 | 2 | Build an archive and scan it for identifiers; draft a disclosure statement for authors to confirm |

Order: 1–4 (math + mechanism, with compute launched in the background first), 5–6 (stats/transfer), 7 (benchmark, run
in parallel), 10–12 (writing, figures, package), 9 (formatting), then final verification and reviews.
Not planned: new algorithms, re-running completed experiments, any tuning on test seeds.
