# Experimental verification ledger

Every experiment that feeds the final manuscript (`paper/final_submission.pdf`) is listed with its seeds, number of
runs, selection status, where its raw results live, and how it was verified. No run was discarded.
"Pre-registered" means the rule or prediction was committed to git before the runs.

| # | Experiment | Seeds | Runs | Used for selection? | Pre-registered | Raw results | Verification |
|---|---|---|---|---|---|---|---|
| 1 | Anti-collapse weight selection (round 1) | 5–6 | 48 | yes (w_cov = 16) | method-agnostic criterion | `results/runs/cov_select/` | recomputed by `scripts/lock_hparams.py` |
| 2 | Development grid: budgets × methods × λ | 5–9 | 280 | yes (4000 updates, λ = 3) | yes, `fd3304c`; amendment A1 `c7d40cb` before any fresh run | `results/final/runs/dev/` | `scripts/freeze_protocol.py` reproduces `configs/final_protocol.yaml` |
| 3 | Closure-objective comparison | 5–9 | 10 | yes (kept Eq. 7) | yes (step 3) | `results/final/runs/dev/*whitened*` | same |
| 4 | Fresh-seed evaluation, 3 groups × 4 methods | 100–119 | 240 | **no** | primary tests H1–H3 | `results/final/runs/test/` | bit-identical re-runs; independent recomputation of all six primary tests (`scripts/review_stats.py`) |
| 5 | Ablations (12 variants incl. references) | 200–209 | 240 | no | no (labelled as ablations) | `results/final/runs/ablation/` | recomputed by `analyze_final.py` |
| 6 | Disjoint-pair alignment and transfer | checkpoints of #4, probes 998/997 | 10 pairs × 4 methods × 3 groups | no | H3 | `results/final/alignment_transfer.json` | seed-disjointness checked (`statistical_audit.json`) |
| 7 | E1 composition error by class | #4 | 80 SO(3) runs | no | registered after the numbers were first inspected; **descriptive only** | `results/review/summary_review.json` | recomputed |
| 8 | E2 generator-span trace | 100–119 (re-run of #4 BracketNet SO(3)) | 20 | no | yes (prediction on \|χ\|); the closure-at-ramp diagnostic is **post hoc** | `results/review/runs/trace/` | 20/20 re-runs bit-identical to #4 |
| 9 | E3 oracle-coefficient intervention | 400–419 | 80 | no | yes | `results/review/runs/oracle/` | see summary_review.json |
| 10 | E4 rendered-image benchmark | 300–319 | 60 | no | yes | `results/review/runs/render/` | see summary_review.json |
| 11 | E5 transfer prediction, all 190 pairs | checkpoints of #4 | 4 × 190 × 2 groups | no | yes; **prediction not supported** | `results/review/transfer_prediction.json`, `transfer_allpairs.json` | seed-level cluster bootstrap |
| 12 | Closure flow from random subspaces (no learning) | flow seed 0 | 200 starts | no | no (verification of the classification) | `results/review/closure_flow.json` | 200/200 converged to χ ∈ {−1, 0, 1} |
| 13 | Theory checks on data (chiral vs diagonal endpoint rules) | data seed 100 | — | no | before registration | `bracketnet/theory_checks.py`, tests T7 | recomputed in `verify_submission.py` |

Round-1 experiments (λ = 0.1 / λ = 30 protocols on seeds 5–6, 10–14, 255 runs) are kept in `results/runs/` as history.
The final paper does not use them.

## Development / test separation
* Hyperparameters were chosen only from #1–#3 (seeds 5–9).
* Seeds 100–119, 200–209, 300–319 and 400–419 were each used for one purpose. Experiment #8 re-runs the seed-100–119
  BracketNet runs with snapshots; the computation is identical, verified bit for bit.
* The review predictions (`configs/review_preregistration.yaml`) were committed in `2236a4b`, before any run of
  #8–#11.
* Nothing in #4–#11 changed any setting.

## Outcomes of the pre-registered review predictions
Filled in from `results/review/summary_review.json` after the runs (see SUBMISSION_READINESS.md for the final numbers):
* E1 (descriptive): chiral composition error lower than correct — **observed** (3.3e-5 vs 7.9e-4, median).
* E2: |χ| at the ramp larger for runs ending chiral — **observed, moderately** (AUC 0.75; medians 0.22 vs 0.13).
* E3: fewer chiral solutions with true coefficients — see readiness report.
* E4: closure lower than +Comp. on rendered images — see readiness report.
* E5: structural distance predicts transfer failure better than CKA — **not supported** (AUC 0.98 vs 1.00 for T²,
  0.62 vs 0.75 for SO(3); the SO(3) difference interval includes 0).
