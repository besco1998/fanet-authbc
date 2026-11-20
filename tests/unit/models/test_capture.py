"""Capture in the loss expression, (G22)–(G24) (src/authbc/models/capture.py).

Held here:
* the test vectors of `docs/prompts/NEXT_PHASE_PROMPT.md` §3: the law with ε′ for Rayleigh
  fading at equal mean power, θ = 4 and 10 dB, 802.11a;
* the trivial cases: q = 0 and ℓ = 0 return the plain target, and identical senders make both
  criteria equal;
* the three closed forms for q against each other, and (1 + θ)^−(k−1) against a seeded draw.
"""
from __future__ import annotations

import numpy as np
import pytest

from authbc.models import capture as cp
from authbc.models import unified_capacity as uc


class TestVectors:
    @pytest.mark.parametrize("theta_db, tf_us, f, law", [(4.0, 304, 12.5, 141.0),
                                                         (4.0, 268, 50.0, 39.6),
                                                         (10.0, 304, 12.5, 127.9),
                                                         (10.0, 268, 50.0, 35.9)])
    def test_the_law_with_eps_prime(self, theta_db, tf_us, f, law) -> None:
        q = cp.q_rayleigh_equal(cp.db_to_ratio(theta_db))
        eps_p = cp.eps_average(0.05, 0.0, q)
        assert round(uc.n_law(f, tf_us * 1e-6, eps_p, uc.A80211A), 1) == law


class TestCriteria:
    def test_no_capture_and_no_link_loss_is_the_plain_target(self) -> None:
        assert cp.eps_average(0.05, 0.0, 0.0) == 0.05
        assert cp.eps_every_sender(0.05, [0.0, 0.0], [0.0, 0.0]) == 0.05
        assert cp.loss_with_capture(0.05, 0.0, 0.0) == 0.05

    def test_identical_senders_make_both_criteria_equal(self) -> None:
        assert cp.eps_every_sender(0.05, [0.01] * 4, [0.3] * 4) == pytest.approx(
            cp.eps_average(0.05, 0.01, 0.3))

    def test_the_worst_sender_sets_the_every_sender_target(self) -> None:
        ew = cp.eps_every_sender(0.05, [0.0, 0.02], [0.5, 0.1])
        assert ew == pytest.approx((0.05 - 0.02) / 0.9)
        assert ew < cp.eps_average(0.05, 0.01, 0.3)

    def test_the_criterion_inverts_g22(self) -> None:
        eps_p = cp.eps_average(0.05, 0.004, 0.25)
        assert cp.loss_with_capture(eps_p, 0.25, 0.004) == pytest.approx(0.05)

    def test_rejects_certain_capture(self) -> None:
        with pytest.raises(ValueError):
            cp.eps_average(0.05, 0.0, 1.0)


class TestClosedFormsForQ:
    def test_path_loss_at_equal_distances_is_the_equal_power_form(self) -> None:
        th = cp.db_to_ratio(4.0)
        assert cp.q_rayleigh_pathloss(th, 3.0, 10.0, [10.0, 10.0]) == pytest.approx(
            cp.q_rayleigh_equal(th))

    def test_no_fading_is_a_distance_threshold(self) -> None:
        th = cp.db_to_ratio(6.0)          # θ^(1/2) ≈ 1.995 at α = 2
        assert cp.q_no_fading(th, 2.0, 1.0, [1.5, 2.1, 3.0, 1.9]) == 0.5

    def test_k_frames_against_a_seeded_draw(self) -> None:
        rng, th, k, n = np.random.default_rng(20261120), cp.db_to_ratio(4.0), 3, 400_000
        draws = rng.exponential(size=(n, k))
        hit = float(np.mean(draws[:, 0] > th * draws[:, 1:].sum(axis=1)))
        q = cp.q_rayleigh_equal(th, k)
        assert abs(hit - q) < 4 * np.sqrt(q * (1 - q) / n)


def test_ns3s_threshold_is_4_db() -> None:
    assert cp.THETA_NS3 == pytest.approx(cp.db_to_ratio(4.0))
    # Rayleigh at equal mean power, two frames: q = 1/(1 + 10^0.4) under ns-3's rule
    assert cp.q_rayleigh_equal(cp.THETA_NS3) == pytest.approx(0.2847, abs=1e-4)
