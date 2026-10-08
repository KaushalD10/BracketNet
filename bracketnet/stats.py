"""Small-sample statistics used for every reported number."""
from __future__ import annotations

import itertools

import numpy as np
from scipy import stats as sps


def mean_sd(x) -> tuple[float, float]:
    x = np.asarray(x, float)
    return float(x.mean()), float(x.std(ddof=1)) if len(x) > 1 else 0.0


def paired_ci(a, b, level: float = 0.95) -> dict:
    """t-interval for mean(a - b) over paired seeds."""
    diff = np.asarray(a, float) - np.asarray(b, float)
    n = len(diff)
    m, s = diff.mean(), diff.std(ddof=1)
    half = sps.t.ppf(0.5 + level / 2, n - 1) * s / np.sqrt(n)
    return dict(mean_diff=float(m), half_width=float(half), lo=float(m - half), hi=float(m + half),
                excludes_zero=bool(abs(m) > half), n=n, sign_flip_p=sign_flip_p(diff))


def sign_flip_p(diff) -> float:
    """Exact two-sided paired permutation (sign-flip) p-value. With n = 5 the minimum is 0.0625."""
    diff = np.asarray(diff, float)
    obs = abs(diff.mean())
    flips = [abs((diff * np.array(s)).mean()) for s in itertools.product([1, -1], repeat=len(diff))]
    return float(np.mean([f >= obs - 1e-15 for f in flips]))


def pct_reduction(baseline_mean: float, method_mean: float) -> float:
    return float(100.0 * (baseline_mean - method_mean) / baseline_mean)


# ----------------------------------------------------------------------------- final-protocol statistics
def sign_flip_exact(diff, alternative: str = "two-sided") -> float:
    """Exact paired sign-flip (permutation) p-value for the mean difference, enumerating all 2^n sign
    vectors in chunks (n <= 24). alternative: 'two-sided' | 'less' (mean < 0) | 'greater'."""
    d = np.asarray(diff, float)
    n = len(d)
    assert n <= 24
    obs = d.mean()
    tot, hit = 0, 0
    chunk = 1 << 16
    bits = 1 << np.arange(n)
    for start in range(0, 1 << n, chunk):
        idx = np.arange(start, min(start + chunk, 1 << n))
        signs = np.where((idx[:, None] & bits) > 0, -1.0, 1.0)
        m = signs @ d / n
        if alternative == "two-sided":
            hit += int(np.sum(np.abs(m) >= abs(obs) - 1e-12))
        elif alternative == "less":
            hit += int(np.sum(m <= obs + 1e-12))
        else:
            hit += int(np.sum(m >= obs - 1e-12))
        tot += len(idx)
    return hit / tot


def paired_report(a, b, alternative: str = "two-sided", level: float = 0.95) -> dict:
    """Paired comparison of a - b over independent units: t-CI, exact sign-flip, Wilcoxon, d_z, wins."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    d = a - b
    n = len(d)
    m, s = float(d.mean()), float(d.std(ddof=1))
    half = float(sps.t.ppf(0.5 + level / 2, n - 1) * s / np.sqrt(n))
    try:
        w = float(sps.wilcoxon(d, alternative=alternative).pvalue) if np.any(d != 0) else 1.0
    except ValueError:
        w = float("nan")
    return dict(n=n, mean_a=float(a.mean()), mean_b=float(b.mean()), mean_diff=m, sd_diff=s,
                ci_lo=m - half, ci_hi=m + half, ci_excludes_zero=bool(abs(m) > half),
                sign_flip_p=sign_flip_exact(d, alternative), wilcoxon_p=w, alternative=alternative,
                cohens_dz=float(m / s) if s > 0 else float("nan"),
                median_diff=float(np.median(d)), wins_a_lower=int(np.sum(d < 0)), ties=int(np.sum(d == 0)),
                pct_change_of_means=float(100 * (a.mean() - b.mean()) / b.mean()) if b.mean() != 0 else float("nan"))


def holm(pvals: dict) -> dict:
    """Holm-Bonferroni adjusted p-values for a dict name -> p."""
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    k = len(items)
    out, running = {}, 0.0
    for i, (name, p) in enumerate(items):
        running = max(running, min(1.0, (k - i) * p))
        out[name] = running
    return out


def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    den = 1 + z ** 2 / n
    c = (p + z ** 2 / (2 * n)) / den
    h = z * np.sqrt(p * (1 - p) / n + z ** 2 / (4 * n ** 2)) / den
    return (float(c - h), float(c + h))


def mcnemar_exact(x, y) -> dict:
    """Exact McNemar test for paired binary outcomes x, y (two-sided)."""
    x, y = np.asarray(x, bool), np.asarray(y, bool)
    b, c = int(np.sum(x & ~y)), int(np.sum(~x & y))
    p = float(min(1.0, 2 * sps.binom.cdf(min(b, c), b + c, 0.5))) if b + c > 0 else 1.0
    return dict(only_first=b, only_second=c, p=p)
