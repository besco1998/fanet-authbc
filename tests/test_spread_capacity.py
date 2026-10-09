"""Capacity with the nodes spread out and capture at work (docs/NMAX_DIRECT_EXPECTATIONS.md, F7).

`spread_capacity_predictions.csv` was committed before the ns-3 runs it predicts. Held here:
that it says what was registered, that the two kinds of prediction are what the registration
text says they are, that the plans run exactly the registered node counts with the registered
geometry, and that nothing is scored from an unfinished campaign.
"""
from __future__ import annotations

import csv
import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
RAW = REPO / "results" / "raw"
sys.path.insert(0, str(REPO / "ns3"))
sys.path.insert(0, str(REPO / "analysis"))
_spec = importlib.util.spec_from_file_location("spread_capacity",
                                               REPO / "analysis" / "spread_capacity.py")
assert _spec and _spec.loader
spread = importlib.util.module_from_spec(_spec)
sys.modules["spread_capacity"] = spread
_spec.loader.exec_module(spread)

PREDICTED = spread.registered()
PLANS = REPO / "experiments" / "nmax-direct"


class TestTheRegisteredPredictions:
    def test_four_cases_as_registered(self) -> None:
        """The numbers of the table in docs/NMAX_DIRECT_EXPECTATIONS.md, F7."""
        assert {c: (r["kind"], r["equal_power_crossing"], r["model_crossing"], r["predicted_lo"],
                    r["predicted_hi"]) for c, r in PREDICTED.items()} == {
            "C, 15 m": ("point", "35.26", "39.52", "37.54", "41.5"),
            "D, 15 m": ("point", "124.55", "139.66", "132.68", "146.64"),
            "C, 100 m": ("bracket", "35.26", "39.52", "35.26", "41.5"),
            "D, 100 m": ("bracket", "124.55", "139.66", "124.55", "146.64")}

    def test_a_point_prediction_is_five_percent_either_side_of_the_model(self) -> None:
        assert spread.TOLERANCE == 0.05
        for r in PREDICTED.values():
            model = float(r["model_crossing"])
            assert float(r["predicted_hi"]) == pytest.approx(1.05 * model, abs=0.0103)
            if r["kind"] == "point":
                assert float(r["predicted_lo"]) == pytest.approx(0.95 * model, abs=0.0103)

    def test_a_bracket_starts_at_the_published_equal_power_crossing(self) -> None:
        published = spread.equal_power_crossings()
        assert published == {"C": 35.26, "D": 124.55}
        for r in PREDICTED.values():
            assert float(r["equal_power_crossing"]) == published[r["cell"]]
            if r["kind"] == "bracket":
                assert r["predicted_lo"] == r["equal_power_crossing"]

    def test_the_constants_are_the_simulators_and_free_space(self) -> None:
        assert {(r["threshold_db"], r["path_loss_exp"]) for r in PREDICTED.values()} == {
            ("4", "2")}
        assert (spread.capture.THRESHOLD_DB, spread.PATH_LOSS_EXP) == (4.0, 2.0)

    def test_every_registered_grid_brackets_its_prediction(self) -> None:
        for r in PREDICTED.values():
            grid = [int(n) for n in r["ns3_grid"].split()]
            assert len(grid) == 7
            assert grid[0] < float(r["predicted_lo"]) and float(r["predicted_hi"]) < grid[-1]

    @pytest.mark.parametrize("radius", ["15", "100"])
    def test_the_plans_run_exactly_the_registered_node_counts(self, radius: str) -> None:
        plan = spread.drv.read_plan(PLANS / f"plan_spread_r{radius}.txt")
        cases = {r["cell"]: r for r in PREDICTED.values() if r["radius_m"] == radius}
        assert [(cell, source) for cell, source, _ in plan] == [("C", "period"), ("D", "period")]
        for cell, _, grid in plan:
            assert " ".join(map(str, grid)) == cases[cell]["ns3_grid"]
            assert cases[cell]["ns3_stem"] == f"ns3_spread_r{radius}"
        text = (PLANS / f"plan_spread_r{radius}.txt").read_text()
        assert f"--radius-m {radius} --path-loss-exp 2" in text

    @pytest.mark.frozen
    def test_the_models_crossings_recompute_to_the_committed_file(self) -> None:
        """Thirty seeds at seven node counts per case; no input that the ns-3 runs change."""
        again = spread.model_crossings(workers=4)
        assert {c: f"{x:.2f}" for c, x in again.items()} == {
            c: f"{float(r['model_crossing']):.2f}" for c, r in PREDICTED.items()}


class TestTheScenarioOptionsAreLeftOutAtTheirDefaults:
    """The published scenario must be invoked exactly as it always was."""

    def test_no_geometry_argument_unless_one_is_asked_for(self) -> None:
        args = spread.drv.scenario_args(146, 50.0, 40, 1, 20.0, Path("p"))
        assert not [a for a in args if "radius" in a or "pathLoss" in a]
        args = spread.drv.scenario_args(146, 50.0, 40, 1, 20.0, Path("p"), radius_m=15.0,
                                        path_loss_exp=2.0)
        assert args[-2:] == ["--radiusM=15.0", "--pathLossExp=2.0"]

    def test_the_scenario_keeps_its_published_placement_and_power_at_zero(self) -> None:
        cc = (REPO / "ns3" / "authbc-delay.cc").read_text(encoding="utf-8")
        assert "double radiusM = 0.0;" in cc and "double pathLossExp = 0.0;" in cc
        assert '"Exponent", DoubleValue(pathLossExp)' in cc
        assert "posAlloc->Add(Vector(i * 0.01, 0.0, 0.0));" in cc
        assert "place->SetStream(4096);" in cc


class TestScoringRefusesAnUnfinishedCampaign:
    def test_without_a_runs_file_nothing_is_scored(self, tmp_path: Path,
                                                    monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(spread, "RAW", tmp_path)
        assert spread.score() == []

    def test_a_bracketed_crossing_on_part_of_the_grid_is_not_scored(
            self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        period = spread.provenance.as_written(1000.0 / spread.drv.CELLS["C"].fps)
        rows = [{"cell": "C", "n_nodes": n, "seed": s, "jitter_ms": period, "skew_ppm": 0,
                 "delivered_frac": d}
                for n, d in ((37, 0.957), (38, 0.954), (39, 0.951), (40, 0.948))
                for s in range(1, 31)]
        with (tmp_path / "ns3_spread_r15_runs.csv").open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
        monkeypatch.setattr(spread, "RAW", tmp_path)
        assert spread.ns3_crossing(spread.CASES[0])["bracketed"] == 1
        assert spread.score() == []
