"""Analytic solutions used to check Proposition 5 (endpoint ambiguity and zero-loss chiral solutions).

With the ground-truth state as the latent code (E = h^{-1}), we compare two closed generator systems in so(4):
  * the true diagonal so(3) (rotations of the first three coordinates), and
  * a chiral su(2) (left-isoclinic rotations, i.e. left multiplication by unit quaternions),
each with an action-inference rule that sees only the endpoints (z, z') of a transition.
"""
from __future__ import annotations

import numpy as np
from scipy.linalg import expm

from .groups import elementary_skew, true_generators


def chiral_basis(sign: int = +1) -> np.ndarray:
    """su(2)_L (sign=+1) or su(2)_R (sign=-1) in so(4), each element normalized to ||.||_F = sqrt(2)."""
    e = lambda i, j: elementary_skew(4, i, j)
    s = sign
    J = np.stack([e(1, 0) + s * e(3, 2), e(2, 0) + s * e(1, 3), e(3, 0) + s * e(2, 1)])
    return J / np.sqrt(2)


def chiral_infer(z: np.ndarray, z2: np.ndarray, sign: int = +1) -> np.ndarray:
    """Coefficients a with exp(sum_k a_k A_k) z = z2 for the chiral basis A (requires |z| = |z2| > 0).

    The unnormalized complex structures J_k = sqrt(2) A_k satisfy J_k^2 = -I and generate left multiplication by
    unit quaternions q = q0 + q.J, which acts simply transitively on each sphere. Solve [z, J1 z, J2 z, J3 z] q = z2,
    then a = sqrt(2) * theta * n for q = cos(theta) + sin(theta) n."""
    J = np.sqrt(2) * chiral_basis(sign)
    out = np.empty((len(z), 3))
    for i, (u, v) in enumerate(zip(z, z2)):
        M = np.stack([u, J[0] @ u, J[1] @ u, J[2] @ u], 1)
        q = np.linalg.solve(M, v)
        q /= np.linalg.norm(q)
        vec = q[1:]
        s = np.linalg.norm(vec)
        theta = np.arctan2(s, q[0])
        n = vec / s if s > 0 else np.zeros(3)
        out[i] = np.sqrt(2) * theta * n
    return out


def diagonal_infer_minimal(z: np.ndarray, z2: np.ndarray) -> np.ndarray:
    """Endpoint-only inference for the true diagonal so(3): the minimal rotation of R^3 taking z[:3] to z2[:3]
    (axis z x z2, angle between them); the 4th coordinate is invariant. Coefficients refer to the true basis
    T = (L_x, L_y, L_z) with ||T_k||_F = sqrt(2); exp(sum a_k T_k) rotates by |a| about -a/|a|."""
    u, v = z[:, :3], z2[:, :3]
    ax = np.cross(u, v)
    s = np.linalg.norm(ax, axis=1)
    c = np.einsum("ij,ij->i", u, v)
    ang = np.arctan2(s, c)
    n = ax / np.maximum(s, 1e-15)[:, None]
    return -n * ang[:, None]          # true basis = minus the textbook L_x, L_y, L_z (see groups.py)


def rho(a: np.ndarray, A: np.ndarray) -> np.ndarray:
    return np.stack([expm(np.einsum("k,kij->ij", ai, A)) for ai in a])


def evaluate_solution(z0, z1, z2, A, infer):
    """Latent transport and composition residuals of an (A, endpoint-inference) pair on triples."""
    a01, a12, a02 = infer(z0, z1), infer(z1, z2), infer(z0, z2)
    R01, R12, R02 = rho(a01, A), rho(a12, A), rho(a02, A)
    tr = np.mean(np.sum((np.einsum("nij,nj->ni", R01, z0) - z1) ** 2, 1) +
                 np.sum((np.einsum("nij,nj->ni", R12, z1) - z2) ** 2, 1))
    comp = np.mean(np.sum((R02 - R12 @ R01) ** 2, (1, 2)))
    coef_max = np.max(np.abs(np.concatenate([a01, a12, a02])), 1)
    return dict(transport=float(tr), composition=float(comp),
                frac_coef_above_bound=float(np.mean(coef_max > 0.65)))


def stabilizer_ambiguity(z, g_true):
    """For the diagonal action, compare the true group element with the minimal-rotation inference: the residual
    is a rotation about z itself (invisible from the endpoints)."""
    a_min = diagonal_infer_minimal(z, np.einsum("nij,nj->ni", g_true, z))
    R_min = rho(a_min, true_generators("SO3"))
    err = np.mean(np.sum((R_min - g_true) ** 2, (1, 2)))
    fixed = np.max(np.abs(np.einsum("nij,nj->ni", np.transpose(R_min, (0, 2, 1)) @ g_true, z) - z))
    return dict(action_error=float(err), residual_fixes_z_maxdev=float(fixed))
