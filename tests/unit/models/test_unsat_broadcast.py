"""Malone–Duffy–Leith adapted to broadcast (src/authbc/models/unsat_broadcast.py).

Held here:
* the closed form (their (5)–(6) with p = 0 in the transitions) equals the numerically solved
  broadcast chain;
* in saturation (q → 1) τ tends to Bianchi's broadcast value 2/(W0 + 1);
* the fixed point gives a loss that rises with load.
"""
from __future__ import annotations

import pytest

from authbc.models import unified_capacity as uc
from authbc.models import unsat_broadcast as ub


@pytest.mark.parametrize("q, p_idle, w", [(0.05, 0.9, 32), (0.3, 0.6, 16), (0.8, 0.95, 32),
                                         (0.01, 0.99, 16)])
def test_the_closed_form_is_the_chain(q, p_idle, w) -> None:
    assert ub.tau_closed(q, p_idle, w) == pytest.approx(ub.tau_chain(q, p_idle, w), rel=1e-9)


def test_saturation_is_bianchis_broadcast_tau() -> None:
    assert ub.tau_closed(1 - 1e-9, 0.5, 16) == pytest.approx(2 / 17, rel=1e-6)


def test_the_loss_rises_with_load() -> None:
    tf = 1640e-6
    losses = [ub.solve(2, u / (2 * tf), tf, uc.A80211B)["loss"] for u in (0.3, 0.5, 0.7, 0.9)]
    assert losses == sorted(losses) and 0 < losses[0] < losses[-1] < 1
