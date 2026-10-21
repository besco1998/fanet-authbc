"""The t interval of a mean, which replaces the percentile bootstrap for V (decision H2, F86)."""

from __future__ import annotations

import numpy as np
import pytest

from authbc.bench.stats import bootstrap_ci, t_interval


def test_by_hand() -> None:
    # mean 3, s = sqrt(2.5), t(0.975; 4) = 2.776445: half-width 2.776445 * 1.581139 / sqrt(5)
    lo, hi = t_interval([1.0, 2.0, 3.0, 4.0, 5.0])
    assert (lo, hi) == pytest.approx((3 - 1.963243, 3 + 1.963243), abs=1e-6)


def test_symmetric_about_the_mean_and_zero_width_without_spread() -> None:
    lo, hi = t_interval([0.95, 0.96, 0.94, 0.97])
    assert (lo + hi) / 2 == pytest.approx(0.955)
    assert t_interval([0.9, 0.9, 0.9]) == (0.9, 0.9)


def test_needs_two_samples() -> None:
    with pytest.raises(ValueError):
        t_interval([0.95])


def test_it_covers_95_percent_where_the_bootstrap_did_not() -> None:
    """V of 30 seeds, each 240 frames at p = 0.05 (the shape of the paper's loss table)."""
    rng = np.random.default_rng(20261021)
    trials, true_v = 2000, 0.95
    t_hits = boot_hits = 0
    for k in range(trials):
        v = list(rng.binomial(240, true_v, size=30) / 240)
        lo, hi = t_interval(v)
        t_hits += lo <= true_v <= hi
        blo, bhi = bootstrap_ci(v, seed=k, statistic=np.mean, resamples=2000)
        boot_hits += blo <= true_v <= bhi
    assert 0.94 <= t_hits / trials <= 0.96
    assert boot_hits < t_hits
