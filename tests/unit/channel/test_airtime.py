"""Airtime against hand-computed values (docs/02 §6). Arithmetic shown per case."""

from __future__ import annotations

import pytest

from authbc.channel import airtime

# 8·nbytes / R with R = 6 Mb/s ⇒ 8·nbytes/6 µs. tx_us(34)=272/6=45.333, tx_us(14)=112/6=18.667.


def test_tx_us() -> None:
    assert airtime.tx_us(34) == pytest.approx(272 / 6)
    assert airtime.tx_us(1500) == pytest.approx(12000 / 6)  # 2000.0 µs


def test_broadcast_hand_values() -> None:
    # T_air(L) = 20 + 8(L+34)/6 + 34 + 1
    # L=0:   20 + 272/6 + 35 = 100.3333
    assert airtime.airtime_broadcast(0) == pytest.approx(20 + 272 / 6 + 35)
    assert airtime.airtime_broadcast(0) == pytest.approx(100.33333, abs=1e-4)
    # L=100: 20 + 8·134/6 + 35 = 20 + 1072/6 + 35 = 233.6667
    assert airtime.airtime_broadcast(100) == pytest.approx(233.66667, abs=1e-4)
    # L=1500: 20 + 8·1534/6 + 35 = 20 + 12272/6 + 35 = 2100.3333
    assert airtime.airtime_broadcast(1500) == pytest.approx(2100.33333, abs=1e-4)


def test_unicast_hand_values() -> None:
    # T_s(L) = 20 + 8(L+34)/6 + 16 + 1 + (20 + 112/6) + 34 + 1
    # L=0:   20 + 45.3333 + 16 + 1 + 38.6667 + 34 + 1 = 156.0
    assert airtime.airtime_unicast(0) == pytest.approx(156.0, abs=1e-4)
    # L=100: 20 + 178.6667 + 16 + 1 + 38.6667 + 34 + 1 = 289.3333
    assert airtime.airtime_unicast(100) == pytest.approx(289.33333, abs=1e-4)


def test_broadcast_below_unicast_and_fixed_parts() -> None:
    # broadcast (no ACK/SIFS) must be cheaper than unicast for the same payload
    for L in (0, 100, 500, 1500):
        assert airtime.airtime_broadcast(L) < airtime.airtime_unicast(L)
    # documented fixed parts — neither equals the docs' ≈123µs approximation
    assert airtime.T_FX_BROADCAST_US == pytest.approx(100.33333, abs=1e-4)
    assert airtime.T_FX_UNICAST_US == pytest.approx(156.0, abs=1e-4)
