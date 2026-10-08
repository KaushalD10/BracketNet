# Adversarial review of the final manuscript

The final paper (`paper/final/main.pdf`) was reviewed from three perspectives. Each concern is marked
**fixed** (changed before release), **disclosed** (stated as a limitation in the paper), or **open**.

## Mathematical reviewer
| Concern | Resolution |
|---|---|
| The original claim that Eq. 7 is invariant to any invertible coordinate change is false | **fixed**: exact transformation law and two-sided bounds (T1), behaviour of the regularized projector (T2), span-only variant |
| The original BCH bound had a δ-independent r³ term and a sketch proof | **fixed**: rigorous δ-proportional bound with explicit constants (Prop. 2, T5, 400 random checks) |
| The loss is not linked to the uniform escape constant δ | **fixed**: Lemma 1 for a general Gram matrix (T4) |
| The BCH bound holds only for ‖X‖ < ln2/4 ≈ 0.17 (rotations ≲ 0.12 rad); typical inferred actions are larger | **disclosed** in Sec. 4 and the limitations |
| "Closure ⇒ correct algebra" is implicit in the original | **fixed**: Prop. 4 classification (T² closed ⇒ conjugate; SO(3) admits chiral classes; K = 4 excludes the truth), tests T6 |
| Prop. 4 relies on standard Lie theory (Cartan conjugacy, automorphisms of su(2)) proved only by citation | **disclosed** as standard results with references; spot-checked numerically |
| The "incorrect Gram target" explanation from the original pilot | **fixed**: removed; the targets are provably gradient-equivalent under normalization |
| The general conjugacy-class claim in the introduction | **fixed**: restricted to the low-dimensional settings studied, with the torus continuum as counterexample |

## Experimental ML reviewer
| Concern | Resolution |
|---|---|
| Hyperparameters were tuned on test data | **fixed**: pre-registered rules on dev seeds, committed before runs; fresh seeds 100–119 run once |
| The λ rule was amended after seeing dev results | **disclosed**: amendment A1, committed before any fresh-seed run; minimal completion of an undefined rule |
| Pairwise alignment samples treated as independent | **fixed**: 10 disjoint seed pairs as units; the all-pairs mean is reported only descriptively, with a seed-level jackknife |
| Multiple comparisons | **fixed**: six pre-registered primary tests, Holm-corrected; the rest labelled secondary |
| T² H1 is significant by sign-flip but the t-interval includes 0 | **disclosed** in Sec. 6 |
| Correct-closed rate improvement for SO(3) (5 → 8/20) is not significant | **disclosed** (McNemar p = 0.25) |
| Low closure taken as recovery | **fixed**: categories with ground-truth distance; chiral failures reported (8/20) |
| The fit–close–refit schedule is claimed as a contribution | **fixed**: the ablation shows no detectable benefit, and the paper says so |
| Comparison only with internal ablations; no LieGAN, LaLiGAN or HAE | **disclosed**: different supervision signals make a fair comparison impossible without redesigning the benchmark |
| Synthetic, small-scale data | **disclosed** |
| Transfer analysis pools methods that share seeds | **disclosed** as descriptive |
| Seed-level fitting failures on T² dominate the variance | **disclosed**, with the seed list verified by `scripts/verify_final.py` |
| The structural thresholds are arbitrary | **disclosed**; fixed in advance, with continuous metrics also reported |
| Five dev seeds are few for selection | **open**: more dev seeds would make the selection more robust; time-limited |

## UniReps reviewer
| Concern | Resolution |
|---|---|
| Relevance to representational alignment | **fixed**: cross-seed algebra comparison after Procrustes, CKA contrast, transformation transfer |
| Overclaiming "unification" | **fixed**: the title and conclusion state comparability without identifiability |
| Does improved agreement reflect correct structure? | **fixed**: pair-type stratification shows it is largely discrete disagreement among closed classes |
| Generality beyond orthogonal compact actions and known K | **disclosed**; K+1 / K−1 ablations included |
| Practical value | **partly open**: transfer works when structure is correct, but no method reliably achieves that for SO(3) |

## Not resolved in this environment
* The official UniReps 2026 call, template and page limit could not be retrieved (network policy). See
  `docs/SUBMISSION_CHECKLIST.md`.
* The official `neurips_2026.sty` was not available, so the final page count must be re-checked with it.
