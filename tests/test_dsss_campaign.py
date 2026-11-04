"""W1b: the contention model at 802.11b against ns-3 (analysis/dsss_campaign.py; W1b.md).

What is held here, before any 802.11b run of ns-3: that the predictions on file are the model's at
ns-3's 802.11b constants; that each grid brackets its predicted crossing and covers every split's
N_eq; that the split cells are A12's mapping at the hardware's five boards; and that the plan runs
what the predictions name. The scores are held after the run.
"""
from __future__ import annotations

import csv
import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("dsss_campaign",
                                               REPO / "analysis" / "dsss_campaign.py")
assert _spec and _spec.loader
w1b = importlib.util.module_from_spec(_spec)
sys.modules["dsss_campaign"] = w1b
_spec.loader.exec_module(w1b)

PRED = {(r["what"], r["cell"]): r for r in csv.DictReader(
    ln for ln in w1b.PREDICTIONS.read_text().splitlines() if not ln.startswith("#"))}


class TestTheModelIs80211b:
    def test_the_rule_and_the_timing(self) -> None:
        assert (w1b.RULE.w_post, w1b.RULE.w_defer, w1b.RULE.slot_s) == (32, 32, 20e-6)
        assert w1b.airtime_s(173) == pytest.approx((192 + 8 * 209) * 1e-6)

    def test_the_closed_form_column(self) -> None:
        for name in w1b.CELLS:
            assert float(PRED[("crossing", name)]["closed_form"]) == pytest.approx(
                w1b.closed_form(name), abs=0.006)


class TestTheGrids:
    @pytest.mark.parametrize("name", ["Pb1B", "Pb1D"])
    def test_each_grid_brackets_its_crossing(self, name: str) -> None:
        r = PRED[("crossing", name)]
        grid = [int(n) for n in r["ns3_grid"].split()]
        assert len(grid) >= w1b.GRID_POINTS and grid[0] < float(r["model"]) < grid[-1]

    def test_every_split_lies_on_its_reference_grid(self) -> None:
        for split, ref in w1b.splits():
            grid = [int(n) for n in PRED[("crossing", ref)]["ns3_grid"].split()]
            neq = float(PRED[("split", split)]["n_eq"])
            assert grid[0] <= neq <= grid[-1], split

    def test_the_splits_are_a12s_mapping_at_five_boards(self) -> None:
        for split, ref in w1b.splits():
            c, r = w1b.cell(split), w1b.cell(ref)
            assert c.frame_bytes == r.frame_bytes and c.standard == "80211b"
            assert w1b.n_equivalent(5, c.fps, r.fps) == pytest.approx(
                float(PRED[("split", split)]["n_eq"]), abs=0.001)

    def test_the_plan_runs_what_the_predictions_name(self) -> None:
        plan = w1b.PLAN.read_text()
        for name in w1b.CELLS:
            assert f"{name} {PRED[('crossing', name)]['ns3_grid']}\n" in plan
        for split, _ref in w1b.splits():
            assert f"{split} 5\n" in plan
