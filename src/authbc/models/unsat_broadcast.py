"""The unsaturated fixed-point model of Malone, Duffy and Leith, adapted to broadcast (C, N = 2).

Source: D. Malone, K. Duffy, D. Leith, "Modeling the 802.11 Distributed Coordination Function in
Nonsaturated Heterogeneous Conditions", IEEE/ACM ToN 15(1):159–172, 2007,
doi:10.1109/TNET.2006.890136. Read in the PDF from the authors' institutional repository
(MURAL 1514, CC BY-NC-SA). Equations (5) and (6) were quoted from the printed page.

**The model.** Bianchi's chain with post-backoff states (0, k)_e: a station that has sent a frame
and holds no other. q is the probability that a frame arrives during an expected state time. A
frame arriving to the empty, idle station is sent in that slot.

**Broadcast.** No acknowledgement: a collision goes undetected and the station returns to stage
0 as after a success. That is the chain of the paper with p = 0 in its *transitions* (m plays no
part). Equations (5)–(6) with p = 0:

    1/b(0,0)_e = (1 − q) + q²W0(W0 + 1)/(2(1 − (1 − q)^W0))
               + q(W0 + 1)/(2(1 − q))·(q²W0/(1 − (1 − q)^W0) + (1 − P_idle)(1 − q) − q·P_idle)
    τ = b(0,0)_e·(q²W0/((1 − q)(1 − (1 − q)^W0)) − q²·P_idle/(1 − q))

The paper's network relations for N identical stations:
* P_idle = (1 − τ)^(N−1);
* **the loss of one frame**, its collision probability, p = 1 − (1 − τ)^(N−1);
* the expected state time E_s = (1 − τ)^N·σ + (1 − (1 − τ)^N)·(T_f + DIFS);
* q = 1 − exp(−f·E_s), the paper's estimate for Poisson arrivals.

A slotted model: two starts coincide when they fall in the same slot σ. It has no detection time
δ and no DIFS-gap rule.

**Status:** under test against rule A's event simulation at N = 2 (Mohamed, 2026-11-20). Proposed
to him only if it holds there.
"""
from __future__ import annotations

import math

import numpy as np

from authbc.models import unified_capacity as uc


def tau_closed(q: float, p_idle: float, w0: int) -> float:
    """τ from MDL (5)–(6) with p = 0 in the transitions (broadcast)."""
    if not 0 < q < 1 or not 0 <= p_idle <= 1 or w0 < 1:
        raise ValueError("0 < q < 1, 0 ≤ P_idle ≤ 1, W0 ≥ 1")
    a = 1 - (1 - q) ** w0
    inv_b = ((1 - q) + q * q * w0 * (w0 + 1) / (2 * a)
             + q * (w0 + 1) / (2 * (1 - q)) * (q * q * w0 / a + (1 - p_idle) * (1 - q)
                                                 - q * p_idle))
    return (1 / inv_b) * (q * q * w0 / ((1 - q) * a) - q * q * p_idle / (1 - q))


def tau_chain(q: float, p_idle: float, w0: int) -> float:
    """τ from the broadcast chain solved numerically: an independent check of `tau_closed`.

    States 0 … W0−1 are (0, k) with a frame; W0 … 2W0−1 are (0, k)_e without one.
    """
    n = 2 * w0
    pmat = np.zeros((n, n))
    for k in range(1, w0):
        pmat[k, k - 1] = 1.0                                   # (0,k) → (0,k−1)
        pmat[w0 + k, w0 + k - 1] = 1 - q                       # (0,k)_e → (0,k−1)_e
        pmat[w0 + k, k - 1] = q                                # … or a frame arrives
    for k in range(w0):                                        # (0,0): send, then a new counter
        pmat[0, w0 + k] += (1 - q) / w0
        pmat[0, k] += q / w0
    pmat[w0, w0] += 1 - q                                      # (0,0)_e, nothing arrives
    for k in range(w0):
        pmat[w0, w0 + k] += q * p_idle / w0                    # arrives, idle: sent at once
        pmat[w0, k] += q * (1 - p_idle) / w0                   # arrives, busy: stage-0 backoff
    vals, vecs = np.linalg.eig(pmat.T)
    pi = np.real(vecs[:, np.argmin(np.abs(vals - 1))])
    pi /= pi.sum()
    return float(pi[0] + pi[w0] * q * p_idle)


def solve(n_nodes: int, f: float, tf_s: float, acc: uc.Access) -> dict[str, float]:
    """The fixed point for N identical stations, each with f frames/s: τ, q, P_idle and the loss."""
    if n_nodes < 2:
        raise ValueError("N ≥ 2")
    tau = 0.01
    for _ in range(2000):
        p_idle = (1 - tau) ** (n_nodes - 1)
        busy = 1 - (1 - tau) ** n_nodes
        e_s = (1 - busy) * acc.slot_s + busy * (tf_s + acc.difs_s)
        q = min(1 - 1e-12, 1 - math.exp(-f * e_s))
        new = tau_closed(q, p_idle, acc.w)
        if abs(new - tau) < 1e-13:
            break
        tau = 0.5 * (tau + new)
    return {"tau": tau, "q": q, "p_idle": p_idle,
            "loss": 1 - (1 - tau) ** (n_nodes - 1)}
