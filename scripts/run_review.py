"""Final-review experiments (pre-registered in configs/review_preregistration.yaml). Frozen protocol unchanged.

    python scripts/run_review.py --phase trace    # E2: re-run BracketNet SO3 test seeds 100-119 with generator snapshots
    python scripts/run_review.py --phase oracle   # E3: oracle-action intervention, seeds 400-419
    python scripts/run_review.py --phase render   # E4: rendered-image SO(3) benchmark, seeds 300-319
Runs with an existing result JSON are skipped (resumable).
"""
import argparse
import json
import os
import platform
import sys
from multiprocessing import Pool
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "results/review"
P = yaml.safe_load((ROOT / "configs/final_protocol.yaml").read_text())
T = P["training"]
SHARED = dict(T["shared"], steps=T["steps"])
BN = dict(SHARED, closure_weight=T["closure_weight"], closure_mode=T["closure_mode"])
RAMP, FREEZE = int(0.35 * T["steps"]), int(0.70 * T["steps"])


def specs(phase):
    out = []
    if phase == "trace":
        for s in range(100, 120):
            out.append(dict(phase=phase, group="SO3", method="bracketnet", seed=s, tag="bracketnet", cfg=BN,
                            snapshots=[0, RAMP, FREEZE]))
    elif phase == "oracle":
        for s in range(400, 420):
            out += [dict(phase=phase, group="SO3", method="bracketnet", seed=s, tag="bracketnet", cfg=BN),
                    dict(phase=phase, group="SO3", method="comp", seed=s, tag="comp", cfg=SHARED),
                    dict(phase=phase, group="SO3", method="bracketnet", seed=s, tag="oracle_bn",
                         cfg=dict(BN, oracle_actions=True)),
                    dict(phase=phase, group="SO3", method="local", seed=s, tag="oracle_local",
                         cfg=dict(SHARED, oracle_actions=True))]
    elif phase == "render":
        for s in range(300, 320):
            out += [dict(phase=phase, group="SO3img", method="local", seed=s, tag="local", cfg=SHARED),
                    dict(phase=phase, group="SO3img", method="comp", seed=s, tag="comp", cfg=SHARED),
                    dict(phase=phase, group="SO3img", method="bracketnet", seed=s, tag="bracketnet", cfg=BN)]
    return out


def run_one(spec):
    import torch
    torch.set_num_threads(1)
    from bracketnet.data import make_dataset
    from bracketnet.metrics import evaluate
    from bracketnet.structure import convergence_report, structural_report
    from bracketnet.train import Config, train
    name = f"{spec['group']}_{spec['tag']}_s{spec['seed']}"
    path = OUT / "runs" / spec["phase"] / f"{name}.json"
    if path.exists():
        return name, None
    path.parent.mkdir(parents=True, exist_ok=True)
    ds = make_dataset(spec["group"], spec["seed"])
    model, info = train(ds, Config(method=spec["method"], **spec["cfg"]), spec["seed"],
                        snapshot_steps=tuple(spec.get("snapshots", ())))
    info.pop("W_freeze")
    res = evaluate(model, ds)
    res["structure"] = structural_report(model, ds)
    res["convergence"] = convergence_report(info["history"])
    ck = OUT / "checkpoints" / spec["phase"]
    ck.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), ck / f"{name}.pt")
    rec = dict(spec=spec, name=name, metrics=res, **info,
               env=dict(python=platform.python_version(), torch=torch.__version__, platform=platform.platform()))
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(rec, indent=1))
    tmp.rename(path)
    return name, (res["mse_10step"], res["closure_residual"], res["structure"]["category"], info["runtime_s"])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", required=True, choices=["trace", "oracle", "render"])
    ap.add_argument("--workers", type=int, default=os.cpu_count())
    a = ap.parse_args()
    todo = specs(a.phase)
    print(f"{a.phase}: {len(todo)} runs", flush=True)
    with Pool(a.workers, maxtasksperchild=10) as pool:
        for name, r in pool.imap_unordered(run_one, todo):
            print(f"  {name:40s} " + ("exists" if r is None else f"10-step={r[0]:.5f} closure={r[1]:.5f} {r[2]} ({r[3]:.0f}s)"), flush=True)
