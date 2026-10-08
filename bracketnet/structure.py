"""Structural evaluation of a learned generator system against the ground truth.

A low closure residual is not evidence of correct algebra recovery. This module separates
collapsed, non-closed, correctly closed and incorrectly closed generator systems (thresholds are
pre-registered in configs/dev_selection.yaml, step_4) and measures action-inference fidelity
separately from algebraic structure.
"""
from __future__ import annotations

from functools import lru_cache

import numpy as np
import torch

from .alignment import conjugate, linear_cka, procrustes, random_span_distance, subspace_distance
from .data import Dataset
from .groups import GROUPS, true_generators
from .metrics import closure_residual_np, orthonormal_span, participation_ratio
from .model import BracketNet

COLLAPSE_RATIO = 0.1       # sigma_min / sigma_max of B below this -> collapsed
CLOSED_FRAC = 0.01         # closure <= 1 % of random-span closure -> closed
CORRECT_FRAC = 0.1         # ground-truth distance <= 10 % of chance -> correct
CHIRAL_PR = 3.0            # SO(3) in so(4): participation ratio >= 3 -> chiral su(2)
ACTION_BAD = 0.5           # normalized action disagreement with truth above this -> inaccurate action


@lru_cache(maxsize=None)
def random_closure_level(d: int, K: int, n: int = 2000, seed: int = 0) -> float:
    """Mean closure residual (Eq. 7, eps = 0) of random sqrt(2)-normalized K-dim spans of so(d)."""
    if K < 2:
        return 0.0
    rng = np.random.default_rng(seed)
    W = rng.standard_normal((n, K, d, d))
    W = W - W.transpose(0, 1, 3, 2)
    W = np.sqrt(2) * W / np.linalg.norm(W, axis=(2, 3), keepdims=True)
    return float(np.mean([closure_residual_np(w) for w in W]))


@lru_cache(maxsize=None)
def chance_distance(d: int, K: int) -> float:
    return random_span_distance(d, K)


def whitened_closure(A: np.ndarray) -> float:
    """Span-only (GL(K)-invariant) closure: Eq. (7) evaluated on a sqrt(2)-scaled orthonormal basis."""
    return closure_residual_np(orthonormal_span(A)) if A.shape[0] > 1 else 0.0


def delta_bound(A: np.ndarray) -> float:
    """Lemma 1: uniform escape constant delta <= K sqrt(L_close^{eps=0}) / lambda_min(B^T B)."""
    K = A.shape[0]
    G = A.reshape(K, -1) @ A.reshape(K, -1).T
    return float(K * np.sqrt(closure_residual_np(A)) / np.linalg.eigvalsh(G)[0]) if K > 1 else 0.0


def gt_coverage(A: np.ndarray, T: np.ndarray) -> float:
    """Fraction of the true span captured by span(A): ||U_T^T U_A||_F^2 / K_true (1 = contained)."""
    def onb(M):
        U, s, _ = np.linalg.svd(M.reshape(M.shape[0], -1).T, full_matrices=False)
        return U[:, s > 1e-9 * s.max()]
    UT, UA = onb(T), onb(A)
    return float(np.linalg.norm(UT.T @ UA) ** 2 / UT.shape[1])


@torch.no_grad()
def structural_report(model: BracketNet, ds: Dataset) -> dict:
    model.eval()
    g = ds.group
    d, K_true = GROUPS[g]["d"], GROUPS[g]["K"]
    T = true_generators(g)
    x = torch.as_tensor(ds.x_test, dtype=torch.float32)
    z = model.encoder(x).double().numpy()                         # (n, T+1, d)
    A_t = model.generators()
    Rm = model.rho(model.infer(model.encoder(x)[:, :-1], model.encoder(x)[:, 1:]), A_t).double().numpy()
    A = A_t.double().numpy()
    K = A.shape[0]

    sv = np.linalg.svd(A.reshape(K, -1), compute_uv=False)
    G = A.reshape(K, -1) @ A.reshape(K, -1).T
    rot, proc_res = procrustes(z.reshape(-1, d), ds.z_test.reshape(-1, d))
    A_al = conjugate(rot, A)
    gt_dist = subspace_distance(A_al, T)
    R_al = conjugate(rot, Rm)
    act = float(np.mean(np.sum((R_al - ds.g_test) ** 2, (-1, -2))) /
                np.mean(np.sum((ds.g_test - np.eye(d)) ** 2, (-1, -2))))

    clo = closure_residual_np(A, 1e-6)
    tau_c = CLOSED_FRAC * random_closure_level(d, K)
    tau_d = CORRECT_FRAC * chance_distance(d, K_true)
    pr = participation_ratio(A) if K > 0 else float("nan")
    collapsed = bool(K > 1 and sv.min() / sv.max() < COLLAPSE_RATIO)
    closed = bool(K < 2 or clo <= tau_c)
    if collapsed:
        cat = "collapsed"
    elif not closed:
        cat = "nonclosed"
    elif gt_dist <= tau_d and K == K_true:
        cat = "correct_closed"
    else:
        cat = "incorrect_closed"
    sub = None
    if cat == "incorrect_closed" and g in ("SO3", "SO3img") and K == 3:
        sub = "chiral" if pr >= CHIRAL_PR else "other"
    return dict(
        generator_singular_values=sv.tolist(), generator_rank=int(np.sum(sv > 1e-3 * sv.max())),
        sv_ratio=float(sv.min() / sv.max()), gram_condition=float(np.linalg.cond(G)),
        closure_whitened=whitened_closure(A), delta_bound=delta_bound(A),
        gt_algebra_distance=gt_dist, gt_coverage=gt_coverage(A_al, T), gt_chance_distance=chance_distance(d, K_true),
        procrustes_residual_truth=proc_res, cka_truth=linear_cka(z.reshape(-1, d), ds.z_test.reshape(-1, d)),
        action_disagreement_truth=act, participation_ratio=pr,
        tau_closed=tau_c, tau_correct=tau_d, category=cat, incorrect_subtype=sub,
        accurate_structure_inaccurate_action=bool(cat == "correct_closed" and act > ACTION_BAD),
    )


def convergence_report(history: list) -> dict:
    """Relative change of the training objective over the last 10 % of logged steps."""
    tot = np.array([h["total"] for h in history])
    n = max(2, len(tot) // 10)
    tail = tot[-n:]
    return dict(final_total=float(tot[-1]), rel_change_last10pct=float((tail[0] - tail[-1]) / max(abs(tail[0]), 1e-12)),
                final_terms={k: history[-1][k] for k in history[-1] if k not in ("step",)})
