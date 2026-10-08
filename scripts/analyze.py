"""Aggregate run JSONs into summary statistics and tables. Every number in the report and the
revised manuscript is produced here (results/summary.json, results/tables/*)."""
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bracketnet.stats import mean_sd, paired_ci, pct_reduction  # noqa: E402

METRICS = ["mse_1step", "mse_10step", "closure_residual", "commutator_norm", "invariant_commutator_norm",
           "composition_mse", "participation_ratio", "jacobi_residual"]
NAMES = {"local": "Local", "comp": "+Comp.", "bracketnet": "BracketNet (A, λ=0.1)",
         "bracketnetB": "BracketNet (B, λ=30)"}
PAPER = {  # Table 1 / Table 2 of the submitted manuscript, for side-by-side comparison only
    ("T2", "comp", "closure_residual"): 0.01303, ("T2", "bracketnet", "closure_residual"): 0.00334,
    ("SO3", "comp", "closure_residual"): 0.06697, ("SO3", "bracketnet", "closure_residual"): 0.01660,
    ("T2", "local", "closure_residual"): 0.01456, ("SO3", "local", "closure_residual"): 0.05882,
}


def load(phase):
    runs = defaultdict(dict)
    for p in sorted((ROOT / "results/runs" / phase).glob("*.json")):
        r = json.loads(p.read_text())
        m = dict(r["metrics"], runtime_s=r["runtime_s"])
        runs[(r["spec"]["group"], r["spec"]["tag"])][r["spec"]["seed"]] = m
    return runs


def summarize(runs):
    out = {}
    for (g, tag), by_seed in runs.items():
        seeds = sorted(by_seed)
        out[f"{g}/{tag}"] = dict(seeds=seeds, **{k: mean_sd([by_seed[s][k] for s in seeds])
                                                 for k in METRICS + ["runtime_s"]},
                                 transport_curve_mean=np.mean([by_seed[s]["transport_curve"] for s in seeds], 0).tolist(),
                                 transport_curve_sd=np.std([by_seed[s]["transport_curve"] for s in seeds], 0, ddof=1).tolist(),
                                 per_seed={k: [by_seed[s][k] for s in seeds] for k in METRICS})
    return out


def paired(runs, g, a, b, k):
    seeds = sorted(set(runs[(g, a)]) & set(runs[(g, b)]))
    return paired_ci([runs[(g, a)][s][k] for s in seeds], [runs[(g, b)][s][k] for s in seeds])


def threshold_from_validation(val):
    """Commutator-norm threshold between validation ranges of T2 and SO3, pooled over methods."""
    tags = ["local", "comp", "bracketnet_lam0.1", "bracketnet_lam30"]
    t2 = [m["commutator_norm"] for t in tags for m in val[("T2", t)].values()]
    so3 = [m["commutator_norm"] for t in tags for m in val[("SO3", t)].values()]
    sep = max(t2) < min(so3)
    return dict(T2_range=[min(t2), max(t2)], SO3_range=[min(so3), max(so3)], separable=sep,
                threshold=0.5 * (max(t2) + min(so3)) if sep else None, tags=tags)


def classify(test, tag, thr):
    pred_ok = [m["commutator_norm"] < thr for m in test[("T2", tag)].values()] + \
              [m["commutator_norm"] > thr for m in test[("SO3", tag)].values()]
    return int(sum(pred_ok)), len(pred_ok)


def fmt(ms, sci=False):
    m, s = ms
    return f"{m:.2e} ± {s:.1e}" if sci else f"{m:.5f} ± {s:.5f}"


def main():
    val, test, abl = load("validation"), load("test"), load("ablation")
    S = dict(validation=summarize(val), test=summarize(test), ablation=summarize(abl))
    comps = {}
    for g in ["T2", "SO3"]:
        for tag in ["bracketnet", "bracketnetB"]:
            c = {}
            for k in ["closure_residual", "mse_10step", "mse_1step", "commutator_norm"]:
                c[k] = paired(test, g, tag, "comp", k)
            sd = sorted(test[(g, tag)])
            c["closure_wins_vs_comp"] = int(sum(test[(g, tag)][x]["closure_residual"] < test[(g, "comp")][x]["closure_residual"] for x in sd))
            c["closure_reduction_pct_vs_comp"] = pct_reduction(S["test"][f"{g}/comp"]["closure_residual"][0],
                                                               S["test"][f"{g}/{tag}"]["closure_residual"][0])
            c["closure_reduction_pct_vs_local"] = pct_reduction(S["test"][f"{g}/local"]["closure_residual"][0],
                                                                S["test"][f"{g}/{tag}"]["closure_residual"][0])
            c["mse10_change_pct_vs_comp"] = -pct_reduction(S["test"][f"{g}/comp"]["mse_10step"][0],
                                                           S["test"][f"{g}/{tag}"]["mse_10step"][0])
            comps[f"{g}/{tag}_vs_comp"] = c
    abl_pairs = {}
    both = lambda g, ta, pa, tb, pb, k: paired_ci(
        [(abl if pa == "ablation" else test)[(g, ta)][s][k] for s in range(10, 15)],
        [(abl if pb == "ablation" else test)[(g, tb)][s][k] for s in range(10, 15)])
    for g in ["T2", "SO3"]:
        for k in ["mse_10step", "closure_residual"]:
            abl_pairs[f"{g}/const30_minus_staged30/{k}"] = both(g, "bracketnet_const30", "ablation", "bracketnetB", "test", k)
            abl_pairs[f"{g}/steps2000_lam30_minus_comp2000/{k}"] = both(g, "bracketnet_steps2000_lam30", "ablation",
                                                                         "comp_steps2000", "ablation", k)
            abl_pairs[f"{g}/splitmap_comp_minus_comp/{k}"] = both(g, "comp_splitmap", "ablation", "comp", "test", k)
        abl_pairs[f"{g}/gram1_minus_gram2/max_abs_diff_closure"] = float(max(
            abs(abl[(g, "bracketnet_gram1")][s]["closure_residual"] - test[(g, "bracketnetB")][s]["closure_residual"])
            for s in range(10, 15)))
    S["ablation_paired"] = abl_pairs
    thr = threshold_from_validation(val)
    cls = {}
    for tag in ["local", "comp", "bracketnet", "bracketnetB"]:
        cls[tag] = dict(at_validation_threshold=classify(test, tag, thr["threshold"]) if thr["separable"] else None,
                        at_paper_threshold_0p9=classify(test, tag, 0.9))
    S.update(paired_vs_comp=comps, threshold=thr, classification=cls,
             locked=json.loads((ROOT / "results/locked_hparams.json").read_text()))
    (ROOT / "results/summary.json").write_text(json.dumps(S, indent=1))
    write_tables(S)
    print_headlines(S)


def write_tables(S):
    T = S["test"]
    tdir = ROOT / "results/tables"
    tdir.mkdir(exist_ok=True)
    md = ["| Group | Method | 1-step MSE | 10-step MSE | Closure residual | Commutator norm |",
          "|---|---|---|---|---|---|"]
    tex = []
    for g, gl in [("SO2", "SO(2)"), ("T2", "$T^2$"), ("SO3", "SO(3)")]:
        for tag in ["local", "comp", "bracketnet", "bracketnetB"]:
            r = T[f"{g}/{tag}"]
            md.append(f"| {g} | {NAMES[tag]} | {fmt(r['mse_1step'])} | {fmt(r['mse_10step'])} | "
                      f"{fmt(r['closure_residual'])} | {r['commutator_norm'][0]:.3f} ± {r['commutator_norm'][1]:.3f} |")
            name = NAMES[tag].replace("λ", "$\\lambda$")
            tex.append(f"{gl} & {name} & {r['mse_1step'][0]:.4f}$\\pm${r['mse_1step'][1]:.4f} & "
                       f"{r['mse_10step'][0]:.4f}$\\pm${r['mse_10step'][1]:.4f} & "
                       f"{r['closure_residual'][0]:.4f}$\\pm${r['closure_residual'][1]:.4f} & "
                       f"{r['commutator_norm'][0]:.3f}$\\pm${r['commutator_norm'][1]:.3f} \\\\")
        tex.append("\\midrule")
    (tdir / "table1_test.md").write_text("\n".join(md) + "\n")
    (tdir / "table1_test.tex").write_text("\n".join(tex[:-1]) + "\n")

    A = S["ablation"]
    rows = ["| Variant | Group | 10-step MSE | Closure residual | Commutator norm | n |", "|---|---|---|---|---|---|"]
    for key in sorted(A):
        r = A[key]
        g, tag = key.split("/")
        rows.append(f"| {tag} | {g} | {fmt(r['mse_10step'])} | {fmt(r['closure_residual'])} | "
                    f"{r['commutator_norm'][0]:.3f} ± {r['commutator_norm'][1]:.3f} | {len(r['seeds'])} |")
    (tdir / "ablations.md").write_text("\n".join(rows) + "\n")

    V = S["validation"]
    rows = ["| Group | Run | 10-step MSE | Closure residual | Commutator norm |", "|---|---|---|---|---|"]
    for key in sorted(V):
        r = V[key]
        g, tag = key.split("/")
        rows.append(f"| {g} | {tag} | {fmt(r['mse_10step'])} | {fmt(r['closure_residual'])} | "
                    f"{r['commutator_norm'][0]:.3f} ± {r['commutator_norm'][1]:.3f} |")
    (tdir / "validation.md").write_text("\n".join(rows) + "\n")

    rows = ["| Group | Method | Composition MSE | Inv. commutator norm κ | Participation ratio | Runtime (s) |",
            "|---|---|---|---|---|---|"]
    for g in ["T2", "SO3"]:
        for tag in ["local", "comp", "bracketnet", "bracketnetB"]:
            r = T[f"{g}/{tag}"]
            rows.append(f"| {g} | {NAMES[tag]} | {fmt(r['composition_mse'], True)} | "
                        f"{r['invariant_commutator_norm'][0]:.3f} ± {r['invariant_commutator_norm'][1]:.3f} | "
                        f"{r['participation_ratio'][0]:.2f} ± {r['participation_ratio'][1]:.2f} | "
                        f"{r['runtime_s'][0]:.1f} ± {r['runtime_s'][1]:.1f} |")
    (tdir / "table2_diagnostics.md").write_text("\n".join(rows) + "\n")


def print_headlines(S):
    for k, c in S["paired_vs_comp"].items():
        cl, tr = c["closure_residual"], c["mse_10step"]
        print(f"{k}: closure {c['closure_reduction_pct_vs_comp']:+.1f}% red. "
              f"(diff {cl['mean_diff']:.4f} ± {cl['half_width']:.4f}, p_signflip={cl['sign_flip_p']:.3f}); "
              f"10-step change {c['mse10_change_pct_vs_comp']:+.1f}% (diff {tr['mean_diff']:.4f} ± {tr['half_width']:.4f})")
    print("threshold:", S["threshold"])
    print("classification:", S["classification"])


if __name__ == "__main__":
    main()
