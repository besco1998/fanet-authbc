"""The own-queue rules of open item G27 (src/authbc/sim/dcf_own_queue.py; predictions/G27.md).

What is held here: that the standard setting IS the frozen model of docs/02 §6g — same counts and
the same groups of frames, in the same order — wherever the frozen model does not make a station
collide with itself (its defect, F114, not copied), so that any difference a rule makes is the
rule's;
that each rule gives one saturated sender the gap its closed form says, which is how its parameter
is set from the measured spacing; and the mechanics each rule adds. Nothing here simulates two
stations with a candidate rule at a measured load: that is the registered experiment.
"""
from __future__ import annotations

import pytest

from authbc.sim import dcf_own_queue as oq
from authbc.sim import dcf_unsaturated as frozen

AIRTIME = 1976e-6                   # the 1400 B frame on air (analysis/contention_hw.airtime_s)
MEAN_STANDARD_GAP = frozen.DIFS_S + (frozen.W0 - 1) / 2 * frozen.SLOT_S      # 101.5 µs


def _groups(module, rule: oq.OwnQueueRule | None = None, **kw) -> tuple[object, list[list[int]]]:
    seen: list[list[int]] = []
    if rule is None:
        r = module.run(on_send=seen.append, **kw)
    else:
        r = module.run(rule=rule, on_send=seen.append, **kw)
    return r, seen


def _self_collisions(groups: list[list[int]]) -> int:
    return sum(len(set(g)) < len(g) for g in groups)


class TestTheStandardSettingIsTheFrozenModel:
    @pytest.mark.parametrize("n,fps", [(2, 124), (2, 211), (3, 83), (5, 50), (10, 12.5),
                                       (30, 12.5)])
    @pytest.mark.parametrize("seed", [1, 2, 7])
    def test_same_counts_and_same_groups(self, n: int, fps: float, seed: int) -> None:
        kw = dict(n_nodes=n, frames_per_s=fps, airtime_s=AIRTIME, seed=seed, sim_time_s=4.0)
        old, old_groups = _groups(frozen, **kw)
        assert _self_collisions(old_groups) == 0      # else the defect is in play: see below
        new, new_groups = _groups(oq, oq.STANDARD, **kw)
        assert (new.frames, new.lost, new.lost_to_ties, new.deferred) == \
            (old.frames, old.lost, old.lost_to_ties, old.deferred)
        assert new_groups == old_groups

    @pytest.mark.parametrize("w0", [1, 4, 8, 32])
    def test_other_windows_and_a_fixed_phase(self, w0: int) -> None:
        kw = dict(n_nodes=4, frames_per_s=100, airtime_s=AIRTIME, seed=3, sim_time_s=4.0)
        old, old_groups = _groups(frozen, w0=w0, redraw_phase=False, **kw)
        new, new_groups = _groups(oq, oq.OwnQueueRule(w_post=w0, w_defer=w0),
                                  redraw_phase=False, **kw)
        assert (new.frames, new.lost, new.lost_to_ties, new.deferred) == \
            (old.frames, old.lost, old.lost_to_ties, old.deferred)
        assert new_groups == old_groups

    @pytest.mark.parametrize("rule", [oq.OwnQueueRule(q_zero=0.0), oq.OwnQueueRule(q_burst=0.0),
                                      oq.OwnQueueRule(slot_s=9e-6),
                                      oq.OwnQueueRule(redraw_on_defer=True)])
    def test_each_rule_at_its_neutral_value_is_the_standard(self, rule: oq.OwnQueueRule) -> None:
        # redraw_on_defer with w_post = w_defer redraws from the same window: the counts move
        # with the extra draws but the law does not, so it is held by its mean, not bit for bit
        kw = dict(n_nodes=2, frames_per_s=211, airtime_s=AIRTIME, seed=5, sim_time_s=4.0)
        old = frozen.run(**kw)
        new = oq.run(rule=rule, **kw)
        if rule.redraw_on_defer:
            assert abs(new.loss - old.lost / old.frames) < 0.01
        else:
            assert (new.frames, new.lost, new.deferred) == (old.frames, old.lost, old.deferred)

    def test_the_frozen_models_defect_is_not_copied(self) -> None:
        # F114. Two saturated stations: the frozen model makes a station collide with itself;
        # this module never does, and agrees with it bit for bit up to the first time it did
        kw = dict(n_nodes=2, frames_per_s=400, airtime_s=AIRTIME, seed=1, sim_time_s=6.0)
        _old, old_groups = _groups(frozen, **kw)
        _new, new_groups = _groups(oq, oq.STANDARD, **kw)
        first = next(k for k, g in enumerate(old_groups) if len(set(g)) < len(g))
        assert _self_collisions(old_groups) > 0 and _self_collisions(new_groups) == 0
        assert new_groups[:first] == old_groups[:first]

    def test_one_station_alone_never_collides(self) -> None:
        # four counted seconds at one frame per 2077.5 µs: 1925 frames
        r = oq.run(1, 900, AIRTIME, seed=1, sim_time_s=5.0, count_until_s=5.0)
        assert r.lost == 0
        assert r.frames == pytest.approx(4.0 / (AIRTIME + MEAN_STANDARD_GAP), rel=0.01)

    def test_the_count_window_only_trims(self) -> None:
        kw = dict(n_nodes=2, frames_per_s=400, airtime_s=AIRTIME, seed=1, sim_time_s=6.0)
        whole = oq.run(**kw)
        trimmed = oq.run(count_until_s=6.0, **kw)
        assert 0 < trimmed.frames < whole.frames          # the drain after 6 s is left out
        assert trimmed.last_start_s < 6.0 <= whole.last_start_s


class TestOneSaturatedSender:
    """How a parameter is set: the closed form of the gap after a frame, checked by simulation."""

    def test_the_standard_gap(self) -> None:
        gap = oq.mean_gap_after_frame_s(oq.STANDARD, AIRTIME, seeds=4)
        assert gap == pytest.approx(MEAN_STANDARD_GAP, abs=1e-6)

    @pytest.mark.parametrize("w", [3, 10])
    def test_a_smaller_window(self, w: int) -> None:
        rule = oq.OwnQueueRule(w_post=w, w_defer=w)
        expected = frozen.DIFS_S + (w - 1) / 2 * frozen.SLOT_S
        assert oq.mean_gap_after_frame_s(rule, AIRTIME, seeds=4) == pytest.approx(expected,
                                                                                    abs=1e-6)

    def test_a_smaller_window_after_the_own_frame_only_is_the_same_alone(self) -> None:
        a = oq.OwnQueueRule(w_post=10, w_defer=10)
        b = oq.OwnQueueRule(w_post=10, w_defer=oq.W0, redraw_on_defer=True)
        assert oq.mean_gap_after_frame_s(a, AIRTIME, seeds=3) == \
            pytest.approx(oq.mean_gap_after_frame_s(b, AIRTIME, seeds=3), abs=1e-6)

    @pytest.mark.parametrize("q", [0.41, 0.84])
    def test_a_share_of_zero_counters(self, q: float) -> None:
        expected = frozen.DIFS_S + (1 - q) * (frozen.W0 - 1) / 2 * frozen.SLOT_S
        assert oq.mean_gap_after_frame_s(oq.OwnQueueRule(q_zero=q), AIRTIME) == \
            pytest.approx(expected, abs=1e-6)

    @pytest.mark.parametrize("q", [0.32, 0.66])
    def test_a_burst(self, q: float) -> None:
        expected = q * oq.SIFS_S + (1 - q) * MEAN_STANDARD_GAP
        assert oq.mean_gap_after_frame_s(oq.OwnQueueRule(q_burst=q), AIRTIME) == \
            pytest.approx(expected, abs=1e-6)

    @pytest.mark.parametrize("slot", [1.44e-6, 5.31e-6])
    def test_a_shorter_slot(self, slot: float) -> None:
        expected = frozen.DIFS_S + (frozen.W0 - 1) / 2 * slot
        assert oq.mean_gap_after_frame_s(oq.OwnQueueRule(slot_s=slot), AIRTIME, seeds=4) == \
            pytest.approx(expected, abs=1e-6)


class TestTheMechanics:
    def test_a_burst_cannot_be_joined(self) -> None:
        # with a burst share near 1 one station holds the medium: the other rarely gets in
        r = oq.run(2, 400, AIRTIME, rule=oq.OwnQueueRule(q_burst=0.99), seed=1, sim_time_s=3.0,
                   count_until_s=3.0)
        assert r.burst_frames > 0.9 * r.frames

    def test_a_zero_counter_is_sent_at_difs(self) -> None:
        # every post-transmission counter at 0: one sender's gap is DIFS exactly
        gap = oq.mean_gap_after_frame_s(oq.OwnQueueRule(q_zero=1.0), AIRTIME, seeds=1)
        assert gap == pytest.approx(frozen.DIFS_S, abs=1e-9)

    def test_a_redraw_needs_another_stations_frame(self) -> None:
        # alone, nothing interrupts a counter: the rule cannot act (held above by the gap); with
        # two saturated stations it does, and moves the outcome. W = 2 is not a registered value.
        kw = dict(n_nodes=2, frames_per_s=400, airtime_s=AIRTIME, seed=4, sim_time_s=5.0,
                  count_until_s=5.0)
        small = oq.run(rule=oq.OwnQueueRule(w_post=2, w_defer=2), **kw)
        redraw = oq.run(rule=oq.OwnQueueRule(w_post=2, w_defer=oq.W0, redraw_on_defer=True),
                        **kw)
        assert redraw.loss != small.loss

    def test_a_shorter_slot_lets_more_counters_through_the_detection_window(self) -> None:
        # slot 1 µs, window 4 µs: counters 1-3 apart cannot hear each other
        kw = dict(n_nodes=2, frames_per_s=400, airtime_s=AIRTIME, seed=1, sim_time_s=5.0,
                  count_until_s=5.0)
        assert oq.run(rule=oq.OwnQueueRule(slot_s=1e-6), **kw).loss > \
            2 * oq.run(**kw).loss

    def test_frames_by_node_add_up(self) -> None:
        r = oq.run(3, 150, AIRTIME, seed=9, sim_time_s=3.0)
        assert sum(r.frames_by_node) == r.frames and len(r.frames_by_node) == 3


class TestBadParameters:
    @pytest.mark.parametrize("kw", [dict(w_post=0), dict(w_defer=0), dict(q_zero=1.5),
                                    dict(q_burst=1.0), dict(q_burst=-0.1), dict(slot_s=0.0)])
    def test_a_rule_out_of_range(self, kw: dict) -> None:
        with pytest.raises(ValueError):
            oq.OwnQueueRule(**kw)

    @pytest.mark.parametrize("args", [(0, 100, AIRTIME), (2, 0, AIRTIME), (2, 100, 0.0)])
    def test_a_run_out_of_range(self, args: tuple) -> None:
        with pytest.raises(ValueError):
            oq.run(*args)
