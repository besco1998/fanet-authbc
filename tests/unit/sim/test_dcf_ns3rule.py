"""The event model with ns-3.48's access rule (src/authbc/sim/dcf_ns3rule.py).

Held here, each on frames placed by hand, against the rule as read from
channel-access-manager.cc (cited in the module):
* an arrival to an idle medium is sent DIFS after it arrives, not at once;
* two arrivals within δ of each other are both sent, and both lost;
* an arrival that a start pre-empts keeps zero slots and goes DIFS after the busy period;
* an arrival to a busy medium draws 0 … W − 1 slots, counted after busy end + DIFS;
* a frame arriving just after its own station sent waits out the post-transmission backoff;
* every collision's starts fall within δ, so (with equal power) no EIFS can follow one.
"""
from __future__ import annotations

import pytest

from authbc.sim import dcf_ns3rule as m

SLOT, DIFS, W, T = 9e-6, 34e-6, 16, 300e-6
KW = {"slot_s": SLOT, "difs_s": DIFS, "w": W, "sim_time_s": 1.0}


def _run(arrivals, n=3, **kw):
    trace: list = []
    r = m.run(n, 1.0, T, arrivals=arrivals, trace=trace, **{**KW, **kw})
    return r, trace


def test_an_idle_arrival_goes_difs_after_it_arrives() -> None:
    r, trace = _run([(0.1, 0)])
    assert trace == [(pytest.approx(0.1 + DIFS), (0,), 0.0)] and r.lost == 0


def test_arrivals_within_delta_both_send_and_both_are_lost() -> None:
    r, trace = _run([(0.1, 0), (0.1 + 1e-6, 1)])
    assert trace[0][1] == (0, 1) and r.lost == 2 and r.frames == 2


def test_a_preempted_arrival_keeps_zero_slots_and_goes_difs_after_the_busy_period() -> None:
    r, trace = _run([(0.1, 0), (0.1 + 10e-6, 1)])
    assert [g[1] for g in trace] == [(0,), (1,)] and r.lost == 0
    assert trace[1][0] == pytest.approx(0.1 + DIFS + T + DIFS)


def test_an_arrival_to_a_busy_medium_draws_a_backoff_after_busy_end() -> None:
    _r, trace = _run([(0.1, 0), (0.1 + DIFS + 100e-6, 1)])
    second = trace[1][0] - (0.1 + DIFS + T + DIFS)
    k = second / SLOT
    assert abs(k - round(k)) < 1e-6 and 0 <= round(k) <= W - 1


def test_a_frame_right_after_its_own_send_waits_out_the_post_backoff() -> None:
    seen = set()
    for seed in range(1, 40):
        _r, trace = _run([(0.1, 0), (0.1 + DIFS + T + 1e-6, 0)], seed=seed)
        after_busy = trace[1][0] - (0.1 + DIFS + T + DIFS)
        k = after_busy / SLOT
        if abs(trace[1][0] - (0.1 + DIFS + T + 1e-6 + DIFS)) < 1e-12:
            seen.add("drew 0: an idle arrival, DIFS after it arrived")
            continue
        assert abs(k - round(k)) < 1e-6 and 1 <= round(k) <= W - 1
        seen.add(round(k))
    assert len(seen) > 4


def test_every_collision_falls_within_delta() -> None:
    trace: list = []
    m.run(60, 50.0, T, trace=trace, **{**KW, "sim_time_s": 2.0})
    groups = [g for g in trace if len(g[1]) > 1]
    assert groups                                   # the load is high enough to collide
    assert all(spread <= 4e-6 + 1e-12 for _t, _who, spread in groups)
