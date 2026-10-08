"""Final-protocol analysis: every number in the final manuscript comes from this script's outputs
(results/final/summary_final.json and results/final/tables/*)."""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bracketnet.stats import holm, mcnemar_exact, mean_sd, paired_report, wilson  # noqa: E402

P = yaml.safe_load((ROOT / "configs/final_protocol.yaml").read_text())
OUT = ROOT / "results/final"
TAB = OUT / "tables"
TAB.mkdir(parents=True, exist_ok=True)
NAMES = {"local": "Local", "comp": "+Comp.", "bracketnet": "BracketNet", "bracketnet_lam0.1": "BracketNet ($\\lambda{=}0.1$)"}
ABL_NAMES = {"reference": "BracketNet (reference)", "comp_reference": "+Comp.\\ (reference)",
             "constant_penalty": "constant penalty, no staging", "no_freeze": "staged ramp, no freeze",
             "no_gram_penalty": "no Gram penalty", "weak_anticollapse": "anti-collapse weight 1",
             "whitened_closure": "span-only (whitened) closure", "lambda_x0.3": "$0.3\\lambda$", "lambda_x3": "$3\\lambda$",
             "K_plus1": "$K{+}1$ generators", "comp_K_plus1": "+Comp., $K{+}1$", "K_minus1": "$K{-}1$ generators"}
CATS = ["correct_closed", "incorrect_closed", "nonclosed", "collapsed"]


def load(phase):
    runs = defaultdict(dict)
    for p in sorted((OUT / "runs" / phase).glob("*.json")):
        r = json.loads(p.read_text())
        runs[(r["spec"]["group"], r["spec"]["tag"])][r["spec"]["seed"]] = r
    return runs


def flat(r):
    m, s, c = r["metrics"], r["metrics"]["structure"], r["metrics"]["convergence"]
    return dict(mse_1step=m["mse_1step"], mse_10step=m["mse_10step"], composition_mse=m["composition_mse"],
                closure=m["closure_residual"], closure_exact=m["closure_residual_exact"], closure_whitened=s["closure_whitened"],
                commutator_norm=m["commutator_norm"], invariant_commutator_norm=m["invariant_commutator_norm"],
                participation_ratio=s["participation_ratio"], gt_distance=s["gt_algebra_distance"], gt_coverage=s["gt_coverage"],
                cka_truth=s["cka_truth"], procrustes_truth=s["procrustes_residual_truth"], action_truth=s["action_disagreement_truth"],
                rank=s["generator_rank"], sv_ratio=s["sv_ratio"], gram_condition=s["gram_condition"], delta_bound=s["delta_bound"],
                runtime_s=r["runtime_s"], rel_change_last10pct=c["rel_change_last10pct"], category=s["category"],
                subtype=s["incorrect_subtype"], acc_struct_bad_action=s["accurate_structure_inaccurate_action"])


NUMERIC = ["mse_1step", "mse_10step", "composition_mse", "closure", "closure_exact", "closure_whitened", "commutator_norm",
           "invariant_commutator_norm", "participation_ratio", "gt_distance", "gt_coverage", "cka_truth", "procrustes_truth",
           "action_truth", "rank", "sv_ratio", "gram_condition", "delta_bound", "runtime_s", "rel_change_last10pct"]


def summarize_cell(by_seed):
    seeds = sorted(by_seed)
    rows = [flat(by_seed[s]) for s in seeds]
    out = dict(seeds=seeds, n=len(seeds), per_seed={k: [r[k] for r in rows] for k in NUMERIC + ["category", "subtype"]})
    out.update({k: mean_sd([r[k] for r in rows]) for k in NUMERIC})
    cnt = Counter(r["category"] for r in rows)
    out["categories"] = {c: cnt.get(c, 0) for c in CATS}
    out["correct_closed_rate_wilson95"] = wilson(cnt.get("correct_closed", 0), len(rows))
    out["chiral_count"] = sum(1 for r in rows if r["subtype"] == "chiral")
    out["acc_struct_bad_action_count"] = sum(r["acc_struct_bad_action"] for r in rows)
    out["transport_curve_mean"] = np.mean([by_seed[s]["metrics"]["transport_curve"] for s in seeds], 0).tolist()
    out["transport_curve_sd"] = np.std([by_seed[s]["metrics"]["transport_curve"] for s in seeds], 0, ddof=1).tolist()
    return out


def paired(runs, g, a, b, key, alt="two-sided"):
    seeds = sorted(set(runs[(g, a)]) & set(runs[(g, b)]))
    return paired_report([flat(runs[(g, a)][s])[key] for s in seeds], [flat(runs[(g, b)][s])[key] for s in seeds], alt)


def main():
    test, abl, dev = load("test"), load("ablation"), load("dev")
    S = dict(protocol=P, test={f"{g}/{t}": summarize_cell(v) for (g, t), v in test.items()},
             ablation={f"{g}/{t}": summarize_cell(v) for (g, t), v in abl.items()},
             dev={f"{g}/{t}": summarize_cell(v) for (g, t), v in dev.items()})

    # ---------------- secondary paired comparisons (two-sided) vs +Comp.
    comps = {}
    for g in ["T2", "SO3", "SO2"]:
        for t in ["bracketnet", "bracketnet_lam0.1", "local"]:
            for k in ["closure", "gt_distance", "mse_1step", "mse_10step", "composition_mse", "action_truth", "cka_truth"]:
                if (g, t) in test and (g, "comp") in test:
                    comps[f"{g}/{t}_vs_comp/{k}"] = paired(test, g, t, "comp", k)
    # paired binary: correct-closed
    for g in ["T2", "SO3"]:
        seeds = sorted(test[(g, "comp")])
        cc = lambda t: [flat(test[(g, t)][s])["category"] == "correct_closed" for s in seeds]
        comps[f"{g}/bracketnet_vs_comp/correct_closed_mcnemar"] = mcnemar_exact(cc("bracketnet"), cc("comp"))

    # ---------------- alignment / transfer (disjoint pairs as independent units)
    AT = json.loads((OUT / "alignment_transfer.json").read_text())
    align = {}
    for g in AT:
        for t in AT[g]:
            pairs = AT[g][t]["disjoint_pairs"]
            rec = {k: mean_sd([p[k] for p in pairs]) for k in ["cka", "procrustes_residual", "algebra_distance", "action_disagreement"]}
            for k in ["transfer", "transfer_projected", "native", "identity"]:
                for h in pairs[0]["transfer"][k]:
                    rec[f"{k}/{h}"] = mean_sd([p["transfer"][k][h] for p in pairs])
            both_cc = [p for p in pairs if p["categories"] == ["correct_closed", "correct_closed"]]
            rec["pairs_both_correct_closed"] = len(both_cc)
            rec["algebra_distance_both_correct"] = mean_sd([p["algebra_distance"] for p in both_cc]) if len(both_cc) > 1 else None
            rec["algebra_distance_other"] = mean_sd([p["algebra_distance"] for p in pairs if p not in both_cc]) \
                if len(pairs) - len(both_cc) > 1 else None
            rec["all_pairs_mean"] = AT[g][t]["all_pairs_algebra_distance_mean"]
            rec["all_pairs_jackknife_se"] = AT[g][t]["all_pairs_algebra_distance_jackknife_se"]
            rec["per_pair_algebra_distance"] = [p["algebra_distance"] for p in pairs]
            align[f"{g}/{t}"] = rec
    pair_cmp = {}
    for g in AT:
        for t in ["bracketnet", "bracketnet_lam0.1", "local"]:
            a, b = AT[g][t]["disjoint_pairs"], AT[g]["comp"]["disjoint_pairs"]
            assert [p["pair"] for p in a] == [p["pair"] for p in b]
            for k, get in [("algebra_distance", lambda p: p["algebra_distance"]), ("cka", lambda p: p["cka"]),
                           ("action_disagreement", lambda p: p["action_disagreement"]),
                           ("transfer_mse1_gap", lambda p: p["transfer"]["transfer"]["mse1_gap"]),
                           ("transfer_mse10_gap", lambda p: p["transfer"]["transfer"]["mse10_gap"]),
                           ("transfer_projected_mse1_gap", lambda p: p["transfer"]["transfer_projected"]["mse1_gap"]),
                           ("transfer_mse1", lambda p: p["transfer"]["transfer"]["mse1"])]:
                pair_cmp[f"{g}/{t}_vs_comp/{k}"] = paired_report([get(p) for p in a], [get(p) for p in b])

    # ---------------- pre-registered primary family (one-sided: BracketNet < +Comp.), Holm-corrected
    prim = {}
    for g in ["T2", "SO3"]:
        prim[f"H1_closure_{g}"] = paired(test, g, "bracketnet", "comp", "closure", "less")
        prim[f"H2_gt_distance_{g}"] = paired(test, g, "bracketnet", "comp", "gt_distance", "less")
        a, b = AT[g]["bracketnet"]["disjoint_pairs"], AT[g]["comp"]["disjoint_pairs"]
        prim[f"H3_cross_seed_distance_{g}"] = paired_report([p["algebra_distance"] for p in a],
                                                            [p["algebra_distance"] for p in b], "less")
    adj = holm({k: v["sign_flip_p"] for k, v in prim.items()})
    for k in prim:
        prim[k]["holm_p"] = adj[k]
        prim[k]["significant_at_0.05_holm"] = bool(adj[k] < 0.05)

    # ---------------- ablations vs reference on the same ablation seeds
    abl_cmp = {}
    for (g, t) in abl:
        if t == "reference":
            continue
        ref = "comp_reference" if t.startswith("comp") and t != "comp_reference" else "reference"
        for k in ["closure", "gt_distance", "mse_10step"]:
            abl_cmp[f"{g}/{t}_vs_{ref}/{k}"] = paired(abl, g, t, ref, k)

    # ---------------- pair-type stratification (descriptive): which structural classes do pairs fall into,
    # and does transfer success depend on structural correctness rather than on the method?
    strat = {}
    sub = {}
    for (g, t), by_seed in test.items():
        for sd, r in by_seed.items():
            st = r["metrics"]["structure"]
            sub[(g, t, sd)] = st["category"] + ("-" + st["incorrect_subtype"] if st["incorrect_subtype"] else "")
    def ptype(g, t, a, b):
        ca, cb = sub[(g, t, a)], sub[(g, t, b)]
        if "nonclosed" in (ca, cb) or "collapsed" in (ca, cb):
            return "involves_nonclosed_or_collapsed"
        if ca == cb == "correct_closed":
            return "both_correct"
        if ca == cb:
            return "both_same_incorrect_type"
        return "closed_different_types"
    pooled = defaultdict(list)
    for g in ["T2", "SO3"]:
        for t in AT[g]:
            types = Counter()
            dist_by = defaultdict(list)
            for p in AT[g][t]["disjoint_pairs"]:
                k = ptype(g, t, *p["pair"])
                types[k] += 1
                dist_by[k].append(p["algebra_distance"])
                pooled[(g, "both_correct" if k == "both_correct" else "not_both_correct")].append(p["transfer"]["transfer"]["mse1_gap"])
            strat[f"{g}/{t}"] = dict(pair_types=dict(types), distance_by_type={k: [float(x) for x in v] for k, v in dist_by.items()})
    transfer_by_correctness = {f"{g}/{k}": dict(n=len(v), median=float(np.median(v)), mean=float(np.mean(v)),
                                                 q25=float(np.percentile(v, 25)), q75=float(np.percentile(v, 75)))
                               for (g, k), v in pooled.items()}
    S.update(pair_strata=strat, transfer_by_correctness=transfer_by_correctness)

    S.update(paired_vs_comp=comps, alignment=align, alignment_paired_vs_comp=pair_cmp, primary=prim, ablation_paired=abl_cmp)
    (OUT / "summary_final.json").write_text(json.dumps(S, indent=1))
    write_tables(S)
    print("macros:", write_numbers(S))
    for k, v in prim.items():
        print(f"{k:32s} diff={v['mean_diff']:+.5f} [{v['ci_lo']:+.5f},{v['ci_hi']:+.5f}] p={v['sign_flip_p']:.2e} holm={v['holm_p']:.2e} dz={v['cohens_dz']:.2f} wins={v['wins_a_lower']}/{v['n']}")


def f(ms, nd=4):
    return f"{ms[0]:.{nd}f}$\\pm${ms[1]:.{nd}f}"


def sci(ms):
    def one(x):
        if x == 0:
            return "0"
        e = int(np.floor(np.log10(abs(x))))
        return f"{x / 10 ** e:.1f}{{\\times}}10^{{{e}}}"
    return f"${one(ms[0])}\\pm{one(ms[1])}$"


def write_tables(S):
    T = S["test"]
    groups = [("SO2", "SO(2)"), ("T2", "$T^2$"), ("SO3", "SO(3)")]
    methods = P["evaluation"]["methods"]
    # main table
    rows = []
    for g, gl in groups:
        for t in methods:
            r = T[f"{g}/{t}"]
            c = r["categories"]
            rows.append(f"{gl} & {NAMES[t]} & {f(r['mse_1step'])} & {f(r['mse_10step'])} & {sci(r['closure'])} & "
                        f"{f(r['gt_distance'], 3)} & {c['correct_closed']}/{r['n']} \\\\")
        rows.append("\\midrule")
    (TAB / "main.tex").write_text("\n".join(rows[:-1]) + "\n")
    # structure table
    rows = []
    for g, gl in groups[1:]:
        for t in methods:
            r = T[f"{g}/{t}"]
            c = r["categories"]
            rows.append(f"{gl} & {NAMES[t]} & {c['correct_closed']} & {c['incorrect_closed']} ({r['chiral_count']}) & "
                        f"{c['nonclosed']} & {c['collapsed']} & {r['acc_struct_bad_action_count']} & "
                        f"{f(r['action_truth'], 3)} & {f(r['participation_ratio'], 2)} \\\\")
        rows.append("\\midrule")
    (TAB / "structure.tex").write_text("\n".join(rows[:-1]) + "\n")
    # alignment table
    rows = []
    A = S["alignment"]
    for g, gl in groups[1:]:
        for t in methods:
            r = A[f"{g}/{t}"]
            rows.append(f"{gl} & {NAMES[t]} & {f(r['cka'], 3)} & {f(r['algebra_distance'], 3)} & "
                        f"{f(r['action_disagreement'], 3)} & {f(r['transfer/mse1_gap'], 3)} & {f(r['transfer_projected/mse1_gap'], 3)} \\\\")
        rows.append("\\midrule")
    (TAB / "alignment.tex").write_text("\n".join(rows[:-1]) + "\n")
    # primary hypotheses
    rows = []
    lab = {"H1_closure": "H1 closure", "H2_gt_distance": "H2 ground-truth distance", "H3_cross_seed_distance": "H3 cross-seed distance"}
    for k, v in S["primary"].items():
        h, g = k.rsplit("_", 1)
        rows.append(f"{lab[h]} & {'$T^2$' if g == 'T2' else 'SO(3)'} & {v['n']} & {v['mean_b']:.4f} & {v['mean_a']:.4f} & "
                    f"[{v['ci_lo']:+.4f}, {v['ci_hi']:+.4f}] & {v['cohens_dz']:.2f} & {v['wins_a_lower']}/{v['n']} & "
                    f"{v['sign_flip_p']:.1e} & {v['holm_p']:.1e} \\\\")
    (TAB / "primary.tex").write_text("\n".join(rows) + "\n")
    # ablations
    rows = []
    for g, gl in groups[1:]:
        for t in ["reference", "comp_reference", "constant_penalty", "no_freeze", "no_gram_penalty", "weak_anticollapse",
                  "whitened_closure", "lambda_x0.3", "lambda_x3", "K_plus1", "comp_K_plus1", "K_minus1"]:
            key = f"{g}/{t}"
            if key not in S["ablation"]:
                continue
            r = S["ablation"][key]
            c = r["categories"]
            rows.append(f"{gl} & {ABL_NAMES[t]} & {f(r['mse_10step'])} & {sci(r['closure'])} & {f(r['gt_distance'], 3)} & "
                        f"{f(r['gt_coverage'], 3)} & {c['correct_closed']}/{c['incorrect_closed']}/{c['nonclosed']}/{c['collapsed']} \\\\")
        rows.append("\\midrule")
    (TAB / "ablations.tex").write_text("\n".join(rows[:-1]) + "\n")
    # dev budget table (convergence analysis)
    rows = []
    D = S["dev"]
    for g, gl in groups[1:]:
        for B in [420, 1000, 2000, 4000]:
            cells = []
            for t in ["local", "comp", f"bracketnet_lam{P['training']['closure_weight']:g}"]:
                key = f"{g}/{t}_B{B}" if not t.startswith("bracketnet") else f"{g}/bracketnet_B{B}_lam{P['training']['closure_weight']:g}"
                r = D[key]
                cells.append(f"{r['mse_10step'][0]:.4f} & {r['closure'][0]:.4f} & {r['categories']['correct_closed']}/{r['n']}")
            rows.append(f"{gl} & {B} & " + " & ".join(cells) + " \\\\")
        rows.append("\\midrule")
    (TAB / "dev_budget.tex").write_text("\n".join(rows[:-1]) + "\n")



# ----------------------------------------------------------------------------- LaTeX number macros
DIG = {"0": "zero", "1": "one", "2": "two", "3": "three", "4": "four", "5": "five", "6": "six", "7": "seven", "8": "eight", "9": "nine"}
GN = {"SO2": "SOtwo", "T2": "Ttwo", "SO3": "SOthree"}
MN = {"local": "Local", "comp": "Comp", "bracketnet": "BN", "bracketnet_lam0.1": "BNref"}


def mname(*parts):
    s = "".join(p[:1].upper() + p[1:] for p in parts)
    s = "".join(DIG.get(c, c) for c in s if c.isalnum())
    assert s.isalpha(), s
    return "\\N" + s


def fnum(x, nd=3):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "n/a"
    ax = abs(x)
    if ax != 0 and (ax < 1e-3 or ax >= 1e4):
        e = int(np.floor(np.log10(ax)))
        return f"{x / 10 ** e:.{max(nd - 2, 1)}f}\\times10^{{{e}}}"
    return f"{x:.{nd}f}" if ax < 10 else f"{x:.{max(nd - 1, 1)}f}"


def fp(x):
    """p-value formatting: scientific below 0.01, two decimals otherwise."""
    return fnum(x, 2) if x >= 0.01 else f"{x / 10 ** int(np.floor(np.log10(x))):.1f}\\times10^{{{int(np.floor(np.log10(x)))}}}"


def write_numbers(S):
    L = []
    add = lambda name, val: L.append(f"\\newcommand{{{name}}}{{{val}}}")
    P_ = S["protocol"]
    add("\\NSteps", P_["training"]["steps"])
    add("\\NLambda", f"{P_['training']['closure_weight']:g}")
    add("\\NNseeds", len(P_["evaluation"]["test_seeds"]))
    add("\\NNpairs", len(P_["evaluation"]["test_seeds"]) // 2)
    add("\\NNabl", len(P_["evaluation"]["ablation_seeds"]))
    for key, r in S["test"].items():
        g, t = key.split("/")
        for k, nd in [("closure", 3), ("gt_distance", 3), ("mse_1step", 4), ("mse_10step", 4), ("composition_mse", 3),
                      ("action_truth", 3), ("cka_truth", 3), ("participation_ratio", 2), ("commutator_norm", 3),
                      ("runtime_s", 1), ("gram_condition", 2), ("closure_whitened", 3)]:
            add(mname(GN[g], MN[t], k.replace("_", "")), fnum(r[k][0], nd))
            add(mname(GN[g], MN[t], k.replace("_", ""), "sd"), fnum(r[k][1], nd))
        for c, v in r["categories"].items():
            add(mname(GN[g], MN[t], "cat", c.replace("_", "")), v)
        add(mname(GN[g], MN[t], "chiral"), r["chiral_count"])
        add(mname(GN[g], MN[t], "badaction"), r["acc_struct_bad_action_count"])
        lo, hi = r["correct_closed_rate_wilson95"]
        add(mname(GN[g], MN[t], "ccrate", "lo"), f"{100 * lo:.0f}")
        add(mname(GN[g], MN[t], "ccrate", "hi"), f"{100 * hi:.0f}")
    for key, v in S["primary"].items():
        h, g = key.rsplit("_", 1)
        hn = {"H1_closure": "Hone", "H2_gt_distance": "Htwo", "H3_cross_seed_distance": "Hthree"}[h]
        for k, nd in [("mean_diff", 4), ("ci_lo", 4), ("ci_hi", 4), ("cohens_dz", 2), ("sign_flip_p", 2),
                      ("holm_p", 2), ("pct_change_of_means", 1), ("mean_a", 4), ("mean_b", 4)]:
            add(mname(hn, GN[g], k.replace("_", "")), fp(v[k]) if k.endswith("_p") else fnum(v[k], nd))
        add(mname(hn, GN[g], "wins"), f"{v['wins_a_lower']}/{v['n']}")
        add(mname(hn, GN[g], "sig"), "yes" if v["significant_at_0.05_holm"] else "no")
    for key, v in S["paired_vs_comp"].items():
        if "mcnemar" in key:
            g = key.split("/")[0]
            add(mname(GN[g], "mcnemarp"), fp(v["p"]))
            continue
        g, rest, k = key.split("/")
        t = rest.replace("_vs_comp", "")
        for kk, nd in [("mean_diff", 4), ("ci_lo", 4), ("ci_hi", 4), ("sign_flip_p", 2), ("pct_change_of_means", 1)]:
            add(mname(GN[g], MN[t], "vs", k.replace("_", ""), kk.replace("_", "")), fp(v[kk]) if kk.endswith("_p") else fnum(v[kk], nd))
    for key, r in S["alignment"].items():
        g, t = key.split("/")
        for k in ["cka", "algebra_distance", "action_disagreement", "transfer/mse1_gap", "transfer/mse10_gap",
                  "transfer_projected/mse1_gap", "native/mse1", "transfer/mse1", "identity/mse1"]:
            add(mname("Al", GN[g], MN[t], k.replace("/", "").replace("_", "")), fnum(r[k][0], 3))
            add(mname("Al", GN[g], MN[t], k.replace("/", "").replace("_", ""), "sd"), fnum(r[k][1], 3))
        add(mname("Al", GN[g], MN[t], "bothcorrect"), r["pairs_both_correct_closed"])
        add(mname("Al", GN[g], MN[t], "allpairs"), fnum(r["all_pairs_mean"], 3))
        add(mname("Al", GN[g], MN[t], "allpairsse"), fnum(r["all_pairs_jackknife_se"], 3))
    for key, v in S["alignment_paired_vs_comp"].items():
        g, rest, k = key.split("/")
        t = rest.replace("_vs_comp", "")
        for kk, nd in [("mean_diff", 3), ("ci_lo", 3), ("ci_hi", 3), ("sign_flip_p", 2), ("cohens_dz", 2)]:
            add(mname("Ap", GN[g], MN[t], k.replace("_", ""), kk.replace("_", "")), fp(v[kk]) if kk.endswith("_p") else fnum(v[kk], nd))
        add(mname("Ap", GN[g], MN[t], k.replace("_", ""), "wins"), f"{v['wins_a_lower']}/{v['n']}")
    for key, r in S["ablation"].items():
        g, t = key.split("/")
        for k, nd in [("closure", 3), ("gt_distance", 3), ("mse_10step", 4), ("gt_coverage", 3), ("action_truth", 3), ("cka_truth", 2)]:
            add(mname("Ab", GN[g], t.replace("_", "").replace(".", "p"), k.replace("_", "")), fnum(r[k][0], nd))
        add(mname("Ab", GN[g], t.replace("_", "").replace(".", "p"), "cc"), f"{r['categories']['correct_closed']}/{r['n']}")
    for key, v in S["ablation_paired"].items():
        g, rest, k = key.split("/")
        a = rest.split("_vs_")[0]
        for kk, nd in [("mean_diff", 4), ("ci_lo", 4), ("ci_hi", 4), ("sign_flip_p", 2)]:
            add(mname("Abp", GN[g], a.replace("_", "").replace(".", "p"), k.replace("_", ""), kk.replace("_", "")), fp(v[kk]) if kk.endswith("_p") else fnum(v[kk], nd))
    for key, r in S["dev"].items():
        g, t = key.split("/")
        tt = t.replace("_", "").replace(".", "p")
        for k, nd in [("closure", 3), ("gt_distance", 3), ("mse_10step", 4)]:
            add(mname("Dev", GN[g], tt, k.replace("_", "")), fnum(r[k][0], nd))
        add(mname("Dev", GN[g], tt, "cc"), f"{r['categories']['correct_closed']}/{r['n']}")
    for key, v in S["pair_strata"].items():
        g, t = key.split("/")
        for k in ["both_correct", "both_same_incorrect_type", "closed_different_types", "involves_nonclosed_or_collapsed"]:
            add(mname("Pt", GN[g], MN[t], k.replace("_", "")), v["pair_types"].get(k, 0))
    for key, v in S["transfer_by_correctness"].items():
        g, k = key.split("/")
        for kk in ["n", "median", "q25", "q75"]:
            add(mname("Tc", GN[g], k.replace("_", ""), kk), v[kk] if kk == "n" else fnum(v[kk], 3))
    names = [l.split("}{")[0] for l in L]
    assert len(names) == len(set(names)), "duplicate macro names"
    (TAB / "numbers.tex").write_text("% AUTO-GENERATED by scripts/analyze_final.py from raw run files. Do not edit.\n" + "\n".join(L) + "\n")
    return len(L)


if __name__ == "__main__":
    main()
