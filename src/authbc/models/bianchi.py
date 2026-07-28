"""Bianchi DCF saturation model for 802.11 (implements docs/02 §6, docs/03 §3 models/).

The saturated-node distributed-coordination-function (DCF) fixed point of Bianchi (2000):

    τ    = 2(1−2p_c) / [(1−2p_c)(W+1) + p_c·W(1−(2p_c)^m)]      (per-slot tx probability)
    p_c  = 1 − (1−τ)^(N−1)                                       (conditional collision prob)

with W = CW_min = 16 and m = 6 backoff stages (docs/02 §6, normative). The undamped
substitution *oscillates* at high N, so we solve the fixed point with damped iteration
p ← 0.7·p + 0.3·p_new to tol 1e-12 (docs/02 §6 — "undamped oscillates at high N, verified").

Saturation throughput (standard Bianchi):

    S = P_tr·P_s·E[payload] / E[slot]

with P_tr = 1−(1−τ)^N (a slot has ≥1 tx), P_s = Nτ(1−τ)^(N−1)/P_tr (that tx is a success),
E[payload] = 8L bits, and E[slot] = (1−P_tr)·σ + P_tr·P_s·T_s + P_tr·(1−P_s)·T_c.

Slot/airtime durations use the OFDM 6 Mb/s timing of docs/02 §6. All times are SI seconds
internally; helpers convert bytes→airtime at R.
"""

from __future__ import annotations

from dataclasses import dataclass

# --- DCF backoff parameters (docs/02 §6, normative) ---------------------------------------
W: int = 16  # CW_min (contention window minimum), slots
M: int = 6   # number of backoff stages, so CW_max = 2^M · W

# --- 802.11a OFDM PHY/MAC timing (docs/02 §6), SI seconds / bytes / bits-per-second -------
T_PHY: float = 20e-6      # PHY preamble + SIGNAL, s
SIFS: float = 16e-6       # short interframe space, s
SLOT: float = 9e-6        # empty (idle) backoff slot σ, s
DIFS: float = 34e-6       # DCF interframe space, s
DELTA: float = 1e-6       # propagation delay δ, s
ACK_BYTES: int = 14       # ACK frame length, bytes
MAC_OVH_BYTES: int = 34   # MAC header + FCS carried with every data frame, bytes
R_BPS: float = 6e6        # OFDM data rate, bits/s

# tol/budget for the damped fixed-point iteration
_TOL: float = 1e-12
_MAX_ITER: int = 100_000


def _airtime(nbytes: float) -> float:
    """On-air time for *nbytes* bytes at the PHY data rate R (seconds)."""
    return 8.0 * nbytes / R_BPS


# ACK airtime includes its own PHY preamble (physically correct; docs/02 §6 lists T_ack).
T_ACK: float = T_PHY + _airtime(ACK_BYTES)


def t_success(payload_bytes: float) -> float:
    """T_s(L): channel time of a *successful* DATA→SIFS→ACK exchange (docs/02 §6), seconds.

    T_s = T_phy + 8(L+MAC_OVH)/R + SIFS + δ + T_ack + DIFS + δ.
    """
    return (
        T_PHY
        + _airtime(payload_bytes + MAC_OVH_BYTES)
        + SIFS
        + DELTA
        + T_ACK
        + DIFS
        + DELTA
    )


def t_collision(payload_bytes: float) -> float:
    """T_c(L): channel time of a *collision* (no ACK; sender waits DIFS), seconds (docs/02 §6).

    T_c = T_phy + 8(L+MAC_OVH)/R + DIFS + δ.
    """
    return T_PHY + _airtime(payload_bytes + MAC_OVH_BYTES) + DIFS + DELTA


# Fixed airtime overhead of a frame for the energy/latency model (docs/02 §6: T_fx ≈ 123 µs).
# T_air(L) = T_fx + 8L/R with T_fx = channel-busy part of a successful exchange minus the DIFS
# idle deferral = T_s(0) − DIFS = T_phy + 8·MAC_OVH/R + SIFS + T_ack + 2δ = 122.0 µs. This
# reconciles with the doc's "≈123 µs" anchor (the doc rounds the 8·34/6 and δ terms).
T_FX: float = T_PHY + _airtime(MAC_OVH_BYTES) + SIFS + T_ACK + 2 * DELTA


def t_air(payload_bytes: float) -> float:
    """T_air(L) = T_fx + 8L/R: channel-busy airtime of one frame (docs/02 §6), seconds.

    Used by the energy model (docs/02 §7) as the receiver on-air time per frame.
    """
    return T_FX + _airtime(payload_bytes)


# --- EXACT 802.11a OFDM airtime (audit A1/A10: for comparison against a real PHY) ------------
# The constants above model airtime as continuous 8N/R. A real 802.11a PHY sends whole 4 µs OFDM
# symbols and prepends 16 SERVICE + 6 TAIL bits, and the MAC prepends LLC/SNAP. Measured against
# NS-3 3.41 the continuous form is 0.41 % short on a 1400 B data frame (1932 vs 1940 µs) and
# **12.1 % short on an ACK** (38.67 vs 44 µs), because a 14 B ACK needs 6 whole symbols.
#
# These helpers are SEPARATE from the constants above on purpose: T_PHY/MAC_OVH_BYTES/R_BPS feed
# `models.energy` (and hence the frozen E5 energy column), so quantising them is a docs/02 §6 spec
# change and Mohamed's call (Law 8). Nothing here is used by the energy path — only by the NS-3
# comparison, which must be apples-to-apples with the simulator's real PHY.
OFDM_SYMBOL: float = 4e-6       # 802.11a OFDM symbol duration, s
SERVICE_BITS: int = 16          # PLCP SERVICE field prepended to the PSDU
TAIL_BITS: int = 6              # convolutional-code tail
LLC_SNAP_BYTES: int = 8         # 802.2 LLC/SNAP header carried under the MSDU
MAC_HDR_FCS_BYTES: int = 28     # non-QoS 3-address MAC header (24) + FCS (4)


def ofdm_ppdu(nbytes: int, rate_bps: float = R_BPS) -> float:
    """Exact 802.11a PPDU duration for an *nbytes* PSDU (seconds).

    T_phy + ceil((16 + 8N + 6) / bits-per-symbol) · 4 µs. Verified against NS-3: 1940 µs for the
    1436 B MPDU of a 1400 B payload, 44 µs for a 14 B ACK.
    """
    bits_per_symbol = rate_bps * OFDM_SYMBOL
    n_symbols = -(-(SERVICE_BITS + 8 * nbytes + TAIL_BITS) // int(bits_per_symbol))
    return T_PHY + n_symbols * OFDM_SYMBOL


def mpdu_bytes(payload_bytes: float) -> int:
    """On-air MPDU size for an *payload_bytes* MAC-SDU: payload + LLC/SNAP + MAC header + FCS."""
    return int(payload_bytes) + LLC_SNAP_BYTES + MAC_HDR_FCS_BYTES


T_ACK_EXACT: float = ofdm_ppdu(ACK_BYTES)  # 44 µs, vs the continuous model's 38.67 µs


def t_success_exact(payload_bytes: float) -> float:
    """T_s with a real OFDM PHY: DATA + SIFS + ACK + DIFS. Measured NS-3 floor: 94 µs after DATA."""
    return ofdm_ppdu(mpdu_bytes(payload_bytes)) + SIFS + T_ACK_EXACT + DIFS


def t_collision_exact(payload_bytes: float) -> float:
    """T_c with a real OFDM PHY: DATA + DIFS. NS-3 gap floor after a collision: DIFS + one slot."""
    return ofdm_ppdu(mpdu_bytes(payload_bytes)) + DIFS


def t_broadcast_exact(payload_bytes: float) -> float:
    """Busy-period time of one broadcast frame (never ACKed): DATA + DIFS."""
    return ofdm_ppdu(mpdu_bytes(payload_bytes)) + DIFS


def tau_of_pc(pc: float) -> float:
    """τ(p_c) — the Bianchi tx probability given conditional collision prob (docs/02 §6)."""
    two_pc = 2.0 * pc
    denom = (1.0 - two_pc) * (W + 1) + pc * W * (1.0 - two_pc**M)
    return 2.0 * (1.0 - two_pc) / denom


def pc_of_tau(tau: float, n: int) -> float:
    """p_c(τ, N) = 1 − (1−τ)^(N−1) — collision prob seen by a station among N (docs/02 §6)."""
    return 1.0 - (1.0 - tau) ** (n - 1)


class ConvergenceError(RuntimeError):
    """Raised when the damped fixed-point iteration fails to converge in the iteration budget.

    Per CLAUDE.md Law 3 we never silently return a non-converged value.
    """


@dataclass(frozen=True)
class BianchiResult:
    """Solved DCF operating point for N saturated stations at payload L bytes."""

    n: int
    payload_bytes: float
    tau: float          # per-slot transmission probability
    p_c: float          # conditional collision probability
    p_tr: float         # P(≥1 transmission in a slot)
    p_s: float          # P(transmission is a success | ≥1 transmission)
    e_slot: float       # E[slot] average slot duration, seconds
    throughput_bps: float  # saturation throughput S, bits/s
    iterations: int     # damped iterations to converge (diagnostic)


def solve(
    n: int,
    payload_bytes: float,
    *,
    t_s: float | None = None,
    t_c: float | None = None,
) -> BianchiResult:
    """Solve the Bianchi DCF fixed point for *n* saturated stations, *payload_bytes* payload.

    Damped iteration p_c ← 0.7·p_c + 0.3·p_c_new from p_c=0, converging on |Δp_c| < 1e-12
    (docs/02 §6). Returns τ, p_c, the success/transmit probabilities, E[slot], and throughput.

    *t_s*/*t_c* override the success/collision slot times. They exist so the NS-3 comparison can
    supply the EXACT OFDM airtimes (`t_success_exact`/`t_collision_exact`) without changing the
    docs/02 §6 constants that the energy model depends on. Defaults reproduce the doc's model.

    Raises ValueError for n < 1 and ConvergenceError if the iteration exceeds the budget.
    """
    if n < 1:
        raise ValueError(f"n must be ≥ 1 (saturated stations), got {n}")
    if payload_bytes <= 0:
        raise ValueError(f"payload_bytes must be > 0, got {payload_bytes}")

    pc = 0.0
    iterations = 0
    while True:
        iterations += 1
        tau = tau_of_pc(pc)
        pc_new = pc_of_tau(tau, n)          # 0 when n == 1 → immediate convergence
        pc_next = 0.7 * pc + 0.3 * pc_new
        converged = abs(pc_next - pc) < _TOL
        pc = pc_next
        if converged:
            break
        if iterations >= _MAX_ITER:
            raise ConvergenceError(
                f"Bianchi fixed point did not converge for n={n} in {_MAX_ITER} iterations"
            )

    tau = tau_of_pc(pc)  # τ consistent with the converged p_c

    p_tr = 1.0 - (1.0 - tau) ** n
    # P_s is well-defined only when a transmission occurs; p_tr>0 for τ>0, n≥1.
    p_s = n * tau * (1.0 - tau) ** (n - 1) / p_tr
    ts = t_success(payload_bytes) if t_s is None else t_s
    tc = t_collision(payload_bytes) if t_c is None else t_c
    e_slot = (1.0 - p_tr) * SLOT + p_tr * p_s * ts + p_tr * (1.0 - p_s) * tc
    throughput_bps = p_tr * p_s * (8.0 * payload_bytes) / e_slot

    return BianchiResult(
        n=n,
        payload_bytes=payload_bytes,
        tau=tau,
        p_c=pc,
        p_tr=p_tr,
        p_s=p_s,
        e_slot=e_slot,
        throughput_bps=throughput_bps,
        iterations=iterations,
    )


def fixed_point_residual(res: BianchiResult) -> float:
    """Max abs violation of the two DCF equations at the solved point — should be ≈ 0.

    Independent consistency gate (docs/02 §6): both τ = τ(p_c) and p_c = p_c(τ, N) must hold.
    """
    r_tau = res.tau - tau_of_pc(res.p_c)
    r_pc = res.p_c - pc_of_tau(res.tau, res.n)
    return max(abs(r_tau), abs(r_pc))
