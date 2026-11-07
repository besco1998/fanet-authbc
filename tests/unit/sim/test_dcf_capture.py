"""The capture rule on top of the access-rule model (`authbc.sim.dcf_capture`, docs/02 §6h).

Held here: that the hook it uses leaves the access-rule model's results untouched, and that the
rule is the one stated — a lone frame reaches everyone; of frames that start together a
receiver keeps the strongest if it is 4 dB above the rest; a sender receives nothing.
"""
from __future__ import annotations

import math

import pytest

from authbc.sim import dcf_capture as capture
from authbc.sim import dcf_unsaturated as access

AIR = 268e-6


class TestTheHookObservesAndChangesNothing:
    @pytest.mark.parametrize("n, fps, seed", [(20, 50.0, 1), (40, 50.0, 3), (90, 12.5, 2)])
    def test_a_run_is_the_same_with_and_without_it(self, n: int, fps: float, seed: int) -> None:
        groups: list[list[int]] = []
        assert access.run(n, fps, AIR, seed=seed, on_send=groups.append) == \
            access.run(n, fps, AIR, seed=seed)

    def test_it_sees_every_frame_and_every_collision(self) -> None:
        groups: list[list[int]] = []
        r = access.run(40, 50.0, AIR, seed=3, on_send=groups.append)
        assert sum(map(len, groups)) == r.frames
        assert sum(len(g) for g in groups if len(g) > 1) == r.lost
        assert all(len(set(g)) == len(g) for g in groups)


class TestTheCaptureRule:
    # four stations on a line: 0 and 1 a metre apart, 2 far to the right, 3 between
    POINTS = [(0.0, 0.0), (1.0, 0.0), (100.0, 0.0), (50.5, 0.0)]
    GAIN = capture.gains(POINTS)
    RATIO = 10 ** 0.4

    def test_a_lone_frame_reaches_every_other_station(self) -> None:
        assert capture.received([2], self.GAIN, self.RATIO) == 3

    def test_the_nearer_of_two_senders_is_received_where_it_is_strong_enough(self) -> None:
        """0 and 2 send. Station 1 is a metre from 0 and 99 m from 2: it keeps 0's frame.
        Station 3 is 50.5 m from 0 and 49.5 m from 2: neither is 4 dB above the other."""
        assert capture.received([0, 2], self.GAIN, self.RATIO) == 1

    def test_a_sender_receives_nothing_while_it_sends(self) -> None:
        assert capture.received([0, 1, 2, 3], self.GAIN, self.RATIO) == 0

    def test_the_threshold_is_four_decibels_of_power(self) -> None:
        """Two senders at distances d and 1.585 d from a receiver differ by exactly 4 dB."""
        d = 10.0
        points = [(0.0, 0.0), (-d, 0.0), (d * 10 ** 0.2, 0.0)]
        gain = capture.gains(points)
        assert gain[1][0] / gain[2][0] == pytest.approx(10 ** 0.4)
        assert capture.received([1, 2], gain, 10 ** 0.4 * 0.999) == 1
        assert capture.received([1, 2], gain, 10 ** 0.4 * 1.001) == 0
        assert capture.THRESHOLD_DB == 4.0 and capture.EXPONENT == 2.0

    def test_distances_under_the_reference_metre_count_as_one_metre(self) -> None:
        gain = capture.gains([(0.0, 0.0), (0.2, 0.0), (3.0, 0.0)])
        assert gain[0][1] == 1.0 and gain[0][2] == pytest.approx(1 / 9)


class TestPlacementAndARun:
    def test_points_are_inside_the_disc_and_repeat_with_the_seed(self) -> None:
        points = capture.positions(500, 15.0, seed=7)
        assert all(math.hypot(x, y) <= 15.0 for x, y in points)
        assert points == capture.positions(500, 15.0, seed=7) != capture.positions(500, 15.0, 8)
        # uniform in area: about a quarter of the points within half the radius
        assert 0.2 < sum(math.hypot(x, y) <= 7.5 for x, y in points) / 500 < 0.3

    def test_capture_can_only_add_receptions_to_the_equal_power_run(self) -> None:
        for seed in (1, 2, 3):
            with_capture = capture.run(40, 50.0, AIR, radius_m=15.0, seed=seed)
            assert with_capture >= access.run(40, 50.0, AIR, seed=seed).delivered_frac

    def test_with_an_unreachable_threshold_it_is_the_equal_power_run_less_the_senders(
            self) -> None:
        """No frame of a collision is ever kept: every collided frame is lost everywhere."""
        seed = 4
        no_capture = capture.run(40, 50.0, AIR, radius_m=15.0, seed=seed, threshold_db=300.0)
        assert no_capture == pytest.approx(access.run(40, 50.0, AIR, seed=seed).delivered_frac)

    def test_the_radius_does_not_matter_in_free_space_but_for_the_reference_metre(self) -> None:
        a = capture.run(40, 50.0, AIR, radius_m=15.0, seed=2)
        b = capture.run(40, 50.0, AIR, radius_m=100.0, seed=2)
        assert a == pytest.approx(b, abs=2e-3)
