"""Apply the pre-registered rules (configs/dev_selection.yaml) to dev-phase results only and write
configs/final_protocol.yaml. Re-running after the dev_mode phase records the step-3 decision."""
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
sel = yaml.safe_load((ROOT / "configs/dev_selection.yaml").read_text())
runs = [json.loads(p.read_text()) for p in (ROOT / "results/final/runs/dev").glob("*.json")]
groups, seeds = sel["groups_for_selection"], sel["dev_seeds"]

cell = defaultdict(list)          # tag -> list of (mse10, closure)
for r in runs:
    if r["spec"]["group"] in groups and r["spec"]["seed"] in seeds:
        cell[r["spec"]["tag"]].append((r["metrics"]["mse_10step"], r["metrics"]["closure_residual"]))
expected = len(groups) * len(seeds)
mean = lambda tag, i: float(np.mean([v[i] for v in cell[tag]]))
meanlog = lambda tag, i: float(np.mean([np.log(v[i]) for v in cell[tag]]))

budgets = sel["grid"]["budgets"]
for B in budgets:
    assert len(cell[f"comp_B{B}"]) == expected, f"dev grid incomplete for comp_B{B}"
m = {B: mean(f"comp_B{B}", 0) for B in budgets}
B_star = min(B for B in budgets if m[B] <= 1.10 * m[max(budgets)])

lams = [l for l in sel["grid"]["bracketnet_lambdas"] if l != 0.1]
tags = {l: f"bracketnet_B{B_star}_lam{l:g}" for l in lams}
for t in tags.values():
    assert len(cell[t]) == expected, f"dev grid incomplete for {t}"
comp_mse = m[B_star]
ok = [l for l in lams if mean(tags[l], 0) <= comp_mse]
tol = 1.0
while not ok:                       # step_2 fallback (tol 1.10) and amendment A1 (further 0.10 steps)
    tol = round(tol + 0.10, 2)
    ok = [l for l in lams if mean(tags[l], 0) <= tol * comp_mse]
lam_star = min(ok, key=lambda l: mean(tags[l], 1))

mode, mode_note = "reg", "dev_mode phase not yet run"
wtag = f"bracketnet_B{B_star}_lam{lam_star:g}_whitened"
if len(cell[wtag]) == expected:
    better_closure = meanlog(wtag, 1) < meanlog(tags[lam_star], 1)
    better_mse = mean(wtag, 0) < mean(tags[lam_star], 0)
    mode = "whitened" if (better_closure and better_mse) else "reg"
    mode_note = dict(reg=dict(mean_log_closure=meanlog(tags[lam_star], 1), mean_mse10=mean(tags[lam_star], 0)),
                     whitened=dict(mean_log_closure=meanlog(wtag, 1), mean_mse10=mean(wtag, 0)),
                     rule="switch only if whitened is better on both", decision=mode)

table = {t: dict(mean_mse10=mean(t, 0), mean_closure=mean(t, 1), mean_log_closure=meanlog(t, 1), n=len(cell[t]))
         for t in sorted(cell)}
wc = sel["fixed_from_previous_validation"]["w_cov"]
P = dict(
    status="FROZEN before any fresh-seed (100-119) or ablation-seed (200-209) run",
    method_name="BracketNet (revised): closure-regularized fit-close-refit with validation-selected closure weight",
    note=("This is a REVISED method. It is not a reproduction of the original manuscript's lambda=0.1 protocol; "
          "lambda=0.1 at the same budget is evaluated as a reference variant 'bracketnet_lam0.1'."),
    data=dict(groups={"SO2": "so(2) in so(3), K=1", "T2": "t^2 in so(5), K=2", "SO3": "so(3) in so(4), K=3"},
              coef_std=0.24, states="z0 ~ N(0, I_d)", observation_map="x = Qz + 0.18 tanh(Bz), p = d, one fixed map per group (seeds 101/102/103), shared by all splits",
              n_train_triples=1400, n_test_sequences=500, test_edges=10),
    model=dict(encoder_decoder_action="2-hidden-layer MLPs, width 64, SiLU", latent_dim="d", coef_bound="0.65 tanh",
               generator_init="W ~ N(0, 1/d)", generator_normalization="antisymmetrize, ||A_k||_F = sqrt(2) every forward pass"),
    training=dict(steps=int(B_star), closure_weight=float(lam_star), closure_mode=mode,
                  schedule="staged: lambda=0 for first 35 % of updates, linear ramp to lambda by 70 %, generators frozen for final 30 %",
                  loss="4 L_rec + 32 L_loc,lat + 2 L_loc,obs + 1.2 L_comp (comp/BracketNet) + lambda(t) L_close + 1 L_basis(2I) + 16 ||Cov(z) - I||_F^2",
                  shared=dict(w_cov=wc, lr=2e-3, weight_decay=1e-5, batch=160, clip=5.0, eps=1e-6, w_basis=1.0),
                  optimizer="AdamW, lr 2e-3, wd 1e-5, batch 160, global grad-norm clip 5",
                  model_selection="none: the final iterate is evaluated (no early stopping, no checkpoint selection)"),
    evaluation=dict(groups=["SO2", "T2", "SO3"], methods=["local", "comp", "bracketnet", "bracketnet_lam0.1"],
                    test_seeds=list(range(100, 120)), ablation_seeds=list(range(200, 210)),
                    alignment_pairs="disjoint seed pairs (100,101), (102,103), ..., (118,119): 10 independent pairs",
                    probe_seeds=dict(alignment_fit=998, transfer_eval=997),
                    metrics=["1-step and 10-step chained observation MSE", "composition MSE", "closure residual (eps=1e-6 and exact)",
                             "whitened (span-only) closure", "generator rank, singular values, Gram condition", "delta bound (Lemma 1)",
                             "ground-truth algebra distance and coverage after Procrustes", "CKA and Procrustes residual vs truth",
                             "action disagreement vs truth", "structural category", "cross-seed algebra distance / CKA / action disagreement",
                             "cross-model transformation transfer", "runtime and convergence"],
                    statistics=sel["rules"]["step_5_primary_hypotheses"],
                    thresholds=sel["rules"]["step_4_thresholds"]),
    provenance=dict(rules="configs/dev_selection.yaml", dev_seeds=seeds, comp_mse10_by_budget={str(k): v for k, v in m.items()},
                    budget_rule_result=int(B_star), lambda_candidates_meeting_constraint=[float(x) for x in ok], lambda_tolerance_used=tol,
                    closure_objective_decision=mode_note, dev_table=table),
)
(ROOT / "configs/final_protocol.yaml").write_text(
    "# AUTO-GENERATED by scripts/freeze_protocol.py from dev-phase results only. Do not edit by hand.\n"
    + yaml.safe_dump(P, sort_keys=False, width=110))
print(f"budget={B_star} lambda={lam_star} closure_mode={mode}")
print("comp mse10 by budget:", {k: round(v, 5) for k, v in m.items()})
for l in lams:
    print(f"  lam={l:g}: mse10={mean(tags[l], 0):.5f} closure={mean(tags[l], 1):.5f}")
if isinstance(mode_note, dict):
    print("closure objective:", mode_note)
