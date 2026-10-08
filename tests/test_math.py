"""Numerical checks of the manuscript's mathematical claims (see docs/AUDIT.md)."""
import numpy as np
import pytest
import torch
from scipy.linalg import expm, logm

from bracketnet.groups import GROUPS, true_generators, elementary_skew
from bracketnet.metrics import (closure_residual_np, invariant_commutator_norm, jacobi_residual,
                                killing_eigenvalues, mean_commutator_norm, participation_ratio,
                                structure_constants)
from bracketnet.model import closure_residual, gram_penalty, normalize_generators

rng = np.random.default_rng(0)


def rand_skew(K, d):
    W = rng.standard_normal((K, d, d))
    return W - W.transpose(0, 2, 1)


def chiral_su2():
    """Left-isoclinic (quaternionic) su(2) inside so(4), normalized to ||.||_F = sqrt(2)."""
    e = lambda i, j: elementary_skew(4, i, j)
    I = e(1, 0) + e(3, 2)
    J = e(2, 0) + e(1, 3)
    K = e(3, 0) + e(2, 1)
    return np.stack([I, J, K]) / np.sqrt(2)


@pytest.mark.parametrize("g", list(GROUPS))
def test_true_algebras_close(g):
    T = true_generators(g)
    assert np.allclose([np.linalg.norm(t) for t in T], np.sqrt(2))
    assert closure_residual_np(T) < 1e-20


def test_true_commutator_norms():
    assert mean_commutator_norm(true_generators("T2")) == 0
    assert np.isclose(mean_commutator_norm(true_generators("SO3")), np.sqrt(2))
    assert np.allclose(killing_eigenvalues(true_generators("SO3")), -2)


def test_vacuous_ambient_so3():
    """Sec. 6.3 item 1: any 3 independent elements of so(3) close; in so(4) they generically do not."""
    assert max(closure_residual_np(rand_skew(3, 3)) for _ in range(50)) < 1e-18
    assert min(closure_residual_np(rand_skew(3, 4)) for _ in range(50)) > 1e-3


def test_closure_invariant_to_orthogonal_basis_change_only():
    """Eq. (7) is O(K)-invariant, but NOT invariant to a general invertible change of coordinates
    (contrary to the sentence after Eq. 7); only its zero set is GL(K)-invariant."""
    A = rand_skew(3, 4)
    Q, _ = np.linalg.qr(rng.standard_normal((3, 3)))
    M = rng.standard_normal((3, 3)) + 3 * np.eye(3)
    AQ = np.einsum("kl,kij->lij", Q, A)
    AM = np.einsum("kl,kij->lij", M, A)
    r = closure_residual_np(A)
    assert np.isclose(closure_residual_np(AQ), r, rtol=1e-10)
    assert not np.isclose(closure_residual_np(AM), r, rtol=1e-3)
    # zero set is GL-invariant
    T = true_generators("SO3")
    assert closure_residual_np(np.einsum("kl,kij->lij", M, T)) < 1e-18
    # scaling the basis by s scales the residual by s^4
    assert np.isclose(closure_residual_np(2 * A), 16 * r)


def test_projector_eps_breaks_exact_span_invariance():
    A = rand_skew(2, 4)
    B = A.reshape(2, -1).T
    M = np.array([[1.0, 0.0], [0.0, 1e-3]])
    BM = B @ M
    P = lambda B, eps: B @ np.linalg.solve(B.T @ B + eps * np.eye(2), B.T)
    assert np.allclose(P(B, 0), P(BM, 0))
    assert not np.allclose(P(B, 1e-6), P(BM, 1e-6), atol=1e-6)


def test_torch_numpy_closure_agree():
    A = rand_skew(3, 4)
    t = closure_residual(torch.tensor(A), eps=0.0).item()
    assert np.isclose(t, closure_residual_np(A), rtol=1e-8)


def test_gram_target_irrelevant_under_normalization():
    """Sec. 6.3 item 3: with generators normalized to ||A||_F = sqrt(2) BEFORE the Gram penalty,
    diag(B^T B) = 2 is constant, so targets I and 2I give identical gradients."""
    W = torch.randn(3, 4, 4, dtype=torch.float64, requires_grad=True)
    g = []
    for target in (1.0, 2.0):
        W.grad = None
        gram_penalty(normalize_generators(W), target).backward()
        g.append(W.grad.clone())
    assert torch.allclose(g[0], g[1], atol=1e-12)


def test_jacobi_exact_for_closed_algebras():
    for A in (true_generators("SO3"), chiral_su2()):
        assert jacobi_residual(structure_constants(A)) < 1e-10


def test_commutator_norm_does_not_identify_representation():
    """Two closed so(3)~su(2) subalgebras of so(4) with the same normalization give different
    commutator norms (sqrt2 vs 2): the diagnostic depends on the embedding, not only on the algebra."""
    S, C = true_generators("SO3"), chiral_su2()
    assert closure_residual_np(C) < 1e-20
    assert np.isclose(invariant_commutator_norm(S), np.sqrt(2))
    assert np.isclose(invariant_commutator_norm(C), 2.0)
    assert np.allclose(killing_eigenvalues(C), -4)
    assert np.isclose(participation_ratio(S), 2.0)
    assert np.isclose(participation_ratio(C), 4.0)


def test_invariant_commutator_norm_is_gl_invariant():
    A = rand_skew(3, 4)
    M = rng.standard_normal((3, 3)) + 3 * np.eye(3)
    assert np.isclose(invariant_commutator_norm(A), invariant_commutator_norm(np.einsum("kl,kij->lij", M, A)))


def _bch_escape(A, r, n=200):
    """max over random X, Y in span(A) with ||X||,||Y|| = r of dist(log(e^X e^Y), span(A))."""
    K = A.shape[0]
    U, _, _ = np.linalg.svd(A.reshape(K, -1).T, full_matrices=False)
    out = 0
    for _ in range(n):
        X, Y = (np.einsum("k,kij->ij", rng.standard_normal(K), A) for _ in range(2))
        X, Y = r * X / np.linalg.norm(X), r * Y / np.linalg.norm(Y)
        L = np.real(logm(expm(X) @ expm(Y))).ravel()
        out = max(out, np.linalg.norm(L - U @ (U.T @ L)))
    return out


def test_prop2_bch_escape_vanishes_with_closure():
    """Prop. 2: exact closure gives zero escape at every radius, so the delta-independent
    C2 r^3 term in Eq. (10) is loose; escape scales like delta * r^2."""
    assert _bch_escape(true_generators("SO3"), 0.3) < 1e-10
    A = true_generators("SO3") + 0.05 * rand_skew(3, 4)
    e1, e2 = _bch_escape(A, 0.05), _bch_escape(A, 0.1)
    assert 3.0 < e2 / e1 < 5.0    # ~ r^2 scaling


def test_prop3_chained_stability():
    d, T = 5, 20
    z = zh = rng.standard_normal(d)
    zh = z + 0.1 * rng.standard_normal(d)
    bound = np.linalg.norm(zh - z)
    for _ in range(T):
        R = expm(rand_skew(1, d)[0])
        e = 0.05 * rng.standard_normal(d)
        z, zh = R @ z + e, R @ zh
        bound += np.linalg.norm(e)
        assert np.linalg.norm(zh - z) <= bound + 1e-12
