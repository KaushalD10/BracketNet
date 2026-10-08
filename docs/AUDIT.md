# Audit of the original manuscript

> **Status:** this is the round-1 audit of the original manuscript. The final study, which supersedes the λ = 0.1 / λ = 30
> protocols below, is documented in `docs/MATHEMATICAL_VERIFICATION.md`, `docs/REPRODUCIBILITY_FINAL.md` and
> `docs/ADVERSARIAL_REVIEW.md`, with the manuscript in `paper/final/`.

Scope: the submitted PDF (`paper/original_submission.pdf`). Numerical checks are in `tests/test_math.py`
(19 tests, all passing). Empirical checks come from `results/summary.json`, produced by `scripts/analyze.py`.

## 1. Repository / auditability claims
| Claim (Sec. D, abstract) | Finding |
|---|---|
| "Code, exact seeds, and failed pilot variants are included" | **Not true of this repository.** At audit time it held only README + .gitignore. No code, JSON, figures, pilots or review log. |
| "No empirical number in this paper was inserted without a corresponding machine-readable result file" | Cannot be verified; no result files existed. |

## 2. Mathematical claims
| Claim | Verdict | Evidence |
|---|---|---|
| Eq. (7) "invariant to any invertible change of generator coordinates" | **Incorrect as stated.** L_close is invariant to *orthogonal* changes B → BM, Mᵀ M = I, and scales as s⁴ under B → sB. Only its **zero set** is GL(K)-invariant. With ε > 0, P_B is not exactly span-dependent either. In practice the Gram penalty and √2 normalization keep the basis near-orthogonal, which limits the effect. | `test_closure_invariant_to_orthogonal_basis_change_only`, `test_projector_eps_breaks_exact_span_invariance` |
| Proposition 1 (exact closure ⇒ subalgebra ⇒ connected immersed subgroup) | Correct (standard Lie correspondence). | `test_true_algebras_close`, `test_jacobi_exact_for_closed_algebras` |
| Proposition 2 (dist(log eˣeʸ, 𝔞) ≤ C₁δr² + C₂r³) | Correct but **loose**: the cubic term is also O(δ). Each degree-n nested commutator leaves 𝔞 by at most c_n δ rⁿ, so dist ≤ ½δr² + Cδr³, which vanishes under exact closure. The paper also never links its hypothesis δ to the loss. For a basis with BᵀB = 2I, δ ≤ (K/2)√L_close (Cauchy–Schwarz). Both points are added to the revised manuscript. | `test_prop2_bch_escape_vanishes_with_closure` |
| Proposition 3 (chained orthogonal stability) | Correct. | `test_prop3_chained_stability` |
| "We monitor the Jacobi residual" | For matrix commutators Jacobi holds identically. The meaningful quantity is the Jacobi residual of the **projected** structure constants, which we compute (`metrics.jacobi_residual`). | — |
| Commutator norm "distinguishes" abelian / non-abelian | It separates abelian from non-abelian, but it is **basis-dependent** and **embedding-dependent**. Standard so(3) ⊂ so(4) gives √2; a chiral su(2) ⊂ so(4), also exactly closed, gives 2. We add a span-only invariant κ and a participation ratio that tell these apart. | `test_commutator_norm_does_not_identify_representation` |
| Sec. 6.3 item 3: "incorrect Gram target I biases the generators" | **Cannot be the mechanism** if the penalty is computed on the √2-normalized generators: diag(BᵀB) = 2 is then constant, so targets I and 2I give identical gradients. Empirically the gram-1 ablation matches the main runs to within 4e-8 in closure. | `test_gram_target_irrelevant_under_normalization`; `ablation_paired` |
| Sec. 6.3 item 1: d = 3 ambient makes closure vacuous | Confirmed: closure is exactly 0 for all methods and seeds with d = 3. | ablation `*_d3` |

## 3. Identifiability
* Closure does not identify the representation. One BracketNet SO(3) run (2,000 updates, seed 14) converged to an
  exactly closed **chiral su(2)** (commutator norm 2.000, participation ratio 4.00) instead of the true 3 ⊕ 1 action.
  The abelian / non-abelian threshold still classifies it correctly.
* Latent identifiability up to conjugacy was tested directly (new experiment, `results/alignment.json`). After
  orthogonal Procrustes, Protocol B SO(3) models agree with each other (subspace distance 0.034 ± 0.021) and with the
  ground truth (0.019). Baselines sit at 0.42–0.45 (chance 0.50). Linear CKA is ≈ 0.89–0.90 for **every** method, so
  pointwise similarity misses the difference.
* Inferred **actions** are not well aligned for any method (normalized action disagreement > 0.7 vs truth).
  Algebra recovery does not imply accurate action inference q within 420 updates.

## 4. Empirical claims (held-out seeds 10–14)
| Manuscript claim | Our result | Status |
|---|---|---|
| 74.4 % closure reduction vs +Comp. on T² (λ = 0.1) | Protocol A: closure **48.8 % higher** (lower on 0/5 seeds) | **Not reproduced** |
| 75.2 % closure reduction vs +Comp. on SO(3) (λ = 0.1) | Protocol A: **17.5 % higher** (lower on 2/5 seeds) | **Not reproduced** |
| (same, with λ re-selected on validation) | Protocol B (λ = 30): −98.9 % (T²), −98.6 % (SO(3)); lower on 5/5 seeds each; sign-flip p = 0.0625 (minimum with n = 5); t-CI for T² includes 0 | Direction reproduced; magnitude differs; weak statistics |
| Baseline closures 0.013 (T²) and 0.067 (SO(3)) | +Comp.: 0.212 ± 0.328 (T²), 0.585 ± 0.459 (SO(3)), bimodal across seeds | Not reproduced; baselines far less converged |
| Threshold 0.9 classifies 10/10 BracketNet runs; Local 7/10, +Comp. 8/10 | Validation threshold 0.918: Protocol B 10/10; Local, +Comp., Protocol A 9/10 each | Partly reproduced |
| No confirmed transport gain | Protocol B vs +Comp.: +5.1 % (T²), −16.9 % (SO(3)); both paired CIs include 0 | Consistent (no significant difference) |
| Fit–close–refit beats a constant penalty on transport | Constant λ = 30 is worse in mean (T² +0.030 ± 0.056, SO(3) +0.075 ± 0.125); CIs include 0 | Direction consistent, inconclusive |
| 1-step / 10-step MSE magnitudes (≈ 0.001–0.06) | ≈ 0.005–0.17 | Not comparable: data scale depends on A1–A4 |

## 5. Methodological issues
1. **λ scale is not portable.** The effect of λ depends on unstated loss reductions; λ = 0.1 is inert in our implementation.
2. **Training budget.** At 420 updates no method has converged. Closure and transport keep improving up to 2,000 updates
   (`fig7_budget`). The freeze at 70 % stops generator learning before convergence, which is why Protocol A ends with
   *worse* closure than the baselines.
3. **n = 5 seeds.** The minimum attainable two-sided sign-flip p-value is 0.0625. Heavy-tailed (bimodal) baseline
   closure makes t-intervals wide. Claims should rest on per-seed wins and effect sizes.
4. **Split-dependent map ablation.** It confounds the result trivially: closure is unchanged (generators only see training data)
   and transport degrades by 0.20 (T²) and 0.36 (SO(3)).
