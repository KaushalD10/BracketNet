"""Ground-truth Lie algebras embedded in a larger ambient so(d).

Every true generator is normalized to Frobenius norm sqrt(2), matching the
normalization BracketNet imposes on its learned generators (Appendix B).
"""
from __future__ import annotations

import numpy as np


def elementary_skew(d: int, i: int, j: int) -> np.ndarray:
    """E_ij - E_ji: infinitesimal rotation in the (i, j) plane. ||.||_F = sqrt(2)."""
    m = np.zeros((d, d))
    m[i, j] = -1.0
    m[j, i] = 1.0
    return m


# name -> (ambient dimension d, generator count K, abelian?)
GROUPS = {
    # SO(2) acting on a plane plus one invariant coordinate: so(2) inside so(3).
    "SO2": dict(d=3, K=1, abelian=True),
    # Two-torus: two commuting rotation planes plus one invariant coordinate: inside so(5).
    "T2": dict(d=5, K=2, abelian=True),
    # SO(3) acting on R^3 plus one invariant coordinate: standard so(3) inside so(4).
    "SO3": dict(d=4, K=3, abelian=False),
    # Rendered-image benchmark: the SO(3) latent structure observed through 20x20 renderings (see data.Renderer).
    "SO3img": dict(d=4, K=3, abelian=False),
    # Rejected pilot (Sec. 6.3, item 1): SO(3) with no invariant coordinate, ambient so(3).
    # Any 3 independent elements of so(3) span so(3), so closure is automatic.
    "SO3_d3": dict(d=3, K=3, abelian=False),
}


def true_generators(group: str) -> np.ndarray:
    """Return an array (K, d, d) of true generators with ||T_k||_F = sqrt(2)."""
    d = GROUPS[group]["d"]
    if group == "SO2":
        gens = [elementary_skew(d, 0, 1)]
    elif group == "T2":
        gens = [elementary_skew(d, 0, 1), elementary_skew(d, 2, 3)]
    elif group in ("SO3", "SO3_d3", "SO3img"):
        # L_x, L_y, L_z on coordinates (0, 1, 2) with [L_x, L_y] = L_z.
        gens = [elementary_skew(d, 2, 1), elementary_skew(d, 0, 2), elementary_skew(d, 1, 0)]
    else:
        raise KeyError(group)
    return np.stack(gens)
