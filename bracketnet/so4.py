"""Tools for so(4) = su(2)_L (+) su(2)_R used in the final mathematical audit.

These are independent of the participation-ratio / Killing-form diagnostics used elsewhere:
  * pfaffian(X) = x01 x23 - x02 x13 + x03 x12 is invariant under SO(4) conjugation and changes sign under a
    reflection; it vanishes exactly on rank-2 (single-plane) rotations, e.g. every element of the diagonal so(3).
  * chirality(U) = e_L - e_R, where e_L, e_R are the fractions of the span's Frobenius energy lying in the two
    simple ideals su(2)_L and su(2)_R (orthogonal complements in so(4)). Diagonal so(3): 0; su(2)_L: +1; su(2)_R: -1.
"""
from __future__ import annotations

import numpy as np
import torch

from .theory_checks import chiral_basis


def pfaffian(X: np.ndarray) -> np.ndarray:
    X = np.asarray(X)
    return X[..., 0, 1] * X[..., 2, 3] - X[..., 0, 2] * X[..., 1, 3] + X[..., 0, 3] * X[..., 1, 2]


def ideal_energies(A: np.ndarray) -> tuple[float, float]:
    """(e_L, e_R) for span(A) in so(4): mean squared norm of the projections of an orthonormal basis of the span
    onto su(2)_L and su(2)_R. e_L + e_R = 1 because so(4) = su(2)_L (+) su(2)_R orthogonally."""
    K = A.shape[0]
    U, s, _ = np.linalg.svd(A.reshape(K, -1).T, full_matrices=False)
    U = U[:, s > 1e-9 * s.max()]
    out = []
    for sign in (+1, -1):
        Bq = (chiral_basis(sign) / 1.0).reshape(3, -1).T          # norm sqrt(2) columns, mutually orthogonal
        Bq = Bq / np.linalg.norm(Bq, axis=0)
        out.append(float(np.linalg.norm(Bq.T @ U) ** 2 / U.shape[1]))
    return out[0], out[1]


def chirality(A: np.ndarray) -> float:
    eL, eR = ideal_energies(A)
    return eL - eR


def closure_flow(n_starts: int = 300, steps: int = 3000, lr: float = 0.05, seed: int = 0, tol: float = 1e-12):
    """Minimize the span-only (whitened) closure residual from random 3-dim subspaces of so(4) by gradient descent on
    an unconstrained basis. Uses no knowledge of the classification. Returns (chirality, Pfaffian-based handedness,
    final closure) per start."""
    from .model import closure_residual
    g = torch.Generator().manual_seed(seed)
    res = []
    for _ in range(n_starts):
        W = torch.randn(3, 4, 4, generator=g, dtype=torch.float64)
        W = (W - W.transpose(1, 2)).requires_grad_(True)
        opt = torch.optim.Adam([W], lr=lr)
        for _ in range(steps):
            A = 0.5 * (W - W.transpose(1, 2))
            loss = closure_residual(A, 0.0, "whitened")
            opt.zero_grad()
            loss.backward()
            opt.step()
            if loss.item() < tol:
                break
        A = (0.5 * (W - W.transpose(1, 2))).detach().numpy()
        U, s, _ = np.linalg.svd(A.reshape(3, -1).T, full_matrices=False)
        Ub = (np.sqrt(2) * U.T).reshape(3, 4, 4)
        pf = pfaffian(Ub)
        res.append(dict(chirality=chirality(A), mean_abs_pf=float(np.mean(np.abs(pf))),
                        closure=float(loss.item())))
    return res
