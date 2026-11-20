"""The unified closed-form capacity model of broadcast DCF, as specified for testing in
docs/revision/2026-11-17_unified_model_spec.md (§4; Mohamed's reference implementation is
`analysis/closed_form_model.py`).

* `loss` / `loss_terms` — the three-mechanism loss of one frame, Eqs. (G4)–(G5);
* `dcf_constants`, `n_law` — the two-constant capacity law, Eqs. (G6)–(G9);
* `n_root` — capacity from the full loss expression with p = ε inside a;
* `design_law` — the law rewritten in the batch size, Eqs. (G10)–(G13);
* `eps_keyrecord`, `eps_fragment`, `n_aloha_duty` — the three design rules.

It stands beside `broadcast_dcf.py` and the §6g closed form of docs/02 and replaces neither. Every
constant is the standard's (or ns-3's, where ns-3 states it); nothing is fitted to a simulation.
"""
from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass

from authbc.models import bianchi
from authbc.models.phy import DsssPhy, OfdmPhy


@dataclass(frozen=True)
class Access:
    """The access constants the model needs: slot σ, DIFS, window W and detection time δ."""

    slot_s: float
    difs_s: float
    w: int
    delta_s: float = 4e-6           # ns-3's preamble-detection duration

    def __post_init__(self) -> None:
        if min(self.slot_s, self.difs_s, self.delta_s) <= 0 or self.w < 1:
            raise ValueError("access constants must be positive and W ≥ 1")


A80211A = Access(slot_s=9e-6, difs_s=34e-6, w=16)
A80211P = Access(slot_s=13e-6, difs_s=58e-6, w=16)     # 10 MHz: SIFS 32 + 2 × 13
A80211B = Access(slot_s=20e-6, difs_s=50e-6, w=32)


def airtime_s(phy: OfdmPhy | DsssPhy, payload_bytes: float) -> float:
    """T_f: the frame's time on air without DIFS, with 36 B of LLC, MAC header and FCS."""
    return phy.ppdu_s(bianchi.mpdu_bytes(payload_bytes))


def affine_airtime(phy: OfdmPhy | DsssPhy, fixed_bytes: float,
                   per_record_bytes: float) -> tuple[float, float]:
    """(Φ_T, Ψ_T) of T_f(b) = Φ_T + Ψ_T·b, without the PHY's rounding to whole symbols."""
    psi = 8.0 * per_record_bytes / phy.rate_bps
    service_tail = (bianchi.SERVICE_BITS + bianchi.TAIL_BITS) if isinstance(phy, OfdmPhy) else 0
    head = phy.preamble_signal_s if isinstance(phy, OfdmPhy) else phy.plcp_s
    phi = head + (service_tail + 8.0 * bianchi.mpdu_bytes(fixed_bytes)) / phy.rate_bps
    return phi, psi


KRatio = Callable[[float], float]
"""A scale on K as a function of the load a + γ: (G25) passes the periodic-source ratio R."""


def _terms(nu: float, tf_s: float, acc: Access, p: float,
           k_ratio: KRatio | None = None) -> dict[str, float] | None:
    a = nu * (tf_s - acc.delta_s) * (1 - p / 2)
    gam, eta = nu * acc.difs_s, nu * acc.slot_s * (acc.w - 1) / 2
    if 1 - gam - a <= 0:
        return None                                   # the medium never empties: saturated
    k = a * (1 + gam + 2 * eta) / (1 - gam - a)       # (G4)
    if k_ratio is not None:
        k *= k_ratio(a + gam)                         # (G25): co-waiting frames of periodic sources
    return {"tie": a * k / (acc.w + k),
            "zero_backoff_after_busy": gam * (2 * a / acc.w + gam),
            "detection_window": 2 * acc.delta_s * nu * (1 + a)}


def loss(nu: float, tf_s: float, acc: Access = A80211A, p_fixed: float | None = None,
         k_ratio: KRatio | None = None) -> float:
    """Loss of one frame at start rate ν = (N − 1)f and airtime T_f, Eq. (G5).

    With `p_fixed`, p inside a is held at that value (one evaluation); otherwise p is the damped
    fixed point. 1.0 where the expression saturates. `k_ratio` scales K (None: Poisson, as G5).
    """
    p = 0.0 if p_fixed is None else p_fixed
    for _ in range(300):
        terms = _terms(nu, tf_s, acc, p, k_ratio)
        if terms is None:
            return 1.0
        pn = min(1.0, sum(terms.values()))
        if p_fixed is not None or abs(pn - p) < 1e-10:
            return pn
        p = 0.5 * (p + pn)
    return p


def loss_terms(nu: float, tf_s: float, acc: Access = A80211A) -> dict[str, float]:
    """The three terms of (G5) at its fixed point: tie, zero backoff after busy, detection."""
    terms = _terms(nu, tf_s, acc, loss(nu, tf_s, acc))
    if terms is None:
        raise ValueError("saturated: the loss expression has no terms here")
    return terms


def dcf_constants(eps: float, acc: Access = A80211A) -> tuple[float, float]:
    """The occupancy ceiling ρ* and protocol time τ0 at loss target ε, Eqs. (G6)–(G8)."""
    w = acc.w
    rho = (-eps * (w - 1) + math.sqrt(eps ** 2 * (w - 1) ** 2 + 4 * eps * w)) / 2
    d0, s = w - (w - 1) * rho, acc.slot_s * (w - 1) / 2
    dp0 = (2 * rho * d0 + (w - 1) * rho ** 2) / d0 ** 2
    c_eff = (rho ** 2 * w * ((acc.difs_s + 2 * s) * (1 - rho) + acc.difs_s) / d0 ** 2
             + 2 * rho * acc.difs_s / w + 2 * acc.delta_s * (1 + rho))
    return rho, c_eff / dp0


def n_law(f: float, tf_s: float, eps: float, acc: Access = A80211A) -> float:
    """N_max by the two-constant law, Eq. (G9)."""
    rho, tau0 = dcf_constants(eps, acc)
    return 1 + rho / (f * ((1 - eps / 2) * (tf_s - acc.delta_s) + tau0))


def n_root(f: float, tf_s: float, eps: float, acc: Access = A80211A) -> float:
    """N_max where the loss expression, with p = ε inside a, reaches ε (bisection on ν)."""
    lo, hi = 0.0, 1.0 / tf_s
    for _ in range(80):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if loss(mid, tf_s, acc, p_fixed=eps) < eps else (lo, mid)
    return 1 + lo / f


@dataclass(frozen=True)
class DesignLaw:
    """N_max(b) − 1 = N_inf·b/(b + β), Eqs. (G10)–(G13)."""

    n_inf: float
    beta: float

    def n_max(self, b: float) -> float:
        return 1 + self.n_inf * b / (b + self.beta)

    def gain(self, b: float) -> float:
        """Γ(b) = b(1 + β)/(b + β): capacity at batch b over capacity at b = 1, less one each."""
        return b * (1 + self.beta) / (b + self.beta)


def design_law(lam: float, phi_t: float, psi_t: float, eps: float,
               acc: Access = A80211A) -> DesignLaw:
    """The law at record rate Λ for T_f(b) = Φ_T + Ψ_T·b: Β = ρ*/κ, τ̂ = τ0/κ − δ."""
    rho, tau0 = dcf_constants(eps, acc)
    kappa = 1 - eps / 2
    big_b, tau_hat = rho / kappa, tau0 / kappa - acc.delta_s
    return DesignLaw(n_inf=big_b / (lam * psi_t), beta=(phi_t + tau_hat) / psi_t)


def eps_keyrecord(r: int, eps: float) -> float:
    """Per-frame target ε_r with a key record once in r frames: the root of
    (1 − p)(1 − (1 − p)^r)/(r·p) = 1 − ε (frame j verifies only if frames 1 … j all arrive)."""
    if r < 1:
        raise ValueError("r ≥ 1")

    def verified(p: float) -> float:
        return (1 - p) * (1 - (1 - p) ** r) / (r * p)

    lo, hi = 1e-15, eps
    for _ in range(200):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if verified(mid) > 1 - eps else (lo, mid)
    return (lo + hi) / 2


def eps_fragment(n: int, eps: float) -> float:
    """Per-frame target ε_n for a signed unit split over n frames that all must arrive."""
    if n < 1:
        raise ValueError("n ≥ 1")
    return 1 - (1 - eps) ** (1 / n)


def n_aloha_duty(channels: int, duty: float, eps: float) -> int:
    """Duty-cycled ALOHA at the duty-cycle limit: 1 + floor(C·ln(1/(1 − ε))/(2d))."""
    if channels < 1 or not 0 < duty <= 1:
        raise ValueError("channels ≥ 1 and 0 < duty ≤ 1")
    return 1 + math.floor(channels * math.log(1 / (1 - eps)) / (2 * duty))
