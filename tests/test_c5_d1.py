"""C5's D1 predictions (analysis/c5_d1.py), without ns-3.

Held here:
* the collision budget: ε_c = 1 − (1 − ε)/(1 − PER), zero when the loss to noise is ε itself;
* (G19)'s b_opt is where N − 1 = (Β₀ − e₁b)·b/(Λ(Φ + Ψb)) stops rising — checked against its own
  inputs by a numerical derivative;
* the (G19) inputs follow the prompt's definitions: the secant airtime between b = 1 and 32 at
  48 Mb/s, and s from b = 1 to b = 2.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("c5_d1", REPO / "analysis" / "c5_d1.py")
assert spec and spec.loader
d1 = importlib.util.module_from_spec(spec)
sys.modules["c5_d1"] = d1
spec.loader.exec_module(d1)


def test_collision_budget() -> None:
    assert d1.eps_c(0.0) == pytest.approx(0.05)
    assert d1.eps_c(0.05) == pytest.approx(0.0, abs=1e-15)
    assert d1.eps_c(0.03) == pytest.approx(1 - 0.95 / 0.97)


def test_g19_b_opt_is_the_stationary_point() -> None:
    g = d1.g19(0.0269, 0.0302)
    phi, psi = (g["phi_t_us"] + g["tau_hat_us"]) * 1e-6, g["psi_t_us"] * 1e-6

    def n_minus_1(b: float) -> float:          # Λ cancels in the optimum; set to 1
        return (g["B0"] - g["e1"] * b) * b / (phi + psi * b)

    b, h = g["b_opt"], 1e-3
    assert (n_minus_1(b + h) - n_minus_1(b - h)) / (2 * h) == pytest.approx(0.0, abs=1e-6)
    assert n_minus_1(b) > n_minus_1(b * 0.8) and n_minus_1(b) > n_minus_1(b * 1.2)


def test_g19_inputs_follow_the_definitions() -> None:
    g = d1.g19(0.0269, 0.0302)
    # 48 Mb/s: 146 B → 52 µs, 425 B → 100 µs; the secant over 31 records
    assert g["psi_t_us"] == pytest.approx(48 / 31)
    assert g["phi_t_us"] == pytest.approx(52 - 48 / 31)
    assert g["s"] == pytest.approx(0.0302 - 0.0269)
    assert g["per0"] == pytest.approx(0.0269 - (0.0302 - 0.0269))
    assert g["beta"] == pytest.approx((g["phi_t_us"] + g["tau_hat_us"]) / g["psi_t_us"])


def test_every_crossing_of_a_flat_curve() -> None:
    means = {51: 0.95072, 52: 0.95075, 53: 0.94979, 54: 0.95009, 55: 0.94953}
    got = d1.all_crossings(means)
    assert len(got) == 3
    assert got[0] == pytest.approx(52 + 0.00075 / 0.00096)
    assert got[-1] == pytest.approx(54 + 0.00009 / 0.00056)
