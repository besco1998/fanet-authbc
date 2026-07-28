"""Unit tests for the NS-3 DCF trace analyser (guards src/authbc/sim/dcf_trace.py).

Strategy (Law 4 TDD, Law 6): every grouping rule is checked on a hand-built trace whose expected
answer is written down first, and the statistical layer is cross-checked against the INDEPENDENT
Bianchi implementation in authbc.models.bianchi — if `matched_binomial_p_success` is fed the mean
multiplicity that Bianchi's own τ implies, it must return Bianchi's own p_s.
"""

from __future__ import annotations

import pytest

from authbc.sim import dcf_trace as dt

# A hand-built trace, times in ns. Node 1 and 2 overlap (a collision); node 3 is alone later.
#   n1 [1000, 3000)   n2 [1500, 3200)   -> one busy period [1000,3200) multiplicity 2
#   n3 [5000, 7000)                     -> one busy period [5000,7000) multiplicity 1
_LINES = [
    "node,event,t_ns",
    "1,B,1000",
    "2,B,1500",
    "1,E,3000",
    "2,E,3200",
    "3,B,5000",
    "3,E,7000",
]


def test_parse_pairs_begin_and_end_per_node() -> None:
    txs = dt.parse_tx_events(_LINES)
    assert txs == [
        dt.Transmission(node=1, start_ns=1000, end_ns=3000),
        dt.Transmission(node=2, start_ns=1500, end_ns=3200),
        dt.Transmission(node=3, start_ns=5000, end_ns=7000),
    ]


def test_parse_drops_a_transmission_still_on_air_at_the_end() -> None:
    txs = dt.parse_tx_events([*_LINES, "4,B,9000"])
    assert [t.node for t in txs] == [1, 2, 3]


def test_parse_rejects_overlapping_begins_on_one_node() -> None:
    with pytest.raises(dt.TraceError, match="already open"):
        dt.parse_tx_events(["node,event,t_ns", "1,B,10", "1,B,20"])


def test_parse_rejects_end_without_begin() -> None:
    with pytest.raises(dt.TraceError, match="no matching begin"):
        dt.parse_tx_events(["node,event,t_ns", "1,E,10"])


def test_busy_periods_merge_overlap_and_split_on_idle() -> None:
    periods = dt.busy_periods(dt.parse_tx_events(_LINES))
    assert [(p.start_ns, p.end_ns, p.nodes) for p in periods] == [
        (1000, 3200, (1, 2)),
        (5000, 7000, (3,)),
    ]
    assert [p.multiplicity for p in periods] == [2, 1]
    assert [p.is_success for p in periods] == [False, True]


def test_touching_intervals_are_separate_busy_periods() -> None:
    """end == start means the medium went idle; DIFS always separates real periods."""
    txs = [dt.Transmission(1, 0, 100), dt.Transmission(2, 100, 200)]
    assert [p.multiplicity for p in dt.busy_periods(txs)] == [1, 1]


def test_window_keeps_only_wholly_contained_periods() -> None:
    periods = dt.busy_periods(dt.parse_tx_events(_LINES))
    assert [p.start_ns for p in dt.within(periods, 0, 10_000)] == [1000, 5000]
    assert [p.start_ns for p in dt.within(periods, 2000, 10_000)] == [5000]
    assert dt.within(periods, 0, 6000) == [periods[0]]


def test_multiplicity_hist_and_p_success() -> None:
    periods = dt.busy_periods(dt.parse_tx_events(_LINES))
    assert dt.multiplicity_hist(periods) == {1: 1, 2: 1}
    assert dt.measured_p_success(periods) == pytest.approx(0.5)
    assert dt.mean_multiplicity(periods) == pytest.approx(1.5)


def test_empty_window_raises_rather_than_returning_zero() -> None:
    with pytest.raises(dt.TraceError, match="no busy periods"):
        dt.measured_p_success([])


@pytest.mark.parametrize("n", [5, 10, 20, 35, 50])
def test_matched_binomial_reproduces_bianchi_exactly(n: int) -> None:
    """Cross-check against the independent model: same τ ⇒ same p_s.

    Feed the analyser the mean multiplicity that Bianchi's no-ACK τ = 2/(W+1) implies; it must
    recover that τ and hence Bianchi's own p_s. This pins the statistical layer to docs/02 §6.
    """
    from authbc.models import bianchi

    tau = 2.0 / (bianchi.W + 1)
    p_tr = 1.0 - (1.0 - tau) ** n
    mean_mult = n * tau / p_tr
    p_s = n * tau * (1.0 - tau) ** (n - 1) / p_tr

    assert dt.tau_matching_mean(n, mean_mult) == pytest.approx(tau, rel=1e-9)
    assert dt.matched_binomial_p_success(n, mean_mult) == pytest.approx(p_s, rel=1e-9)


def test_matched_binomial_edge_cases() -> None:
    """Mean multiplicity 1 ⇒ every busy period is a success (τ → 0)."""
    assert dt.matched_binomial_p_success(50, 1.0) == pytest.approx(1.0, abs=1e-6)
    with pytest.raises(ValueError, match="must lie in"):
        dt.matched_binomial_p_success(50, 0.5)
    with pytest.raises(ValueError, match="must be ≥ 2"):
        dt.matched_binomial_p_success(1, 1.0)


def test_winner_was_participant_counts_and_expectation() -> None:
    """Three periods: {1,2} collide, then 2 wins (a participant), then 7 wins (an outsider)."""
    periods = [
        dt.BusyPeriod(0, 100, (1, 2)),
        dt.BusyPeriod(200, 300, (2,)),
        dt.BusyPeriod(400, 500, (7,)),
    ]
    hs = dt.winner_was_participant(periods, n_stations=10)
    assert hs.transitions == 2
    assert hs.winner_was_participant == 1
    # expectation under uniform choice: 2/10 after the pair, 1/10 after the single
    assert hs.expected_uniform == pytest.approx(0.3)
    assert hs.observed_fraction == pytest.approx(0.5)
    assert hs.expected_fraction == pytest.approx(0.15)
    # conditional success split: after the collision → success; after the success → success
    assert (hs.collisions_seen, hs.successes_after_collision) == (1, 1)
    assert (hs.successes_seen, hs.successes_after_success) == (1, 1)
    assert hs.p_success_after_collision == pytest.approx(1.0)
    assert hs.p_success_after_success == pytest.approx(1.0)


def test_winner_was_participant_dedupes_repeat_transmitters_in_expectation() -> None:
    """A station appearing twice in one busy period must not inflate the uniform expectation."""
    periods = [dt.BusyPeriod(0, 100, (1, 1, 2)), dt.BusyPeriod(200, 300, (3,))]
    hs = dt.winner_was_participant(periods, n_stations=10)
    assert hs.expected_uniform == pytest.approx(0.2)


def test_deferral_gaps() -> None:
    periods = [
        dt.BusyPeriod(0, 100, (1, 2)),
        dt.BusyPeriod(300, 400, (2,)),
        dt.BusyPeriod(900, 1000, (7,)),
    ]
    assert dt.deferral_gaps(periods) == [(200, True, True), (500, False, False)]


def test_winner_statistic_skips_pairs_with_an_ambiguous_winner() -> None:
    """Audit A7: when the next busy period is itself a collision there is no single winner, so the
    pair must not be counted — picking the lowest-numbered simultaneous starter is arbitrary and
    dilutes the statistic (measured: 7.6× → 3.1× at N=50)."""
    periods = [
        dt.BusyPeriod(0, 100, (1, 2)),
        dt.BusyPeriod(200, 300, (3, 4)),   # collision ⇒ this transition is skipped
        dt.BusyPeriod(400, 500, (4,)),     # success   ⇒ counted, winner 4 was in the previous
    ]
    hs = dt.winner_was_participant(periods, n_stations=10)
    assert hs.transitions == 1
    assert hs.winner_was_participant == 1
    assert hs.expected_uniform == pytest.approx(0.2)
    assert hs.enrichment == pytest.approx(5.0)
    # the conditional success-rate counters still see BOTH transitions
    assert hs.collisions_seen + hs.successes_seen == 2


def test_enrichment_is_zero_when_the_winner_is_never_a_previous_participant() -> None:
    """Round-robin winners: no station ever repeats, so the head-start signal must be absent."""
    periods = [dt.BusyPeriod(i * 1000, i * 1000 + 500, (i,)) for i in range(1, 11)]
    hs = dt.winner_was_participant(periods, n_stations=10)
    assert hs.transitions == 9
    assert hs.winner_was_participant == 0
    assert hs.enrichment == 0.0


def test_head_start_statistics_are_zero_safe_on_a_degenerate_trace() -> None:
    """A single busy period yields no transitions; the properties must not divide by zero."""
    hs = dt.winner_was_participant([dt.BusyPeriod(0, 100, (1,))], n_stations=10)
    assert (hs.transitions, hs.observed_fraction, hs.expected_fraction, hs.enrichment) == (
        0, 0.0, 0.0, 0.0)
    assert (hs.p_success_after_collision, hs.p_success_after_success) == (0.0, 0.0)
