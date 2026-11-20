"""U-C7 (predictions/UC7.md): the registered table is generated from the model, and the cells'
timing follows the registration (period ToA/d, jitter 2·ToA, d_eff = d/(1 + d)).
"""
from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def uc7():
    sys.path.insert(0, str(REPO / "src"))
    spec = importlib.util.spec_from_file_location("uc7", REPO / "analysis" / "uc7.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["uc7"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_the_registered_table_is_generated(uc7) -> None:
    reg = (REPO / "predictions" / "UC7.md").read_text()
    for line in uc7.markdown().splitlines()[2:]:
        assert line in reg, line


def test_eighteen_cells_and_the_effective_duty(uc7) -> None:
    assert len(uc7.CELLS) == 18
    for c in uc7.CELLS:
        assert c.duty_eff == pytest.approx(c.duty / (1 + c.duty))
        assert c.n_max() == 1 + math.floor(c.channels * math.log(1 / 0.95) / (2 * c.duty_eff))


def test_length_does_not_enter_the_prediction(uc7) -> None:
    by = {(c.duty, c.channels): set() for c in uc7.CELLS}
    for c in uc7.CELLS:
        by[(c.duty, c.channels)].add(round(c.n_star(), 9))
    assert all(len(v) == 1 for v in by.values())


def test_the_new_cell_runs_past_the_class_a_windows(uc7) -> None:
    (c,) = uc7.CELLS_B
    assert c.name == "D10C8L120SF8" and c.dr == 4 and c.period_s > 2.5
    assert c.n_max() == 3 and round(c.n_star(), 3) == 3.257
    assert c.name not in {x.name for x in uc7.CELLS}
