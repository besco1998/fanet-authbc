"""Capture in the loss expression, Eqs. (G22)–(G24) of `docs/prompts/NEXT_PHASE_PROMPT.md` §3.

The inputs:
* q_ij, the probability that receiver i decodes sender j's frame when it collides;
* ℓ_ij, the link loss with no other sender.

    p_ij = p_c(ν)·(1 − q_ij) + ℓ_ij                                  (G22)
    the average criterion:      p_c(ν) = ε′,  ε′ = (ε − mean ℓ)/(1 − mean q)      (G23)
    the every-sender criterion: ε_w = min over senders j of (ε − ℓ_j)/(1 − q_j)   (G24)

The capacity laws are then used with ε′ or ε_w in place of ε.

**The closed forms for q,** with one interferer, threshold θ and path-loss exponent α, assume the
receiver decodes whichever frame is stronger by θ:
* Rayleigh, equal mean power: 1/(1 + θ), and (1 + θ)^−(k−1) for k frames;
* Rayleigh with path loss: the mean over interferers of 1/(1 + θ(d_ij/d_im)^α);
* no fading: the share of interferers with d_im > θ^(1/α)·d_ij.

**ns-3's own rule** (work package D: `predictions/UCAP.md`, `UCAP2.md`):
* ns-3's DCF collisions start within the 4 µs preamble-detection window;
* there the strongest preamble is kept if its SINR, counting every frame that arrived in the
  window, is at least 4 dB (`threshold-preamble-detection-model.cc:31–40`);
* the frame-capture model is never consulted inside the window. It acts only for a later frame
  that is stronger by its margin and arrives within 16 µs of the first frame's *start*
  (`simple-frame-capture-model.cc:71–72`), which DCF ties never do;
* a decoded frame then passes the error model at that SINR. At 6 Mb/s and 1 Mb/s, ns-3's models
  give success 1 at SINR ≥ 4 dB (U-CAP: 184 of 184 window points).

So for ns-3 the closed forms below hold with **θ = THETA_NS3 = 10^0.4**.
"""
from __future__ import annotations

from collections.abc import Sequence


def db_to_ratio(db: float) -> float:
    return 10 ** (db / 10)


THETA_NS3 = 10 ** 0.4   # ns-3.48's preamble-detection threshold, 4 dB, as a power ratio


def loss_with_capture(p_c: float, q: float, link_loss: float) -> float:
    """(G22): a frame lost to collision unless captured, or lost on its link."""
    _check_prob(p_c, q, link_loss)
    return p_c * (1 - q) + link_loss


def eps_average(eps: float, mean_link_loss: float, mean_q: float) -> float:
    """(G23): the collision-loss target ε′ when the mean frame must meet ε."""
    _check_prob(eps, mean_link_loss, mean_q)
    if mean_q >= 1:
        raise ValueError("mean q must be below 1")
    return (eps - mean_link_loss) / (1 - mean_q)


def eps_every_sender(eps: float, link_loss: Sequence[float], q: Sequence[float]) -> float:
    """(G24): the collision-loss target ε_w when every sender must meet ε."""
    if not link_loss or len(link_loss) != len(q):
        raise ValueError("one link loss and one q per sender")
    _check_prob(eps, *link_loss, *q)
    if max(q) >= 1:
        raise ValueError("every q must be below 1")
    return min((eps - lj) / (1 - qj) for lj, qj in zip(link_loss, q, strict=True))


def q_rayleigh_equal(theta: float, k: int = 2) -> float:
    """q for Rayleigh fading at equal mean power: P(S > θ·ΣI) over k − 1 interferers."""
    if theta < 0 or k < 1:
        raise ValueError("θ ≥ 0 and k ≥ 1")
    return (1 + theta) ** (-(k - 1))


def q_rayleigh_pathloss(theta: float, alpha: float, d_signal: float,
                        d_interferers: Sequence[float]) -> float:
    """q for Rayleigh fading with path loss: the mean over interferers of 1/(1 + θ(d_ij/d_im)^α)."""
    _check_geometry(theta, alpha, d_signal, d_interferers)
    return sum(1 / (1 + theta * (d_signal / dm) ** alpha) for dm in d_interferers) \
        / len(d_interferers)


def q_no_fading(theta: float, alpha: float, d_signal: float,
                d_interferers: Sequence[float]) -> float:
    """q without fading: the share of interferers farther than θ^(1/α)·d_ij."""
    _check_geometry(theta, alpha, d_signal, d_interferers)
    reach = theta ** (1 / alpha) * d_signal
    return sum(dm > reach for dm in d_interferers) / len(d_interferers)


def _check_prob(*xs: float) -> None:
    if any(not 0 <= x <= 1 for x in xs):
        raise ValueError("probabilities must lie in [0, 1]")


def _check_geometry(theta: float, alpha: float, d_signal: float,
                    d_interferers: Sequence[float]) -> None:
    if theta < 0 or alpha <= 0 or d_signal <= 0 or not d_interferers \
            or min(d_interferers) <= 0:
        raise ValueError("θ ≥ 0, α > 0 and positive distances, with at least one interferer")
