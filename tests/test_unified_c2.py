"""U-C2's scorer (analysis/unified_c2.py), as predictions/UC2.md fixes it.

Held here:
* the model values it scores against are the registered ones (law, root, design law, T_f);
* a crossing holds within ±5 % of ns-3's, inclusive, and fails outside;
* the gain takes the receiver off both counts: Γ(b) = (N(b) − 1)/(N(1) − 1).
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("unified_c2", REPO / "analysis" / "unified_c2.py")
assert spec and spec.loader
c2 = importlib.util.module_from_spec(spec)
sys.modules["unified_c2"] = c2
spec.loader.exec_module(c2)

REGISTERED = {16: (448, 359.53, 356.31, 360.63),
              32: (640, 531.13, 528.72, 532.34),
              64: (1024, 697.93, 696.65, 698.97)}


@pytest.mark.parametrize("b", sorted(REGISTERED))
def test_model_values_are_the_registered_ones(b: int) -> None:
    tf, law, root, design = REGISTERED[b]
    m = c2.model_values(b)
    assert m["tf_us"] == pytest.approx(tf, abs=1e-6)
    assert round(m["law"], 2) == law
    assert round(m["root"], 2) == root
    assert round(m["design"], 2) == design
    assert round(m["n_inf"], 1) == 1016.9 and round(m["beta"], 2) == 29.24


def test_tolerance_is_five_percent_inclusive() -> None:
    assert c2.held(105.0, 100.0) and c2.held(95.0, 100.0)
    assert not c2.held(105.01, 100.0) and not c2.held(94.99, 100.0)
    assert c2.err_pct(98.0, 100.0) == pytest.approx(-2.0)


def test_gain_takes_the_receiver_off_both() -> None:
    assert c2.gain(35.26, 35.26) == 1.0
    assert c2.gain(69.52, 35.26) == pytest.approx(2.0)
