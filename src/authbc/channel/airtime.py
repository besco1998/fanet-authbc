"""802.11a OFDM airtime (docs/02 §6, P3 inlined) — the on-air time model for the emulator.

Constants (6 Mb/s base rate): T_phy=20µs, MAC overhead=36 B (LLC/SNAP 8 + MAC header 24 + FCS 4),
SIFS=16µs, DIFS=34µs, slot=9µs, ACK=14 B.

  Broadcast (NO ACK/SIFS/retry):  T_air(L) = PPDU(L+36) + DIFS
  Unicast (successful exchange):  T_s(L)   = PPDU(L+36) + SIFS + PPDU(14) + DIFS

**Airtime is quantised, not linear** (decision D9, audit A1): an 802.11a PHY sends whole 4 µs OFDM
symbols, so `PPDU(N) = T_phy + ceil((16 + 8N + 6)/24)·4µs` at 6 Mb/s. The former continuous
`8N/R` form understated a 1400 B frame by 0.41 % and an ACK by 12.1 % against NS-3 3.41. This
module therefore delegates to `models.bianchi.ofdm_ppdu` so there is exactly ONE airtime
implementation in the repo.

The emulator uses the **broadcast** form (no ACKs on 802.11 broadcast). Mixing the two airtime
models is the documented scientific-integrity trap revisited at P6 (NS-3); here we keep them
separate and labelled.
"""

from __future__ import annotations

from authbc.models import bianchi

T_PHY_US = bianchi.T_PHY * 1e6
R_BPS = bianchi.R_BPS
MAC_HDR_B = bianchi.MAC_OVH_BYTES   # 36 = LLC/SNAP 8 + MAC header 24 + FCS 4
SIFS_US = bianchi.SIFS * 1e6
DIFS_US = bianchi.DIFS * 1e6
SLOT_US = bianchi.SLOT * 1e6
ACK_B = bianchi.ACK_BYTES
DELTA_US = bianchi.DELTA * 1e6  # propagation δ (not charged: NS-3's measured gap floor is DIFS)


def ppdu_us(nbytes: float) -> float:
    """Exact 802.11a PPDU duration (µs) for an *nbytes* PSDU — whole 4 µs OFDM symbols."""
    return bianchi.ofdm_ppdu(nbytes) * 1e6


def airtime_broadcast(payload_bytes: float) -> float:
    """Broadcast airtime (µs) for an L-byte frame payload (no ACK/SIFS/retry)."""
    return bianchi.t_broadcast(payload_bytes) * 1e6


def airtime_unicast(payload_bytes: float) -> float:
    """Successful unicast exchange time (µs) for an L-byte frame payload (with ACK)."""
    return bianchi.t_success(payload_bytes) * 1e6


# Airtime is a STEP function of L, so these are the L=0 anchors only — not "fixed parts" that a
# linear term may be added to. Reported for provenance.
T_BROADCAST_L0_US = airtime_broadcast(0)
T_UNICAST_L0_US = airtime_unicast(0)
