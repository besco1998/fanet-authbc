"""OFDM PHY timing as a parameter (docs/02 §6c; review comment 4.7)."""

from __future__ import annotations

import random

import pytest

from authbc.models import bianchi, optimizer, phy


class TestTheValidatedPhyIsReproducedExactly:
    """Nothing published may move: at 20 MHz / 6 Mb/s this module IS the validated model."""

    def test_airtime_for_every_frame_size(self) -> None:
        for payload in range(1, 1501):
            assert phy.OFDM_20MHZ_6M.t_broadcast(payload) == bianchi.t_broadcast(payload)

    def test_timing_constants(self) -> None:
        p = phy.OFDM_20MHZ_6M
        assert (p.sifs_s, p.slot_s, p.preamble_signal_s, p.symbol_s) == (
            bianchi.SIFS, bianchi.SLOT, bianchi.T_PHY, bianchi.OFDM_SYMBOL)
        assert p.difs_s == pytest.approx(bianchi.DIFS)

    def test_channel_utilisation(self) -> None:
        rng = random.Random(1)
        for _ in range(200):
            n, lam = rng.randint(1, 300), rng.choice([10, 20, 50])
            b, size = rng.choice([1, 4]), rng.uniform(60, 1400)
            assert phy.channel_utilisation(phy.OFDM_20MHZ_6M, n, lam, b, size) == \
                optimizer.channel_utilisation(n, lam, b, size)

    def test_the_published_capacities(self) -> None:
        assert phy.n_max(phy.OFDM_20MHZ_6M, 50, 4, 288, 1.0) == 35
        assert phy.n_max(phy.OFDM_20MHZ_6M, 50, 4, 288, 2.435) == 100
        assert phy.n_max(phy.OFDM_20MHZ_6M, 20, 1, 174.252, 1.0) == 32


class TestOtherPhys:
    def test_the_10_mhz_channel_doubles_every_interval_but_the_slot(self) -> None:
        """802.11-2016 Table 17-21, as implemented in ns-3.48 `wifi-standard-constants.h`."""
        p = phy.ofdm_10mhz(6)
        assert (p.sifs_s, p.slot_s, p.preamble_signal_s, p.symbol_s) == (32e-6, 13e-6, 40e-6, 8e-6)
        assert p.difs_s == pytest.approx(58e-6)

    def test_a_faster_rate_shortens_the_payload_but_not_the_fixed_cost(self) -> None:
        slow, fast = phy.ofdm_20mhz(6), phy.ofdm_20mhz(24)
        assert fast.t_broadcast(288) < slow.t_broadcast(288)
        # preamble, DIFS and backoff do not shrink; only the MAC overhead bits do
        assert slow.fixed_cost_s() - fast.fixed_cost_s() == pytest.approx(
            (8 * 36 + 22) * (1 / 6e6 - 1 / 24e6))

    def test_the_fixed_cost_at_the_validated_phy(self) -> None:
        """20 + 34 + 7.5·9 µs of preamble, DIFS and mean backoff, plus 310 overhead bits."""
        assert phy.OFDM_20MHZ_6M.fixed_cost_s() == pytest.approx(173.17e-6, abs=0.01e-6)

    def test_capacity_grows_with_the_rate(self) -> None:
        ns = [phy.n_max(phy.ofdm_20mhz(r), 50, 4, 288) for r in (6, 12, 24)]
        assert ns == sorted(ns) and ns[0] == 35

    def test_guards(self) -> None:
        with pytest.raises(ValueError, match="> 0"):
            phy.OfdmPhy("bad", 0, 4e-6, 20e-6, 16e-6, 9e-6)
        with pytest.raises(ValueError, match="channel_utilisation needs"):
            phy.channel_utilisation(phy.OFDM_20MHZ_6M, 0, 50, 4, 288)
