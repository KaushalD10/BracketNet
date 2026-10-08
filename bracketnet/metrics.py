"""Evaluation metrics (Sec. 6.1) and additional basis-invariant algebra diagnostics."""
from __future__ import annotations

import itertools

import numpy as np
import torch

from .data import Dataset
from .model import BracketNet


# --------------------------------------------------------------------------- transport
@torch.no_grad()
def transport_curve(model: BracketNet, ds: Dataset) -> np.ndarray:
    """Observation-space MSE of chained transport after 1..T edges.

    Each edge coefficient is inferred from its observed endpoints, a_t = q(E x_t, E x_{t+1});
    the encoded start is transported by the product of inferred actions and decoded.
    This measures consistency of composing inferred actions, not forecasting (Sec. 6.1).
    """
    x = torch.as_tensor(ds.x_test, dtype=torch.float32)
    z = model.encoder(x)
    A = model.generators()
    zh = z[:, 0]
    errs = []
    for t in range(x.shape[1] - 1):
        R = model.rho(model.infer(z[:, t], z[:, t + 1]), A)
        zh = torch.einsum("bij,bj->bi", R, zh)
        errs.append(float(((model.decoder(zh) - x[:, t + 1]) ** 2).mean()))
    return np.array(errs)


@torch.no_grad()
def composition_mse(model: BracketNet, ds: Dataset) -> float:
    """Elementwise mean of (rho(a02) - rho(a12) rho(a01))^2 on the first two test edges.
    ASSUMPTION: the paper's Table 2 'Composition MSE' normalization is not stated."""
    x = torch.as_tensor(ds.x_test[:, :3], dtype=torch.float32)
    z = model.encoder(x)
    A = model.generators()
    R01 = model.rho(model.infer(z[:, 0], z[:, 1]), A)
    R12 = model.rho(model.infer(z[:, 1], z[:, 2]), A)
    R02 = model.rho(model.infer(z[:, 0], z[:, 2]), A)
    return float(((R02 - R12 @ R01) ** 2).mean())


# --------------------------------------------------------------------------- algebra (numpy, float64)
def _comm(X, Y):
    return X @ Y - Y @ X


def closure_residual_np(A: np.ndarray, eps: float = 0.0) -> float:
    K = A.shape[0]
    if K < 2:
        return 0.0
    B = A.reshape(K, -1).T
    C = np.stack([_comm(A[i], A[j]).ravel() for i in range(K) for j in range(K)], 1)
    G = B.T @ B + eps * np.eye(K)
    R = C - B @ np.linalg.solve(G, B.T @ C)
    return float((R ** 2).sum() / K ** 2)


def mean_commutator_norm(A: np.ndarray) -> float:
    """Paper's diagnostic: mean ||[A_i, A_j]||_F over i < j (basis-dependent)."""
    K = A.shape[0]
    if K < 2:
        return 0.0
    return float(np.mean([np.linalg.norm(_comm(A[i], A[j])) for i, j in itertools.combinations(range(K), 2)]))


def orthonormal_span(A: np.ndarray) -> np.ndarray:
    """An orthonormal basis of span(A) (Frobenius inner product), each scaled to norm sqrt(2).
    Every quantity computed from it is invariant to GL(K) changes of generator coordinates
    (up to an O(K) rotation, under which the quantities below are invariant)."""
    K, d, _ = A.shape
    U, s, _ = np.linalg.svd(A.reshape(K, -1).T, full_matrices=False)
    U = U[:, s > 1e-9 * s.max()]
    return np.sqrt(2.0) * U.T.reshape(-1, d, d)


def invariant_commutator_norm(A: np.ndarray) -> float:
    """kappa = sqrt(mean_{i<j} ||[U_i, U_j]||_F^2) for an orthonormal sqrt(2)-scaled basis U of the span.
    Depends on the span only. sqrt(2) for standard so(3) in so(4), 2 for a chiral su(2) factor, 0 abelian."""
    U = orthonormal_span(A)
    K = U.shape[0]
    if K < 2:
        return 0.0
    return float(np.sqrt(np.mean([np.linalg.norm(_comm(U[i], U[j])) ** 2
                                  for i, j in itertools.combinations(range(K), 2)])))


def structure_constants(A: np.ndarray) -> np.ndarray:
    """c[i, j, k]: least-squares coefficients of proj_span [A_i, A_j] on A_k (eps = 0)."""
    K = A.shape[0]
    B = A.reshape(K, -1).T
    C = np.stack([_comm(A[i], A[j]).ravel() for i in range(K) for j in range(K)], 1)
    coef = np.linalg.lstsq(B, C, rcond=None)[0]           # (K, K*K)
    return coef.T.reshape(K, K, K)


def jacobi_residual(c: np.ndarray) -> float:
    """||sum_cyc c^k_ij c^m_kl|| over all (i, j, l, m). Zero iff projected bracket satisfies Jacobi."""
    J = (np.einsum("ijk,klm->ijlm", c, c) + np.einsum("jlk,kim->ijlm", c, c)
         + np.einsum("lik,kjm->ijlm", c, c))
    return float(np.linalg.norm(J))


def killing_eigenvalues(A: np.ndarray) -> np.ndarray:
    """Eigenvalues of the Killing form tr(ad_a ad_b) of the projected bracket in an orthonormal basis.
    Basis-invariant up to O(K). Standard so(3) (norm sqrt2 basis): (-2,-2,-2); chiral su(2): (-4,-4,-4)."""
    U = orthonormal_span(A)
    if U.shape[0] < 2:
        return np.zeros(U.shape[0])
    c = structure_constants(U)
    ad = np.transpose(c, (0, 2, 1))           # ad[a][k, j] = c[a, j, k]
    Kf = np.einsum("akj,bjk->ab", ad, ad)
    return np.sort(np.linalg.eigvalsh(0.5 * (Kf + Kf.T)))


def participation_ratio(A: np.ndarray, n: int = 2000, seed: int = 0) -> float:
    """Mean of tr(X^T X)^2 / tr((X^T X)^2) for random unit X in the span. In so(4): 2 for a
    single-plane rotation (standard so(3) rep), 4 for an isoclinic rotation (chiral su(2))."""
    U = orthonormal_span(A)
    rng = np.random.default_rng(seed)
    w = rng.standard_normal((n, U.shape[0]))
    X = np.einsum("nk,kij->nij", w, U)
    M = np.einsum("nji,njk->nik", X, X)
    tr = np.trace(M, axis1=1, axis2=2)
    tr2 = np.einsum("nij,nji->n", M, M)
    return float(np.mean(tr ** 2 / tr2))


def algebra_report(A: np.ndarray, eps: float = 1e-6) -> dict:
    c = structure_constants(A) if A.shape[0] > 1 else np.zeros((1, 1, 1))
    return dict(
        closure_residual=closure_residual_np(A, eps),
        closure_residual_exact=closure_residual_np(A, 0.0),
        commutator_norm=mean_commutator_norm(A),
        invariant_commutator_norm=invariant_commutator_norm(A),
        jacobi_residual=jacobi_residual(c),
        killing_eigenvalues=killing_eigenvalues(A).tolist(),
        participation_ratio=participation_ratio(A),
        gram=(A.reshape(A.shape[0], -1) @ A.reshape(A.shape[0], -1).T).tolist(),
        structure_constants=c.tolist(),
    )


def evaluate(model: BracketNet, ds: Dataset) -> dict:
    model.eval()
    curve = transport_curve(model, ds)
    A = model.generators().detach().double().numpy()
    out = dict(transport_curve=curve.tolist(), mse_1step=float(curve[0]), mse_10step=float(curve[-1]),
               composition_mse=composition_mse(model, ds))
    out.update(algebra_report(A))
    out["generators"] = A.tolist()
    return out
