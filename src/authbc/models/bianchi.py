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
MAC_OVH_BYTES: int = 36   # LLC/SNAP 8 + MAC header 24 + FCS 4, carried with every data frame
R_BPS: float = 6e6        # OFDM data rate, bits/s

# tol/budget for the damped fixed-point iteration
_TOL: float = 1e-12
_MAX_ITER: int = 100_000


# --- EXACT 802.11a OFDM airtime (docs/02 §6, decision D9) -----------------------------------
# Airtime is NOT linear in the payload: an 802.11a PHY transmits whole 4 µs OFDM symbols and
# prepends 16 SERVICE + 6 TAIL bits. Modelling it as continuous 8N/R understated a 1400 B data
# frame by 0.41 % and an ACK by 12.1 % against NS-3 3.41 (audit A1). Because airtime is a step
# function of L, there is no meaningful constant "T_fx" and no linear `t_air(L)` — every airtime
# below is computed from the frame's actual size.
OFDM_SYMBOL: float = 4e-6       # 802.11a OFDM symbol duration, s
SERVICE_BITS: int = 16          # PLCP SERVICE field prepended to the PSDU
TAIL_BITS: int = 6              # convolutional-code tail
LLC_SNAP_BYTES: int = 8         # 802.2 LLC/SNAP header carried under the MSDU
MAC_HDR_FCS_BYTES: int = 28     # non-QoS 3-address MAC header (24) + FCS (4)


def ofdm_ppdu(nbytes: float, rate_bps: float = R_BPS) -> float:
    """Exact 802.11a PPDU duration for an *nbytes* PSDU (seconds).

    T_phy + ceil((16 + 8N + 6) / bits-per-symbol) · 4 µs. Verified against NS-3 3.41: 1940 µs for
    the 1436 B MPDU of a 1400 B payload, and 44 µs for a 14 B ACK.
    """
    bits_per_symbol = rate_bps * OFDM_SYMBOL
    n_symbols = -(-(SERVICE_BITS + 8.0 * nbytes + TAIL_BITS) // bits_per_symbol)
    return T_PHY + n_symbols * OFDM_SYMBOL


def mpdu_bytes(payload_bytes: float) -> float:
    """On-air MPDU size for a *payload_bytes* MAC-SDU: payload + LLC/SNAP + MAC header + FCS."""
    return payload_bytes + MAC_OVH_BYTES


# ACK airtime includes its own PHY preamble. 14 B needs 6 whole symbols ⇒ 44 µs, not 38.67 µs.
T_ACK: float = ofdm_ppdu(ACK_BYTES)


def t_success(payload_bytes: float) -> float:
    """T_s(L): channel time of a *successful* DATA→SIFS→ACK exchange (docs/02 §6), seconds.

    T_s = PPDU(L+MAC_OVH) + SIFS + T_ack + DIFS. NS-3 measures the deferral floor after a
    successful unicast exchange at exactly SIFS + T_ack + DIFS = 94 µs past the data frame.
    """
    return ofdm_ppdu(mpdu_bytes(payload_bytes)) + SIFS + T_ACK + DIFS


def t_collision(payload_bytes: float) -> float:
    """T_c(L): channel time of a *collision* (no ACK; the field waits DIFS), seconds.

    T_c = PPDU(L+MAC_OVH) + DIFS. NS-3's measured post-collision gap floor is DIFS + one slot.
    """
    return ofdm_ppdu(mpdu_bytes(payload_bytes)) + DIFS


def t_broadcast(payload_bytes: float) -> float:
    """Channel-busy time of one BROADCAST frame (never ACKed): PPDU(L+MAC_OVH) + DIFS, seconds.

    This is the energy model's per-frame on-air time (docs/02 §7) and Ma & Chen's `T`.
    """
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

    *t_s*/*t_c* override the success/collision slot times; the defaults are the exact OFDM
    airtimes and are what docs/02 §6 specifies. The overrides exist for sensitivity studies.

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
