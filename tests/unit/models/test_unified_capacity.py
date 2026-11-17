"""The unified closed-form capacity model (src/authbc/models/unified_capacity.py).

Held here, before any simulation is scored against it:
* every test vector of the specification (docs/revision/2026-11-17_unified_model_spec.md), to the
  digits shown, at IEEE 802.11a and 802.11b;
* the design law is the two-constant law rewritten in b, exactly, when the airtime is affine;
* the three design rules reduce to the plain loss target in their trivial case (r = 1, n = 1);
* the module agrees with the reference implementation (`analysis/closed_form_model.py`) on a grid.
"""
from __future__ import annotations

import importlib.util
import math
from pathlib import Path

import pytest

from authbc.models import bianchi, phy
from authbc.models import unified_capacity as uc

REPO = Path(__file__).resolve().parents[3]


def _reference():
    spec = importlib.util.spec_from_file_location("closed_form_model",
                                                  REPO / "analysis" / "closed_form_model.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestVectors80211a:
    @pytest.mark.parametrize("eps, rho, tau0_us", [(0.02, 0.43523, 143.27),
                                                   (0.05, 0.59486, 98.04),
                                                   (0.10, 0.72054, 73.89)])
    def test_the_two_constants(self, eps, rho, tau0_us) -> None:
        r, t = uc.dcf_constants(eps, uc.A80211A)
        assert round(r, 5) == rho and round(t * 1e6, 2) == tau0_us

    @pytest.mark.parametrize("nu, tf_us, p", [(1425, 304, 0.04497), (1700, 268, 0.05439)])
    def test_the_loss_at_its_fixed_point(self, nu, tf_us, p) -> None:
        assert round(uc.loss(nu, tf_us * 1e-6, uc.A80211A), 5) == p

    @pytest.mark.parametrize("f, tf_us, law, root", [(12.5, 304, 122.85, 120.64),
                                                     (50, 268, 34.47, 33.71)])
    def test_capacity_by_the_law_and_by_the_root(self, f, tf_us, law, root) -> None:
        assert round(uc.n_law(f, tf_us * 1e-6, 0.05, uc.A80211A), 2) == law
        assert round(uc.n_root(f, tf_us * 1e-6, 0.05, uc.A80211A), 2) == root


class TestVectors80211b:
    @pytest.mark.parametrize("eps, rho, tau0_us", [(0.02, 0.54796, 254.94),
                                                   (0.05, 0.70845, 186.04),
                                                   (0.10, 0.81696, 140.79)])
    def test_the_two_constants(self, eps, rho, tau0_us) -> None:
        r, t = uc.dcf_constants(eps, uc.A80211B)
        assert round(r, 5) == rho and round(t * 1e6, 2) == tau0_us

    @pytest.mark.parametrize("payload, f, tf_us, law, root", [(146, 50, 1648, 8.92, 8.95),
                                                              (173, 12.5, 1864, 29.34, 29.43)])
    def test_capacity_at_1_mbps(self, payload, f, tf_us, law, root) -> None:
        tf = uc.airtime_s(phy.DSSS_1M, payload)
        assert round(tf * 1e6) == tf_us
        assert round(uc.n_law(f, tf, 0.05, uc.A80211B), 2) == law
        assert round(uc.n_root(f, tf, 0.05, uc.A80211B), 2) == root


class TestTheAirtime:
    def test_36_bytes_of_lower_layers_and_no_difs(self) -> None:
        assert bianchi.MAC_OVH_BYTES == 36
        assert uc.airtime_s(phy.OFDM_20MHZ_6M, 173) == pytest.approx(304e-6)
        assert uc.airtime_s(phy.OFDM_20MHZ_6M, 173) == pytest.approx(
            bianchi.t_broadcast(173) - bianchi.DIFS)

    def test_the_affine_form_of_the_lean_frame(self) -> None:
        phi_t, psi_t = uc.affine_airtime(phy.OFDM_20MHZ_6M, fixed_bytes=137, per_record_bytes=9)
        assert psi_t == pytest.approx(72 / 6e6)
        assert phi_t == pytest.approx(20e-6 + (22 + 8 * (137 + 36)) / 6e6)


class TestTheDesignLaw:
    def test_it_is_the_law_rewritten_in_b(self) -> None:
        phi_t, psi_t = uc.affine_airtime(phy.OFDM_20MHZ_6M, 137, 9)
        law = uc.design_law(50.0, phi_t, psi_t, 0.05, uc.A80211A)
        for b in (1, 2, 4, 16, 64):
            assert law.n_max(b) == pytest.approx(
                uc.n_law(50.0 / b, phi_t + psi_t * b, 0.05, uc.A80211A), rel=1e-12)

    def test_the_lean_frame_saturates_near_1017_with_beta_near_29(self) -> None:
        law = uc.design_law(50.0, *uc.affine_airtime(phy.OFDM_20MHZ_6M, 137, 9), 0.05,
                            uc.A80211A)
        assert law.n_inf == pytest.approx(1017, abs=1) and law.beta == pytest.approx(29.2, abs=0.1)

    def test_the_gain_is_below_both_bounds(self) -> None:
        law = uc.design_law(50.0, *uc.affine_airtime(phy.OFDM_20MHZ_6M, 137, 9), 0.05,
                            uc.A80211A)
        for b in (2, 4, 16, 64, 1000):
            assert law.gain(b) < min(b, 1 + law.beta)
        assert law.gain(1) == pytest.approx(1.0)


class TestTheDesignRules:
    def test_a_key_record_in_every_frame_keeps_the_target(self) -> None:
        assert uc.eps_keyrecord(1, 0.05) == pytest.approx(0.05, rel=1e-9)

    @pytest.mark.parametrize("r", [2, 4, 8])
    def test_the_key_record_target_solves_its_equation(self, r) -> None:
        p = uc.eps_keyrecord(r, 0.05)
        assert (1 - p) * (1 - (1 - p) ** r) / (r * p) == pytest.approx(0.95, rel=1e-9)
        assert p < uc.eps_keyrecord(r - 1, 0.05) if r > 1 else True

    def test_the_fragment_target(self) -> None:
        assert uc.eps_fragment(1, 0.05) == pytest.approx(0.05)
        for n in (2, 3, 5):
            assert (1 - uc.eps_fragment(n, 0.05)) ** n == pytest.approx(0.95)

    @pytest.mark.parametrize("c, d, n", [(1, 0.01, 3), (3, 0.01, 8), (8, 0.001, 206),
                                         (1, 0.1, 1)])
    def test_duty_cycled_aloha(self, c, d, n) -> None:
        assert uc.n_aloha_duty(c, d, 0.05) == n
        assert n == 1 + math.floor(c * math.log(1 / 0.95) / (2 * d))


class TestTheLossExpression:
    def test_saturation_returns_total_loss(self) -> None:
        assert uc.loss(1e5, 304e-6, uc.A80211A) == 1.0

    def test_it_grows_with_the_start_rate(self) -> None:
        ps = [uc.loss(nu, 304e-6, uc.A80211A) for nu in (200, 600, 1000, 1400, 1800)]
        assert ps == sorted(ps) and ps[0] > 0

    def test_the_three_terms_add_up(self) -> None:
        terms = uc.loss_terms(1425, 304e-6, uc.A80211A)
        assert sum(terms.values()) == pytest.approx(uc.loss(1425, 304e-6, uc.A80211A), rel=1e-9)
        assert set(terms) == {"tie", "zero_backoff_after_busy", "detection_window"}


class TestAgainstTheReference:
    def test_every_function_on_a_grid(self) -> None:
        ref = _reference()
        for acc, kw in ((uc.A80211A, {}),
                        (uc.A80211B, {"W": 32, "slot": 20e-6, "difs": 50e-6, "delta": 4e-6})):
            for eps in (0.02, 0.05, 0.1):
                assert uc.dcf_constants(eps, acc) == pytest.approx(ref.dcf_constants(eps, **kw),
                                                                   rel=1e-12)
            for tf in (200e-6, 304e-6, 600e-6, 1648e-6):
                for nu in (100, 500, 1000):
                    assert uc.loss(nu, tf, acc) == pytest.approx(ref.loss(nu, tf, **kw), abs=1e-6)
                for f in (12.5, 50):
                    assert uc.n_law(f, tf, 0.05, acc) == pytest.approx(
                        ref.n_law(f, tf, 0.05, **kw), rel=1e-12)
                    assert uc.n_root(f, tf, 0.05, acc) == pytest.approx(
                        ref.n_root(f, tf, 0.05, **kw), rel=1e-9)
