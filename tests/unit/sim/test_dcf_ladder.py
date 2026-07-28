"""Unit tests for the slot-exact DCF reference simulator (guards src/authbc/sim/dcf_ladder.py).

The scientific contract this file pins down (Law 4/6):

1. With the post-transmission head start REMOVED, the simulator must reproduce the analytic no-ACK
   Bianchi variant. That is what makes it a fair test: it agrees with the model everywhere except
   on the one assumption under investigation.
2. With the head start present — i.e. real DCF — it must diverge sharply at large N, in the same
   direction and by the same order of magnitude as NS-3.
3. Its bookkeeping must be internally consistent and independent of the initial state.
"""

from __future__ import annotations

import math

import pytest

from authbc.models import bianchi
from authbc.sim import dcf_ladder as dl

_PERIODS = 300_000
_L = 1400.0
_T_BUSY = bianchi.T_PHY + 8 * (_L + bianchi.MAC_OVH_BYTES) / bianchi.R_BPS + bianchi.DIFS \
    + bianchi.DELTA
_RUN = {"w": bianchi.W, "busy_periods": _PERIODS, "t_busy_s": _T_BUSY,
        "slot_s": bianchi.SLOT, "payload_bytes": _L, "seed": 1}


def _bianchi_no_ack(n: int) -> tuple[float, float]:
    """(p_s, throughput_bps) of the analytic no-ACK broadcast variant — τ = 2/(W+1)."""
    tau = 2.0 / (bianchi.W + 1)
    p_tr = 1.0 - (1.0 - tau) ** n
    p_s = n * tau * (1.0 - tau) ** (n - 1) / p_tr
    e_slot = (1.0 - p_tr) * bianchi.SLOT + p_tr * _T_BUSY
    return p_s, p_tr * p_s * 8.0 * _L / e_slot


@pytest.mark.parametrize("n", [5, 10, 20, 35, 50])
def test_without_head_start_the_ladder_reproduces_bianchi(n: int) -> None:
    """The one assumption removed ⇒ simulation and analytic model must agree.

    Tolerance is 6 % relative, which is >3 Monte-Carlo standard errors on p_s at the worst point
    (N=50, p_s≈0.013 over 3e5 busy periods ⇒ σ/p_s ≈ 1.6 %). A real disagreement in the slot
    process would be a factor, not a few percent — the head-start variant below differs by 17×.
    """
    p_s_model, s_model = _bianchi_no_ack(n)
    r = dl.run(n, head_start=False, **_RUN)
    assert r.p_success == pytest.approx(p_s_model, rel=0.06)
    assert r.throughput_bps == pytest.approx(s_model, rel=0.06)


@pytest.mark.parametrize(("n", "min_ratio"), [(5, 0.9), (20, 1.2), (35, 3.0), (50, 10.0)])
def test_head_start_raises_p_success_increasingly_with_n(n: int, min_ratio: float) -> None:
    """Real DCF must beat the model, and by more as collisions come to dominate."""
    p_s_model, _ = _bianchi_no_ack(n)
    r = dl.run(n, head_start=True, **_RUN)
    assert r.p_success / p_s_model >= min_ratio


def test_head_start_success_rate_matches_the_closed_form_mechanism() -> None:
    """A success follows a collision iff exactly one collider redraws backoff 0.

    Independent hand-check of the mechanism: P(success | previous collided) = k·(1/W)·(1−1/W)^(k−1)
    at the simulated mean collision multiplicity k. Ties the simulator to an argument, not just to
    another number.
    """
    n, w = 50, bianchi.W
    r = dl.run(n, head_start=True, **_RUN)
    collided = {k: c for k, c in r.multiplicity_hist.items() if k > 1}
    k_bar = sum(k * c for k, c in collided.items()) / sum(collided.values())
    predicted = k_bar * (1.0 / w) * (1.0 - 1.0 / w) ** (k_bar - 1)
    assert r.p_success_after_collision == pytest.approx(predicted, rel=0.10)


def test_without_head_start_the_previous_period_carries_no_information() -> None:
    """Bianchi's independence assumption, stated as a test: with the head start removed, whether
    the previous busy period collided must not change the next one's success rate."""
    r = dl.run(50, head_start=False, **_RUN)
    assert r.p_success_after_collision == pytest.approx(r.p_success_after_success, rel=0.20)
    # …and with it present, a collision more than triples the next period's success chance.
    h = dl.run(50, head_start=True, **_RUN)
    assert h.p_success_after_collision > 3 * h.p_success_after_success


def test_bookkeeping_is_self_consistent() -> None:
    r = dl.run(20, head_start=True, busy_periods=5_000, w=16, seed=7)
    assert sum(r.multiplicity_hist.values()) == r.busy_periods == 5_000
    assert sum(k * c for k, c in r.multiplicity_hist.items()) == r.transmissions
    assert r.multiplicity_hist.get(1, 0) == r.successes
    assert r.mean_multiplicity == pytest.approx(r.transmissions / r.busy_periods)
    assert r.p_success == pytest.approx(r.successes / r.busy_periods)
    assert r.tau == pytest.approx(r.transmissions / (20 * (r.busy_periods + r.idle_slots)))


def test_elapsed_time_and_throughput_follow_the_slot_accounting() -> None:
    r = dl.run(10, busy_periods=1_000, t_busy_s=_T_BUSY, slot_s=bianchi.SLOT,
               payload_bytes=_L, seed=3)
    assert r.elapsed_s == pytest.approx(1_000 * _T_BUSY + r.idle_slots * bianchi.SLOT)
    assert r.throughput_bps == pytest.approx(r.successes * 8.0 * _L / r.elapsed_s)


def test_pure_slot_run_carries_no_payload_hence_no_throughput() -> None:
    """With t_busy_s=0 the only elapsed time is the idle slots, and throughput is 0."""
    r = dl.run(10, busy_periods=100, seed=1)
    assert r.throughput_bps == 0.0
    assert r.elapsed_s == pytest.approx(r.idle_slots * 9e-6)


def test_is_deterministic_under_a_seed() -> None:
    a = dl.run(20, busy_periods=2_000, seed=42)
    b = dl.run(20, busy_periods=2_000, seed=42)
    c = dl.run(20, busy_periods=2_000, seed=43)
    assert (a.transmissions, a.successes, a.idle_slots) == (b.transmissions, b.successes,
                                                            b.idle_slots)
    assert a.multiplicity_hist == b.multiplicity_hist
    assert (a.transmissions, a.successes) != (c.transmissions, c.successes)


def test_result_is_insensitive_to_the_initial_state() -> None:
    """All counters at 0 is the worst case — every station collides in round 1 — yet the
    steady state must be the same, so the reported statistics may not depend on it."""
    n = 50
    default = dl.run(n, head_start=True, busy_periods=_PERIODS, w=16, seed=5)
    pathological = dl.run(n, head_start=True, busy_periods=_PERIODS, w=16, seed=5,
                          initial=[0] * n)
    assert pathological.p_success == pytest.approx(default.p_success, rel=0.03)
    assert pathological.mean_multiplicity == pytest.approx(default.mean_multiplicity, rel=0.03)


def test_every_busy_period_has_at_least_one_transmitter() -> None:
    r = dl.run(30, busy_periods=5_000, seed=2)
    assert min(r.multiplicity_hist) >= 1
    assert max(r.multiplicity_hist) <= 30


def test_single_station_would_never_collide_but_is_rejected_as_degenerate() -> None:
    with pytest.raises(ValueError, match="n must be ≥ 2"):
        dl.run(1)
    with pytest.raises(ValueError, match="w .* must be ≥ 2"):
        dl.run(5, w=1)
    with pytest.raises(ValueError, match="busy_periods must be ≥ 1"):
        dl.run(5, busy_periods=0)
    with pytest.raises(ValueError, match="initial has"):
        dl.run(5, initial=[0, 0])


def test_access_rate_per_busy_period_matches_bianchis_tau() -> None:
    """Transmissions per station per busy period must be Bianchi's τ = 2/(W+1) = 0.1176.

    This is the quantity the two agree on. They do NOT agree on transmissions per *virtual slot*,
    because Bianchi's Bernoulli abstraction badly undercounts idle slots — see the next test.
    """
    r = dl.run(50, head_start=False, busy_periods=_PERIODS, w=16, seed=1)
    assert r.mean_multiplicity / 50 == pytest.approx(2.0 / (bianchi.W + 1), rel=0.02)
    assert not math.isnan(r.tau)


def test_bianchi_undercounts_idle_slots_between_busy_periods() -> None:
    """Documents the second face of the same modelling error, and pins the measured value.

    Bianchi predicts (1−p_tr)/p_tr ≈ 0.0019 idle slots per busy period at N=50. The real slot
    process spends ≈0.74 — a station that deferred holds a counter ≥ 1, so unless someone who just
    transmitted redrew 0, the field must count down at least one slot. NS-3 measures 0.741.
    """
    tau = 2.0 / (bianchi.W + 1)
    p_tr = 1.0 - (1.0 - tau) ** 50
    assert (1.0 - p_tr) / p_tr < 0.005, "the model's own prediction, for contrast"

    r = dl.run(50, head_start=True, busy_periods=_PERIODS, w=16, seed=1)
    assert r.idle_slots_per_busy_period == pytest.approx(0.741, abs=0.02)
    # Without the head start nobody can ever take the DIFS+0 slot, so it is exactly one per period.
    no_hs = dl.run(50, head_start=False, busy_periods=_PERIODS, w=16, seed=1)
    assert no_hs.idle_slots_per_busy_period == pytest.approx(1.0, abs=0.02)
