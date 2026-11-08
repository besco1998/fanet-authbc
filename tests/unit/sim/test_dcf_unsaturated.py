"""The access-rule simulator of docs/02 §6g: what must be true of it whatever ns-3 says.

Its agreement with ns-3 is an artifact (`results/raw/dcf_model_vs_ns3.csv`), held elsewhere.
These hold the rule itself: every frame is sent exactly once, the two ways of losing a frame are
the only two, and each responds to the one constant that governs it.
"""

from __future__ import annotations

import pytest

from authbc.sim import dcf_unsaturated as du

AIRTIME = 268e-6            # a 146 B payload at 6 Mb/s
BUSY = dict(n_nodes=35, frames_per_s=50.0, airtime_s=AIRTIME, sim_time_s=6.0)


class TestBookkeeping:
    def test_every_frame_is_sent_exactly_once(self) -> None:
        assert du.run(seed=3, warmup_s=0.0, **BUSY).frames == 35 * 50 * 6

    def test_the_warm_up_is_left_out_of_the_count(self) -> None:
        """Counted by the instant a frame is sent, so a frame or two straddle the boundary."""
        assert abs(du.run(seed=3, **BUSY).frames - 35 * 50 * (6 - 1)) <= 3

    def test_a_run_is_a_function_of_its_seed(self) -> None:
        assert du.run(seed=7, **BUSY) == du.run(seed=7, **BUSY)
        assert du.run(seed=7, **BUSY) != du.run(seed=8, **BUSY)

    def test_lost_frames_come_in_groups_of_two_or_more(self) -> None:
        r = du.run(seed=1, **BUSY)
        assert 0 < r.lost_to_ties <= r.lost < r.frames
        assert r.delivered_frac == pytest.approx(1 - r.lost / r.frames)

    @pytest.mark.parametrize("bad", [dict(n_nodes=1), dict(frames_per_s=0.0),
                                     dict(airtime_s=0.0), dict(w0=0)])
    def test_impossible_inputs_are_refused(self, bad: dict) -> None:
        with pytest.raises(ValueError):
            du.run(**(BUSY | bad))


class TestTheTwoWaysToLoseAFrame:
    def test_two_stations_far_apart_in_time_lose_nothing(self) -> None:
        r = du.run(2, 1.0, AIRTIME, sim_time_s=60.0, seed=1)
        assert (r.lost, r.deferred) == (0, 0)

    def test_without_a_detection_window_every_loss_is_a_tie(self) -> None:
        r = du.run(seed=1, detect_s=0.0, **BUSY)
        assert r.lost == r.lost_to_ties > 0

    def test_a_contention_window_of_one_slot_makes_every_deferral_a_possible_tie(self) -> None:
        narrow, wide = (sum(du.run(seed=s, w0=w, **BUSY).lost_to_ties for s in (1, 2, 3))
                        for w in (2, 64))
        assert narrow > 8 * wide

    def test_doubling_the_window_roughly_halves_the_ties_and_leaves_the_rest(self) -> None:
        def losses(w0: int) -> tuple[int, int]:
            runs = [du.run(seed=s, w0=w0, **BUSY) for s in range(1, 9)]
            return (sum(r.lost_to_ties for r in runs),
                    sum(r.lost - r.lost_to_ties for r in runs))

        (ties16, rest16), (ties32, rest32) = losses(16), losses(32)
        assert 0.4 < ties32 / ties16 < 0.65
        assert 0.8 < rest32 / rest16 < 1.25

    def test_the_share_that_defers_is_the_share_of_time_the_medium_is_held(self) -> None:
        """A frame defers when it arrives during another frame or the DIFS after it."""
        runs = [du.run(seed=s, **BUSY) for s in (1, 2, 3)]
        deferred = sum(r.deferred for r in runs) / sum(r.frames for r in runs)
        held = 34 * 50.0 * (AIRTIME + du.DIFS_S)
        assert deferred == pytest.approx(held, rel=0.06)

    def test_loss_grows_with_the_neighbourhood(self) -> None:
        delivered = [du.mean_delivered(n, 50.0, AIRTIME, seeds=4, sim_time_s=6.0)
                     for n in (20, 35, 50)]
        assert delivered[0] > delivered[1] > delivered[2]


class TestFrozenPhases:
    def test_strictly_periodic_senders_are_far_more_variable_between_runs(self) -> None:
        """The reason the reported capacities redraw the send time (F51), seen without ns-3."""
        import statistics as st

        spread = {redraw: st.pstdev(du.run(seed=s, redraw_phase=redraw, **BUSY).delivered_frac
                                    for s in range(1, 13)) for redraw in (True, False)}
        assert spread[False] > 4 * spread[True]
