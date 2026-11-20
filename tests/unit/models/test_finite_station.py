"""The finite-station form (src/authbc/models/finite_station.py), a proposal under work package C.

Held here (docs/revision/2026-11-20_finite_station_derivation.md §2):
* at N = 2 only the detection window is left: p = 2δf(1 + a);
* as N grows the form approaches (G5), and its terms differ from (G5)'s only by the tie term's
  limit gap, −2.8 % at K/W ≈ 0.05;
* the co-waiting count never exceeds the m = N − 2 bystanders, and π ≤ 1.
"""
from __future__ import annotations

import pytest

from authbc.models import finite_station as fs
from authbc.models import unified_capacity as uc

B = uc.A80211B
TF = 1640e-6


def test_two_stations_leave_only_the_detection_window() -> None:
    f = 100.0
    t = fs.terms(2, f, TF, B, 0.0)
    assert t is not None and t["tie"] == 0.0 and t["zero_backoff_after_busy"] == 0.0
    a = f * (TF - B.delta_s)
    assert t["detection_window"] == pytest.approx(2 * B.delta_s * f * (1 + a))


def test_many_stations_approach_g5() -> None:
    for n in (200, 1000):
        f = 0.3 / (n * TF)
        mine, g5 = fs.loss(n, f, TF, B), uc.loss((n - 1) * f, TF, B)
        assert mine == pytest.approx(g5, rel=0.03)


def test_the_tie_limit_gap() -> None:
    assert fs.tie_limit_gap(1.6, 32) == pytest.approx(-0.0276, abs=5e-4)
    assert fs.tie_limit_gap(0.0, 32) == 0.0


def test_fewer_stations_lose_less_than_g5_at_equal_load() -> None:
    for n in (3, 4, 5):
        f = 0.5 / (n * TF)
        assert fs.loss(n, f, TF, B) < uc.loss((n - 1) * f, TF, B)


def test_rejects_one_station() -> None:
    with pytest.raises(ValueError):
        fs.terms(1, 10.0, TF, B, 0.0)
