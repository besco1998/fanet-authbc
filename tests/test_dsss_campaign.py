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


# --------------------------------------------------------------------- after the run, 2026-11-05
REGISTRATION = "38a5370"            # predictions/W1b.md, tag prereg-W1b


def _ns3() -> dict[tuple[str, int], list[dict[str, str]]]:
    by: dict[tuple[str, int], list[dict[str, str]]] = {}
    for r in csv.DictReader(ln for ln in w1b.RUNS.read_text().splitlines()
                            if not ln.startswith("#")):
        by.setdefault((r["cell"], int(r["n_nodes"])), []).append(r)
    return by


class TestTheOutcome:
    SCORED = {(r["what"], r["cell"]): r for r in csv.DictReader(
        ln for ln in w1b.SCORED.read_text().splitlines() if not ln.startswith("#"))}

    def test_the_scored_code_is_the_registered_code(self) -> None:
        import subprocess
        for path in ("analysis/dsss_campaign.py", "ns3/authbc-links.cc"):
            then = subprocess.run(["git", "show", f"{REGISTRATION}:{path}"], cwd=REPO,
                                  capture_output=True, text=True, check=True).stdout
            assert then == (REPO / path).read_text(), path

    def test_w1b_1_and_2_held(self) -> None:
        for key in (("crossing", "Pb1B"), ("crossing", "Pb1D"), ("ratio", "D/C")):
            assert self.SCORED[key]["held"] == "True", key

    def test_w1b_4_the_equivalence_holds_up_to_the_crossing_and_fails_beyond(self) -> None:
        for split in ("Pb1S146_62.5", "Pb1S146_87.5", "Pb1S173_65.625", "Pb1S173_90.625"):
            assert self.SCORED[("split", split)]["held"] == "True", split
        for split in ("Pb1S146_112.5", "Pb1S146_137.5", "Pb1S173_115.625"):
            assert float(self.SCORED[("split", split)]["difference"]) < -0.02, split

    def test_w1b_3_six_of_seven_and_the_miss_is_the_queue_limit(self) -> None:
        import statistics as st
        runs = _ns3()
        missed = []
        for split, _ref in w1b.splits():
            v = st.mean(float(r["delivered_frac"]) for r in runs[(split, 5)])
            if abs(v - float(PRED[("split", split)]["model"])) > 0.02:
                missed.append(split)
        assert missed == ["Pb1S146_137.5"]
        # ns-3 discards a frame after 500 ms in its MAC queue (WifiMacQueue MaxDelay); the
        # largest delay reaches that limit in exactly the two overloaded splits
        at_limit = {s for s, _ in w1b.splits()
                    if max(float(r["delay_max_ms"]) for r in runs[(s, 5)]) > 499.0}
        assert at_limit == {"Pb1S146_137.5", "Pb1S173_115.625"}
