# Reproducibility report: final protocol (round 2)

This report covers the final manuscript (`paper/final/main.pdf`). The round-1 report (`docs/REPRODUCIBILITY.md`)
covers the historical λ = 0.1 and λ = 30 experiments; they are kept for the record and the final paper does not use them.

## Environment
* CPU only (Intel Xeon @ 2.30 GHz, 4 cores), Linux 6.18, Python 3.13.16
* torch 2.14.1, numpy 2.5.3, scipy 1.18.1, matplotlib 3.11.2, PyYAML 6.0.1 (`requirements.txt`)
* TeX Live 2023 (Debian packages) for the manuscript
* One torch thread per run; 4 worker processes

## Order of operations (as executed, with commits)
| Step | What | Commit |
|---|---|---|
| 1 | Selection rules written | `fd3304c` (before any dev run) |
| 2 | Dev grid: 280 runs on seeds 5–9 (budgets × methods × λ) | results in `547bf8a` |
| 3 | Amendment A1 to the λ rule (no candidate met the stated constraint) | `c7d40cb` (before any fresh-seed run) |
| 4 | `scripts/freeze_protocol.py` applied the rules: 4000 updates, λ = 3 | `547bf8a` |
| 5 | Closure-objective comparison (10 runs); kept Eq. 7 | `547bf8a` |
| 6 | Fresh-seed phase: 240 runs (seeds 100–119 × SO2/T2/SO3 × 4 methods), run once | final commit |
| 7 | Ablation phase: 240 runs (seeds 200–209 × T2/SO3 × 12 variants), run once | final commit |
| 8 | Alignment/transfer on fresh checkpoints; analysis; figures; manuscript | final commit |

No hyperparameter or threshold was changed after step 6 began.

## Commands
```bash
pip install -r requirements.txt
python -m pytest -q tests                          # all unit tests
python scripts/run_final.py --phase dev            # ~45 min on 4 cores
python scripts/freeze_protocol.py
python scripts/run_final.py --phase dev_mode
python scripts/freeze_protocol.py                  # writes configs/final_protocol.yaml
python scripts/run_final.py --phase test           # ~70 min
python scripts/run_final.py --phase ablation       # ~70 min
python scripts/run_alignment_final.py              # ~2 min
python scripts/analyze_final.py                    # summary_final.json, tables, LaTeX number macros
python scripts/make_figures_final.py
python scripts/verify_final.py                     # determinism re-runs + manuscript number audit
cd paper/final && latexmk -pdf main.tex            # or pdflatex/bibtex/pdflatex/pdflatex
```
`run_final.py` skips runs whose JSON already exists, so an interrupted phase resumes by re-running the same command.

## Artifacts
| Path | Content |
|---|---|
| `configs/dev_selection.yaml` | pre-registered rules and amendment A1 |
| `configs/final_protocol.yaml` | frozen protocol, generated, with the full dev table as provenance |
| `results/final/runs/{dev,test,ablation}/*.json` | one file per run: config, all metrics, structural report, loss history, runtime, environment |
| `results/final/checkpoints/test/*.pt` | 240 fresh-seed models, used by the alignment and transfer analysis |
| `results/final/alignment_transfer.json` | disjoint-pair alignment and transfer, plus all-pairs jackknife |
| `results/final/summary_final.json` | every aggregate, paired test, Holm-adjusted primary family, stratification |
| `results/final/tables/*.tex`, `numbers.tex` | tables and LaTeX macros used verbatim by the manuscript |
| `results/final/verification.json` | determinism re-runs and number audit (written by `scripts/verify_final.py`) |
| `figures/final/*` | figures (TrueType fonts embedded) |
