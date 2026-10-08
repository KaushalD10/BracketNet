"""BracketNet model: encoder E, decoder D, action inference q and K skew generators."""
from __future__ import annotations

import math

import torch
from torch import nn

GEN_NORM = math.sqrt(2.0)   # Frobenius norm of every generator (Appendix B)
COEF_BOUND = 0.65           # a = 0.65 tanh(q(z, z')) (Appendix B)


def mlp(n_in: int, n_out: int, width: int = 64) -> nn.Sequential:
    """Two-hidden-layer MLP, width 64, SiLU (Appendix B)."""
    return nn.Sequential(nn.Linear(n_in, width), nn.SiLU(),
                         nn.Linear(width, width), nn.SiLU(),
                         nn.Linear(width, n_out))


def normalize_generators(W: torch.Tensor) -> torch.Tensor:
    """Antisymmetrize (K, d, d) parameters and scale each to Frobenius norm sqrt(2)."""
    A = 0.5 * (W - W.transpose(-1, -2))
    return GEN_NORM * A / A.flatten(1).norm(dim=1).clamp_min(1e-12)[:, None, None]


def commutators(A: torch.Tensor) -> torch.Tensor:
    """All pairwise brackets [A_i, A_j] as (K, K, d, d)."""
    AB = torch.einsum("iab,jbc->ijac", A, A)
    return AB - AB.transpose(0, 1)


def closure_residual(A: torch.Tensor, eps: float = 1e-6, mode: str = "reg") -> torch.Tensor:
    """Eq. (7): (1/K^2) sum_ij ||(I - P_B) vec[A_i, A_j]||^2, P_B = B (B^T B + eps I)^-1 B^T.

    mode='reg' is the evaluated objective (invariant only under orthogonal coordinate changes).
    mode='whitened' replaces A by the sqrt(2)-scaled orthonormal basis U = sqrt(2) B G^{-1/2},
    G = B^T B, and projects exactly; it depends only on span(A) (GL(K)-invariant)."""
    K = A.shape[0]
    if mode == "whitened":
        B = A.flatten(1).T
        evals, evecs = torch.linalg.eigh(B.T @ B)
        Ginv_half = evecs @ torch.diag(evals.clamp_min(1e-12).rsqrt()) @ evecs.T
        U = (2.0 ** 0.5) * (B @ Ginv_half).T.reshape(A.shape)
        Ub = U.flatten(1).T                                   # columns have norm sqrt(2)
        C = commutators(U).reshape(K * K, -1).T
        return ((C - 0.5 * Ub @ (Ub.T @ C)) ** 2).sum() / K ** 2
    if mode != "reg":
        raise ValueError(mode)
    B = A.flatten(1).T                                   # (d^2, K)
    C = commutators(A).reshape(K * K, -1).T              # (d^2, K^2)
    G = B.T @ B + eps * torch.eye(K, dtype=A.dtype)
    proj = B @ torch.linalg.solve(G, B.T @ C)
    return ((C - proj) ** 2).sum() / K ** 2


def gram_penalty(A: torch.Tensor, target: float = 2.0) -> torch.Tensor:
    """Eq. (8): ||B^T B - 2 I||_F^2. target=1 reproduces the rejected pilot."""
    B = A.flatten(1).T
    K = A.shape[0]
    return ((B.T @ B - target * torch.eye(K, dtype=A.dtype)) ** 2).sum()


def covariance_penalty(z: torch.Tensor) -> torch.Tensor:
    """ASSUMPTION: anti-collapse regularizer ||Cov(z) - I||_F^2 on a batch of codes."""
    zc = z - z.mean(0, keepdim=True)
    cov = zc.T @ zc / (z.shape[0] - 1)
    return ((cov - torch.eye(z.shape[1], dtype=z.dtype)) ** 2).sum()


class BracketNet(nn.Module):
    def __init__(self, obs_dim: int, latent_dim: int, n_gen: int, width: int = 64):
        super().__init__()
        self.d, self.K = latent_dim, n_gen
        self.encoder = mlp(obs_dim, latent_dim, width)
        self.decoder = mlp(latent_dim, obs_dim, width)
        self.action = mlp(2 * latent_dim, n_gen, width)
        self.W = nn.Parameter(torch.randn(n_gen, latent_dim, latent_dim) / math.sqrt(latent_dim))

    def generators(self) -> torch.Tensor:
        return normalize_generators(self.W)

    def infer(self, z0: torch.Tensor, z1: torch.Tensor) -> torch.Tensor:
        return COEF_BOUND * torch.tanh(self.action(torch.cat([z0, z1], -1)))

    def rho(self, a: torch.Tensor, A: torch.Tensor | None = None) -> torch.Tensor:
        A = self.generators() if A is None else A
        return torch.linalg.matrix_exp(torch.einsum("...k,kij->...ij", a, A))
