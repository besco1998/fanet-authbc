"""Airtime against hand-computed values (docs/02 §6). Arithmetic shown per case.

Since decision D9 airtime is quantised to whole 4 µs OFDM symbols and the MAC overhead is the
real 36 B (LLC/SNAP 8 + MAC header 24 + FCS 4), so every value below is
`20 + 4·ceil((16 + 8·(L+36) + 6)/24) + interframe`, computed by hand per case.
"""

from __future__ import annotations

import math

import pytest

from authbc.channel import airtime


def _symbols(nbytes: int) -> int:
    """Whole OFDM symbols for an nbytes PSDU at 6 Mb/s (24 bits/symbol)."""
    return math.ceil((16 + 8 * nbytes + 6) / 24)


def test_ppdu_us_is_quantised_to_whole_symbols() -> None:
    # A 14 B ACK needs ceil((16+112+6)/24) = ceil(5.58) = 6 symbols ⇒ 20 + 24 = 44 µs,
    # NOT the continuous 20 + 112/6 = 38.67 µs. Measured at exactly 44 000 ns in NS-3.
    assert _symbols(14) == 6
    assert airtime.ppdu_us(14) == pytest.approx(44.0)
    # 1436 B (a 1400 B payload) ⇒ 480 symbols ⇒ 1940 µs. Also measured exactly in NS-3.
    assert _symbols(1436) == 480
    assert airtime.ppdu_us(1436) == pytest.approx(1940.0)


def test_broadcast_hand_values() -> None:
    # T_air(L) = PPDU(L+36) + DIFS, DIFS = 34 µs
    # L=0:    MPDU 36   -> 13 symbols  -> 20 + 52   + 34 = 106
    assert airtime.airtime_broadcast(0) == pytest.approx(20 + 4 * 13 + 34)
    assert airtime.airtime_broadcast(0) == pytest.approx(106.0)
    # L=100:  MPDU 136  -> 47 symbols  -> 20 + 188  + 34 = 242
    assert airtime.airtime_broadcast(100) == pytest.approx(242.0)
    # L=1500: MPDU 1536 -> 513 symbols -> 20 + 2052 + 34 = 2106
    assert airtime.airtime_broadcast(1500) == pytest.approx(2106.0)


def test_unicast_hand_values() -> None:
    # T_s(L) = PPDU(L+36) + SIFS + ACK + DIFS = PPDU(L+36) + 16 + 44 + 34
    # L=0:   72  + 94 = 166
    assert airtime.airtime_unicast(0) == pytest.approx(166.0)
    # L=100: 208 + 94 = 302
    assert airtime.airtime_unicast(100) == pytest.approx(302.0)


def test_broadcast_below_unicast_by_exactly_sifs_plus_ack() -> None:
    """Broadcast never ACKs, so it is cheaper by SIFS + T_ack = 60 µs at EVERY payload."""
    for length in (0, 100, 500, 1500):
        assert airtime.airtime_broadcast(length) < airtime.airtime_unicast(length)
        assert airtime.airtime_unicast(length) - airtime.airtime_broadcast(length) == (
            pytest.approx(airtime.SIFS_US + 44.0))
    assert airtime.T_BROADCAST_L0_US == pytest.approx(106.0)
    assert airtime.T_UNICAST_L0_US == pytest.approx(166.0)


def test_airtime_is_a_step_function_not_a_line() -> None:
    """The defining property of the D9 change: adding one byte usually costs nothing, then
    jumps a whole 4 µs symbol. A linear model cannot represent this."""
    steps = {airtime.airtime_broadcast(length) for length in range(100, 104)}
    assert len(steps) < 4, "consecutive payload sizes must share symbol counts"
    jumps = {round(airtime.airtime_broadcast(x + 1) - airtime.airtime_broadcast(x), 6)
             for x in range(100, 130)}
    assert jumps <= {0.0, 4.0}, "every increment is either free or exactly one OFDM symbol"
