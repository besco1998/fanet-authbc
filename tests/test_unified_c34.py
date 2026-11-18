"""U-C3 / U-C4's scorer (analysis/unified_c34.py): its model values are the registered ones
(predictions/UC3.md, UC4.md), and the tolerance is ±5 %, inclusive."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("unified_c34", REPO / "analysis" / "unified_c34.py")
assert spec and spec.loader
c34 = importlib.util.module_from_spec(spec)
sys.modules["unified_c34"] = c34
spec.loader.exec_module(c34)


@pytest.mark.parametrize(("r", "eps", "tf", "law", "root"),
                         [(1, 0.05, 304, 122.85, 120.64),
                          (2, 0.03371, 294, 105.67, 102.68),
                          (4, 0.02041, 289, 83.72, 80.05)])
def test_c3_model_values(r: int, eps: float, tf: int, law: float, root: float) -> None:
    e, t, n_law, n_root = c34.c3_model(r)
    assert (round(e, 5), round(t * 1e6), round(n_law, 2), round(n_root, 2)) == (eps, tf, law, root)


@pytest.mark.parametrize(("n", "size", "eps", "tf", "law", "root"),
                         [(2, 98, 0.02532, 204, 58.97, 55.37),
                          (3, 73, 0.01695, 172, 35.06, 31.70)])
def test_c4_model_values(n: int, size: int, eps: float, tf: int, law: float, root: float) -> None:
    e, t, n_law, n_root = c34.c4_model(n, size)
    assert (round(e, 5), round(t * 1e6), round(n_law, 2), round(n_root, 2)) == (eps, tf, law, root)


def test_tolerance() -> None:
    assert c34.within(105.0, 100.0) and c34.within(95.0, 100.0)
    assert not c34.within(105.1, 100.0) and not c34.within(94.9, 100.0)
