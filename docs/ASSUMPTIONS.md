# Assumptions and deviations

The repository originally contained only a README; the manuscript's claimed archive (code, JSON
results, pilots, review log; Sec. D) was **not present**. Everything here was re-implemented from the
manuscript text. Where the text is silent, the choice below was made. Each is visible in code (search for `ASSUMPTION`).

## Specified in the manuscript and implemented as stated
| Item | Value | Where |
|---|---|---|
| Groups / ambient dims | SO(2) in so(3), T² in so(5), SO(3) in so(4); K = 1, 2, 3 | `bracketnet/groups.py` |
| Local coefficients | Gaussian, std 0.24 | `data.py` |
| Observation map | x = Qz + 0.18 tanh(Bz), one fixed map per group, shared by train/test | `data.py` |
| Data | 1,400 two-edge train triples; 500 ten-edge test sequences | `data.py` |
| Networks | E, D, q: 2-hidden-layer MLPs, width 64, SiLU | `model.py` |
| Generators | antisymmetrized, Frobenius norm √2 every forward pass | `model.py` |
| Coefficients | 0.65·tanh(q(z, z′)) | `model.py` |
| Loss | 4 L_rec + 32 L_loc,lat + 2 L_loc,obs + 1.2 L_comp + λ(t) L_close + L_reg | `train.py` |
| Closure | Eq. (7); Gram penalty Eq. (8) with target 2I | `model.py` |
| Schedule | λ=0 for first 35 %; ramp 35–70 %; generators frozen final 30 % | `train.py` |
| Optimizer | AdamW, lr 2e-3, wd 1e-5, batch 160, grad clip 5, 420 updates | `train.py` |
| Seeds | validation 5–6, test 10–14 | `scripts/run_experiments.py` |
| Baselines | Local (rec + one-step transport), +Comp. (adds Eq. 6), BracketNet (adds closure + staging) | `train.py` |

## Underspecified: our choices
| # | Item | Choice | Rationale |
|---|---|---|---|
| A1 | Observation dim p | p = d (Q square orthogonal) | "Q is orthogonal" |
| A2 | Matrix B | G/√d, G standard normal, rescaled so 0.18‖B‖₂ ≤ 0.5 | guarantees injectivity of h |
| A3 | Map seed | fixed per group (101/102/103), independent of run seed | "one fixed map per group" |
| A4 | Initial states | z₀ ~ N(0, I_d) | not stated |
| A5 | True generator normalization | ‖T_k‖_F = √2 | matches learned normalization |
| A6 | Seed usage | run seed → train stream `[seed,0]`, test stream `[seed,1]`, torch init and batch order | not stated |
| A7 | Loss reductions | squared norms summed over coordinates (and over t), averaged over the batch | as written in Eqs. 4–6 |
| A8 | Covariance regularizer | w_cov·‖Cov(z) − I‖²_F over all encoded frames in the batch | form not stated |
| A9 | w_cov | **16**, selected on validation seeds 5–6 among {1,4,16,64} with a method-agnostic criterion (mean log 1-step MSE of Local/+Comp.; closure not used) | w_cov = 1 collapsed 4 of 5 latent dims (eigenvalues < 0.1) |
| A10 | w_basis | 1 | not stated |
| A11 | ε in P_B | 1e-6 | not stated |
| A12 | Ramp shape | linear from 0 to λ | not stated |
| A13 | Batching | epoch-wise reshuffle, drop last partial batch | not stated |
| A14 | Frozen generators | gradients removed (AdamW skips them, so no weight decay either) | "frozen" |
| A15 | 1-/10-step MSE | observation-space MSE (mean over coords and sequences) after 1 / 10 chained inferred edges | Fig. 4 axis label |
| A16 | Composition MSE (Table 2) | elementwise mean of (ρ(a₀₂) − ρ(a₁₂)ρ(a₀₁))² on the first two test edges | normalization not stated |
| A17 | Generator init | W ~ N(0, 1/d) | not stated |
| A18 | Commutator threshold | midpoint between pooled validation ranges of T² and SO(3) (Local, +Comp., λ=0.1, λ=30) | "chosen between the validation ranges" |

## Deviations from the manuscript's protocol (disclosed)
1. **Two closure-weight protocols.** *Protocol A* uses the manuscript's locked λ = 0.1. On validation, λ = 0.1
   had no effect on closure in our implementation, because the λ scale depends on reduction conventions (A7) that
   the paper does not state. *Protocol B* extends the validation grid to {0.05, 0.1, 0.3, 1, 3, 10, 30} and
   selects λ = 30 with the rule in `scripts/select_closure_weight.py`. That rule was written after looking at
   validation results but **before any test-seed run**. Both protocols are reported.
2. **Ablations on test seeds.** The rejected-pilot ablations and a training-budget sensitivity study (2,000 updates)
   were run post hoc on seeds 10–14. They were not used to select any hyperparameter.
3. **New experiment.** Cross-seed structural alignment (`scripts/run_alignment.py`) is not in the original manuscript.
