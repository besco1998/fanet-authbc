"""Ma & Chen's saturation model for IEEE 802.11 BROADCAST (docs/02 §6, audit F9).

    X. Ma and X. Chen, "Saturation Performance of IEEE 802.11 Broadcast Networks,"
    IEEE Communications Letters, vol. 11, no. 8, pp. 686–688, Aug. 2007,
    doi:10.1109/LCOMM.2007.070040.
    X. Ma and X. Chen, "Performance Analysis of IEEE 802.11 Broadcast Scheme in Ad Hoc
    Wireless LANs," IEEE Trans. Vehicular Technology, vol. 57, no. 6, pp. 3757–3768,
    Nov. 2008, doi:10.1109/TVT.2008.918731.

Equation numbers below refer to the 2008 journal version, which is the authoritative one: the
2007 letter's eq. (6) prints `pss = 1−(1−τs)^(n−1)`, which is a collision probability and cannot
be a success probability; the journal's eq. (8) gives the correct `pss = nτs(1−τs)^(n−1)`.

WHY THIS MODULE EXISTS. `models.bianchi` is the ACK/unicast DCF model and is validated against
NS-3 to +0.6…−2.9 %. Broadcast is NOT that model with the ACK removed. Ma & Chen open by warning
that unicast models "cannot simply be reduced for the analysis of broadcast service", and this
project made exactly that mistake: an in-house reduction using τ = 2/(W+1) under-predicted NS-3
by **16× at N=50** (audit F9). `naive_reduction_mbps` below is kept only so the figure can show
that failure explicitly.

THE MECHANISM (Ma & Chen call it the backoff counter Consecutive Freeze Process, CFP). Broadcast
is never acknowledged, so there is no retransmission and the contention window never doubles — it
stays at W₀. A station that has just transmitted redraws its backoff and may draw **0**, taking
the medium immediately after DIFS, while every station that deferred necessarily holds a counter
≥ 1. In unicast the ACK timeout (> DIFS) blocks the colliders from doing this, so CFP can only
follow a *success*; in broadcast there is no ACK timeout, so CFP follows collisions too and every
collider can seize the next slot. With W₀ small relative to N this becomes the dominant channel
through which any frame succeeds alone.

The backoff counter is therefore NOT a Markov process once CFP is included, so the model splits
it into two sub-processes: the sequential backoff process (SBP, zero initial backoff excluded)
and the CFP itself.

Verified against our own NS-3 3.41 measurements (802.11a, 6 Mb/s, W₀=16, L=1400 B): throughput,
p_s and idle-slots-per-busy-period all agree to **≤0.36 %** at N = 5, 10, 20, 35, 50 — a parameter
regime the original papers did not test (they used W₀ = 32 and 128 at 1 Mb/s).
"""

from __future__ import annotations

from dataclasses import dataclass

# Freeze stages summed in the CFP series. τ_f(i) = τs/W₀^i falls by a factor W₀ each stage, so at
# W₀=16 the i=6 term is below 1e-9 of the first; 12 is far past convergence at any sane W₀.
_CFP_STAGES: int = 12


@dataclass(frozen=True)
class BroadcastResult:
    """Solved broadcast operating point for *n* saturated stations."""

    n: int
    w0: int
    tau_s: float             # τs — tx probability in the sequential backoff process, eq. (5)
    p_bs: float              # P(channel busy | SBP slot), eq. (7)
    p_ss: float              # P(success | SBP slot), eq. (8)
    e_nsf: float             # E[N_sf] — successes contributed by the CFP per virtual slot
    e_nbf: float             # E[N_bf] — busy freeze stages per virtual slot
    throughput_bps: float    # saturation throughput S, eq. (12)

    @property
    def successes_per_vslot(self) -> float:
        """Frames delivered per virtual slot (SBP + CFP)."""
        return self.p_ss + self.e_nsf

    @property
    def busy_periods_per_vslot(self) -> float:
        """Transmission periods per virtual slot (SBP + CFP)."""
        return self.p_bs + self.e_nbf

    @property
    def p_success(self) -> float:
        """P(a busy period carries exactly one frame) — comparable to Bianchi's p_s."""
        return self.successes_per_vslot / self.busy_periods_per_vslot

    @property
    def idle_slots_per_busy_period(self) -> float:
        """Backoff slots that elapse per busy period.

        Ma & Chen charge exactly one idle slot per *virtual* slot ("considering that there must be
        an idle back off slot in each virtual slot", eq. 12), and a virtual slot holds
        `busy_periods_per_vslot` transmissions — so this is its reciprocal. Measured 0.741 at
        N=50 against the model's 0.7413; Bianchi's abstraction predicts 0.0019 here.
        """
        return 1.0 / self.busy_periods_per_vslot


def solve(
    n: int,
    payload_bytes: float,
    t_busy_s: float,
    *,
    w0: int = 16,
    slot_s: float = 9e-6,
) -> BroadcastResult:
    """Solve Ma & Chen's broadcast model for *n* saturated stations.

    *t_busy_s* is the channel time of one transmission including the following DIFS —
    Ma & Chen's ``T = T_H + E[P] + DIFS + δ``, which is success/collision symmetric because
    broadcast never ACKs. Use `bianchi.t_broadcast_exact` for real 802.11a OFDM timing.

    Raises ValueError for n < 1 or a degenerate window.
    """
    if n < 1:
        raise ValueError(f"n must be ≥ 1 saturated stations, got {n}")
    if w0 < 2:
        raise ValueError(f"w0 (backoff window size) must be ≥ 2, got {w0}")
    if payload_bytes <= 0:
        raise ValueError(f"payload_bytes must be > 0, got {payload_bytes}")
    if t_busy_s <= 0:
        raise ValueError(f"t_busy_s must be > 0, got {t_busy_s}")

    tau_s = 2.0 / w0                                        # eq. (5)
    p_bs = 1.0 - (1.0 - tau_s) ** n                         # eq. (7)
    p_ss = n * tau_s * (1.0 - tau_s) ** (n - 1)             # eq. (8)

    e_nsf = e_nbf = 0.0
    for i in range(1, _CFP_STAGES + 1):
        tau_f = tau_s / w0**i                               # eq. (6)
        e_nsf += n * tau_f * (1.0 - tau_f) ** (n - 1)       # P(success in freeze stage i)
        e_nbf += 1.0 - (1.0 - tau_f) ** n                   # P(channel busy in freeze stage i)

    # eq. (12): S = E[P]' / (σ + T_b'), one idle backoff slot per virtual slot.
    payload_bits = (p_ss + e_nsf) * 8.0 * payload_bytes
    busy_time = (p_bs + e_nbf) * t_busy_s
    throughput = payload_bits / (slot_s + busy_time)

    return BroadcastResult(
        n=n, w0=w0, tau_s=tau_s, p_bs=p_bs, p_ss=p_ss,
        e_nsf=e_nsf, e_nbf=e_nbf, throughput_bps=throughput,
    )


def naive_reduction_mbps(n: int, payload_bytes: float, t_busy_s: float, *, w: int = 16,
                         slot_s: float = 9e-6) -> float:
    """The WRONG model — the unicast Bianchi form with the ACK removed, τ = 2/(W+1).

    Retained solely so the validation figure can show the failure it produces. It ignores the CFP
    entirely, treating consecutive channel slots as independent, and under-predicts NS-3 by up to
    16× at N=50 (audit F9). Never use it for a prediction.
    """
    tau = 2.0 / (w + 1)
    p_tr = 1.0 - (1.0 - tau) ** n
    p_s = n * tau * (1.0 - tau) ** (n - 1) / p_tr
    e_slot = (1.0 - p_tr) * slot_s + p_tr * t_busy_s
    return p_tr * p_s * (8.0 * payload_bytes) / e_slot / 1e6
