"""Verification of the final manuscript's mathematical statements (docs/MATHEMATICAL_VERIFICATION.md).

Each test checks a precise, falsifiable form of a statement:
  T1 transformation law of L_close under B -> BM (eps = 0) and its two-sided bounds;
  T2 transformation law of the regularized projector P_eps;
  T3 generator normalization and Gram-penalty facts;
  T4 Lemma 1 (closure loss controls the uniform escape constant delta);
  T5 Proposition 2 (rigorous BCH escape bound) on random near-closed algebras;
  T6 the classification of closed 3-dim subalgebras of so(4) used for failure analysis.
"""
import itertools

import numpy as np
import pytest
import torch
from scipy.linalg import expm, logm

from bracketnet.groups import elementary_skew, true_generators
from bracketnet.metrics import closure_residual_np, orthonormal_span, participation_ratio
from bracketnet.model import closure_residual, gram_penalty, normalize_generators
from bracketnet.structure import delta_bound

rng = np.random.default_rng(1)


def rand_skew(K, d):
    W = rng.standard_normal((K, d, d))
    return W - W.transpose(0, 2, 1)


def residual_matrix(A):
    """R = (I - P_B) C with C = [vec[A_i, A_j]]_(i,j) (columns ordered i-major), eps = 0."""
    K = A.shape[0]
    B = A.reshape(K, -1).T
    C = np.stack([(A[i] @ A[j] - A[j] @ A[i]).ravel() for i in range(K) for j in range(K)], 1)
    return C - B @ np.linalg.lstsq(B, C, rcond=None)[0]


def change_basis(A, M):
    return np.einsum("kl,kij->lij", M, A)          # A'_l = sum_k M_kl A_k  (B' = B M)


# ---------------------------------------------------------------- T1
@pytest.mark.parametrize("trial", range(5))
def test_T1_gl_transformation_law(trial):
    K, d = 3, 4
    A = rand_skew(K, d)
    M = rng.standard_normal((K, K))
    AM = change_basis(A, M)
    R = residual_matrix(A)
    lhs = closure_residual_np(AM)
    rhs = np.linalg.norm(R @ np.kron(M, M)) ** 2 / K ** 2
    assert np.isclose(lhs, rhs, rtol=1e-8)
    s = np.linalg.svd(M, compute_uv=False)
    L = closure_residual_np(A)
    assert s.min() ** 4 * L * (1 - 1e-9) <= lhs <= s.max() ** 4 * L * (1 + 1e-9)


def test_T1_orthogonal_invariance_and_zero_set():
    A = rand_skew(3, 4)
    Q, _ = np.linalg.qr(rng.standard_normal((3, 3)))
    assert np.isclose(closure_residual_np(change_basis(A, Q)), closure_residual_np(A), rtol=1e-10)
    T = true_generators("SO3")
    M = rng.standard_normal((3, 3))
    assert closure_residual_np(change_basis(T, M)) < 1e-16


def test_T1_whitened_closure_is_span_only():
    A = rand_skew(3, 4)
    M = rng.standard_normal((3, 3)) + 2 * np.eye(3)
    a, b = closure_residual_np(orthonormal_span(A)), closure_residual_np(orthonormal_span(change_basis(A, M)))
    assert np.isclose(a, b, rtol=1e-8)
    t = torch.tensor(A)
    assert np.isclose(closure_residual(t, 0.0, "whitened").item(), a, rtol=1e-8)


# ---------------------------------------------------------------- T2
def test_T2_regularized_projector_law():
    K, d, eps = 2, 4, 0.3
    B = rand_skew(K, d).reshape(K, -1).T
    M = rng.standard_normal((K, K)) + 2 * np.eye(K)
    P = lambda B, E: B @ np.linalg.solve(B.T @ B + E, B.T)
    Minv = np.linalg.inv(M)
    assert np.allclose(P(B @ M, eps * np.eye(K)), P(B, eps * Minv.T @ Minv), atol=1e-10)
    Q, _ = np.linalg.qr(rng.standard_normal((K, K)))
    assert np.allclose(P(B @ Q, eps * np.eye(K)), P(B, eps * np.eye(K)), atol=1e-10)
    assert not np.allclose(P(B @ M, eps * np.eye(K)), P(B, eps * np.eye(K)), atol=1e-4)


def test_T2_eps_effect_is_negligible_for_normalized_bases():
    """For sqrt(2)-normalized, well-conditioned bases eps = 1e-6 changes L_close by O(eps)."""
    A = normalize_generators(torch.tensor(rand_skew(3, 4))).numpy()
    a, b = closure_residual_np(A, 1e-6), closure_residual_np(A, 0.0)
    assert abs(a - b) <= 1e-5 * max(b, 1e-12) + 1e-9


# ---------------------------------------------------------------- T3
def test_T3_normalization_and_gram():
    W = torch.randn(3, 5, 5, dtype=torch.float64)
    A = normalize_generators(W)
    assert torch.allclose(A, -A.transpose(1, 2))
    assert torch.allclose(A.flatten(1).norm(dim=1), torch.full((3,), 2 ** 0.5, dtype=torch.float64))
    assert torch.allclose(normalize_generators(A), A)
    G = A.flatten(1) @ A.flatten(1).T
    assert torch.allclose(torch.diag(G), torch.full((3,), 2.0, dtype=torch.float64))
    # Gram penalty on normalized generators = off-diagonal energy + a constant depending on the target
    off = (G - torch.diag(torch.diag(G))).pow(2).sum()
    for c in (1.0, 2.0):
        assert torch.isclose(gram_penalty(A, c), off + 3 * (2 - c) ** 2)


# ---------------------------------------------------------------- T4
def true_delta(A, restarts=60, iters=60):
    """max over unit X, Y in span(A) of ||(I-P)[X, Y]||_F (alternating maximization, many restarts)."""
    U = orthonormal_span(A) / np.sqrt(2)               # Frobenius-orthonormal basis
    K = U.shape[0]
    R = residual_matrix(U).T.reshape(K, K, -1)          # R[i, j] = (I-P)[U_i, U_j]
    best = 0.0
    for _ in range(restarts):
        v = rng.standard_normal(K)
        v /= np.linalg.norm(v)
        for _ in range(iters):
            Mv = np.einsum("ijn,j->ni", R, v)
            uu, s, vt = np.linalg.svd(Mv, full_matrices=False)
            u = vt[0]
            Mu = np.einsum("ijn,i->nj", R, u)
            uu, s, vt = np.linalg.svd(Mu, full_matrices=False)
            v = vt[0]
        best = max(best, s[0])
    return best


@pytest.mark.parametrize("pert", [0.02, 0.1, 0.5])
def test_T4_lemma1_delta_bound(pert):
    for _ in range(5):
        A = true_generators("SO3") + pert * rand_skew(3, 4)
        A = A * rng.uniform(0.5, 2.0, size=(3, 1, 1))   # non-orthonormal, non-normalized basis
        assert true_delta(A) <= delta_bound(A) * (1 + 1e-9)


# ---------------------------------------------------------------- T5
def phi_total(r):
    """Rigorous bound factor: dist <= (delta / 4) * (-log(2 - e^{4r}) - 4r) for r < log(2)/4."""
    return 0.25 * (-np.log(2 - np.exp(4 * r)) - 4 * r)


def bch_escape(A, X, Y):
    U = orthonormal_span(A) / np.sqrt(2)
    Ub = U.reshape(U.shape[0], -1).T
    L = np.real(logm(expm(X) @ expm(Y))).ravel()
    return np.linalg.norm(L - Ub @ (Ub.T @ L))


@pytest.mark.parametrize("pert,r", [(0.02, 0.05), (0.02, 0.15), (0.2, 0.1), (0.5, 0.17)])
def test_T5_prop2_rigorous_bound(pert, r):
    A = true_generators("SO3") + pert * rand_skew(3, 4)
    delta = true_delta(A)
    U = orthonormal_span(A)
    for _ in range(100):
        X, Y = (np.einsum("k,kij->ij", rng.standard_normal(3), U) for _ in range(2))
        X = rng.uniform(0, r) * X / np.linalg.norm(X)
        Y = rng.uniform(0, r) * Y / np.linalg.norm(Y)
        rr = max(np.linalg.norm(X), np.linalg.norm(Y))
        e = bch_escape(A, X, Y)
        assert e <= delta * phi_total(rr) + 1e-10
        # sharpened form: 1/2 delta r^2 + delta C(r0) r^3, C(r0) = (phi_total(r0) - 4 r0^2) / r0^3
        assert e <= 0.5 * delta * rr ** 2 + delta * (phi_total(r) - 4 * r ** 2) / r ** 3 * rr ** 3 + 1e-10


def test_T5_exact_closure_zero_escape():
    A = true_generators("SO3")
    U = orthonormal_span(A)
    X, Y = 0.15 * U[0] / np.sqrt(2), 0.15 * (U[1] + U[2]) / 2
    assert bch_escape(A, X, Y) < 1e-12


def test_T5_series_coefficients_nonnegative():
    """phi_total(r) - 4 r^2 >= 0 and (phi_total(r) - 4 r^2) / r^3 is increasing (used for C(r0))."""
    r = np.linspace(1e-3, 0.17, 200)
    h = (phi_total(r) - 4 * r ** 2) / r ** 3
    assert np.all(phi_total(r) - 4 * r ** 2 >= -1e-15) and np.all(np.diff(h) > 0)


# ---------------------------------------------------------------- T6
def chiral(sign):
    e = lambda i, j: elementary_skew(4, i, j)
    if sign > 0:
        return np.stack([e(1, 0) + e(3, 2), e(2, 0) + e(1, 3), e(3, 0) + e(2, 1)]) / np.sqrt(2)
    return np.stack([e(1, 0) - e(3, 2), e(2, 0) - e(1, 3), e(3, 0) - e(2, 1)]) / np.sqrt(2)


def test_T6_three_closed_su2_classes_in_so4():
    S, Lh, Rh = true_generators("SO3"), chiral(+1), chiral(-1)
    for A in (S, Lh, Rh):
        assert closure_residual_np(A) < 1e-20
    # left and right chiral algebras commute with each other and are exchanged by a reflection (det -1)
    for a, b in itertools.product(Lh, Rh):
        assert np.allclose(a @ b, b @ a)
    P = np.diag([1.0, 1.0, 1.0, -1.0])
    from bracketnet.alignment import subspace_distance, conjugate
    assert subspace_distance(conjugate(P, Lh), Rh) < 1e-12
    # standard vs chiral are not conjugate: participation ratio is a conjugation invariant
    assert np.isclose(participation_ratio(S), 2.0) and np.isclose(participation_ratio(Lh), 4.0)
    Q, _ = np.linalg.qr(rng.standard_normal((4, 4)))
    assert np.isclose(participation_ratio(conjugate(Q, Lh)), 4.0)


def test_T6_diagonal_vs_chiral_distance_is_one_half():
    """Diagonal so(3) and a chiral su(2) in so(4) meet at principal angles of 45 degrees (subspace distance 1/2);
    the two chiral factors are orthogonal (distance 1)."""
    from bracketnet.alignment import subspace_distance
    S, Lh, Rh = true_generators("SO3"), chiral(+1), chiral(-1)
    assert np.isclose(subspace_distance(S, Lh), 0.5) and np.isclose(subspace_distance(S, Rh), 0.5)
    assert np.isclose(subspace_distance(Lh, Rh), 1.0)


def test_T6_no_closed_4dim_span_contains_diagonal_so3():
    """The centralizer of the diagonal so(3) in so(4) is trivial; hence a 4-dim subalgebra (su(2)+u(1) type) can
    never contain the true so(3), and spans of the true so(3) plus any extra generator are never closed."""
    T = true_generators("SO3")
    basis = np.stack([elementary_skew(4, i, j) for i in range(4) for j in range(i + 1, 4)])   # so(4), dim 6
    M = np.stack([np.stack([(t @ b - b @ t).ravel() for b in basis], 1) for t in T]).reshape(-1, 6)
    assert np.linalg.matrix_rank(M, tol=1e-10) == 6          # [T_k, X] = 0 for all k  =>  X = 0
    for _ in range(20):
        W = rand_skew(1, 4)
        assert closure_residual_np(np.concatenate([T, W])) > 1e-6
    # su(2)_L + u(1)_R is a closed 4-dim subalgebra
    assert closure_residual_np(np.concatenate([chiral(+1), chiral(-1)[:1]])) < 1e-20


# ---------------------------------------------------------------- T7: Proposition 3 of the paper (endpoint ambiguity)
def test_T7_chiral_exact_transport_and_composition_on_data():
    """With the true state as latent code, su(2)_L and su(2)_R generators with endpoint-only inference transport
    and compose exactly (left multiplication by unit quaternions acts simply transitively on each sphere)."""
    from bracketnet.data import make_dataset
    from bracketnet.theory_checks import chiral_basis, chiral_infer, evaluate_solution
    ds = make_dataset("SO3", 7, n_train=200, n_test=5)
    z0, z1, z2 = ds.z_train[:, 0], ds.z_train[:, 1], ds.z_train[:, 2]
    for s in (+1, -1):
        r = evaluate_solution(z0, z1, z2, chiral_basis(s), lambda u, v: chiral_infer(u, v, s))
        assert r["transport"] < 1e-20 and r["composition"] < 1e-20


def test_T7_diagonal_endpoint_inference_cannot_compose():
    """The minimal-rotation rule for the true diagonal so(3) transports exactly but does not compose: the defect of a
    small triangle is a rotation about the start point (holonomy), so the composition residual is strictly positive."""
    from bracketnet.data import make_dataset
    from bracketnet.groups import true_generators
    from bracketnet.theory_checks import diagonal_infer_minimal, evaluate_solution, rho
    ds = make_dataset("SO3", 7, n_train=200, n_test=5)
    z0, z1, z2 = ds.z_train[:, 0], ds.z_train[:, 1], ds.z_train[:, 2]
    r = evaluate_solution(z0, z1, z2, true_generators("SO3"), diagonal_infer_minimal)
    assert r["transport"] < 1e-20 and r["composition"] > 1e-4
    T = true_generators("SO3")
    D = rho(diagonal_infer_minimal(z0, z2), T)
    P = rho(diagonal_infer_minimal(z1, z2), T) @ rho(diagonal_infer_minimal(z0, z1), T)
    defect = np.transpose(D, (0, 2, 1)) @ P
    # D and P both map z0 to z2, so the defect D^T P fixes z0: it is a rotation about the start point
    assert np.max(np.abs(np.einsum("nij,nj->ni", defect, z0) - z0)) < 1e-10
    assert np.mean(np.sum((defect - np.eye(4)) ** 2, (1, 2))) > 1e-4


def test_T7_stabilizer_component_is_invisible():
    """g and g * exp(t * (rotation about z)) produce the same endpoints (z, g z): the stabilizer component of an
    action cannot be inferred from endpoints."""
    from bracketnet.groups import true_generators
    T = true_generators("SO3")
    z = np.array([0.3, -1.1, 0.7, 0.4])
    axis = z[:3] / np.linalg.norm(z[:3])
    stab = expm(-0.9 * np.einsum("k,kij->ij", axis, T))       # sign convention of groups.py: rotation about +axis
    assert np.allclose(stab @ z, z)
    g = expm(np.einsum("k,kij->ij", np.array([0.2, -0.1, 0.3]), T))
    assert np.allclose((g @ stab) @ z, g @ z) and not np.allclose(g @ stab, g)


# ---------------------------------------------------------------- T8: independent classification checks
def test_T8_pfaffian_handedness_and_conjugation_groups():
    from bracketnet.so4 import chirality, pfaffian
    from bracketnet.theory_checks import chiral_basis
    from bracketnet.alignment import conjugate
    L, R, S = chiral_basis(+1), chiral_basis(-1), true_generators("SO3")
    assert np.allclose(pfaffian(S), 0) and np.allclose(pfaffian(L), 0.5) and np.allclose(pfaffian(R), -0.5)
    for _ in range(5):
        Q, _ = np.linalg.qr(rng.standard_normal((4, 4)))
        if np.linalg.det(Q) < 0:
            Q[:, 0] *= -1
        Pm = Q.copy()
        Pm[:, 0] *= -1
        assert np.isclose(chirality(conjugate(Q, L)), 1) and np.isclose(chirality(conjugate(Pm, L)), -1)
        assert np.isclose(chirality(conjugate(Q, S)), 0)


def test_T8_closure_flow_reaches_only_three_classes():
    """Optimization-based check that does not use the classification: minimizing the span-only closure from random
    3-dim subspaces of so(4) converges only to spans with chirality exactly -1, 0 or +1."""
    from bracketnet.so4 import closure_flow
    res = closure_flow(n_starts=12, steps=3000, seed=1)
    for r in res:
        assert r["closure"] < 1e-9
        assert min(abs(r["chirality"] - c) for c in (-1.0, 0.0, 1.0)) < 1e-4
