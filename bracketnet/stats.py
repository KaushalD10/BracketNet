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
