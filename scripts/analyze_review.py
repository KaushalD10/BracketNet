"""Analysis of the final-review experiments (E1-E5, configs/review_preregistration.yaml).
Writes results/review/summary_review.json and results/review/numbers_review.tex (LaTeX macros, prefix \\R...)."""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bracketnet.so4 import chirality, ideal_energies  # noqa: E402
from bracketnet.metrics import closure_residual_np  # noqa: E402
from bracketnet.stats import mcnemar_exact, paired_report, wilson  # noqa: E402

RV = ROOT / "results/review"
FINAL = ROOT / "results/final/runs/test"


def cls(r):
    s = r["metrics"]["structure"]
    return s["category"] + ("-" + s["incorrect_subtype"] if s["incorrect_subtype"] else "")


def load(phase):
    out = defaultdict(dict)
    for p in sorted((RV / "runs" / phase).glob("*.json")):
        r = json.loads(p.read_text())
        out[r["spec"]["tag"]][r["spec"]["seed"]] = r
    return out


def auc(score_pos_high, y):
    s, y = np.asarray(score_pos_high, float), np.asarray(y, bool)
    pos, neg = s[y], s[~y]
    if not len(pos) or not len(neg):
        return float("nan")
    return float(np.mean(pos[:, None] > neg[None, :]) + 0.5 * np.mean(pos[:, None] == neg[None, :]))


def threshold_sensitivity():
    """Robustness (not pre-registered): SO(3) fresh-seed category counts under alternative thresholds."""
    from bracketnet.structure import random_closure_level, chance_distance
    tc0, td0 = random_closure_level(4, 3), chance_distance(4, 3)
    out = []
    for cf in (0.001, 0.01, 0.05):
        for df in (0.05, 0.1, 0.2):
            row = dict(closed_frac=cf, correct_frac=df)
            for tag in ("comp", "bracketnet"):
                c = Counter()
                for p in sorted(FINAL.glob(f"SO3_{tag}_s*.json")):
                    r = json.loads(p.read_text())
                    st = r["metrics"]["structure"]
                    closed = r["metrics"]["closure_residual"] <= cf * tc0
                    if not closed:
                        c["nonclosed"] += 1
                    elif st["gt_algebra_distance"] <= df * td0:
                        c["correct"] += 1
                    elif st["participation_ratio"] >= 3:
                        c["chiral"] += 1
                    else:
                        c["other"] += 1
                row[tag] = dict(c)
            out.append(row)
    return out


def e1():
    """Composition error by structural class, all fresh-seed SO(3) runs (descriptive)."""
    by = defaultdict(list)
    for p in FINAL.glob("SO3_*.json"):
        r = json.loads(p.read_text())
        by[cls(r)].append((r["metrics"]["composition_mse"], r["metrics"]["mse_1step"], r["metrics"]["structure"]["action_disagreement_truth"]))
    return {k: dict(n=len(v), median_composition_mse=float(np.median([x[0] for x in v])),
                    median_mse1=float(np.median([x[1] for x in v])), median_action=float(np.median([x[2] for x in v])))
            for k, v in by.items()}


def e2():
    T = load("trace")["bracketnet"]
    rows, identical = [], []
    for s, r in sorted(T.items()):
        ref = json.loads((FINAL / f"SO3_bracketnet_s{s}.json").read_text())
        identical.append(all(r["metrics"][k] == ref["metrics"][k] for k in ["mse_1step", "mse_10step", "closure_residual"])
                         and cls(r) == cls(ref))
        snaps = {int(k): np.array(v) for k, v in r["snapshots"].items()}
        row = dict(seed=s, final_class=cls(r))
        for k, A in sorted(snaps.items()):
            row[f"chi_{k}"] = chirality(A)
            row[f"closure_{k}"] = closure_residual_np(A)
        rows.append(row)
    steps = sorted({int(k.split("_")[1]) for k in rows[0] if k.startswith("chi_")})
    ramp = steps[1]
    closed = [r for r in rows if r["final_class"] in ("correct_closed", "incorrect_closed-chiral")]
    y = [r["final_class"] == "incorrect_closed-chiral" for r in closed]
    out = dict(rows=rows, steps=steps, all_bit_identical=bool(all(identical)), n_identical=int(sum(identical)),
               auc_abs_chi_at_ramp=auc([abs(r[f"chi_{ramp}"]) for r in closed], y),
               auc_abs_chi_at_init=auc([abs(r[f"chi_{steps[0]}"]) for r in closed], y),
               n_closed=len(closed), n_chiral=int(sum(y)))
    # POST-HOC (not pre-registered): closure residual of the span at the ramp start as a predictor
    out["posthoc_auc_closure_at_ramp"] = auc([r[f"closure_{ramp}"] for r in closed], y)
    out["posthoc_correct_nearclosed_at_ramp"] = int(sum(r[f"closure_{ramp}"] < 0.1 for r in closed if r["final_class"] == "correct_closed"))
    out["posthoc_chiral_far_at_ramp"] = int(sum(r[f"closure_{ramp}"] >= 0.1 for r in closed if r["final_class"] != "correct_closed"))
    out["n_correct_closed"] = int(sum(r["final_class"] == "correct_closed" for r in closed))
    for c in ["correct_closed", "incorrect_closed-chiral", "nonclosed"]:
        sub = [r for r in rows if r["final_class"] == c]
        out[f"median_abs_chi_ramp_{c}"] = float(np.median([abs(r[f"chi_{ramp}"]) for r in sub])) if sub else None
        out[f"median_abs_chi_final_{c}"] = float(np.median([abs(r[f"chi_{steps[-1]}"]) for r in sub])) if sub else None
    return out


def e3():
    O = load("oracle")
    out = {}
    for tag, runs in O.items():
        c = Counter(cls(r) for r in runs.values())
        n = len(runs)
        out[tag] = dict(n=n, counts=dict(c), chiral=c.get("incorrect_closed-chiral", 0), correct=c.get("correct_closed", 0),
                        nonclosed=c.get("nonclosed", 0), correct_wilson=wilson(c.get("correct_closed", 0), n),
                        mean_gt=float(np.mean([r["metrics"]["structure"]["gt_algebra_distance"] for r in runs.values()])),
                        mean_closure=float(np.mean([r["metrics"]["closure_residual"] for r in runs.values()])),
                        mean_action=float(np.mean([r["metrics"]["structure"]["action_disagreement_truth"] for r in runs.values()])))
    seeds = sorted(O["bracketnet"])
    ind = lambda tag, f: [f(O[tag][s]) for s in seeds]
    out["chiral_oracle_bn_vs_bn"] = mcnemar_exact(ind("oracle_bn", lambda r: cls(r) == "incorrect_closed-chiral"),
                                                  ind("bracketnet", lambda r: cls(r) == "incorrect_closed-chiral"))
    out["correct_oracle_bn_vs_bn"] = mcnemar_exact(ind("oracle_bn", lambda r: cls(r) == "correct_closed"),
                                                   ind("bracketnet", lambda r: cls(r) == "correct_closed"))
    out["gt_oracle_bn_vs_bn"] = paired_report(ind("oracle_bn", lambda r: r["metrics"]["structure"]["gt_algebra_distance"]),
                                              ind("bracketnet", lambda r: r["metrics"]["structure"]["gt_algebra_distance"]))
    return out


def render_class(r):
    """Rendered benchmark: the learned latent is far from an isometry of the true state, so the Procrustes-based
    ground-truth distance is not interpretable; the class of a closed span is identified by the alignment-free
    chirality invariant (|chi| > 0.9: chiral; |chi| < 0.1: diagonal-type)."""
    s = r["metrics"]["structure"]
    if s["category"] == "nonclosed" or s["category"] == "collapsed":
        return s["category"]
    chi = chirality(np.array(r["metrics"]["generators"]))
    return "incorrect_closed-chiral" if abs(chi) > 0.9 else ("diagonal_type" if abs(chi) < 0.1 else "other_closed")


def e4():
    R = load("render")
    out = {}
    for tag, runs in R.items():
        c = Counter(render_class(r) for r in runs.values())
        out[tag] = dict(n=len(runs), counts=dict(c), chiral=c.get("incorrect_closed-chiral", 0),
                        correct=c.get("correct_closed", 0) + c.get("diagonal_type", 0), nonclosed=c.get("nonclosed", 0),
                        **{k: [float(np.mean(v)), float(np.std(v, ddof=1))] for k, v in {
                            "closure": [r["metrics"]["closure_residual"] for r in runs.values()],
                            "gt": [r["metrics"]["structure"]["gt_algebra_distance"] for r in runs.values()],
                            "mse1": [r["metrics"]["mse_1step"] for r in runs.values()],
                            "mse10": [r["metrics"]["mse_10step"] for r in runs.values()],
                            "cka_truth": [r["metrics"]["structure"]["cka_truth"] for r in runs.values()],
                            "procrustes_truth": [r["metrics"]["structure"]["procrustes_residual_truth"] for r in runs.values()],
                            "comp_mse": [r["metrics"]["composition_mse"] for r in runs.values()]}.items()})
    seeds = sorted(R["comp"])
    g = lambda tag, f: [f(R[tag][s]) for s in seeds]
    out["closure_bn_vs_comp"] = paired_report(g("bracketnet", lambda r: r["metrics"]["closure_residual"]),
                                              g("comp", lambda r: r["metrics"]["closure_residual"]), "less")
    out["gt_bn_vs_comp"] = paired_report(g("bracketnet", lambda r: r["metrics"]["structure"]["gt_algebra_distance"]),
                                         g("comp", lambda r: r["metrics"]["structure"]["gt_algebra_distance"]))
    out["mse10_bn_vs_comp"] = paired_report(g("bracketnet", lambda r: r["metrics"]["mse_10step"]),
                                            g("comp", lambda r: r["metrics"]["mse_10step"]))
    return out


DIG = dict(zip("0123456789", ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]))


def mac(*parts):
    s = "".join(p[:1].upper() + p[1:] for p in parts)
    s = "".join(DIG.get(c, c) for c in s if c.isalnum())
    return "\\R" + s


def fmt(x, nd=3):
    if x is None:
        return "n/a"
    if isinstance(x, (int, np.integer)):
        return str(int(x))
    ax = abs(x)
    if ax != 0 and ax < 1e-3:
        e = int(np.floor(np.log10(ax)))
        return f"{x / 10 ** e:.1f}\\times10^{{{e}}}"
    return f"{x:.{nd}f}"


def fp(x):
    return fmt(x, 2) if x >= 0.01 else f"{x / 10 ** int(np.floor(np.log10(x))):.1f}\\times10^{{{int(np.floor(np.log10(x)))}}}"


def mathsafe(v):
    """Wrap values with math syntax so the macro works in text and in math mode."""
    v = str(v)
    return f"\\ensuremath{{{v}}}" if ("\\times" in v or "^" in v) else v


def main():
    S = dict(E1=e1(), threshold_sensitivity=threshold_sensitivity())
    L = []
    add = lambda n, v: L.append(f"\\newcommand{{{n}}}{{{mathsafe(v)}}}")
    for k, v in S["E1"].items():
        kk = k.replace("_", "").replace("-", "")
        add(mac("Eone", kk, "n"), v["n"])
        add(mac("Eone", kk, "comp"), fmt(v["median_composition_mse"]))
        add(mac("Eone", kk, "mseone"), fmt(v["median_mse1"], 4))
        add(mac("Eone", kk, "action"), fmt(v["median_action"], 2))
    if (RV / "runs/trace").exists():
        S["E2"] = e2()
        e = S["E2"]
        add(mac("Etwo", "identical"), f"{e['n_identical']}/{len(e['rows'])}")
        add(mac("Etwo", "aucramp"), fmt(e["auc_abs_chi_at_ramp"], 2))
        add(mac("Etwo", "aucinit"), fmt(e["auc_abs_chi_at_init"], 2))
        add(mac("Etwo", "nclosed"), e["n_closed"])
        add(mac("Etwo", "nchiral"), e["n_chiral"])
        add(mac("Etwo", "ncorrect"), e["n_correct_closed"])
        add(mac("Etwo", "aucclosure"), fmt(e["posthoc_auc_closure_at_ramp"], 2))
        add(mac("Etwo", "correctnear"), e["posthoc_correct_nearclosed_at_ramp"])
        add(mac("Etwo", "chiralfar"), e["posthoc_chiral_far_at_ramp"])
        for c in ["correct_closed", "incorrect_closed-chiral", "nonclosed"]:
            add(mac("Etwo", "chiramp", c.replace("_", "").replace("-", "")), fmt(e[f"median_abs_chi_ramp_{c}"], 2))
            add(mac("Etwo", "chifinal", c.replace("_", "").replace("-", "")), fmt(e[f"median_abs_chi_final_{c}"], 2))
    if (RV / "runs/oracle").exists() and len(list((RV / "runs/oracle").glob("*.json"))) == 80:
        S["E3"] = e3()
        for tag in ["bracketnet", "comp", "oracle_bn", "oracle_local"]:
            v = S["E3"][tag]
            t = tag.replace("_", "")
            for k in ["n", "chiral", "correct", "nonclosed"]:
                add(mac("Ethree", t, k), v[k])
            add(mac("Ethree", t, "gt"), fmt(v["mean_gt"]))
            add(mac("Ethree", t, "action"), fmt(v["mean_action"], 2))
            add(mac("Ethree", t, "cclo"), f"{100 * v['correct_wilson'][0]:.0f}")
            add(mac("Ethree", t, "cchi"), f"{100 * v['correct_wilson'][1]:.0f}")
        add(mac("Ethree", "chiralp"), fp(S["E3"]["chiral_oracle_bn_vs_bn"]["p"]))
        add(mac("Ethree", "correctp"), fp(S["E3"]["correct_oracle_bn_vs_bn"]["p"]))
        g = S["E3"]["gt_oracle_bn_vs_bn"]
        add(mac("Ethree", "gtdiff"), fmt(g["mean_diff"]))
        add(mac("Ethree", "gtlo"), fmt(g["ci_lo"]))
        add(mac("Ethree", "gthi"), fmt(g["ci_hi"]))
        add(mac("Ethree", "gtp"), fp(g["sign_flip_p"]))
    if (RV / "runs/render").exists() and len(list((RV / "runs/render").glob("*.json"))) == 60:
        S["E4"] = e4()
        for tag in ["local", "comp", "bracketnet"]:
            v = S["E4"][tag]
            for k in ["chiral", "correct", "nonclosed", "n"]:
                add(mac("Efour", tag, k), v[k])
            for k in ["closure", "gt", "mse1", "mse10", "cka_truth", "procrustes_truth", "comp_mse"]:
                add(mac("Efour", tag, k.replace("_", "")), fmt(v[k][0], 4 if "mse" in k else 3))
                add(mac("Efour", tag, k.replace("_", ""), "sd"), fmt(v[k][1], 4 if "mse" in k else 3))
        for k in ["closure_bn_vs_comp", "gt_bn_vs_comp", "mse10_bn_vs_comp"]:
            v = S["E4"][k]
            for kk in ["mean_diff", "ci_lo", "ci_hi"]:
                add(mac("Efour", k.replace("_", ""), kk.replace("_", "")), fmt(v[kk], 4))
            add(mac("Efour", k.replace("_", ""), "p"), fp(v["sign_flip_p"]))
            add(mac("Efour", k.replace("_", ""), "wins"), f"{v['wins_a_lower']}/{v['n']}")
    if (RV / "transfer_prediction.json").exists():
        TP = json.loads((RV / "transfer_prediction.json").read_text())
        S["E5"] = TP
        for g, v in TP.items():
            gg = {"T2": "Ttwo", "SO3": "SOthree"}[g]
            add(mac("Efive", gg, "aucdist"), fmt(v["auc_algebra_distance"], 2))
            add(mac("Efive", gg, "auccka"), fmt(v["auc_cka"], 2))
            add(mac("Efive", gg, "aucdistlo"), fmt(v["ci_auc_algebra_distance"][0], 2))
            add(mac("Efive", gg, "aucdisthi"), fmt(v["ci_auc_algebra_distance"][1], 2))
            add(mac("Efive", gg, "auccKalo"), fmt(v["ci_auc_cka"][0], 2))
            add(mac("Efive", gg, "auccKahi"), fmt(v["ci_auc_cka"][1], 2))
            add(mac("Efive", gg, "diff"), fmt(v["auc_difference"], 2))
            add(mac("Efive", gg, "difflo"), fmt(v["ci_auc_difference"][0], 2))
            add(mac("Efive", gg, "diffhi"), fmt(v["ci_auc_difference"][1], 2))
            add(mac("Efive", gg, "npairs"), v["n_pairs"])
            add(mac("Efive", gg, "nfail"), v["n_fail"])
            for pt, w in v["by_pair_type"].items():
                p = pt.replace("_", "")
                add(mac("Efive", gg, p, "n"), w["n"])
                add(mac("Efive", gg, p, "gap"), fmt(w["median_gap"], 3))
                add(mac("Efive", gg, p, "oraclegap"), fmt(w["median_oracle_gap"], 3))
                add(mac("Efive", gg, p, "fail"), f"{100 * w['frac_fail']:.0f}")
                add(mac("Efive", gg, p, "cka"), fmt(w["median_cka"], 3))
    CF = json.loads((RV / "closure_flow.json").read_text())
    c = Counter(CF["classes"])
    S["closure_flow"] = dict(c)
    add(mac("Flow", "n"), len(CF["classes"]))
    add(mac("Flow", "diag"), c.get("diagonal", 0))
    add(mac("Flow", "chiral"), c.get("chiral_L", 0) + c.get("chiral_R", 0))
    SA = json.loads((RV / "statistical_audit.json").read_text())
    S["statistical_audit"] = SA
    for k in ["H1_T2", "H2_T2", "H3_T2", "H1_SO3", "H2_SO3", "H3_SO3"]:
        h, g = k.split("_")
        gg = {"T2": "Ttwo", "SO3": "SOthree"}[g]
        hh = {"H1": "Hone", "H2": "Htwo", "H3": "Hthree"}[h]
        add(mac("Inv", hh, gg, "lo"), fmt(SA[k]["signflip_inverted_ci"][0], 4))
        add(mac("Inv", hh, gg, "hi"), fmt(SA[k]["signflip_inverted_ci"][1], 4))
        add(mac("Inv", hh, gg, "median"), fmt(SA[k]["median_diff"], 4))
        add(mac("Inv", hh, gg, "skew"), fmt(SA[k]["skew"], 2))
    # statistical audit table (appendix): t vs. sign-flip-inverted vs. bootstrap intervals
    tab = []
    lab = {"H1": "H1 closure", "H2": "H2 GT distance", "H3": "H3 cross-seed"}
    for k in ["H1_T2", "H2_T2", "H3_T2", "H1_SO3", "H2_SO3", "H3_SO3"]:
        h, g = k.split("_")
        v = SA[k]
        ci = lambda c: f"[{c[0]:+.4f}, {c[1]:+.4f}]"
        tab.append(f"{lab[h]} & {'$T^2$' if g == 'T2' else 'SO(3)'} & {v['n']} & {v['median_diff']:+.4f} & {v['skew']:.2f} & "
                   f"{ci(v['t_ci'])} & {ci(v['signflip_inverted_ci'])} & {ci(v['bootstrap_ci'])} \\\\")
    (RV / "tables").mkdir(exist_ok=True)
    (RV / "tables/stats_audit.tex").write_text("\n".join(tab) + "\n")
    rows = []
    for r in S["threshold_sensitivity"]:
        f = lambda d: f"{d.get('correct', 0)}/{d.get('chiral', 0)}/{d.get('other', 0)}/{d.get('nonclosed', 0)}"
        rows.append(f"{100 * r['closed_frac']:g}\\% & {100 * r['correct_frac']:g}\\% & {f(r['comp'])} & {f(r['bracketnet'])} \\\\")
    (RV / "tables/threshold_sensitivity.tex").write_text("\n".join(rows) + "\n")
    # main-text table without the trivial SO(2) block (full table stays in the appendix)
    main_rows = (ROOT / "results/final/tables/main.tex").read_text().split("\\midrule\n")
    (RV / "tables/main_t2so3.tex").write_text("\\midrule\n".join(b for b in main_rows if not b.startswith("SO(2)")))
    names = [l.split("}{")[0] for l in L]
    assert len(names) == len(set(names)), "duplicate macro"
    (RV / "summary_review.json").write_text(json.dumps(S, indent=1, default=str))
    (RV / "numbers_review.tex").write_text("% AUTO-GENERATED by scripts/analyze_review.py. Do not edit.\n" + "\n".join(L) + "\n")
    print("macros:", len(L))
    print(json.dumps({k: v for k, v in S.items() if k not in ("statistical_audit",)}, indent=1, default=str)[:6000])


if __name__ == "__main__":
    main()
