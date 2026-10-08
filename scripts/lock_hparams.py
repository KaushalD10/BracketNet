"""Select the anti-collapse weight w_cov from validation seeds only (method-agnostic criterion:
mean log 1-step transport MSE over Local and +Comp runs on SO2/T2/SO3, seeds 5-6). Closure is not used."""
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
runs = [json.loads(p.read_text()) for p in (ROOT / "results/runs/cov_select").glob("*.json")]
score = defaultdict(list)
for r in runs:
    score[r["spec"]["cfg"]["w_cov"]].append(np.log(r["metrics"]["mse_1step"]))
table = {w: float(np.mean(v)) for w, v in sorted(score.items())}
best = min(table, key=table.get)
locked = dict(w_cov=best, closure_weight=0.1,
              note="w_cov selected by scripts/lock_hparams.py on validation seeds 5-6 with criterion "
                   "mean log 1-step MSE of Local/+Comp; closure_weight 0.1 is the manuscript's locked value.",
              cov_select_scores={str(k): v for k, v in table.items()},
              n_runs_per_value={str(k): len(v) for k, v in sorted(score.items())})
(ROOT / "results/locked_hparams.json").write_text(json.dumps(locked, indent=1))
print(json.dumps(locked, indent=1))
