"""The batch size as a dimension of the capacity (docs/NMAX_DIRECT_EXPECTATIONS.md, F6).

Every capacity simulated before follow-up F6 had one record to a frame or four (audit F80,
open item G31). `batch_capacity_predictions.csv` was committed before the ns-3 runs it
predicts. Held here: that it says what was registered, that the line's column is the line as
calibrated before, that the plan runs exactly the registered node counts, and that nothing is
scored from an unfinished campaign.
"""
from __future__ import annotations

import csv
import importlib.util
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
RAW = REPO / "results" / "raw"
sys.path.insert(0, str(REPO / "ns3"))
sys.path.insert(0, str(REPO / "analysis"))
_spec = importlib.util.spec_from_file_location("batch_capacity",
                                               REPO / "analysis" / "batch_capacity.py")
assert _spec and _spec.loader
batch = importlib.util.module_from_spec(_spec)
sys.modules["batch_capacity"] = batch
_spec.loader.exec_module(batch)

PREDICTED = batch.registered()
CELLS = ("B2", "B3", "B8")


class TestTheRegisteredPredictions:
    def test_three_cells_as_registered(self) -> None:
        """The numbers of the table in docs/NMAX_DIRECT_EXPECTATIONS.md, F6."""
        assert {c: (r["batch"], r["frame_bytes"], r["frames_per_s"], r["line_crossing"],
                    r["model_crossing"], r["single_ceiling"]) for c, r in PREDICTED.items()} == {
            "B2": ("2", "155", "25.0", "66.0", "66.6", "75"),
            "B3": ("3", "164", "16.6667", "96.29", "95.96", "113"),
            "B8": ("8", "209", "6.25", "225.88", "220.64", "215")}

    def test_the_deadline_named_is_the_smallest_that_admits_the_batch(self) -> None:
        assert {c: r["deadline_ms"] for c, r in PREDICTED.items()} == {
            "B2": "60", "B3": "80", "B8": "180"}

    def test_the_line_is_the_one_calibrated_before_and_nothing_is_refitted(self) -> None:
        slope, _ = batch.airtime.calibrate(batch.airtime.crossings("period"))
        line = batch.airtime.predictions(slope, CELLS)
        for cell, r in PREDICTED.items():
            assert float(r["line_slope"]) == round(slope, 4) == 0.071
            assert float(r["line_crossing"]) == round(line[cell], 2)

    def test_the_bands_are_the_ones_registered_for_the_line_and_for_the_model(self) -> None:
        assert (batch.LINE_TOLERANCE, batch.MODEL_TOLERANCE) == (0.06, 0.03)
        # each band is of the unrounded crossing and both are printed to 0.01: the two
        # roundings together move a bound by at most 0.005 * 1.06 + 0.005
        for r in PREDICTED.values():
            line, model = float(r["line_crossing"]), float(r["model_crossing"])
            assert float(r["line_lo"]) == pytest.approx(0.94 * line, abs=0.0103)
            assert float(r["line_hi"]) == pytest.approx(1.06 * line, abs=0.0103)
            assert float(r["model_lo"]) == pytest.approx(0.97 * model, abs=0.0103)
            assert float(r["model_hi"]) == pytest.approx(1.03 * model, abs=0.0103)

    def test_every_registered_grid_brackets_both_bands_of_the_model_and_the_lines_value(
            self) -> None:
        for r in PREDICTED.values():
            grid = [int(n) for n in r["ns3_grid"].split()]
            assert len(grid) == 7
            assert grid[0] < float(r["model_lo"]) and float(r["model_hi"]) < grid[-1]
            assert grid[0] < float(r["line_crossing"]) < grid[-1]

    def test_the_plan_runs_exactly_the_registered_node_counts(self) -> None:
        plan = batch.drv.read_plan(REPO / "experiments" / "nmax-direct" / "plan_batch.txt")
        assert [(cell, source) for cell, source, _ in plan] == [(c, "period") for c in CELLS]
        for cell, _, grid in plan:
            assert " ".join(map(str, grid)) == PREDICTED[cell]["ns3_grid"]
            assert tuple(grid) == batch.GRIDS[cell][1]

    @pytest.mark.frozen
    def test_the_models_column_recomputes_to_the_committed_file(
            self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Thirty seeds at nine node counts per cell; the model has no input these runs change.

        The model's worker is sent to a pool by name. Another test module loads its own copy
        of `dcf_model_check` under that name, so the name is pointed back at the copy in use."""
        monkeypatch.setitem(sys.modules, "dcf_model_check", batch.rule)
        fields = ("cell", "model_crossing", "model_lo", "model_hi", "line_crossing")
        again = {r["cell"]: {k: str(r[k]) for k in fields} for r in batch.predict(workers=4)}
        assert again == {c: {k: r[k] for k in fields} for c, r in PREDICTED.items()}


class TestScoringRefusesAnUnfinishedCampaign:
    def test_without_a_runs_file_nothing_is_scored(self, tmp_path: Path,
                                                    monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(batch, "RAW", tmp_path)
        assert batch.ns3_crossings() == {} and batch.score() == []

    def test_node_counts_short_of_thirty_runs_do_not_enter(self, tmp_path: Path,
                                                           monkeypatch: pytest.MonkeyPatch
                                                           ) -> None:
        period = batch.provenance.as_written(1000.0 / batch.drv.CELLS["B2"].fps)
        rows = [{"cell": "B2", "n_nodes": n, "seed": s, "jitter_ms": period, "skew_ppm": 0,
                 "delivered_frac": d}
                for n, d, seeds in ((60, 0.97, 30), (62, 0.96, 30), (64, 0.93, 29))
                for s in range(1, seeds + 1)]
        with (tmp_path / "ns3_batch_runs.csv").open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
        monkeypatch.setattr(batch, "RAW", tmp_path)
        # two complete points, both above the threshold: the crossing is not bracketed
        assert batch.score() == []

    def test_a_bracketed_crossing_on_an_unfinished_grid_is_not_scored(
            self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Four of B8's seven node counts were complete, and bracketed the crossing, an hour
        before the campaign ended. Scoring then would have been scoring a different test."""
        period = batch.provenance.as_written(1000.0 / batch.drv.CELLS["B8"].fps)
        rows = [{"cell": "B8", "n_nodes": n, "seed": s, "jitter_ms": period, "skew_ppm": 0,
                 "delivered_frac": d}
                for n, d in ((205, 0.957), (212, 0.955), (219, 0.952), (226, 0.948))
                for s in range(1, 31)]
        with (tmp_path / "ns3_batch_runs.csv").open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
        monkeypatch.setattr(batch, "RAW", tmp_path)
        assert batch.ns3_crossings()["B8"]["bracketed"] == 1
        assert batch.score() == []


REGISTRATION = "64322fc"
SCORED = {r["cell"]: r for r in csv.DictReader(
    ln for ln in (RAW / "batch_capacity.csv").read_text().splitlines() if not ln.startswith("#"))}
RUNS = batch.drv.read_runs(RAW / "ns3_batch_runs.csv")
NUMBERS = dict(re.findall(r"\\newcommand\{\\(\w+)\}\{(.*)\}",
                          (REPO / "paper" / "numbers.tex").read_text(encoding="utf-8")))


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True,
                          check=True).stdout


def _body(text: str) -> list[str]:
    return [ln for ln in text.splitlines() if not ln.startswith("#")]


class TestTheRegistrationPrecededTheRuns:
    def test_the_predictions_are_in_a_commit_that_holds_no_run(self) -> None:
        files = _git("ls-tree", "-r", "--name-only", REGISTRATION)
        assert "results/raw/batch_capacity_predictions.csv" in files
        assert "ns3_batch" not in files and "results/raw/batch_capacity.csv" not in files

    def test_the_predictions_have_not_changed_since(self) -> None:
        then = _git("show", f"{REGISTRATION}:results/raw/batch_capacity_predictions.csv")
        assert _body(then) == _body((RAW / "batch_capacity_predictions.csv").read_text())

    def test_the_registration_text_names_the_numbers_that_were_scored(self) -> None:
        text = _git("show", f"{REGISTRATION}:docs/NMAX_DIRECT_EXPECTATIONS.md")
        for needle in ("| B2 | 2 | 60 ms | 155 B | 25 | **66.00** | 62.04–69.96 | **66.60** |",
                       "| B3 | 3 | 80 ms | 164 B | 16.67 | **96.29** | 90.52–102.07 | **95.96** |",
                       "| B8 | 8 | 180 ms | 209 B | 6.25 | **225.88** | 212.33–239.44 | "
                       "**220.64** |",
                       "No ns-3 run of any of these three cells has been made"):
            assert needle in text, needle


class TestTheRunsAreTheRegisteredOnes:
    def test_six_hundred_and_thirty_runs_thirty_seeds_at_each_registered_node_count(self) -> None:
        assert len(RUNS) == 630
        seeds: dict[tuple[str, int], list[int]] = {}
        for r in RUNS:
            seeds.setdefault((r["cell"], int(r["n_nodes"])), []).append(int(r["seed"]))
        assert set(seeds) == {(c, n) for c in CELLS for n in batch.GRIDS[c][1]}
        assert all(sorted(v) == list(range(1, 31)) for v in seeds.values())

    def test_every_run_redraws_its_send_time_within_one_period_for_twenty_seconds(self) -> None:
        for r in RUNS:
            cell = batch.drv.CELLS[r["cell"]]
            assert float(r["jitter_ms"]) == batch.provenance.as_written(1000.0 / cell.fps)
            assert float(r["skew_ppm"]) == 0.0 and float(r["sim_time_s"]) == 20.0
            assert int(r["frame_bytes"]) == cell.frame_bytes

    def test_a_run_delivers_a_possible_fraction(self) -> None:
        for r in RUNS:
            n, tx, rx = int(r["n_nodes"]), int(r["tx_frames"]), int(r["rx_frames"])
            assert 0 < rx <= tx * (n - 1)
            assert float(r["delivered_frac"]) == pytest.approx(rx / (tx * (n - 1)), abs=1e-6)


class TestThePredictionsAsScored:
    def test_the_table_is_what_the_script_gives_from_the_runs(self) -> None:
        again = {r["cell"]: {k: str(v) for k, v in r.items()} for r in batch.score()}
        assert again == SCORED and set(SCORED) == set(CELLS)

    def test_every_crossing_is_inside_both_registered_bands(self) -> None:
        for cell, r in SCORED.items():
            reg, x = PREDICTED[cell], float(r["ns3_crossing"])
            assert float(reg["line_lo"]) <= x <= float(reg["line_hi"]), cell
            assert float(reg["model_lo"]) <= x <= float(reg["model_hi"]), cell
            assert (r["line_within_band"], r["model_within_band"]) == ("1", "1")

    def test_the_crossings_and_how_far_each_is_from_its_predictions(self) -> None:
        assert {c: (r["ns3_crossing"], r["vs_line_pct"], r["vs_model_pct"])
                for c, r in SCORED.items()} == {
            "B2": ("66.73", "1.11", "0.2"), "B3": ("96.51", "0.23", "0.57"),
            "B8": ("222.33", "-1.57", "0.77")}

    def test_one_crossing_recomputed_by_hand_from_its_two_bracketing_means(self) -> None:
        """B2: between 66 and 68 nodes, by straight line through the two means."""
        def mean_at(n: int) -> float:
            v = [float(r["delivered_frac"]) for r in RUNS
                 if r["cell"] == "B2" and int(r["n_nodes"]) == n]
            return sum(v) / len(v)
        above, below = mean_at(66), mean_at(68)
        assert above > 0.95 > below
        by_hand = 66 + 2 * (above - 0.95) / (above - below)
        assert by_hand == pytest.approx(float(SCORED["B2"]["ns3_crossing"]), abs=0.006)

    def test_the_model_is_nearer_than_the_line_at_the_largest_batch(self) -> None:
        """Where the two predictions parted by 2.4 %, the simulator sided with the model."""
        r = SCORED["B8"]
        assert abs(float(r["vs_model_pct"])) < abs(float(r["vs_line_pct"]))
        assert float(r["vs_line_pct"]) < 0 < float(r["vs_model_pct"])

    def test_the_single_ceiling_misses_by_more_than_either(self) -> None:
        worst = {c: abs(float(r["vs_ceiling_pct"])) for c, r in SCORED.items()}
        assert worst["B2"] > 10 and worst["B3"] > 10
        for c, r in SCORED.items():
            assert worst[c] > abs(float(r["vs_line_pct"])), c

    def test_the_weaker_expectation_had_the_trend_and_missed_the_middle_cell(self) -> None:
        """Recorded beside the predictions: B2 within a percent of its line, B3 about one
        percent below, B8 about two below. The sign for B3 was wrong."""
        line = {c: float(r["vs_line_pct"]) for c, r in SCORED.items()}
        assert line["B2"] > line["B3"] > line["B8"]
        assert 1.0 < line["B2"] < 1.5 and line["B3"] > 0 and -2.5 < line["B8"] < -1.0
        outcome = (REPO / "docs" / "NMAX_DIRECT_EXPECTATIONS.md").read_text(encoding="utf-8")
        assert "The weaker expectation had the trend and missed the middle cell" in outcome


class TestWhatTheDocumentsQuote:
    PAPER = re.sub(r"\s+", " ", (REPO / "paper" / "main.tex").read_text(encoding="utf-8"))
    CODESIGN = re.sub(r"\s+", " ", (REPO / "thesis" / "ch08_codesign.tex").read_text())

    def test_the_macros_are_the_table(self) -> None:
        for cell, tag in (("B2", "Two"), ("B3", "Three"), ("B8", "Eight")):
            r = SCORED[cell]
            assert NUMBERS[f"batNs{tag}"] == f"{float(r['ns3_crossing']):.1f}"
            assert NUMBERS[f"batLine{tag}"] == f"{float(r['line_crossing']):.1f}"
            assert NUMBERS[f"batModel{tag}"] == f"{float(r['model_crossing']):.1f}"
        assert (NUMBERS["batLineWorst"], NUMBERS["batModelWorst"]) == ("1.6", "0.8")

    def test_the_paper_says_they_were_predicted_first_and_what_they_are_not(self) -> None:
        assert "were predicted before they were simulated" in self.PAPER
        assert "within \\batLineWorst\\% of the rule and \\batModelWorst\\% of the access-rule " \
               "model" in self.PAPER
        assert "nothing else here is evaluated at them" in self.PAPER
        assert "for batches of one and four records only" not in self.PAPER

    def test_the_thesis_tabulates_all_three_and_scopes_them(self) -> None:
        for needle in ("\\label{tab:batchdim}", "\\batNsTwo\\ \\batCiTwo",
                       "\\batNsEight\\ \\batCiEight", "All six held.",
                       "the three deadlines are hypothetical operating points"):
            assert needle in self.CODESIGN, needle
