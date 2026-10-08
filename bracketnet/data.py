"""Synthetic benchmark: nonlinear observations of SO(2), T^2 and SO(3) actions.

Implements Sec. 6.1 of the manuscript. Choices the manuscript leaves open are
marked ASSUMPTION and collected in docs/ASSUMPTIONS.md.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.linalg import expm

from .groups import GROUPS, true_generators

COEF_STD = 0.24          # std of Gaussian local coefficients (Sec. 6.1)
NONLIN_SCALE = 0.18      # x = Qz + 0.18 tanh(Bz) (Eq. 12)
GROUP_MAP_SEED = {"SO2": 101, "T2": 102, "SO3": 103, "SO3_d3": 104}  # ASSUMPTION: fixed per group


@dataclass
class ObservationMap:
    """x = Q z + 0.18 tanh(B z), Q orthogonal (d x d), B fixed.

    ASSUMPTION: observation dimension p = d (the paper calls Q 'orthogonal',
    i.e. square). B = G / sqrt(d) with G standard normal, rescaled if needed so
    that 0.18 * ||B||_2 <= 0.5, which makes the map injective (the Jacobian
    Q + 0.18 diag(sech^2) B is then never singular).
    """

    Q: np.ndarray
    B: np.ndarray

    @classmethod
    def sample(cls, d: int, seed: int) -> "ObservationMap":
        rng = np.random.default_rng(seed)
        q, r = np.linalg.qr(rng.standard_normal((d, d)))
        q = q * np.sign(np.diag(r))
        b = rng.standard_normal((d, d)) / np.sqrt(d)
        s = np.linalg.norm(b, 2)
        if NONLIN_SCALE * s > 0.5:
            b = b * (0.5 / (NONLIN_SCALE * s))
        return cls(Q=q, B=b)

    def __call__(self, z: np.ndarray) -> np.ndarray:
        return z @ self.Q.T + NONLIN_SCALE * np.tanh(z @ self.B.T)


def group_map(group: str, split_dependent: bool = False, split: str = "train") -> ObservationMap:
    """The fixed observation map for a group.

    split_dependent=True reproduces the rejected pilot (Sec. 6.3, item 2) in
    which the test split used a separately sampled map.
    """
    seed = GROUP_MAP_SEED[group]
    if split_dependent and split == "test":
        seed += 10_000
    return ObservationMap.sample(GROUPS[group]["d"], seed)


def sample_actions(rng: np.random.Generator, group: str, n: int) -> np.ndarray:
    """Near-identity group elements g = exp(sum_k a_k T_k), a ~ N(0, 0.24^2 I)."""
    T = true_generators(group)
    a = rng.normal(0.0, COEF_STD, size=(n, T.shape[0]))
    gen = np.einsum("nk,kij->nij", a, T)
    return np.stack([expm(m) for m in gen]), a


def sample_states(rng: np.random.Generator, group: str, n: int) -> np.ndarray:
    """ASSUMPTION: initial latent states u ~ N(0, I_d)."""
    return rng.standard_normal((n, GROUPS[group]["d"]))


def make_sequences(rng: np.random.Generator, group: str, n: int, n_edges: int):
    """Latent trajectories z_0..z_T with z_{t+1} = g_t z_t and fresh g_t per edge.

    Returns z (n, T+1, d), coefficients a (n, T, K) and group elements g (n, T, d, d).
    """
    d = GROUPS[group]["d"]
    z = np.empty((n, n_edges + 1, d))
    z[:, 0] = sample_states(rng, group, n)
    gs, as_ = [], []
    for t in range(n_edges):
        g, a = sample_actions(rng, group, n)
        z[:, t + 1] = np.einsum("nij,nj->ni", g, z[:, t])
        gs.append(g)
        as_.append(a)
    return z, np.stack(as_, 1), np.stack(gs, 1)


@dataclass
class Dataset:
    group: str
    x_train: np.ndarray      # (1400, 3, p) two-edge triples
    z_train: np.ndarray
    x_test: np.ndarray       # (500, 11, p) ten-edge sequences
    z_test: np.ndarray
    a_test: np.ndarray       # true coefficients of each test edge
    g_test: np.ndarray       # true group element of each test edge


def make_dataset(group: str, seed: int, n_train: int = 1400, n_test: int = 500,
                 n_test_edges: int = 10, split_dependent_map: bool = False) -> Dataset:
    """ASSUMPTION: run seed drives train and test sampling through independent streams."""
    rng_train = np.random.default_rng([seed, 0])
    rng_test = np.random.default_rng([seed, 1])
    z_tr, _, _ = make_sequences(rng_train, group, n_train, 2)
    z_te, a_te, g_te = make_sequences(rng_test, group, n_test, n_test_edges)
    f_tr = group_map(group, split_dependent_map, "train")
    f_te = group_map(group, split_dependent_map, "test")
    return Dataset(group, f_tr(z_tr), z_tr, f_te(z_te), z_te, a_te, g_te)
