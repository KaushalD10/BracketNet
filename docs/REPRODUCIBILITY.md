# Reproducibility report

## Environment (where every reported number was produced)
* CPU only: Intel Xeon @ 2.30 GHz, 4 cores; Linux 6.18; Python 3.13.16
* torch 2.14.1, numpy 2.5.3, scipy 1.18.1, matplotlib 3.11.2 (`requirements.txt`)
* `torch.set_num_threads(1)` per run; runs parallelized over 4 worker processes

## What was run (all runs completed; none were discarded)
| Phase | Seeds | Runs | Purpose |
|---|---|---|---|
| `cov_select` | 5, 6 | 48 | choose anti-collapse weight w_cov (method-agnostic criterion) → 16 |
| `validation` | 5, 6 | 42 | closure-weight sweep {0.05 … 30}, threshold ranges → λ_B = 30 |
| `test` | 10–14 | 60 | SO(2)/T²/SO(3) × {Local, +Comp., BracketNet A (λ=0.1), BracketNet B (λ=30)}; run once |
| `ablation` | 10–14 | 105 | d = 3 ambient, split-dependent map, Gram target I, constant penalty, 2,000-update budget |
| alignment | probe seed 999 | 10 pairs × 4 methods × 3 groups | cross-seed structural alignment (inference only) |

Order of execution: cov_select → lock w_cov → validation → lock λ_B → test → ablation → alignment.
`results/locked_hparams.json` records both locks and the scores they were based on.

## Determinism
`scripts/verify_reproducibility.py` re-trained 5 stored runs from scratch (including test runs of both protocols).
The maximum absolute difference in all checked metrics was **0.0**: bitwise identical on this machine
(`results/reproducibility_check.json`). Other CPUs or BLAS builds may differ in the last digits.

## Runtime per run (s, mean ± sd over 5 test seeds, 4 concurrent workers)
| | Local | +Comp. | BracketNet A | BracketNet B |
|---|---|---|---|---|
| T² | 5.3 ± 1.1 | 9.2 ± 2.4 | 7.6 ± 2.6 | 8.3 ± 2.6 |
| SO(3) | 5.5 ± 2.3 | 7.2 ± 2.7 | 6.2 ± 2.3 | 6.4 ± 2.5 |
Runtimes are confounded by contention among concurrent workers, so they are not a clean cost comparison.

## Files
* `results/runs/<phase>/<group>_<variant>_s<seed>.json`: config, metrics, transport curve, generators, structure constants, loss history, runtime, environment
* `results/checkpoints/test/*.pt`: trained held-out models
* `results/summary.json`: every aggregate statistic; `results/tables/*.md|tex`; `results/alignment.json`
* `figures/*.pdf|png`: generated only by `scripts/make_figures.py`

## Known limitations of this reproduction
* The original code was unavailable, so this is an independent re-implementation. Absolute MSE values depend on
  unstated data-scale choices (docs/ASSUMPTIONS.md A1–A4) and are not comparable with the manuscript's.
* The ablations on test seeds are post hoc and were not used for any selection.
