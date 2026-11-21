"""(G25): the loss expression (G5) for periodic sources with a random phase.

`docs/prompts/NEXT_PHASE_PROMPT.md` §3 specifies it. Mohamed's reference implementation is
`analysis/periodic_model.py`.

What it changes. The number of co-waiting frames K of (G4) is scaled by the ratio of the mean
backlogs of two queues: the N·D/D/1 queue (n periodic streams with random phases) over the M/D/1
queue (Poisson). The ratio comes from the Brownian-bridge tail P(Q > x) ≈ exp(−2x(x/n + 1 − ρ)):

    c = (1 − ρ)·sqrt(n/2),   R(n, ρ) = 2(1 − ρ)·sqrt(π n / 8)·exp(c²)·erfc(c),
    K_per = R(N − 1, a + γ)·K.

Everything else in (G5) is unchanged.

The stated limit, before any test: R holds for about 8 or more other stations. Against a queue
simulation it is wrong at 1–4 (R 0.30–0.75 against simulated 0.07–0.62).

The limit found since, at 802.11b: checked up to occupancy 0.78 (U-G25, −1.9 … +0.3 %). At
occupancy 0.84–0.87 and loss 6.4–7.9 % it was 3.6–5.5 % optimistic (F140). Beyond 0.78 at
802.11b it is stated as a limit (Mohamed, 2026-11-21), its error quantified once (`UG25H`).
"""
from __future__ import annotations

import math

from authbc.models import unified_capacity as uc

_C_ASYMPTOTIC = 25.0      # above this, exp(c²)·erfc(c) by its series: exp(c²) would overflow


def r_bb(n: float, rho: float) -> float:
    """R(n, ρ): mean backlog of n periodic random-phase streams over Poisson's, at load ρ.

    1.0 at or above ρ = 1, where the bridge argument no longer applies.
    """
    if n <= 0:
        raise ValueError("n, the number of other stations, must be positive")
    if rho >= 1:
        return 1.0
    c = (1 - rho) * math.sqrt(n / 2)
    if c > _C_ASYMPTOTIC:
        ex = (1 - 1 / (2 * c * c) + 3 / (4 * c ** 4)) / (c * math.sqrt(math.pi))
    else:
        ex = math.exp(c * c) * math.erfc(c)
    return 2 * (1 - rho) * math.sqrt(math.pi * n / 8) * ex


def loss_periodic(n_nodes: float, f: float, tf_s: float, acc: uc.Access = uc.A80211A,
                  p_fixed: float | None = None) -> float:
    """The loss of one frame at N stations, each sending f frames/s periodically, by (G25)."""
    if n_nodes <= 1:
        raise ValueError("N must exceed 1")
    n_other = n_nodes - 1
    return uc.loss(n_other * f, tf_s, acc, p_fixed, k_ratio=lambda rho: r_bb(n_other, rho))


def n_root_periodic(f: float, tf_s: float, eps: float, acc: uc.Access = uc.A80211A) -> float:
    """N_max where (G25)'s loss, with p = ε inside a, reaches ε. Bisection on a real N ≥ 2.

    R depends on N itself, not only on ν = (N − 1)f, so the bisection runs on N, not on ν.
    It returns 2.0 when two stations already exceed ε.
    """
    lo, hi = 2.0, 1.0 / (f * tf_s) + 2.0
    for _ in range(80):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if loss_periodic(mid, f, tf_s, acc, p_fixed=eps) < eps else (lo, mid)
    return lo
