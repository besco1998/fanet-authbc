"""U-D's D1/D2 scorer (analysis/unified_d.py), as predictions/UD.md fixes it.

Held here:
* the model values it scores against are the registered tables (D1, D2, the design law);
* the band follows ns-3's crossing: ±5 % from 15 stations, −9 … +5 % from 8 to 14, none below 8;
* a crossing on a band's edge holds (checked where the edge is exact in floating point).
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("unified_d", REPO / "analysis" / "unified_d.py")
assert spec and spec.loader
ud = importlib.util.module_from_spec(spec)
sys.modules["unified_d"] = ud
spec.loader.exec_module(ud)

D1 = {("Pb1B", 32): ((6.82, 6.83), (8.92, 8.95), (10.60, 10.63)),
      ("Pb1B", 16): ((5.81, 5.80), (7.83, 7.83), (9.61, 9.62)),
      ("Pb1B", 8): ((4.81, 4.80), (6.62, 6.62), (8.39, 8.39)),
      ("Pb1D", 32): ((21.91, 21.94), (29.34, 29.43), (35.26, 35.35)),
      ("Pb1D", 16): ((18.20, 18.19), (25.37, 25.38), (31.67, 31.69)),
      ("Pb1D", 8): ((14.58, 14.57), (21.03, 21.03), (27.28, 27.28))}
D2 = {1: (40.60, 40.74), 2: (77.21, 77.47), 4: (142.72, 143.14), 8: (249.54, 250.11),
      16: (399.85, 400.46), 32: (572.74, 573.21)}


@pytest.mark.parametrize(("cell", "w"), sorted(D1))
def test_d1_model_values_are_the_registered_ones(cell: str, w: int) -> None:
    for eps, want in zip((0.02, 0.05, 0.10), D1[(cell, w)], strict=True):
        law, root = ud.d1_model(cell, w, eps)
        assert (round(law, 2), round(root, 2)) == want, (cell, w, eps)


@pytest.mark.parametrize("b", sorted(D2))
def test_d2_model_values_are_the_registered_ones(b: int) -> None:
    law, root = ud.d2_model(b)
    assert (round(law, 2), round(root, 2)) == D2[b]


def test_d2_design_law() -> None:
    dl = ud.d2_design()
    assert round(dl.n_inf, 1) == 1009.2 and round(dl.beta, 2) == 24.48


def test_bands() -> None:
    assert ud.band(15.0) == (-5.0, 5.0) and ud.band(14.99) == (-9.0, 5.0)
    assert ud.band(8.0) == (-9.0, 5.0) and ud.band(7.99) is None
    assert ud.verdict(91.0, 100.0) == "failed" and ud.verdict(95.0, 100.0) == "held"
    assert ud.verdict(10.5, 10.0) == "held" and ud.verdict(10.6, 10.0) == "failed"
    assert ud.verdict(9.2, 10.0) == "held" and ud.verdict(9.0, 10.0) == "failed"
    assert ud.verdict(7.0, 7.5).startswith("not scored")
