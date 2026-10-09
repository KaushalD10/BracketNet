# BracketNet: Lie-closure regularization for learned transformation representations

**Submission package (final review):** `paper/final_submission.pdf`, built with the official NeurIPS 2026 style
(`paper/submission/build.sh official`; source in `paper/submission/`),
`supplement/bracketnet_supplement_anonymous.zip`, and `docs/SUBMISSION_READINESS.md` (status and required human
actions). The sections below describe the round-2 study; the final review added the endpoint-ambiguity mechanism, an
oracle intervention, a rendered-image benchmark and a transfer-prediction analysis (`docs/FINAL_REVIEW_CHANGELOG.md`).

This is the research code, raw results and manuscript for

> **Closing the Algebra Is Not Enough: Lie-Closure Regularization Makes Learned Transformation Structure Comparable, Not Identifiable**
> (anonymous submission prepared for the NeurIPS 2026 UniReps workshop; manuscript: `paper/final/main.pdf`)

BracketNet learns an encoder, decoder, action-inference network and K skew-symmetric latent generators from
unlabeled transition triples. It penalizes the component of each generator commutator that leaves the generator
span (Lie closure). We ask whether this makes **independently trained models learn the same transformation
algebra**, and whether that algebra is the correct one.

## Main findings
Fresh seeds 100–119, frozen protocol (4000 updates, λ = 3), pre-registered tests. Numbers come from
`results/final/summary_final.json`.

| | T² | SO(3) |
|---|---|---|
| Correct-closed runs, +Comp. → BracketNet | 14 → 16 / 20 | 5 → 8 / 20 |
| Non-closed runs, +Comp. → BracketNet | 6 → 3 | **15 → 4** |
| Incorrect-closed (chiral su(2)) runs, BracketNet | 1 (0 chiral) | **8 (8 chiral)** |
| H1 closure, +Comp. → BracketNet (Holm p) | 0.291 → 0.022 (2.1e-4; t-CI includes 0) | 0.616 → 0.025 (5.7e-6) |
| H2 ground-truth algebra distance (Holm p) | 0.151 → 0.129 (0.31, n.s.) | 0.475 → 0.243 (4.9e-4) |
| H3 cross-seed algebra distance, 10 disjoint pairs (Holm p) | 0.214 → 0.198 (0.38, n.s.) | 0.685 → 0.392 (8.8e-3) |
| 10-step transport, BracketNet − +Comp. | no detectable difference | no detectable difference |
| Latent CKA across seeds, +Comp. / BracketNet | 0.920 / 0.925 | 0.949 / 0.952 |

* Fitting transitions alone recovers the abelian T² algebra in most runs but leaves SO(3) **non-closed**.
* Closure regularization improves SO(3) algebraic fidelity and cross-model agreement at no detectable transport cost.
* **Closure is not recovery.** Many SO(3) runs close onto a *chiral* su(2), a provably possible wrong class.
  Cross-model agreement improves largely because disagreement becomes discrete.
* Transferring transformations between models works when both recovered the correct algebra (T² median gap 0.006,
  22 pairs) and mostly fails otherwise (0.855, 18 pairs), whatever the objective.
* Ablations (seeds 200–209): the anti-collapse term is essential. The fit–close–refit schedule, Gram penalty and
  span-only closure variant make no detectable difference. With K+1 generators, no closed span can contain the true
  SO(3) algebra (proved).

## Reproduce
```bash
pip install -r requirements.txt
python -m pytest -q tests                 # 49 tests: mathematical claims + pipeline
# full pipeline and exact order: docs/REPRODUCIBILITY_FINAL.md
python scripts/verify_final.py            # determinism re-runs, recomputation, manuscript number audit, PDF checks
```

## Layout
| Path | Contents |
|---|---|
| `bracketnet/` | data generation, model, losses, training, metrics, structural evaluation, alignment, statistics |
| `configs/dev_selection.yaml` | pre-registered selection rules (+ amendment A1, committed before fresh runs) |
| `configs/final_protocol.yaml` | frozen protocol generated from development seeds only |
| `scripts/run_final.py`, `freeze_protocol.py`, `run_alignment_final.py`, `analyze_final.py`, `make_figures_final.py`, `verify_final.py` | final pipeline |
| `results/final/` | raw per-run JSON (dev 290, test 240, ablation 240), fresh-seed checkpoints, summaries, tables, LaTeX number macros |
| `figures/final/` | final figures |
| `paper/final/` | final LaTeX source (`main.tex`, `sections/`, `refs.bib`) and compiled `main.pdf` |
| `docs/MATHEMATICAL_VERIFICATION.md` | verification of every mathematical statement |
| `docs/ASSUMPTIONS.md`, `docs/REPRODUCIBILITY_FINAL.md`, `docs/SUBMISSION_CHECKLIST.md` | assumptions, reproducibility, submission status |
| `docs/AUDIT.md`, `results/runs/`, `paper/bracketnet_revised.*`, `paper/original_submission.pdf` | round-1 audit of the original manuscript (historical) |

## History
The original manuscript reported 74.4 % / 75.2 % closure reductions at λ = 0.1. An independent re-implementation
could not reproduce them (`docs/AUDIT.md`): λ = 0.1 has no effect at the loss scales used here. The final paper
is a revised study with a protocol selected on development seeds only, and does not report those numbers.
