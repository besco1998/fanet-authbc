"""Unit tests for Ma & Chen's 802.11 broadcast model (guards src/authbc/models/broadcast_dcf.py).

Validation strategy (Law 4 TDD, Law 6):
  * the equations are checked term-by-term against hand-computed values at W₀=16, N=50;
  * the model is cross-checked against `sim.dcf_ladder`, a slot-process simulator written before
    the paper was found and sharing no code or assumption with it;
  * structural properties (monotonicity, limits, the CFP's sign) are pinned so a refactor cannot
    quietly turn it back into the naive reduction.
The comparison against the measured NS-3 fixture lives in tests/integration/.
"""

from __future__ import annotations

import pytest

from authbc.models import bianchi, broadcast_dcf
from authbc.sim import dcf_ladder

_L = 1400.0
_T_BUSY = bianchi.t_broadcast_exact(_L)      # 1974 µs — measured NS-3 PPDU + DIFS
_W0 = 16


def test_tau_s_is_two_over_w0_not_two_over_w_plus_one() -> None:
    """Eq. (5). The SBP excludes a zero initial backoff, so the max counter is W₀−2 and τs=2/W₀.

    Our discarded in-house reduction used 2/(W+1); the difference is not cosmetic.
    """
    r = broadcast_dcf.solve(50, _L, _T_BUSY, w0=_W0)
    assert r.tau_s == pytest.approx(2.0 / _W0)
    assert r.tau_s != pytest.approx(2.0 / (_W0 + 1))


def test_sbp_terms_match_hand_computation_at_n50() -> None:
    """Eqs. (7) and (8) at N=50, W₀=16, τs=0.125 — computed by hand, independently."""
    r = broadcast_dcf.solve(50, _L, _T_BUSY, w0=_W0)
    assert r.p_bs == pytest.approx(1.0 - 0.875**50, rel=1e-12)
    assert r.p_ss == pytest.approx(50 * 0.125 * 0.875**49, rel=1e-12)
    assert r.p_ss == pytest.approx(0.009001, abs=1e-6)


def test_cfp_series_matches_hand_computation_and_dominates_the_sbp() -> None:
    """The CFP contributes ~30× more successes than the SBP at N=50 — it IS the mechanism."""
    r = broadcast_dcf.solve(50, _L, _T_BUSY, w0=_W0)
    tau_f1 = 0.125 / 16
    first_stage = 50 * tau_f1 * (1 - tau_f1) ** 49
    assert first_stage == pytest.approx(0.2660, abs=1e-3)
    assert r.e_nsf == pytest.approx(0.29144, abs=1e-4)
    assert r.e_nsf / r.p_ss > 25.0, "the freeze process must dominate at small W₀ / large N"


def test_derived_quantities_at_n50() -> None:
    r = broadcast_dcf.solve(50, _L, _T_BUSY, w0=_W0)
    assert r.successes_per_vslot == pytest.approx(0.300446, abs=1e-5)
    assert r.busy_periods_per_vslot == pytest.approx(1.348894, abs=1e-5)
    assert r.p_success == pytest.approx(0.22274, abs=1e-4)
    assert r.idle_slots_per_busy_period == pytest.approx(0.74134, abs=1e-4)
    assert r.throughput_bps / 1e6 == pytest.approx(1.2595, abs=2e-3)


@pytest.mark.parametrize("n", [5, 10, 20, 35, 50])
def test_agrees_with_the_independent_slot_process_simulator(n: int) -> None:
    """Cross-implementation check: a closed form from the literature against our own simulator.

    `dcf_ladder` simulates counters only — no PHY, no packets, no equations from the paper — and
    was written before the paper was located. Agreement to 2 % is therefore meaningful evidence
    that both describe the same process.
    """
    model = broadcast_dcf.solve(n, _L, _T_BUSY, w0=_W0)
    sim = dcf_ladder.run(n, w=_W0, busy_periods=200_000, head_start=True,
                         t_busy_s=_T_BUSY, slot_s=bianchi.SLOT, payload_bytes=_L, seed=1)
    assert model.throughput_bps == pytest.approx(sim.throughput_bps, rel=0.02)
    assert model.p_success == pytest.approx(sim.p_success, rel=0.02)
    assert model.idle_slots_per_busy_period == pytest.approx(
        sim.idle_slots_per_busy_period, rel=0.02)


@pytest.mark.parametrize("n", [5, 10, 20, 35, 50])
def test_the_naive_reduction_never_exceeds_the_correct_model(n: int) -> None:
    """Ignoring the CFP always loses throughput, and catastrophically so at high N."""
    correct = broadcast_dcf.solve(n, _L, _T_BUSY, w0=_W0).throughput_bps / 1e6
    naive = broadcast_dcf.naive_reduction_mbps(n, _L, _T_BUSY, w=_W0)
    assert naive <= correct
    if n == 50:
        assert correct / naive > 15.0, "the discarded reduction must stay visibly broken"
    if n == 5:
        assert correct / naive == pytest.approx(1.0, abs=0.02), "at low N the two agree"


def test_cfp_effect_shrinks_as_the_window_grows() -> None:
    """Ma & Chen's own conclusion: CFP matters when W₀ is small relative to N."""
    ratios = []
    for w0 in (16, 32, 128, 1024):
        correct = broadcast_dcf.solve(50, _L, _T_BUSY, w0=w0).throughput_bps / 1e6
        naive = broadcast_dcf.naive_reduction_mbps(50, _L, _T_BUSY, w=w0)
        ratios.append(correct / naive)
    assert ratios == sorted(ratios, reverse=True), "the discrepancy must shrink as W₀ grows"
    assert ratios[0] > 15.0 and ratios[-1] < 1.5


def test_throughput_falls_then_RECOVERS_as_contention_grows() -> None:
    """Broadcast throughput is NON-monotonic in N, and the recovery is a signature of the CFP.

    Naive intuition (and the discarded reduction) says throughput falls monotonically toward zero.
    It does not: it bottoms out near N≈40 and rises again, because the more stations have just
    transmitted, the likelier it is that exactly one of them redraws a zero backoff and takes the
    next slot alone. NS-3 measures the same reversal — 1.2407 Mb/s at N=35 rising to 1.2631 at
    N=50 — so this is a real, non-obvious feature the model reproduces, not an artefact.
    """
    s = {n: broadcast_dcf.solve(n, _L, _T_BUSY, w0=_W0).throughput_bps / 1e6
         for n in (5, 10, 20, 35, 40, 45, 50)}
    assert s[5] > s[10] > s[20] > s[35] > s[40], "falls while collisions dominate"
    assert s[40] < s[45] < s[50], "then recovers as the freeze process takes over"
    assert max(s.values()) < 6.0, "never exceeds the 6 Mb/s PHY ceiling"

    # The naive reduction, by contrast, decays monotonically toward zero — it cannot reproduce
    # the reversal at all, which is the qualitative half of the 16× failure.
    naive = [broadcast_dcf.naive_reduction_mbps(n, _L, _T_BUSY, w=_W0)
             for n in (5, 10, 20, 35, 40, 45, 50)]
    assert naive == sorted(naive, reverse=True)


def test_cfp_series_has_converged_at_the_configured_stage_count() -> None:
    """The τs/W₀^i series must be summed far enough that truncation is invisible."""
    r = broadcast_dcf.solve(50, _L, _T_BUSY, w0=_W0)
    tau_s = 2.0 / _W0
    last = 50 * (tau_s / _W0**broadcast_dcf._CFP_STAGES)
    assert last < 1e-12 * r.e_nsf


def test_rejects_degenerate_inputs() -> None:
    with pytest.raises(ValueError, match="n must be ≥ 1"):
        broadcast_dcf.solve(0, _L, _T_BUSY)
    with pytest.raises(ValueError, match="w0 .* must be ≥ 2"):
        broadcast_dcf.solve(5, _L, _T_BUSY, w0=1)
    with pytest.raises(ValueError, match="payload_bytes must be > 0"):
        broadcast_dcf.solve(5, 0.0, _T_BUSY)
    with pytest.raises(ValueError, match="t_busy_s must be > 0"):
        broadcast_dcf.solve(5, _L, 0.0)
