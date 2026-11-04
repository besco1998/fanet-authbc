"""W1(a): the capacity ratio under a non-standard radio (analysis/mac_robustness.py; W1a.md).

What is held here, before ns-3 is run: that the predictions on file are what the model and the
closed form give; that the control (the standard's window) reproduces the model crossings
published in results/raw/dcf_model_vs_ns3.csv; that each ns-3 grid brackets its predicted
crossing; and that the plans run the registered window. The scores are held after the run.
"""
from __future__ import annotations

import csv
import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("mac_robustness",
                                               REPO / "analysis" / "mac_robustness.py")
assert _spec and _spec.loader
w1a = importlib.util.module_from_spec(_spec)
sys.modules["mac_robustness"] = w1a
_spec.loader.exec_module(w1a)


def _rows(path: Path) -> list[dict[str, str]]:
    return list(csv.DictReader(ln for ln in path.read_text().splitlines()
                               if not ln.startswith("#")))


PRED = {(r["rule"], r["cell"]): r for r in _rows(w1a.PREDICTIONS) if r["set"] == "window"}


class TestThePredictionsOnFile:
    @pytest.mark.parametrize("w", w1a.WINDOWS)
    def test_the_closed_form_column(self, w: int) -> None:
        for cell in w1a.CELLS:
            assert float(PRED[(f"W={w}", cell)]["closed_form_crossing"]) == pytest.approx(
                w1a.closed_form(cell, w), abs=0.006)

    def test_the_control_reproduces_the_published_model_crossings(self) -> None:
        published = {r["cell"]: float(r["model_crossing"])
                     for r in _rows(REPO / "results" / "raw" / "dcf_model_vs_ns3.csv")
                     if r["n_nodes"] == "CROSSING"}
        for cell in w1a.CELLS:
            mine = float(PRED[("W=16", cell)]["model_crossing"])
            assert mine == pytest.approx(published[cell], rel=0.005), cell

    @pytest.mark.parametrize("w", w1a.NS3_WINDOWS)
    def test_each_grid_brackets_its_crossing_and_the_band_is_registered(self, w: int) -> None:
        for cell in w1a.CELLS:
            r = PRED[(f"W={w}", cell)]
            x, grid = float(r["model_crossing"]), [int(n) for n in r["ns3_grid"].split()]
            assert len(grid) == w1a.GRID_POINTS and grid[0] < x < grid[-1]
            # the band was computed from the unrounded crossing; both are written to 0.01
            assert float(r["band_lo"]) == pytest.approx(0.97 * x, abs=0.011)
            assert float(r["band_hi"]) == pytest.approx(1.03 * x, abs=0.011)
        ratio = PRED[(f"W={w}", "D/C")]
        assert (float(ratio["band_lo"]), float(ratio["band_hi"])) == w1a.RATIO_BAND

    @pytest.mark.parametrize("w", w1a.NS3_WINDOWS)
    def test_each_plan_runs_its_window(self, w: int) -> None:
        plan = (w1a.PLANS / f"plan_cw{w - 1}.txt").read_text()
        assert f"--cw-min {w - 1} " in plan and f"--out-stem ns3_w1a_cw{w - 1} " in plan
        for cell in w1a.CELLS:
            assert f"{cell} period {PRED[(f'W={w}', cell)]['ns3_grid']}" in plan
