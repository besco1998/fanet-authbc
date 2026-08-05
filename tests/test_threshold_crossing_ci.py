"""Uncertainty on a capacity threshold crossing (docs/02 §6b, Tier 1 item 3).

**Why this file exists.** `N_max` is "the largest N whose delivered fraction still meets V ≥ 1−ε".
It is a *crossing*, not a mean, so it does not get a confidence interval for free — and this project
has already had four headline numbers move because a small-sample mean was compared against a
threshold and then reported as a point. These tests pin the behaviour of the bootstrap that attaches
an interval to the crossing itself.
"""

import pytest

from authbc.bench.stats import threshold_crossing_ci

RESAMPLES = 2000  # enough to be stable at the tolerances asserted here, fast enough for the suite


def _flat(value: float, n_seeds: int = 30) -> list[float]:
    return [value] * n_seeds


class TestUnambiguousCases:
    """When the data are not near the threshold, the interval must collapse to the point."""

    def test_clean_crossing_has_zero_width_interval(self):
        per_n = {5: _flat(0.99), 10: _flat(0.98), 20: _flat(0.60), 50: _flat(0.20)}
        r = threshold_crossing_ci(per_n, threshold=0.95, resamples=RESAMPLES)
        assert (r.point, r.ci_lo, r.ci_hi) == (10, 10, 10)
        assert not r.is_knife_edge

    def test_everything_fails_reports_zero(self):
        per_n = {5: _flat(0.10), 10: _flat(0.05)}
        r = threshold_crossing_ci(per_n, threshold=0.95, resamples=RESAMPLES)
        assert r.point == 0

    def test_everything_passes_reports_the_largest_n(self):
        per_n = {5: _flat(0.99), 10: _flat(0.99), 20: _flat(0.99)}
        r = threshold_crossing_ci(per_n, threshold=0.95, resamples=RESAMPLES)
        assert r.point == 20


class TestTheCaseThisWasBuiltFor:
    """A crossing sitting on the threshold must report a WIDE interval, not a confident point."""

    def test_knife_edge_is_detected_and_flagged(self):
        # N=10 straddles the threshold: half the seeds pass, half fail, mean lands right on it.
        per_n = {
            5: _flat(0.99),
            10: [0.99] * 15 + [0.91] * 15,   # mean 0.95 -- exactly the threshold
            20: _flat(0.50),
        }
        r = threshold_crossing_ci(per_n, threshold=0.95, resamples=RESAMPLES)
        assert r.ci_lo < r.ci_hi, "a crossing on the threshold must not report a zero-width CI"
        assert {5, 10} <= set(r.distribution), "both outcomes should appear across replicates"
        assert r.is_knife_edge, "a CI spanning two candidates must be flagged"
        # ⚠️ This split is ~56/44. An earlier version of `is_knife_edge` asked whether the point
        # held a majority and therefore passed this as settled. It is not settled: the data do not
        # distinguish N=5 from N=10 at 95 %, which is exactly what must be flagged.
        assert max(r.distribution.values()) > 0.5, "the split really is close to even here"

    def test_a_single_outlier_seed_widens_the_interval(self):
        """The concrete failure mode: one unlucky seed decides the reported capacity."""
        per_n = {5: _flat(0.99), 10: [0.96] * 29 + [0.60], 20: _flat(0.10)}
        r = threshold_crossing_ci(per_n, threshold=0.95, resamples=RESAMPLES)
        # mean is 0.948 -> the point estimate fails at N=10, but resampling sometimes drops the
        # outlier and N=10 passes. The interval must expose that, and the point must not hide it.
        assert set(r.distribution) == {5, 10}
        assert r.ci_lo == 5


class TestTheCrossingRuleMatchesTheDriver:
    def test_non_monotone_curve_stops_at_the_first_failure(self):
        """F26/A4: taking the LAST passing N would over-report capacity on a noisy curve."""
        per_n = {5: _flat(0.99), 10: _flat(0.50), 20: _flat(0.99)}
        r = threshold_crossing_ci(per_n, threshold=0.95, resamples=RESAMPLES)
        assert r.point == 5, "N=20 passing after N=10 failed must NOT raise the reported capacity"


class TestGuards:
    def test_uneven_seed_counts_are_rejected(self):
        with pytest.raises(ValueError, match="same seed count"):
            threshold_crossing_ci({5: _flat(0.99, 30), 10: _flat(0.99, 10)}, threshold=0.95)

    def test_single_seed_is_rejected(self):
        with pytest.raises(ValueError, match=">= 2 seeds"):
            threshold_crossing_ci({5: [0.99]}, threshold=0.95)

    def test_empty_input_is_rejected(self):
        with pytest.raises(ValueError, match="at least one N"):
            threshold_crossing_ci({}, threshold=0.95)


class TestDeterminism:
    def test_same_seed_gives_the_same_interval(self):
        """Law 6: a CI that moves between identical runs would itself be a bug."""
        per_n = {5: _flat(0.99), 10: [0.99] * 15 + [0.91] * 15, 20: _flat(0.5)}
        a = threshold_crossing_ci(per_n, threshold=0.95, resamples=RESAMPLES, seed=1)
        b = threshold_crossing_ci(per_n, threshold=0.95, resamples=RESAMPLES, seed=1)
        assert (a.point, a.ci_lo, a.ci_hi) == (b.point, b.ci_lo, b.ci_hi)
        assert a.distribution == b.distribution


class TestLoneSenderStillOccupiesAirtime:
    """Audit S3/O5: `channel_utilisation` used to short-circuit N=1 to exactly 0.0.

    That confused *contention* with *utilisation* — a lone sender does not collide, but it still
    occupies the medium. The bug was harmless only while nothing was reported at N=1; the strict
    N_max criterion now reports exactly that, which is what made it load-bearing.
    """

    def test_single_node_utilisation_is_positive(self):
        from authbc.models.optimizer import channel_utilisation

        u = channel_utilisation(1, lam=20.0, batch=4, frame_bytes=288.0)
        assert u > 0.0, "a lone sender occupies airtime; U=0 would imply unbounded capacity"

    def test_single_node_matches_the_closed_form_lone_sender_rate(self):
        """Independent cross-check: Ma & Chen at n=1 must equal 1/(T_broadcast + mean backoff)."""
        import pytest as _pytest

        from authbc.models import bianchi
        from authbc.models.optimizer import channel_utilisation

        frame_bytes, lam, batch = 288.0, 20.0, 4
        cycle = bianchi.t_broadcast(frame_bytes) + ((bianchi.W - 1) / 2) * bianchi.SLOT
        expected = (lam / batch) / (1.0 / cycle)
        got = channel_utilisation(1, lam=lam, batch=batch, frame_bytes=frame_bytes)
        assert got == _pytest.approx(expected, rel=1e-3)

    def test_utilisation_still_rises_with_node_count(self):
        from authbc.models.optimizer import channel_utilisation

        us = [channel_utilisation(n, lam=20.0, batch=4, frame_bytes=288.0) for n in (1, 2, 5, 10)]
        assert all(b > a for a, b in zip(us, us[1:], strict=False))
