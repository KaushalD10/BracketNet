"""Protocol B closure-weight selection (validation seeds 5-6 only; T2 and SO3 jointly).

Rule (fixed before any test-seed run): among the grid, choose the lambda with the lowest mean
validation closure residual subject to its mean validation 10-step transport MSE not exceeding
that of +Comp. Writes closure_weight_B into results/locked_hparams.json.
Protocol A keeps the manuscript's locked lambda = 0.1 regardless of this script.
"""
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
runs = [json.loads(p.read_text()) for p in (ROOT / "results/runs/validation").glob("*.json")]
clo, tr = defaultdict(list), defaultdict(list)
for r in runs:
    if r["spec"]["group"] not in ("T2", "SO3"):
        continue
    key = r["spec"]["cfg"].get("closure_weight") if r["spec"]["method"] == "bracketnet" else r["spec"]["method"]
    clo[key].append(r["metrics"]["closure_residual"])
    tr[key].append(r["metrics"]["mse_10step"])
comp_tr = float(np.mean(tr["comp"]))
table = {str(k): dict(closure=float(np.mean(clo[k])), mse10=float(np.mean(tr[k])), n=len(clo[k])) for k in clo}
ok = [k for k in clo if isinstance(k, float) and np.mean(tr[k]) <= comp_tr]
best = min(ok, key=lambda k: np.mean(clo[k]))
locked = json.loads((ROOT / "results/locked_hparams.json").read_text())
locked.update(closure_weight_B=best, protocol_B_rule=__doc__.strip(), protocol_B_table=table,
              comp_val_mse10=comp_tr)
(ROOT / "results/locked_hparams.json").write_text(json.dumps(locked, indent=1))
print(json.dumps(table, indent=1)); print("comp mse10", comp_tr, "-> lambda_B =", best)
