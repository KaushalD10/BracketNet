#!/usr/bin/env bash
# Full pipeline, in the order it was actually executed. ~25 min on 4 CPU cores.
set -euo pipefail
cd "$(dirname "$0")"
python -m pytest -q tests                                   # mathematical audit + pipeline checks
python scripts/run_experiments.py --phase cov_select        # anti-collapse weight (validation seeds only)
python scripts/lock_hparams.py
python scripts/run_experiments.py --phase validation        # closure-weight sweep, seeds 5-6
python scripts/select_closure_weight.py                     # Protocol B lambda (validation only)
python scripts/run_experiments.py --phase test              # held-out seeds 10-14 (run once)
python scripts/run_experiments.py --phase ablation          # rejected pilots + budget sensitivity
python scripts/run_alignment.py                             # cross-seed structural alignment
python scripts/analyze.py                                   # summary.json + tables
python scripts/make_figures.py                              # figures/
python scripts/verify_reproducibility.py                    # re-run a sample, compare to stored JSON
