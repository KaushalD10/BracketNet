"""Run every experiment phase. Each run writes one JSON (and a checkpoint) under results/.

    python scripts/run_experiments.py --phase cov_select     # pick anti-collapse weight (validation seeds)
    python scripts/run_experiments.py --phase validation     # closure-weight sweep + threshold (seeds 5-6)
    python scripts/run_experiments.py --phase test           # held-out seeds 10-14
    python scripts/run_experiments.py --phase ablation       # rejected pilot variants (seeds 10-14)
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import sys
from multiprocessing import Pool
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

VAL_SEEDS = [5, 6]
TEST_SEEDS = [10, 11, 12, 13, 14]
GROUPS = ["SO2", "T2", "SO3"]
SWEEP = [0.05, 0.1, 0.3, 1.0]          # manuscript grid
SWEEP_EXT = [3.0, 10.0, 30.0]          # extension (deviation; see docs/ASSUMPTIONS.md)


def load_locked():
    p = ROOT / "results" / "locked_hparams.json"
    return json.loads(p.read_text()) if p.exists() else {}


def specs(phase: str):
    locked = load_locked()
    wc = locked.get("w_cov")
    out = []
    if phase == "cov_select":
        for w in [1.0, 4.0, 16.0, 64.0]:
            for g in GROUPS:
                for m in ["local", "comp"]:
                    for s in VAL_SEEDS:
                        out.append(dict(phase=phase, group=g, method=m, seed=s, tag=f"{m}_wcov{w:g}",
                                        cfg=dict(w_cov=w)))
        return out
    assert wc is not None, "run --phase cov_select and scripts/lock_hparams.py first"
    base = dict(w_cov=wc)
    if phase == "validation":
        for g in GROUPS:
            for s in VAL_SEEDS:
                out.append(dict(phase=phase, group=g, method="local", seed=s, tag="local", cfg=base))
                out.append(dict(phase=phase, group=g, method="comp", seed=s, tag="comp", cfg=base))
                for lam in (SWEEP + SWEEP_EXT if g != "SO2" else [0.1]):
                    out.append(dict(phase=phase, group=g, method="bracketnet", seed=s, tag=f"bracketnet_lam{lam:g}",
                                    cfg=dict(base, closure_weight=lam)))
    elif phase == "test":
        lam = locked.get("closure_weight", 0.1)
        for g in GROUPS:
            for s in TEST_SEEDS:
                out.append(dict(phase=phase, group=g, method="local", seed=s, tag="local", cfg=base))
                out.append(dict(phase=phase, group=g, method="comp", seed=s, tag="comp", cfg=base))
                out.append(dict(phase=phase, group=g, method="bracketnet", seed=s, tag="bracketnet",
                                cfg=dict(base, closure_weight=lam)))                     # Protocol A
                out.append(dict(phase=phase, group=g, method="bracketnet", seed=s, tag="bracketnetB",
                                cfg=dict(base, closure_weight=locked["closure_weight_B"])))  # Protocol B
    elif phase == "ablation":
        lam = locked["closure_weight_B"]
        for s in TEST_SEEDS:
            # (1) vacuous ambient: SO(3) in so(3)
            for m in ["local", "comp", "bracketnet"]:
                out.append(dict(phase=phase, group="SO3_d3", method=m, seed=s, tag=f"{m}_d3",
                                cfg=dict(base, closure_weight=lam)))
            for g in ["T2", "SO3"]:
                # (2) split-dependent observation map
                for m in ["comp", "bracketnet"]:
                    out.append(dict(phase=phase, group=g, method=m, seed=s, tag=f"{m}_splitmap",
                                    cfg=dict(base, closure_weight=lam), split_map=True))
                # (3) incorrect Gram target I
                out.append(dict(phase=phase, group=g, method="bracketnet", seed=s, tag="bracketnet_gram1",
                                cfg=dict(base, closure_weight=lam, gram_target=1.0)))
                # (4) constant closure penalty, no staging/freeze
                for cl in [0.1, lam]:
                    out.append(dict(phase=phase, group=g, method="bracketnet", seed=s, tag=f"bracketnet_const{cl:g}",
                                    cfg=dict(base, closure_weight=cl, schedule="constant")))
                # (5) training-budget sensitivity: 2000 instead of 420 updates
                for m, cl in [("local", lam), ("comp", lam), ("bracketnet", 0.1), ("bracketnet", lam)]:
                    tag = f"{m}_steps2000" + (f"_lam{cl:g}" if m == "bracketnet" else "")
                    out.append(dict(phase=phase, group=g, method=m, seed=s, tag=tag,
                                    cfg=dict(base, closure_weight=cl, steps=2000)))
    else:
        raise ValueError(phase)
    return out


def run_one(spec):
    import torch
    torch.set_num_threads(1)
    from bracketnet.data import make_dataset
    from bracketnet.metrics import evaluate
    from bracketnet.train import Config, train

    name = f"{spec['group']}_{spec['tag']}_s{spec['seed']}"
    out_dir = ROOT / "results" / "runs" / spec["phase"]
    out_dir.mkdir(parents=True, exist_ok=True)
    ck_dir = ROOT / "results" / "checkpoints" / spec["phase"]
    ck_dir.mkdir(parents=True, exist_ok=True)
    ds = make_dataset(spec["group"], spec["seed"], split_dependent_map=spec.get("split_map", False))
    cfg = Config(method=spec["method"], **spec["cfg"])
    model, info = train(ds, cfg, spec["seed"])
    res = evaluate(model, ds)
    torch.save(model.state_dict(), ck_dir / f"{name}.pt")
    info.pop("W_freeze")
    rec = dict(spec=spec, name=name, metrics=res, **info,
               env=dict(python=platform.python_version(), torch=torch.__version__, platform=platform.platform()))
    (out_dir / f"{name}.json").write_text(json.dumps(rec, indent=1))
    return name, res["mse_10step"], res["closure_residual"], info["runtime_s"]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", required=True)
    ap.add_argument("--workers", type=int, default=os.cpu_count())
    args = ap.parse_args()
    todo = specs(args.phase)
    print(f"{args.phase}: {len(todo)} runs")
    with Pool(args.workers) as pool:
        for name, t10, cl, rt in pool.imap_unordered(run_one, todo):
            print(f"  {name:40s} 10-step={t10:.5f} closure={cl:.5f} ({rt:.1f}s)", flush=True)
