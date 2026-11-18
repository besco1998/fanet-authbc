"""U-C4S / U-C4B's scorer (analysis/unified_c4sb.py): the model values are the registered ones
(predictions/UC4S.md, UC4B.md), and the 802.11b cells take U-D's bands."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("unified_c4sb", REPO / "analysis" / "unified_c4sb.py")
assert spec and spec.loader
sb = importlib.util.module_from_spec(spec)
sys.modules["unified_c4sb"] = sb
spec.loader.exec_module(sb)


@pytest.mark.parametrize(("cell", "key", "want"),
                         [("F2P", "root", 55.37), ("F3P", "root", 31.70),
                          ("BB2", "correction", 14.77), ("BB3", "correction", 8.96),
                          ("AB120", "correction", 48.97), ("BB2", "root", 16.99),
                          ("AB120", "root", 60.83)])
def test_registered_values(cell: str, key: str, want: float) -> None:
    assert round(sb.model(cell)[key], 2) == want


def test_bands() -> None:
    assert sb.band("AB120", 7.0) == (-5.0, 5.0)          # 802.11a: ±5 % at any size
    assert sb.band("BB2", 15.0) == (-5.0, 5.0)
    assert sb.band("BB2", 13.6) == (-9.0, 5.0)
    assert sb.band("BB3", 7.5) is None
