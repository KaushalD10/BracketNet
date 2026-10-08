"""Independent statistical audit of the six pre-registered primary tests, from raw run files only.

Re-implements everything (does not import bracketnet.stats or analyze_final):
  * per-unit paired differences, exact one-sided sign-flip p (full enumeration), Holm adjustment;
  * t-intervals (as reported) vs. intervals obtained by INVERTING the two-sided exact sign-flip test
    (the interval matched to the primary inferential procedure) vs. percentile bootstrap intervals;
  * category counts; disjointness of the alignment pairs.
"""
import itertools
import json
from pathlib import Path

import numpy as np
from scipy import stats as sps

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "results/final/runs/test"
AT = json.loads((ROOT / "results/final/alignment_transfer.json").read_text())
SEEDS = list(range(100, 120))


def raw(group, tag, key):
    out = []
    for s in SEEDS:
        r = json.loads((RUNS / f"{group}_{tag}_s{s}.json").read_text())
        out.append(r["metrics"]["closure_residual"] if key == "closure" else r["metrics"]["structure"]["gt_algebra_distance"])
    return np.array(out)


def sign_matrix(n):
    idx = np.arange(1 << n)
    return np.where((idx[:, None] >> np.arange(n)) & 1, -1.0, 1.0)


def signflip(d, alt):
    S = sign_matrix(len(d))
    m = S @ d / len(d)
    obs = d.mean()
    if alt == "less":
        return float(np.mean(m <= obs + 1e-12))
    return float(np.mean(np.abs(m) >= abs(obs) - 1e-12))


def inverted_ci(d, level=0.95):
    """{mu : two-sided exact sign-flip p(d - mu) > 1 - level}, found by bisection on each side of the mean."""
    S = sign_matrix(len(d))
    n = len(d)
    md, ms = S @ d / n, S.sum(1) / n

    def p(mu):
        obs = abs(d.mean() - mu)
        return np.mean(np.abs(md - mu * ms) >= obs - 1e-12)
    alpha = 1 - level
    c, span = d.mean(), max(np.ptp(d), 1e-9) * 2

    def edge(direction):
        lo, hi = c, c + direction * span
        while p(hi) > alpha:
            hi += direction * span
        for _ in range(60):
            mid = 0.5 * (lo + hi)
            lo, hi = (mid, hi) if p(mid) > alpha else (lo, mid)
        return lo
    return [float(edge(-1)), float(edge(+1))]


def boot_ci(d, B=20000, seed=0):
    rng = np.random.default_rng(seed)
    m = d[rng.integers(0, len(d), (B, len(d)))].mean(1)
    return np.percentile(m, [2.5, 97.5]).tolist()


def t_ci(d):
    h = sps.t.ppf(0.975, len(d) - 1) * d.std(ddof=1) / np.sqrt(len(d))
    return [float(d.mean() - h), float(d.mean() + h)]


def main():
    tests = {}
    for g in ["T2", "SO3"]:
        for h, key in [("H1", "closure"), ("H2", "gt")]:
            d = raw(g, "bracketnet", key) - raw(g, "comp", key)
            tests[f"{h}_{g}"] = d
        a = [p["algebra_distance"] for p in AT[g]["bracketnet"]["disjoint_pairs"]]
        b = [p["algebra_distance"] for p in AT[g]["comp"]["disjoint_pairs"]]
        tests[f"H3_{g}"] = np.array(a) - np.array(b)
    out = {}
    for k, d in tests.items():
        out[k] = dict(n=len(d), mean_diff=float(d.mean()), median_diff=float(np.median(d)), sd=float(d.std(ddof=1)),
                      skew=float(sps.skew(d)), n_negative=int(np.sum(d < 0)), n_positive=int(np.sum(d > 0)),
                      p_signflip_one_sided=signflip(d, "less"), t_ci=t_ci(d), signflip_inverted_ci=inverted_ci(d),
                      bootstrap_ci=boot_ci(d), cohens_dz=float(d.mean() / d.std(ddof=1)),
                      per_unit=d.tolist())
    # Holm over the six one-sided p-values
    order = sorted(out, key=lambda k: out[k]["p_signflip_one_sided"])
    run = 0.0
    for i, k in enumerate(order):
        run = max(run, min(1.0, (len(order) - i) * out[k]["p_signflip_one_sided"]))
        out[k]["holm_p"] = run
    # consistency with the reported summary
    S = json.loads((ROOT / "results/final/summary_final.json").read_text())["primary"]
    name = {"H1": "H1_closure", "H2": "H2_gt_distance", "H3": "H3_cross_seed_distance"}
    for k in out:
        h, g = k.split("_")
        rep = S[f"{name[h]}_{g}"]
        out[k]["matches_reported"] = bool(np.isclose(rep["mean_diff"], out[k]["mean_diff"]) and
                                          np.isclose(rep["sign_flip_p"], out[k]["p_signflip_one_sided"]) and
                                          np.isclose(rep["holm_p"], out[k]["holm_p"]))
    # disjoint pairs: genuinely independent at the seed level
    pairs = [tuple(p["pair"]) for p in AT["SO3"]["bracketnet"]["disjoint_pairs"]]
    flat = [s for p in pairs for s in p]
    out["pairs_disjoint"] = dict(pairs=pairs, all_seeds_distinct=len(flat) == len(set(flat)) == 20)
    (ROOT / "results/review/statistical_audit.json").write_text(json.dumps(out, indent=1))
    for k, v in out.items():
        if k.startswith("H"):
            print(f"{k:7s} n={v['n']:2d} mean={v['mean_diff']:+.4f} med={v['median_diff']:+.4f} neg/pos={v['n_negative']}/{v['n_positive']} "
                  f"p1={v['p_signflip_one_sided']:.2e} holm={v['holm_p']:.2e} t={np.round(v['t_ci'],4)} "
                  f"inv={np.round(v['signflip_inverted_ci'],4)} boot={np.round(v['bootstrap_ci'],4)} skew={v['skew']:.2f} ok={v['matches_reported']}")
    print(out["pairs_disjoint"])


if __name__ == "__main__":
    main()
