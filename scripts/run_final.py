"""Final-protocol experiment runner.

    python scripts/run_final.py --phase dev        # pre-registered dev grid (configs/dev_selection.yaml)
    python scripts/freeze_protocol.py              # applies the rules -> configs/final_protocol.yaml
    python scripts/run_final.py --phase dev_mode   # step 3: closure-objective variant at the chosen point
    python scripts/freeze_protocol.py              # re-run: records the closure-objective decision
    python scripts/run_final.py --phase test       # fresh seeds 100-119, frozen protocol, run once
    python scripts/run_final.py --phase ablation   # ablation seeds 200-209, frozen protocol

Runs that already have a result JSON are skipped, so an interrupted phase resumes by re-running it.
"""
from __future__ import annotations

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
OUT = ROOT / "results" / "final"


def dev_specs():
    sel = yaml.safe_load((ROOT / "configs/dev_selection.yaml").read_text())
    wc = sel["fixed_from_previous_validation"]["w_cov"]
    out = []
    for B in sel["grid"]["budgets"]:
        for g in sel["groups_for_selection"]:
            for s in sel["dev_seeds"]:
                for m in sel["grid"]["baselines"]:
                    out.append(dict(phase="dev", group=g, method=m, seed=s, tag=f"{m}_B{B}",
                                    cfg=dict(w_cov=wc, steps=B)))
                for lam in sel["grid"]["bracketnet_lambdas"]:
                    out.append(dict(phase="dev", group=g, method="bracketnet", seed=s, tag=f"bracketnet_B{B}_lam{lam:g}",
                                    cfg=dict(w_cov=wc, steps=B, closure_weight=lam)))
    return out


def protocol():
    return yaml.safe_load((ROOT / "configs/final_protocol.yaml").read_text())


def dev_mode_specs():
    P = protocol()
    sel = yaml.safe_load((ROOT / "configs/dev_selection.yaml").read_text())
    base = dict(P["training"]["shared"], steps=P["training"]["steps"], closure_weight=P["training"]["closure_weight"])
    return [dict(phase="dev", group=g, method="bracketnet", seed=s,
                 tag=f"bracketnet_B{base['steps']}_lam{base['closure_weight']:g}_whitened",
                 cfg=dict(base, closure_mode="whitened"))
            for g in sel["groups_for_selection"] for s in sel["dev_seeds"]]


def method_cfgs(P):
    t = P["training"]
    shared = dict(t["shared"], steps=t["steps"])
    return {
        "local": ("local", dict(shared)),
        "comp": ("comp", dict(shared)),
        "bracketnet": ("bracketnet", dict(shared, closure_weight=t["closure_weight"], closure_mode=t["closure_mode"])),
        "bracketnet_lam0.1": ("bracketnet", dict(shared, closure_weight=0.1, closure_mode="reg")),
    }


def test_specs():
    P = protocol()
    out = []
    for g in P["evaluation"]["groups"]:
        for s in P["evaluation"]["test_seeds"]:
            for tag, (m, cfg) in method_cfgs(P).items():
                out.append(dict(phase="test", group=g, method=m, seed=s, tag=tag, cfg=cfg))
    return out


def ablation_specs():
    P = protocol()
    bn = method_cfgs(P)["bracketnet"][1]
    lam = bn["closure_weight"]
    var = {
        "reference": dict(bn),                                    # final BracketNet on ablation seeds
        "comp_reference": dict(method_cfgs(P)["comp"][1]),        # +Comp. on ablation seeds
        "constant_penalty": dict(bn, schedule="constant"),
        "no_freeze": dict(bn, schedule="staged_nofreeze"),
        "no_gram_penalty": dict(bn, w_basis=0.0),
        "weak_anticollapse": dict(bn, w_cov=1.0),
        "whitened_closure": dict(bn, closure_mode="whitened"),
        "lambda_x0.3": dict(bn, closure_weight=lam * 0.3),
        "lambda_x3": dict(bn, closure_weight=lam * 3),
        "K_plus1": dict(bn, n_gen="K+1"),
        "comp_K_plus1": dict(method_cfgs(P)["comp"][1], n_gen="K+1"),
        "K_minus1": dict(bn, n_gen="K-1"),
    }
    out = []
    for g in ["T2", "SO3"]:
        for s in P["evaluation"]["ablation_seeds"]:
            for tag, cfg in var.items():
                out.append(dict(phase="ablation", group=g, method="comp" if tag.startswith("comp") else "bracketnet",
                                seed=s, tag=tag, cfg=cfg))
    return out


def run_one(spec):
    import torch
    torch.set_num_threads(1)
    from bracketnet.data import make_dataset
    from bracketnet.groups import GROUPS
    from bracketnet.metrics import evaluate
    from bracketnet.structure import convergence_report, structural_report
    from bracketnet.train import Config, train

    name = f"{spec['group']}_{spec['tag']}_s{spec['seed']}"
    out_dir = OUT / "runs" / spec["phase"]
    path = out_dir / f"{name}.json"
    if path.exists():
        return name, None
    out_dir.mkdir(parents=True, exist_ok=True)
    cfg = dict(spec["cfg"])
    if isinstance(cfg.get("n_gen"), str):
        cfg["n_gen"] = GROUPS[spec["group"]]["K"] + (1 if cfg["n_gen"] == "K+1" else -1)
    ds = make_dataset(spec["group"], spec["seed"])
    model, info = train(ds, Config(method=spec["method"], **cfg), spec["seed"])
    info.pop("W_freeze")
    res = evaluate(model, ds)
    res["structure"] = structural_report(model, ds)
    res["convergence"] = convergence_report(info["history"])
    if spec["phase"] in ("test", "ablation"):
        ck = OUT / "checkpoints" / spec["phase"]
        ck.mkdir(parents=True, exist_ok=True)
        torch.save(model.state_dict(), ck / f"{name}.pt")
    rec = dict(spec=dict(spec, cfg=cfg), name=name, metrics=res, **info,
               env=dict(python=platform.python_version(), torch=torch.__version__, platform=platform.platform()))
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(rec, indent=1))
    tmp.rename(path)
    return name, (res["mse_10step"], res["closure_residual"], res["structure"]["category"], info["runtime_s"])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", required=True, choices=["dev", "dev_mode", "test", "ablation"])
    ap.add_argument("--workers", type=int, default=os.cpu_count())
    args = ap.parse_args()
    todo = dict(dev=dev_specs, dev_mode=dev_mode_specs, test=test_specs, ablation=ablation_specs)[args.phase]()
    print(f"{args.phase}: {len(todo)} runs", flush=True)
    with Pool(args.workers, maxtasksperchild=20) as pool:
        for name, r in pool.imap_unordered(run_one, sorted(todo, key=lambda s: -s["cfg"].get("steps", 420))):
            if r is None:
                print(f"  {name:48s} (exists, skipped)", flush=True)
            else:
                print(f"  {name:48s} 10-step={r[0]:.5f} closure={r[1]:.5f} {r[2]} ({r[3]:.1f}s)", flush=True)
