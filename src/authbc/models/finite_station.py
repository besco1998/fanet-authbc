"""A finite-station form of the loss expression (G5), for 2–5 stations with periodic sources.

Work package C of `docs/prompts/NEXT_PHASE_PROMPT.md`. The derivation is in
`docs/revision/2026-11-20_finite_station_derivation.md`.

**Status: a proposal.** It is not registered against ns-3 or hardware until Mohamed accepts it.

**What changes from (G5).** Each station sends one frame per period. When the tagged frame waits
through a busy period, the station transmitting it cannot also be co-waiting: its next frame is
about a period away. So:
* co-waiting frames and arrivals in the DIFS gap come from the m = N − 2 stations other than the
  tagged one and the transmitter;
* they are counted as a binomial over those m stations, never more than m.

With n = N − 1 and ν = n·f as in (G4), and primes for the m-station rates:

    a  = ν(T_f − δ)(1 − p/2),   γ  = ν·DIFS,        η  = ν·σ(W − 1)/2          (as G4)
    a' = (m/n)·a,               γ' = (m/n)·γ,        η' = (m/n)·η
    K_N = a'(1 + γ' + 2η')/(1 − γ' − a')            (G4's K from the m stations)
    M ~ Binomial(m, π),  π = K_N/m                  (each of the m co-waiting with prob. π)
    p = a·E[M/(W + M)]  +  γ(2a'/W + γ')  +  2δν(1 + a)

**Its limits.**
* At N = 2 the first two terms vanish, leaving the detection window alone.
* As N grows, m/n → 1, K_N → K and the binomial tends to a Poisson count of mean K. The tie term
  then tends to a·E_Poisson[M/(W + M)], which equals (G5)'s a·K/(W + K) to first order in K/W.
  The difference is below 3 % of the tie term at the crossings of this work (K/W ≤ 0.05), and
  `tie_limit_gap` reports it.
"""
from __future__ import annotations

import math

from authbc.models import unified_capacity as uc


def _binomial_mean_ratio(m: int, pi: float, w: int) -> float:
    """E[M/(W + M)] for M ~ Binomial(m, π)."""
    return sum(math.comb(m, k) * pi ** k * (1 - pi) ** (m - k) * k / (w + k)
               for k in range(1, m + 1))


def terms(n_nodes: int, f: float, tf_s: float, acc: uc.Access, p: float) -> dict[str, float] | None:
    """The three terms at N stations, f frames/s each, with p inside a. None if saturated."""
    if n_nodes < 2:
        raise ValueError("N ≥ 2")
    n, m = n_nodes - 1, n_nodes - 2
    nu = n * f
    a = nu * (tf_s - acc.delta_s) * (1 - p / 2)
    gam, eta = nu * acc.difs_s, nu * acc.slot_s * (acc.w - 1) / 2
    if 1 - gam - a <= 0:
        return None
    share = m / n
    a1, g1, e1 = share * a, share * gam, share * eta
    tie = 0.0
    if m > 0:
        k_n = a1 * (1 + g1 + 2 * e1) / (1 - g1 - a1)
        tie = a * _binomial_mean_ratio(m, min(1.0, k_n / m), acc.w)
    return {"tie": tie,
            "zero_backoff_after_busy": gam * (2 * a1 / acc.w + g1),
            "detection_window": 2 * acc.delta_s * nu * (1 + a)}


def loss(n_nodes: int, f: float, tf_s: float, acc: uc.Access = uc.A80211B,
         p_fixed: float | None = None) -> float:
    """The finite-station loss of one frame, at its fixed point in p (or at `p_fixed`)."""
    p = 0.0 if p_fixed is None else p_fixed
    for _ in range(300):
        t = terms(n_nodes, f, tf_s, acc, p)
        if t is None:
            return 1.0
        pn = min(1.0, sum(t.values()))
        if p_fixed is not None or abs(pn - p) < 1e-12:
            return pn
        p = 0.5 * (p + pn)
    return p


def tie_limit_gap(k: float, w: int) -> float:
    """Relative gap between E_Poisson(K)[M/(W + M)] and (G5)'s K/(W + K): the limit's error."""
    if k <= 0:
        return 0.0
    poisson, term, j = 0.0, math.exp(-k), 0
    while j < 200:
        poisson += term * j / (w + j)
        j += 1
        term *= k / j
    return poisson / (k / (w + k)) - 1
