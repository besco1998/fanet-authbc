"""(G25), the periodic-source loss (src/authbc/models/periodic_capacity.py).

Held here, before any ns-3 cell is scored against it:
* every test vector of `docs/prompts/NEXT_PHASE_PROMPT.md` §3, to the digits shown;
* R tends to 1 (the Poisson case) as the number of other stations grows, and the asymptotic
  series joins the exact form without a step;
* without the ratio, the loss is (G5) unchanged;
* the module agrees with Mohamed's reference (`analysis/periodic_model.py`) on a grid.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from authbc.models import periodic_capacity as pc
from authbc.models import phy
from authbc.models import unified_capacity as uc

REPO = Path(__file__).resolve().parents[3]
B = uc.A80211B
B_KW = {"W": 32, "slot": 20e-6, "difs": 50e-6}


def _reference():
    spec = importlib.util.spec_from_file_location("periodic_model",
                                                  REPO / "analysis" / "periodic_model.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _tf_b(payload: int) -> float:
    """802.11b at 1 Mb/s with the long preamble: 192 µs + 8(ℓ + 36)/R."""
    return 192e-6 + 8 * (payload + 36) / 1e6


class TestVectors:
    @pytest.mark.parametrize("n, rho, r", [(8, 0.678, 0.6263), (28, 0.743, 0.7470),
                                           (120, 0.536, 0.9651)])
    def test_the_ratio(self, n, rho, r) -> None:
        assert round(pc.r_bb(n, rho), 4) == r

    def test_the_airtime_of_the_802_11b_vectors(self) -> None:
        assert uc.airtime_s(phy.DSSS_1M, 173) == pytest.approx(1864e-6, abs=1e-12)
        assert uc.airtime_s(phy.DSSS_1M, 146) == pytest.approx(_tf_b(146), abs=1e-12)

    def test_the_loss_at_802_11b_periodic_and_poisson(self) -> None:
        tf = _tf_b(173)
        assert round(pc.loss_periodic(29, 12.5, tf, B), 5) == 0.04093
        assert round(uc.loss(28 * 12.5, tf, B), 5) == 0.04752

    def test_capacity_at_802_11b_design_frame(self) -> None:
        tf = _tf_b(173)
        assert round(pc.n_root_periodic(12.5, tf, 0.05, B), 2) == 30.84
        assert round(uc.n_root(12.5, tf, 0.05, B), 2) == 29.43

    def test_capacity_at_802_11b_base_frame(self) -> None:
        assert round(pc.n_root_periodic(50, _tf_b(146), 0.05, B), 2) == 9.89

    def test_capacity_at_802_11a_design_frame(self) -> None:
        tf = uc.airtime_s(phy.OFDM_20MHZ_6M, 173)
        assert round(pc.n_root_periodic(12.5, tf, 0.05, uc.A80211A), 2) == 121.43
        assert round(uc.n_root(12.5, tf, 0.05, uc.A80211A), 2) == 120.64


class TestProperties:
    def test_the_ratio_tends_to_poisson_with_many_stations(self) -> None:
        assert pc.r_bb(1e6, 0.5) == pytest.approx(1.0, abs=1e-5)

    def test_the_ratio_lies_in_zero_one(self) -> None:
        for n in (1, 2, 4, 8, 30, 120, 700):
            for rho in (0.05, 0.3, 0.6, 0.9, 0.99):
                assert 0 < pc.r_bb(n, rho) <= 1

    def test_the_asymptotic_series_joins_the_exact_form(self) -> None:
        # c = (1 − ρ)·sqrt(n/2) crosses 25 between these two n at ρ = 0.5.
        below, above = pc.r_bb(4999.9, 0.5), pc.r_bb(5000.1, 0.5)
        assert above == pytest.approx(below, rel=1e-6)

    def test_saturation_returns_one(self) -> None:
        assert pc.r_bb(10, 1.0) == 1.0

    def test_without_the_ratio_it_is_g5(self) -> None:
        for nu in (200.0, 800.0, 1500.0):
            assert uc.loss(nu, 304e-6, k_ratio=None) == uc.loss(nu, 304e-6)

    def test_periodic_is_less_lossy_than_poisson(self) -> None:
        tf = _tf_b(173)
        for n in (10, 20, 29):
            assert pc.loss_periodic(n, 12.5, tf, B) < uc.loss((n - 1) * 12.5, tf, B)

    @pytest.mark.parametrize("bad", [0.0, 1.0, -3.0])
    def test_rejects_n_not_above_one(self, bad) -> None:
        with pytest.raises(ValueError):
            pc.loss_periodic(bad, 12.5, 1e-3, B)


class TestAgreesWithTheReference:
    @pytest.mark.parametrize("n, rho", [(n, r) for n in (2, 5, 9, 31, 200)
                                        for r in (0.1, 0.45, 0.8, 0.97)])
    def test_the_ratio(self, n, rho) -> None:
        assert pc.r_bb(n, rho) == pytest.approx(_reference().R_bb(n, rho), rel=1e-12)

    @pytest.mark.parametrize("payload, f", [(73, 37.5), (146, 50), (173, 12.5), (300, 10)])
    def test_loss_and_capacity_at_802_11b(self, payload, f) -> None:
        ref, tf = _reference(), _tf_b(payload)
        for n in (5, 12, 25):
            for periodic in (True, False):
                mine = pc.loss_periodic(n, f, tf, B) if periodic else uc.loss((n - 1) * f, tf, B)
                assert mine == pytest.approx(ref.loss(n, f, tf, periodic=periodic, **B_KW),
                                             abs=1e-9)
        assert pc.n_root_periodic(f, tf, 0.05, B) == pytest.approx(
            ref.nmax(f, tf, 0.05, periodic=True, **B_KW), abs=1e-9)

    @pytest.mark.parametrize("payload, f", [(146, 50), (173, 12.5), (600, 25)])
    def test_capacity_at_802_11a(self, payload, f) -> None:
        tf = uc.airtime_s(phy.OFDM_20MHZ_6M, payload)
        assert pc.n_root_periodic(f, tf, 0.05) == pytest.approx(
            _reference().nmax(f, tf, 0.05, periodic=True), abs=1e-9)
