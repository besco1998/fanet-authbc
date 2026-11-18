"""The burst correction (src/authbc/models/burst_correction.py; predictions/UC4B.md).

Held here:
* with n = 1 it is the original loss expression (`unified_capacity.loss`), term for term;
* fragments 2 … n lose at least as much as the first: their tie term lacks the factor a < 1;
* the unit loss is 1 − (1 − p₁)(1 − p₂)^(n − 1);
* the capacity is where the unit loss reaches ε, and lies below the original root at n·f.
"""
from __future__ import annotations

import pytest

from authbc.models import phy
from authbc.models import unified_capacity as uc
from authbc.models.burst_correction import burst_terms, unit_capacity


@pytest.mark.parametrize("nu", [200.0, 800.0, 1500.0, 2500.0])
def test_n1_is_the_original_expression(nu: float) -> None:
    tf = uc.airtime_s(phy.OFDM_20MHZ_6M, 173)
    assert burst_terms(nu, tf, 1)["unit"] == pytest.approx(uc.loss(nu, tf), abs=1e-9)


def test_later_fragments_lose_more_and_the_unit_combines_them() -> None:
    tf = uc.airtime_s(phy.OFDM_20MHZ_6M, 98)
    t = burst_terms(1000.0, tf, 2)
    assert 0 < t["a"] < 1 and t["p2"] > t["p1"]
    assert t["unit"] == pytest.approx(1 - (1 - t["p1"]) * (1 - t["p2"]))
    t3 = burst_terms(1000.0, uc.airtime_s(phy.OFDM_20MHZ_6M, 73), 3)
    assert t3["unit"] == pytest.approx(1 - (1 - t3["p1"]) * (1 - t3["p2"]) ** 2)


@pytest.mark.parametrize(("size", "n"), [(98, 2), (73, 3)])
def test_capacity_is_where_the_unit_loss_is_eps_and_below_the_original(size: int, n: int) -> None:
    tf = uc.airtime_s(phy.OFDM_20MHZ_6M, size)
    cap = unit_capacity(12.5, tf, n, 0.05)
    nu = (cap - 1) * n * 12.5
    assert burst_terms(nu, tf, n)["unit"] == pytest.approx(0.05, abs=1e-6)
    assert cap < uc.n_root(12.5 * n, tf, uc.eps_fragment(n, 0.05))


def test_rejects_n_below_one() -> None:
    with pytest.raises(ValueError):
        burst_terms(100.0, 1e-4, 0)
