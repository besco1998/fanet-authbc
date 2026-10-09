"""Capacity with the nodes spread out and capture at work (docs/NMAX_DIRECT_EXPECTATIONS.md, F7).

`spread_capacity_predictions.csv` was committed before the ns-3 runs it predicts. Held here:
that it says what was registered, that the two kinds of prediction are what the registration
text says they are, that the plans run exactly the registered node counts with the registered
geometry, and that nothing is scored from an unfinished campaign.
"""
from __future__ import annotations

import csv
import importlib.util
import re
import subprocess
import sys
from decimal import ROUND_HALF_UP, Decimal
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


REGISTRATION = "db0bca1"
SCORED = {r["case"]: r for r in csv.DictReader(
    ln for ln in (RAW / "spread_capacity.csv").read_text().splitlines()
    if not ln.startswith("#"))}
NUMBERS = dict(re.findall(r"\\newcommand\{\\(\w+)\}\{(.*)\}",
                          (REPO / "paper" / "numbers.tex").read_text(encoding="utf-8")))
RUNS = {radius: spread.drv.read_runs(RAW / f"ns3_spread_r{radius}_runs.csv")
        for radius in ("15", "100")}


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True,
                          check=True).stdout


class TestTheRegistrationPrecededTheRuns:
    def test_the_predictions_are_in_a_commit_that_holds_no_run(self) -> None:
        files = _git("ls-tree", "-r", "--name-only", REGISTRATION)
        assert "results/raw/spread_capacity_predictions.csv" in files
        assert "src/authbc/sim/dcf_capture.py" in files
        assert "ns3_spread_r" not in files and "results/raw/spread_capacity.csv" not in files

    def test_the_predictions_and_the_model_have_not_changed_since(self) -> None:
        def body(text: str) -> list[str]:
            return [ln for ln in text.splitlines() if not ln.startswith("#")]
        then = _git("show", f"{REGISTRATION}:results/raw/spread_capacity_predictions.csv")
        assert body(then) == body((RAW / "spread_capacity_predictions.csv").read_text())
        for path in ("src/authbc/sim/dcf_capture.py", "src/authbc/sim/dcf_unsaturated.py"):
            assert _git("show", f"{REGISTRATION}:{path}") == (REPO / path).read_text(), path

    def test_the_disclosures_are_in_the_registration(self) -> None:
        text = _git("show", f"{REGISTRATION}:docs/NMAX_DIRECT_EXPECTATIONS.md")
        for needle in ("Three single-seed runs were made to check that the new option works",
                       "0.9333 with the published geometry, 0.9466",
                       "a scratch copy was run at a radius of",
                       "Hidden stations are not"):
            assert needle in text, needle


class TestTheRunsAreTheRegisteredOnes:
    @pytest.mark.parametrize("radius", ["15", "100"])
    def test_thirty_seeds_at_each_registered_node_count_and_no_other(self, radius: str) -> None:
        runs = RUNS[radius]
        assert len(runs) == 420
        seeds: dict[tuple[str, int], list[int]] = {}
        for r in runs:
            seeds.setdefault((r["cell"], int(r["n_nodes"])), []).append(int(r["seed"]))
        registered = {(r["cell"], int(n)) for r in PREDICTED.values() if r["radius_m"] == radius
                      for n in r["ns3_grid"].split()}
        assert set(seeds) == registered
        assert all(sorted(v) == list(range(1, 31)) for v in seeds.values())

    @pytest.mark.parametrize("radius", ["15", "100"])
    def test_the_file_says_which_geometry_it_was_run_with(self, radius: str) -> None:
        head = (RAW / f"ns3_spread_r{radius}_runs.csv").read_text().splitlines()[:30]
        assert any(ln.startswith("# config_hash=") for ln in head)
        for r in RUNS[radius]:
            cell = spread.drv.CELLS[r["cell"]]
            assert int(r["frame_bytes"]) == cell.frame_bytes and float(r["sim_time_s"]) == 20.0
            n, tx, rx = int(r["n_nodes"]), int(r["tx_frames"]), int(r["rx_frames"])
            assert 0 < rx <= tx * (n - 1)


class TestThePredictionsAsScored:
    def test_the_table_is_what_the_script_gives_from_the_runs(self) -> None:
        again = {r["case"]: {k: str(v) for k, v in r.items()} for r in spread.score()}
        assert again == SCORED and set(SCORED) == set(PREDICTED)

    def test_all_four_crossings_are_inside_what_was_registered(self) -> None:
        for case, r in SCORED.items():
            x = float(r["ns3_crossing"])
            assert float(PREDICTED[case]["predicted_lo"]) <= x <= \
                float(PREDICTED[case]["predicted_hi"]), case
            assert r["within_prediction"] == "1"

    def test_the_crossings_and_how_far_each_is_from_the_model(self) -> None:
        assert {c: (r["ns3_crossing"], r["vs_model_pct"], r["vs_equal_power_pct"])
                for c, r in SCORED.items()} == {
            "C, 15 m": ("39.58", "0.15", "12.25"), "D, 15 m": ("140.35", "0.49", "12.69"),
            "C, 100 m": ("39.4", "-0.3", "11.74"), "D, 100 m": ("139.34", "-0.23", "11.87")}

    def test_one_crossing_recomputed_by_hand(self) -> None:
        """The design at 100 m, between 134 and 140 nodes."""
        def mean_at(n: int) -> float:
            v = [float(r["delivered_frac"]) for r in RUNS["100"]
                 if r["cell"] == "D" and int(r["n_nodes"]) == n]
            return sum(v) / len(v)
        above, below = mean_at(134), mean_at(140)
        assert above > 0.95 > below
        by_hand = 134 + 6 * (above - 0.95) / (above - below)
        assert by_hand == pytest.approx(float(SCORED["D, 100 m"]["ns3_crossing"]), abs=0.006)

    def test_equal_power_was_the_unfavourable_assumption(self) -> None:
        gains = [float(r["vs_equal_power_pct"]) for r in SCORED.values()]
        assert 11.5 < min(gains) and max(gains) < 13.0
        assert (NUMBERS["sprGainLo"], NUMBERS["sprGainHi"]) == ("12", "13")

    def test_the_ratio_of_design_to_baseline_does_not_move(self) -> None:
        x = {c: float(r["ns3_crossing"]) for c, r in SCORED.items()}
        ratios = (124.55 / 35.26, x["D, 15 m"] / x["C, 15 m"], x["D, 100 m"] / x["C, 100 m"])
        assert max(ratios) - min(ratios) < 0.02
        assert NUMBERS["sprRatioNear"] == NUMBERS["sprRatioFar"] == NUMBERS["ratioLean"] == "3.5"

    def test_the_weaker_expectation_had_the_sign_and_was_too_large(self) -> None:
        """Recorded beside the predictions: at 100 m, below the 15 m figure 'by a few percent'.
        It is below, by under one percent."""
        x = {c: float(r["ns3_crossing"]) for c, r in SCORED.items()}
        for cell in ("C", "D"):
            drop = 1 - x[f"{cell}, 100 m"] / x[f"{cell}, 15 m"]
            assert 0.0 < drop < 0.01
        assert NUMBERS["sprFarBelowPct"] == "0.7"
        outcome = (REPO / "docs" / "NMAX_DIRECT_EXPECTATIONS.md").read_text(encoding="utf-8")
        assert "The weaker expectation had the sign and was too large" in outcome


class TestWhatTheDocumentsQuote:
    PAPER = re.sub(r"\s+", " ", (REPO / "paper" / "main.tex").read_text(encoding="utf-8"))
    CODESIGN = re.sub(r"\s+", " ", (REPO / "thesis" / "ch08_codesign.tex").read_text())

    def test_the_macros_are_the_table(self) -> None:
        for case, tag in (("C, 15 m", "NearBase"), ("D, 15 m", "NearDesign"),
                          ("C, 100 m", "FarBase"), ("D, 100 m", "FarDesign")):
            # half up, as the generator rounds: 140.35 is 140.4 in the text
            assert NUMBERS[f"spr{tag}"] == str(Decimal(SCORED[case]["ns3_crossing"]).quantize(
                Decimal("0.1"), rounding=ROUND_HALF_UP))
        assert (NUMBERS["sprModelBase"], NUMBERS["sprModelDesign"]) == ("39.5", "139.7")
        assert NUMBERS["sprModelWorst"] == "0.5"

    def test_the_paper_says_conservative_and_says_what_was_not_tested(self) -> None:
        for needle in ("gave \\sprModelBase{} and \\sprModelDesign{} nodes for baseline and design "
                       "before the runs",
                       "are therefore conservative for unequal power",
                       "hidden stations, which would lower the capacity, are not in this test",
                       "Unequal power with capture was simulated separately and raises them"):
            assert needle in self.PAPER, needle
        assert "capture, hidden terminals, spatial reuse and mobility are absent" not in self.PAPER

    def test_the_thesis_tabulates_the_four_and_keeps_the_caveat(self) -> None:
        for needle in ("\\label{tab:spread}", "\\sprNearDesign\\ \\sprCiNearDesign",
                       "\\sprFarDesign\\ \\sprCiFarDesign", "All four held",
                       "It was the unfavourable one.",
                       "it was the right sign and too large"):
            assert needle in self.CODESIGN, needle
