"""Re-run a sample of stored runs from scratch and check the metrics match the saved JSON exactly."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import torch  # noqa: E402
from bracketnet.data import make_dataset  # noqa: E402
from bracketnet.metrics import evaluate  # noqa: E402
from bracketnet.train import Config, train  # noqa: E402

torch.set_num_threads(1)
SAMPLE = ["test/T2_bracketnetB_s10", "test/SO3_bracketnetB_s12", "test/SO3_comp_s13", "test/T2_bracketnet_s11",
          "validation/SO3_bracketnet_lam30_s5"]
report = []
for key in SAMPLE:
    stored = json.loads((ROOT / f"results/runs/{key}.json").read_text())
    sp = stored["spec"]
    ds = make_dataset(sp["group"], sp["seed"], split_dependent_map=sp.get("split_map", False))
    model, _ = train(ds, Config(method=sp["method"], **sp["cfg"]), sp["seed"])
    new = evaluate(model, ds)
    keys = ["mse_1step", "mse_10step", "closure_residual", "commutator_norm"]
    diffs = {k: abs(new[k] - stored["metrics"][k]) for k in keys}
    report.append(dict(run=key, max_abs_diff=max(diffs.values()), **{k: (stored["metrics"][k], new[k]) for k in keys}))
    print(f"{key:40s} max|diff| = {max(diffs.values()):.3e}")
(ROOT / "results/reproducibility_check.json").write_text(json.dumps(report, indent=1))
