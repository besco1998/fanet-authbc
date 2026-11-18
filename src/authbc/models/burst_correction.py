"""A burst correction to the loss expression, proposed by Mohamed on 2026-11-18 after U-C4 failed
(predictions/UC4.md), registered in predictions/UC4B.md and tested only on new cells.

A signed unit is sent as n frames handed to the MAC together. The first frame meets the channel
as an independent start does; frames 2 … n always find the medium busy, since each follows its
own station's previous transmission. In the loss expression (G4–G5) of
docs/revision/2026-11-17_unified_model_spec.md only the same-slot tie changes for them:

    p₁ = a·K/(W + K) + γ(2a/W + γ) + 2δν(1 + a)        (the first frame: the original)
    p₂ =   K/(W + K) + γ(2a/W + γ) + 2δν(1 + a)        (frames 2 … n: the tie without a)
    unit loss = 1 − (1 − p₁)(1 − p₂)^(n − 1)

with ν = (N − 1)·n·f the start rate of every station's frames, γ = ν·DIFS,
η = ν·σ(W − 1)/2, K = a(1 + γ + 2η)/(1 − γ − a), and a = ν(T_f − δ)(1 − p̄/2). The mean frame
loss p̄ = (p₁ + (n − 1)·p₂)/n is solved together with them by fixed-point iteration, as `loss` in
`unified_capacity` does for one frame.
"""
from __future__ import annotations

from authbc.models.unified_capacity import A80211A, Access


def burst_terms(nu: float, tf_s: float, n: int, acc: Access = A80211A) -> dict[str, float]:
    """p₁, p₂, the unit loss and the fixed point's a and K at start rate ν (all frames)."""
    if n < 1:
        raise ValueError("n ≥ 1")
    w = acc.w
    gam, eta = nu * acc.difs_s, nu * acc.slot_s * (w - 1) / 2
    p_bar = 0.0
    p1 = p2 = 1.0
    a = k = float("inf")
    for _ in range(500):
        a = nu * (tf_s - acc.delta_s) * (1 - p_bar / 2)
        if 1 - gam - a <= 0:
            return {"p1": 1.0, "p2": 1.0, "unit": 1.0, "a": a, "K": float("inf")}
        k = a * (1 + gam + 2 * eta) / (1 - gam - a)
        rest = gam * (2 * a / w + gam) + 2 * acc.delta_s * nu * (1 + a)
        p1 = min(1.0, a * k / (w + k) + rest)
        p2 = min(1.0, k / (w + k) + rest)
        new = (p1 + (n - 1) * p2) / n
        if abs(new - p_bar) < 1e-12:
            break
        p_bar = 0.5 * (p_bar + new)
    unit = 1 - (1 - p1) * (1 - p2) ** (n - 1)
    return {"p1": p1, "p2": p2, "unit": unit, "a": a, "K": k}


def unit_capacity(f_unit: float, tf_s: float, n: int, eps: float,
                  acc: Access = A80211A) -> float:
    """N where the unit loss reaches ε, for f_unit units per second, each sent as n frames."""
    lo, hi = 0.0, 1.0 / tf_s
    for _ in range(100):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if burst_terms(mid, tf_s, n, acc)["unit"] < eps else (lo, mid)
    return 1 + lo / (n * f_unit)
