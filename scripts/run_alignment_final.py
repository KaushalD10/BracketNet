"""Cross-seed structural alignment and cross-model transformation transfer (fresh test seeds).

Independent units: the 10 DISJOINT seed pairs (100,101), (102,103), ..., (118,119), identical for every
method so that methods are compared pair-by-pair. All-pairs (190 pairs) means are reported as a
descriptive U-statistic with a seed-level jackknife standard error, never as independent samples.

Latent alignment R is fitted on probe set A (probe seed 998) and every transfer metric is evaluated on a
disjoint held-out probe set B (probe seed 997).
"""
import itertools
import json
import sys
from pathlib import Path

import numpy as np
import torch
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bracketnet.alignment import conjugate, linear_cka, procrustes, subspace_distance  # noqa: E402
from bracketnet.data import make_dataset  # noqa: E402
from bracketnet.groups import GROUPS  # noqa: E402
from bracketnet.model import BracketNet  # noqa: E402

torch.set_num_threads(1)
P = yaml.safe_load((ROOT / "configs/final_protocol.yaml").read_text())
SEEDS = P["evaluation"]["test_seeds"]
PAIRS = [(SEEDS[i], SEEDS[i + 1]) for i in range(0, len(SEEDS), 2)]
METHODS = P["evaluation"]["methods"]
CK = ROOT / "results/final/checkpoints/test"
RUNS = ROOT / "results/final/runs/test"


def load(group, tag, seed):
    sd = torch.load(CK / f"{group}_{tag}_s{seed}.pt")
    d, K = GROUPS[group]["d"], sd["W"].shape[0]
    m = BracketNet(d, d, K)
    m.load_state_dict(sd)
    return m.eval()


@torch.no_grad()
def encode(m, x):
    return m.encoder(torch.as_tensor(x, dtype=torch.float32)).double()


def procrustes_uncentered(Za, Zb):
    """Origin-preserving orthogonal R with Zb ~ Za R^T (the group acts linearly about the origin)."""
    U, _, Vt = np.linalg.svd(Zb.T @ Za)
    return U @ Vt


@torch.no_grad()
def transfer(ma, mb, xa_fit, x_eval):
    """Transfer actions inferred by model a to model b's representation (eval on held-out x_eval)."""
    d = mb.d
    Ra = procrustes_uncentered(encode(ma, xa_fit).reshape(-1, d).numpy(), encode(mb, xa_fit).reshape(-1, d).numpy())
    R = torch.as_tensor(Ra)
    za, zb = encode(ma, x_eval), encode(mb, x_eval)
    Aa, Ab = ma.generators().double(), mb.generators().double()
    x = torch.as_tensor(x_eval, dtype=torch.float64)
    Ta = torch.linalg.matrix_exp(torch.einsum("ntk,kij->ntij", ma.infer(za[:, :-1].float(), za[:, 1:].float()).double(), Aa))
    Tb = torch.linalg.matrix_exp(torch.einsum("ntk,kij->ntij", mb.infer(zb[:, :-1].float(), zb[:, 1:].float()).double(), Ab))
    Tab = R @ Ta @ R.T                                         # a's actions expressed in b's coordinates
    # algebra-projected transfer: express R A^a(a) R^T in b's generator basis, re-exponentiate in b's algebra
    Xa = torch.einsum("ntk,kij->ntij", ma.infer(za[:, :-1].float(), za[:, 1:].float()).double(), Aa)
    Xab = R @ Xa @ R.T
    Bb = Ab.reshape(Ab.shape[0], -1).T
    coef = torch.linalg.lstsq(Bb, Xab.reshape(-1, d * d).T).solution.T.reshape(*Xab.shape[:2], -1)
    Tproj = torch.linalg.matrix_exp(torch.einsum("ntk,kij->ntij", coef, Ab))
    dec = lambda z: mb.decoder(z.float()).double()
    out = {}
    for name, T in [("native", Tb), ("transfer", Tab), ("transfer_projected", Tproj), ("identity", None)]:
        one = dec(zb[:, :-1]) if T is None else dec(torch.einsum("ntij,ntj->nti", T, zb[:, :-1]))
        mse1 = float(((one - x[:, 1:]) ** 2).mean())
        zh = zb[:, 0]
        for t in range(x.shape[1] - 1):
            if T is not None:
                zh = torch.einsum("nij,nj->ni", T[:, t], zh)
        mse10 = float(((dec(zh) - x[:, -1]) ** 2).mean())
        out[name] = dict(mse1=mse1, mse10=mse10)
    n, i = out["native"], out["identity"]
    for k in ("transfer", "transfer_projected"):
        for h in ("mse1", "mse10"):
            out[k][f"{h}_gap"] = (out[k][h] - n[h]) / (i[h] - n[h])   # 0 = native quality, 1 = identity guess
    return out


@torch.no_grad()
def structural(ma, mb, x_fit):
    """Align a onto b on the fit probe set; compare latents, algebras, actions."""
    d = mb.d
    za, zb = encode(ma, x_fit).numpy(), encode(mb, x_fit).numpy()
    rot, res = procrustes(za.reshape(-1, d), zb.reshape(-1, d))
    Aa, Ab = ma.generators().double().numpy(), mb.generators().double().numpy()
    with torch.no_grad():
        Ra = ma.rho(ma.infer(torch.as_tensor(za[:, :-1]).float(), torch.as_tensor(za[:, 1:]).float())).double().numpy()
        Rb = mb.rho(mb.infer(torch.as_tensor(zb[:, :-1]).float(), torch.as_tensor(zb[:, 1:]).float())).double().numpy()
    Ra_al = conjugate(rot, Ra)
    act = float(np.mean(np.sum((Ra_al - Rb) ** 2, (-1, -2))) / np.mean(np.sum((Rb - np.eye(d)) ** 2, (-1, -2))))
    return dict(cka=linear_cka(za.reshape(-1, d), zb.reshape(-1, d)), procrustes_residual=res,
                algebra_distance=subspace_distance(conjugate(rot, Aa), Ab), action_disagreement=act)


def category(group, tag, seed):
    r = json.loads((RUNS / f"{group}_{tag}_s{seed}.json").read_text())
    return r["metrics"]["structure"]["category"]


def main():
    out = {}
    for group in P["evaluation"]["groups"]:
        fit = make_dataset(group, P["evaluation"]["probe_seeds"]["alignment_fit"], n_train=1, n_test=200).x_test
        ev = make_dataset(group, P["evaluation"]["probe_seeds"]["transfer_eval"], n_train=1, n_test=200).x_test
        out[group] = {}
        for tag in METHODS:
            models = {s: load(group, tag, s) for s in SEEDS}
            cats = {s: category(group, tag, s) for s in SEEDS}
            pairs = []
            for a, b in PAIRS:
                st = structural(models[a], models[b], fit)
                st_rev = structural(models[b], models[a], fit)
                tr_ab = transfer(models[a], models[b], fit, ev)
                tr_ba = transfer(models[b], models[a], fit, ev)
                sym = {k: 0.5 * (st[k] + st_rev[k]) for k in st}
                trans = {k: {h: 0.5 * (tr_ab[k][h] + tr_ba[k][h]) for h in tr_ab[k]} for k in tr_ab}
                pairs.append(dict(pair=[a, b], categories=[cats[a], cats[b]], **sym, transfer=trans))
            # descriptive all-pairs U-statistic with seed-level jackknife SE for the algebra distance
            D = {}
            for a, b in itertools.combinations(SEEDS, 2):
                D[(a, b)] = structural(models[a], models[b], fit)["algebra_distance"]
            allmean = float(np.mean(list(D.values())))
            jk = [np.mean([v for (a, b), v in D.items() if s not in (a, b)]) for s in SEEDS]
            n = len(SEEDS)
            jk_se = float(np.sqrt((n - 1) / n * np.sum((np.array(jk) - np.mean(jk)) ** 2)))
            out[group][tag] = dict(disjoint_pairs=pairs, all_pairs_algebra_distance_mean=allmean,
                                   all_pairs_algebra_distance_jackknife_se=jk_se, n_all_pairs=len(D))
            print(group, tag, "pairs alg-dist", np.round([p["algebra_distance"] for p in pairs], 3),
                  "| transfer gap1", np.round(np.mean([p["transfer"]["transfer"]["mse1_gap"] for p in pairs]), 3), flush=True)
    (ROOT / "results/final/alignment_transfer.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
