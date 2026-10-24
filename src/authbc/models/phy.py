"""OFDM PHY timing as a parameter, so capacity can be asked about other rates (docs/02 §6c).

`models/bianchi.py` hard-codes 802.11a at 6 Mb/s because that is the configuration the broadcast
model was validated at (NS-3, 30 seeds, ≤ 0.51 %). Every published capacity figure uses it, and
nothing here changes it: `OFDM_20MHZ_6M` reproduces `bianchi.t_broadcast` and
`optimizer.channel_utilisation` exactly (`tests/unit/models/test_phy.py`).

This module exists to answer a reviewer's question — *is 6 Mb/s a special case?* — without
pretending to more than a model can give. ⚠️ **The broadcast model is validated at 6 Mb/s on a
20 MHz channel only.** Results at any other rate or channel width are the same closed form with
different timing constants: predictions, not validated results, and they must be labelled so.

Timing constants are IEEE 802.11-2016 Table 17-21 / 17-4 / 17-5, read from the ns-3.48 source that
implements them (`wifi-standard-constants.h`, `ofdm-phy.cc`):

    channel   SIFS    slot    preamble   SIGNAL   symbol   rates (Mb/s)
    20 MHz    16 µs    9 µs    16 µs      4 µs     4 µs    6 … 54
    10 MHz    32 µs   13 µs    32 µs      8 µs     8 µs    3 … 27   (802.11p)
"""

from __future__ import annotations

from dataclasses import dataclass

from authbc.models import bianchi, broadcast_dcf

_SERVICE_TAIL_BITS: int = bianchi.SERVICE_BITS + bianchi.TAIL_BITS


@dataclass(frozen=True)
class OfdmPhy:
    """An OFDM PHY: one data rate on one channel width."""

    name: str
    rate_bps: float
    symbol_s: float
    preamble_signal_s: float     # PHY preamble + SIGNAL field
    sifs_s: float
    slot_s: float

    def __post_init__(self) -> None:
        if min(self.rate_bps, self.symbol_s, self.preamble_signal_s, self.sifs_s,
               self.slot_s) <= 0:
            raise ValueError("PHY timing constants must be > 0")

    @property
    def difs_s(self) -> float:
        """DIFS = SIFS + 2 slots (802.11-2016 §10.3.2.3)."""
        return self.sifs_s + 2.0 * self.slot_s

    def ppdu_s(self, psdu_bytes: float) -> float:
        """PPDU duration: preamble + SIGNAL + a whole number of OFDM symbols."""
        bits_per_symbol = self.rate_bps * self.symbol_s
        # the same ceiling-by-floor-division `bianchi.ofdm_ppdu` uses, so the two cannot disagree
        # by a symbol at an exact multiple
        n_symbols = -(-(_SERVICE_TAIL_BITS + 8.0 * psdu_bytes) // bits_per_symbol)
        return self.preamble_signal_s + n_symbols * self.symbol_s

    def t_broadcast(self, payload_bytes: float) -> float:
        """Channel-busy time of one broadcast frame: PPDU(payload + MAC overhead) + DIFS."""
        return self.ppdu_s(bianchi.mpdu_bytes(payload_bytes)) + self.difs_s

    def fixed_cost_s(self, w0: int = bianchi.W) -> float:
        """Channel time a frame costs before it carries a single payload byte.

        Preamble and SIGNAL, the MAC/LLC overhead and the SERVICE and TAIL bits at this rate, DIFS,
        and the mean backoff of a station that never doubles its window.
        """
        overhead_bits = 8.0 * bianchi.MAC_OVH_BYTES + _SERVICE_TAIL_BITS
        return (self.preamble_signal_s + overhead_bits / self.rate_bps + self.difs_s
                + (w0 - 1) / 2.0 * self.slot_s)


def ofdm_20mhz(rate_mbps: float) -> OfdmPhy:
    """802.11a on a 20 MHz channel."""
    return OfdmPhy(f"20 MHz, {rate_mbps:g} Mb/s", rate_mbps * 1e6, symbol_s=4e-6,
                   preamble_signal_s=20e-6, sifs_s=16e-6, slot_s=9e-6)


def ofdm_10mhz(rate_mbps: float) -> OfdmPhy:
    """802.11p on a 10 MHz channel: every interval of the 20 MHz PHY doubled, slot 13 µs."""
    return OfdmPhy(f"10 MHz, {rate_mbps:g} Mb/s", rate_mbps * 1e6, symbol_s=8e-6,
                   preamble_signal_s=40e-6, sifs_s=32e-6, slot_s=13e-6)


OFDM_20MHZ_6M: OfdmPhy = ofdm_20mhz(6)


def channel_utilisation(phy: OfdmPhy, n_local: int, lam: float, batch: int, frame_bytes: float,
                        *, w0: int = bianchi.W) -> float:
    """Offered frames over saturation-deliverable frames, at this PHY (cf. `optimizer`)."""
    if n_local < 1 or lam <= 0 or batch < 1 or frame_bytes <= 0:
        raise ValueError("channel_utilisation needs n_local≥1, lam>0, batch≥1, frame_bytes>0")
    solved = broadcast_dcf.solve(n_local, frame_bytes, phy.t_broadcast(frame_bytes), w0=w0,
                                 slot_s=phy.slot_s)
    return (n_local * lam / batch) / (solved.throughput_bps / (8.0 * frame_bytes))


def n_max(phy: OfdmPhy, lam: float, batch: int, frame_bytes: float, u_ceiling: float = 1.0,
          *, n_limit: int = 2000) -> int:
    """Largest neighbourhood whose utilisation stays at or under `u_ceiling`.

    The search stops at the first failure; that is sound because utilisation rises with N
    (`tests/test_math_audit.py::TestNmaxSearchIsSound`).
    """
    best = 0
    for n in range(2, n_limit + 1):
        if channel_utilisation(phy, n, lam, batch, frame_bytes) > u_ceiling:
            break
        best = n
    return best
