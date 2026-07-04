"""Ed25519 ↔ BLS energy crossover, power-independent form (implements docs/02 T4).

T4's per-record energy comparison is E = P_c·(CPU time) + P_r·(radio time). Which scheme wins
depends on the two platform powers only through their **ratio** κ = P_r/P_c, so we can locate the
crossover WITHOUT measuring absolute watts (those wait for the P7 energy meter, ⚠️ D5): for two
schemes,

    ΔCPU   = extra CPU time BLS costs vs Ed25519        [s/record, >0 ⇒ BLS costlier]
    ΔRADIO = radio time BLS saves  vs Ed25519           [s/record, >0 ⇒ BLS fewer on-air bytes]
    BLS is energy-optimal  ⇔  P_r·ΔRADIO > P_c·ΔCPU  ⇔  P_r/P_c > κ* = ΔCPU / ΔRADIO.

So κ* is the break-even power ratio: for any plausible platform (Wi-Fi receive power below CPU
active power ⇒ P_r/P_c ≲ 0.5), BLS wins only if κ* < that ratio. All inputs below are MEASURED
timings (P1 `p1_crypto.csv`) or byte-accounting constants (docs/02 T4) — no fabricated numbers.

Relay (cross-signer) vs own (self-batch) byte accounting (docs/02 T4, docs/01 §4):
  * own:   both schemes fold b own records under ONE signature ⇒ Ed carries g_own/b, BLS g_agg/b.
  * relay: Ed carries one g_own per record (b·g_own in a frame); BLS aggregates to g_agg+H_a ⇒
           BLS saves Δ(b) = g_own − (g_agg+H_a)/b bytes/record.
Radio time uses only the auth-byte DIFFERENCE (the b·s data bytes are identical for both schemes
and cancel); the second-order frame-count/T_fx effect is documented in docs/audits/p5.
"""

from __future__ import annotations

import math

# Auth-object sizes, bytes (docs/02 T4): Ed25519/ECDSA raw sig 64 B; BLS min-sig aggregate 48 B.
G_OWN_BYTES: float = 64.0
G_AGG_BYTES: float = 48.0
R_BPS: float = 6e6  # 802.11a OFDM data rate (docs/02 §6)

# Above this power ratio κ=P_r/P_c a radio-heavy platform could favour BLS. Wi-Fi receive power is
# below CPU-active power on RPi4-class nodes ⇒ the physically plausible band is P_r/P_c ≲ 0.5.
PLAUSIBLE_KAPPA_MAX: float = 0.5


def delta_relay_bytes(b: int, g_own: float = G_OWN_BYTES, g_agg: float = G_AGG_BYTES,
                      h_a: float = 0.0) -> float:
    """Δ(b) = g_own − (g_agg+H_a)/b — bytes/record BLS saves on RELAYED traffic (docs/02 T4)."""
    return g_own - (g_agg + h_a) / b


def delta_own_bytes(b: int, g_own: float = G_OWN_BYTES, g_agg: float = G_AGG_BYTES) -> float:
    """(g_own − g_agg)/b — bytes/record BLS saves on OWN self-batched traffic (one sig each)."""
    return (g_own - g_agg) / b


def radio_saving_s(delta_bytes: float, r_bps: float = R_BPS) -> float:
    """8·Δ/R — on-air time saved per record by carrying Δ fewer auth bytes, seconds."""
    return 8.0 * delta_bytes / r_bps


def extra_cpu_relay_s(t_agg_verify_b_s: float, b: int, t_verify_ed_s: float) -> float:
    """Δt = t_av(b)/b − t_vf^ed — BLS extra receiver CPU/record on relayed traffic (docs/02 T4).

    BLS aggregate-verifies b sigs once per frame (amortized /b); Ed25519 verifies each record.
    """
    return t_agg_verify_b_s / b - t_verify_ed_s


def extra_cpu_own_s(t_verify_bls_s: float, t_verify_ed_s: float, b: int) -> float:
    """(t_vf^bls − t_vf^ed)/b — BLS extra CPU/record on own self-batched traffic (verify diff)."""
    return (t_verify_bls_s - t_verify_ed_s) / b


def mix(rho: float, own: float, relay: float) -> float:
    """Workload mean of a per-record quantity at relay fraction ρ: (1−ρ)·own + ρ·relay."""
    if not 0.0 <= rho <= 1.0:
        raise ValueError(f"rho must be in [0,1], got {rho}")
    return (1.0 - rho) * own + rho * relay


def kappa_star(extra_cpu_s: float, radio_saving_s: float) -> float:
    """Break-even power ratio κ* = ΔCPU/ΔRADIO. BLS wins iff P_r/P_c > κ* (docs/02 T4).

    Degenerate cases (reported honestly, never as a bogus finite number):
      * ΔRADIO ≤ 0 (BLS saves no on-air bytes) with ΔCPU ≥ 0 ⇒ BLS can never win ⇒ +∞.
      * ΔCPU ≤ 0 (BLS also cheaper on CPU) with ΔRADIO > 0 ⇒ BLS wins for all powers ⇒ 0.
    """
    if radio_saving_s <= 0.0:
        return math.inf if extra_cpu_s >= 0.0 else -math.inf
    if extra_cpu_s <= 0.0:
        return 0.0
    return extra_cpu_s / radio_saving_s


def winner_for_plausible_powers(
    kstar: float, plausible_kappa_max: float = PLAUSIBLE_KAPPA_MAX
) -> str:
    """Which scheme is energy-optimal across the plausible P_r/P_c band (≤ plausible max)."""
    if kstar <= 0.0:
        return "bls"                       # BLS wins even at P_r/P_c → 0
    if kstar > plausible_kappa_max:
        return "ed25519"                   # break-even needs an implausibly radio-heavy platform
    return "regime-dependent"              # crossover falls inside the plausible band


def verify_throughput_ok(t_verify_per_record_s: float, lam: float) -> bool:
    """Receiver keeps up iff t_verify(b)·Λ ≤ 1 (docs/02 T4/T5 throughput feasibility)."""
    return t_verify_per_record_s * lam <= 1.0
