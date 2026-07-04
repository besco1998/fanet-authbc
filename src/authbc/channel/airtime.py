"""802.11a OFDM airtime (docs/02 §6, P3 inlined) — the on-air time model for the emulator.

Constants (6 Mb/s base rate): T_phy=20µs, MAC+FCS header=34 B, SIFS=16µs, DIFS=34µs, slot=9µs,
ACK=14 B, propagation δ=1µs.

  Broadcast (NO ACK/SIFS/retry):  T_air(L) = T_phy + 8(L+34)/R + DIFS + δ
  Unicast (successful exchange):  T_s(L) = T_air-body + SIFS + δ + (T_phy + 8·14/R) + DIFS + δ
                                  where T_air-body = T_phy + 8(L+34)/R

The emulator uses the **broadcast** form (no ACKs on 802.11 broadcast). We implement the exact
component formulas and do NOT hard-code the docs/02 "T_fx ≈ 123µs" approximation — it matches
neither the broadcast fixed part (100.33µs) nor the unicast one (156µs). Mixing the two airtime
models is the documented scientific-integrity trap revisited at P6 (NS-3); here we keep them
separate and labelled.
"""

from __future__ import annotations

T_PHY_US = 20.0
R_BPS = 6_000_000  # 6 Mb/s base rate
MAC_HDR_B = 34
SIFS_US = 16.0
DIFS_US = 34.0
SLOT_US = 9.0
ACK_B = 14
DELTA_US = 1.0  # propagation δ


def tx_us(nbytes: int) -> float:
    """Transmission time (µs) of ``nbytes`` at R: 8·nbytes / R."""
    return 8.0 * nbytes / R_BPS * 1e6


def airtime_broadcast(payload_bytes: int) -> float:
    """Broadcast airtime for an L-byte frame payload (no ACK/SIFS/retry)."""
    return T_PHY_US + tx_us(payload_bytes + MAC_HDR_B) + DIFS_US + DELTA_US


def airtime_unicast(payload_bytes: int) -> float:
    """Successful unicast exchange time for an L-byte frame payload (with ACK)."""
    return (
        T_PHY_US + tx_us(payload_bytes + MAC_HDR_B) + SIFS_US + DELTA_US
        + (T_PHY_US + tx_us(ACK_B)) + DIFS_US + DELTA_US
    )


# Fixed parts (payload L=0) — reported for provenance; note neither is the docs' ≈123µs.
T_FX_BROADCAST_US = airtime_broadcast(0)  # 100.333…
T_FX_UNICAST_US = airtime_unicast(0)      # 156.0
