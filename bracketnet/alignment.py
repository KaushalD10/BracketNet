"""Structural alignment between independently trained representations (new experiment).

Two models trained from different seeds see the same observation map, so they can be
compared on a shared probe set. Latent codes are only identifiable up to conjugacy, so
we first align latents with orthogonal Procrustes and then ask whether the *algebras*
and the *inferred actions* agree in the aligned coordinates. The same machinery compares
each model with the ground-truth latent state and generators.
"""
from __future__ import annotations

import numpy as np
import torch

from .model import BracketNet


def procrustes(Za: np.ndarray, Zb: np.ndarray):
    """Orthogonal R minimizing ||Zb_c - Za_c R^T||_F (centered). Returns R, normalized residual."""
    a, b = Za - Za.mean(0), Zb - Zb.mean(0)
    U, _, Vt = np.linalg.svd(b.T @ a)
    R = U @ Vt
    res = np.linalg.norm(b - a @ R.T) ** 2 / np.linalg.norm(b) ** 2
    return R, float(res)


def linear_cka(Za: np.ndarray, Zb: np.ndarray) -> float:
    a, b = Za - Za.mean(0), Zb - Zb.mean(0)
    return float(np.linalg.norm(a.T @ b) ** 2 / (np.linalg.norm(a.T @ a) * np.linalg.norm(b.T @ b)))


def subspace_distance(A1: np.ndarray, A2: np.ndarray) -> float:
    """Mean squared sine of principal angles between span(A1) and span(A2) in so(d). 0 = same span."""
    def onb(A):
        U, s, _ = np.linalg.svd(A.reshape(A.shape[0], -1).T, full_matrices=False)
        return U[:, s > 1e-9 * s.max()]
    U1, U2 = onb(A1), onb(A2)
    k = max(U1.shape[1], U2.shape[1])
    return float(1.0 - np.linalg.norm(U1.T @ U2) ** 2 / k)


def random_span_distance(d: int, K: int, n: int = 2000, seed: int = 0) -> float:
    """Chance level of subspace_distance for two random K-dim subspaces of so(d)."""
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n):
        A1, A2 = rng.standard_normal((2, K, d, d))
        out.append(subspace_distance(A1 - A1.transpose(0, 2, 1), A2 - A2.transpose(0, 2, 1)))
    return float(np.mean(out))


@torch.no_grad()
def model_probe(model: BracketNet, x_seq: np.ndarray):
    """Latent codes of all probe frames and inferred actions of every adjacent edge."""
    x = torch.as_tensor(x_seq, dtype=torch.float32)
    z = model.encoder(x)
    A = model.generators()
    R = model.rho(model.infer(z[:, :-1], z[:, 1:]), A)
    return z.double().numpy(), R.double().numpy(), A.double().numpy()


def conjugate(R: np.ndarray, M: np.ndarray) -> np.ndarray:
    return np.einsum("ij,...jk,lk->...il", R, M, R)


def compare(za, Ra, Aa, zb, Rb, Ab) -> dict:
    """Align representation a onto b and measure latent, algebra and action agreement."""
    d = za.shape[-1]
    Rot, res = procrustes(za.reshape(-1, d), zb.reshape(-1, d))
    Aa_al = conjugate(Rot, Aa)
    Ra_al = conjugate(Rot, Ra)
    act_err = np.mean(np.sum((Ra_al - Rb) ** 2, (-1, -2)))
    act_scale = np.mean(np.sum((Rb - np.eye(d)) ** 2, (-1, -2)))
    return dict(
        cka=linear_cka(za.reshape(-1, d), zb.reshape(-1, d)),
        procrustes_residual=res,
        algebra_subspace_distance=subspace_distance(Aa_al, Ab),
        action_disagreement=float(act_err / act_scale),   # 0 = identical actions; 1 ~ identity-guess error
    )
