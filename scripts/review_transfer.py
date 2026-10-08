"""E5 (pre-registered): does a label-free structural metric predict cross-model transfer failure better than CKA?

For every group (T2, SO3), method and unordered seed pair (190 per method), on the fresh-seed checkpoints:
  * predictors on probe set A (seed 998): latent linear CKA, cross-seed algebra distance after Procrustes;
  * outcome on held-out probe set B (seed 997): one-step transfer gap (mean of both directions);
  * transfer failure := gap > 0.5 (fixed in configs/review_preregistration.yaml);
  * oracle alignment: the same transfer, but with the latent alignment obtained through the ground-truth state
    (R_ab = R_b^T R_a with R_m the uncentered Procrustes map from model m's codes to the true state).
AUCs use all pairs pooled over methods; 95 % intervals come from a seed-level cluster bootstrap (seeds are shared
by all methods, so resampling seeds resamples every pair that involves them).
"""
import itertools
import json
import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from run_alignment_final import (METHODS, SEEDS, encode, load, procrustes_uncentered,  # noqa: E402
                                 structural, transfer)
from bracketnet.data import make_dataset  # noqa: E402

torch.set_num_threads(1)
OUT = ROOT / "results/review"


@torch.no_grad()
def transfer_with_R(ma, mb, R, x_eval):
    """One-step transfer gap with a given alignment R (b-latent ~ R a-latent)."""
    za, zb = encode(ma, x_eval), encode(mb, x_eval)
    Aa, Ab = ma.generators().double(), mb.generators().double()
    x = torch.as_tensor(x_eval, dtype=torch.float64)
    Ta = torch.linalg.matrix_exp(torch.einsum("ntk,kij->ntij", ma.infer(za[:, :-1].float(), za[:, 1:].float()).double(), Aa))
    Tb = torch.linalg.matrix_exp(torch.einsum("ntk,kij->ntij", mb.infer(zb[:, :-1].float(), zb[:, 1:].float()).double(), Ab))
    Rt = torch.as_tensor(R)
    dec = lambda z: mb.decoder(z.float()).double()
    native = float(((dec(torch.einsum("ntij,ntj->nti", Tb, zb[:, :-1])) - x[:, 1:]) ** 2).mean())
    trans = float(((dec(torch.einsum("ntij,ntj->nti", Rt @ Ta @ Rt.T, zb[:, :-1])) - x[:, 1:]) ** 2).mean())
    ident = float(((dec(zb[:, :-1]) - x[:, 1:]) ** 2).mean())
    return (trans - native) / (ident - native)


def auc(score_fail_high, fail):
    s, y = np.asarray(score_fail_high, float), np.asarray(fail, bool)
    pos, neg = s[y], s[~y]
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    return float((np.mean(pos[:, None] > neg[None, :]) + 0.5 * np.mean(pos[:, None] == neg[None, :])))


def main():
    rows = []
    for group in ["T2", "SO3"]:
        fit = make_dataset(group, 998, n_train=1, n_test=200)
        ev = make_dataset(group, 997, n_train=1, n_test=200)
        d = fit.z_test.shape[-1]
        for tag in METHODS:
            models = {s: load(group, tag, s) for s in SEEDS}
            # alignment of each model to the ground-truth state on the fit set (oracle alignment)
            Rtrue = {s: procrustes_uncentered(encode(models[s], fit.x_test).reshape(-1, d).numpy(),
                                              fit.z_test.reshape(-1, d)) for s in SEEDS}
            cats = {s: json.loads((ROOT / f"results/final/runs/test/{group}_{tag}_s{s}.json").read_text())
                    ["metrics"]["structure"] for s in SEEDS}
            for a, b in itertools.combinations(SEEDS, 2):
                st = structural(models[a], models[b], fit.x_test)
                st2 = structural(models[b], models[a], fit.x_test)
                tab, tba = transfer(models[a], models[b], fit.x_test, ev.x_test), transfer(models[b], models[a], fit.x_test, ev.x_test)
                gap = 0.5 * (tab["transfer"]["mse1_gap"] + tba["transfer"]["mse1_gap"])
                og = 0.5 * (transfer_with_R(models[a], models[b], Rtrue[b].T @ Rtrue[a], ev.x_test) +
                            transfer_with_R(models[b], models[a], Rtrue[a].T @ Rtrue[b], ev.x_test))
                lab = lambda s: cats[s]["category"] + ("-" + cats[s]["incorrect_subtype"] if cats[s]["incorrect_subtype"] else "")
                rows.append(dict(group=group, method=tag, a=a, b=b, cka=0.5 * (st["cka"] + st2["cka"]),
                                 algebra_distance=0.5 * (st["algebra_distance"] + st2["algebra_distance"]),
                                 gap=gap, oracle_gap=og, class_a=lab(a), class_b=lab(b)))
            print(group, tag, "done", flush=True)
    (OUT / "transfer_allpairs.json").write_text(json.dumps(rows, indent=0))

    rng = np.random.default_rng(0)
    summary = {}
    for group in ["T2", "SO3"]:
        R = [r for r in rows if r["group"] == group]
        fail = np.array([r["gap"] > 0.5 for r in R])
        dist = np.array([r["algebra_distance"] for r in R])
        cka = np.array([r["cka"] for r in R])
        point = dict(auc_algebra_distance=auc(dist, fail), auc_cka=auc(-cka, fail), n_pairs=len(R),
                     n_fail=int(fail.sum()))
        boots = []
        for _ in range(1000):
            draw = rng.choice(SEEDS, size=len(SEEDS), replace=True)
            w = {s: int(np.sum(draw == s)) for s in SEEDS}
            idx = [i for i, r in enumerate(R) for _ in range(w[r["a"]] * w[r["b"]])]
            if not idx or fail[idx].all() or (~fail[idx]).all():
                continue
            boots.append((auc(dist[idx], fail[idx]), auc(-cka[idx], fail[idx])))
        bt = np.array(boots)
        diff = bt[:, 0] - bt[:, 1]
        point.update(ci_auc_algebra_distance=np.percentile(bt[:, 0], [2.5, 97.5]).tolist(),
                     ci_auc_cka=np.percentile(bt[:, 1], [2.5, 97.5]).tolist(),
                     auc_difference=point["auc_algebra_distance"] - point["auc_cka"],
                     ci_auc_difference=np.percentile(diff, [2.5, 97.5]).tolist(), n_boot=len(bt))
        # transfer by structural pair class, data-fitted vs oracle alignment (descriptive)
        def ptype(r):
            ca, cb = r["class_a"], r["class_b"]
            if "nonclosed" in (ca, cb) or "collapsed" in (ca, cb):
                return "involves_nonclosed"
            if ca == cb == "correct_closed":
                return "both_correct"
            if ca == cb:
                return "both_same_incorrect"
            return "correct_vs_incorrect"
        by = {}
        for r in R:
            by.setdefault(ptype(r), []).append(r)
        point["by_pair_type"] = {k: dict(n=len(v), median_gap=float(np.median([x["gap"] for x in v])),
                                         median_oracle_gap=float(np.median([x["oracle_gap"] for x in v])),
                                         frac_fail=float(np.mean([x["gap"] > 0.5 for x in v])),
                                         median_cka=float(np.median([x["cka"] for x in v])))
                                 for k, v in by.items()}
        summary[group] = point
        print(group, json.dumps({k: v for k, v in point.items() if k != "by_pair_type"}), flush=True)
        for k, v in point["by_pair_type"].items():
            print("   ", k, v)
    (OUT / "transfer_prediction.json").write_text(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
