"""The direct 802.11 `N_max` search: summary logic and cells (docs/NMAX_DIRECT_EXPECTATIONS.md).

The simulator runs need NS-3 and are not repeated here. What is held instead:

* the summary is a pure function of the raw runs file, and the committed summary **is** that
  function applied to the committed runs — so the table cannot drift from the simulator output;
* the reported `N_max` is the sample's own crossing. The first version reported the median of the
  bootstrap replicates instead, which read 31 in a cell where the sample's crossing was 29;
* every cell simulates the frame the design ladder actually lists.
"""

from __future__ import annotations

import csv
import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
RAW = REPO / "results" / "raw"

_spec = importlib.util.spec_from_file_location("run_nmax_direct",
                                               REPO / "ns3" / "run_nmax_direct.py")
assert _spec and _spec.loader
drv = importlib.util.module_from_spec(_spec)
sys.modules["run_nmax_direct"] = drv          # dataclasses resolve annotations through sys.modules
_spec.loader.exec_module(drv)


def _rows(path: Path) -> list[dict[str, str]]:
    return list(csv.DictReader(ln for ln in path.read_text().splitlines()
                               if not ln.startswith("#")))


def _runs(cell: str, per_n: dict[int, list[float]], jitter: str = "0",
          skew: str = "0") -> list[dict]:
    return [{"cell": cell, "n_nodes": str(n), "seed": str(seed), "delivered_frac": str(v),
             "jitter_ms": jitter, "skew_ppm": skew}
            for n, values in per_n.items() for seed, v in enumerate(values, 1)]


class TestSummaryLogic:
    PER_N = {20: [0.99] * 4, 24: [0.97, 0.96, 0.97, 0.96], 28: [0.96, 0.93, 0.96, 0.93],
             32: [0.90] * 4}

    def _crossing(self, runs: list[dict], seeds: int = 4) -> dict:
        return next(r for r in drv.summarise(runs, seeds) if r["n_nodes"] == "CROSSING")

    def test_n_max_is_the_samples_crossing(self) -> None:
        """N=28 has mean 0.945: it fails, so the sample's answer is 24."""
        row = self._crossing(_runs("A", self.PER_N))
        assert row["n_max_mean"] == 24 and row["bracketed"] == 1
        assert row["n_max_ci_lo"] <= 24 <= row["n_max_ci_hi"]
        assert row["deviation_pct"] == round(100.0 * (24 - 31) / 31, 1)

    def test_the_interpolated_crossing_by_hand(self) -> None:
        """0.965 at N=24 and 0.945 at N=28: three quarters of the way down is N = 27."""
        row = self._crossing(_runs("A", self.PER_N))
        assert row["n_cross_interp"] == pytest.approx(27.0)
        assert row["n_cross_interp_lo"] <= 27.0 <= row["n_cross_interp_hi"]

    def test_the_per_run_criterion_needs_95_percent_of_runs_to_pass(self) -> None:
        """At N=24 every run passes and at N=28 only half do, so here it agrees with the mean."""
        assert self._crossing(_runs("A", self.PER_N))["n_max_per_run"] == 24

    def test_it_is_stricter_than_the_mean_when_one_run_in_four_fails(self) -> None:
        per_n = {20: [0.99] * 4, 24: [0.99, 0.99, 0.99, 0.94], 28: [0.90] * 4}
        row = self._crossing(_runs("A", per_n))
        assert row["n_max_mean"] == 24 and row["n_max_per_run"] == 20

    def test_a_node_count_with_missing_seeds_is_left_out(self) -> None:
        runs = _runs("A", self.PER_N)
        runs = [r for r in runs if not (r["n_nodes"] == "24" and r["seed"] == "4")]
        row = self._crossing(runs)
        assert row["grid"] == "20 28 32" and row["n_max_mean"] == 20

    def test_an_unbracketed_crossing_is_flagged_and_not_interpolated(self) -> None:
        row = self._crossing(_runs("A", {20: [0.99] * 4, 24: [0.98] * 4}))
        assert row["bracketed"] == 0 and "n_cross_interp" not in row

    def test_each_traffic_source_is_summarised_separately(self) -> None:
        other = {20: [0.99] * 4, 24: [0.9] * 4}
        runs = (_runs("A", self.PER_N) + _runs("A", other, "1")
                + _runs("A", {20: [0.9] * 4}, "1", "5000"))
        rows = [r for r in drv.summarise(runs, 4) if r["n_nodes"] == "CROSSING"]
        assert [(r["jitter_ms"], r["skew_ppm"], r["n_max_mean"]) for r in rows] == [
            ("0", "0", 24), ("1", "0", 20), ("1", "5000", 0)]

    def test_each_row_carries_the_load_in_both_units(self) -> None:
        row = next(r for r in drv.summarise(_runs("D", {120: [0.95] * 4}), 4)
                   if r["n_nodes"] == 120)
        # 120 nodes x 12.5 frames/s x 338 us of busy medium per 173 B frame
        assert row["airtime_occupancy"] == pytest.approx(120 * 12.5 * 338e-6, abs=1e-4)
        assert row["model_util"] == pytest.approx(2.011, abs=1e-3)


class TestTrafficSource:
    def test_a_number_is_milliseconds_and_period_is_one_sending_period(self) -> None:
        assert drv.source_of("0", 12.5) == (0.0, 0.0)
        assert drv.source_of("0.1", 12.5) == (0.1, 0.0)
        assert drv.source_of("period", 12.5) == (80.0, 0.0)
        assert drv.source_of("period", 50) == (20.0, 0.0)

    def test_a_rate_offset_follows_a_slash(self) -> None:
        assert drv.source_of("0.1/5000", 50) == (0.1, 5000.0)

    def test_runs_recorded_before_an_option_existed_did_not_use_it(self, tmp_path) -> None:
        p = tmp_path / "runs.csv"
        p.write_text("# old\ncell,n_nodes,seed,delivered_frac\nA,25,1,0.97\n")
        (row,) = drv.read_runs(p)
        assert (row["jitter_ms"], row["skew_ppm"]) == ("0", "0")


class TestRunPlan:
    def test_lines_are_cell_jitter_and_node_counts(self, tmp_path) -> None:
        p = tmp_path / "plan.txt"
        p.write_text("# stage 2\nA 0.1/5000 28 30 32   # fine grid\n\nRD period 240 300\n")
        assert drv.read_plan(p) == [("A", "0.1/5000", [28, 30, 32]),
                                    ("RD", "period", [240, 300])]

    @pytest.mark.parametrize("line", ["Z 1 30", "A 1"])
    def test_an_unknown_cell_or_a_line_without_node_counts_is_refused(self, tmp_path,
                                                                      line: str) -> None:
        p = tmp_path / "plan.txt"
        p.write_text(line + "\n")
        with pytest.raises(SystemExit, match="bad plan line"):
            drv.read_plan(p)


class TestCellsAreTheLaddersFrames:
    """A cell that simulated a frame the ladder does not list would validate nothing."""

    LADDER = {(r["op"], r["format"], r["rung"]): r for r in _rows(RAW / "design_ladder.csv")}

    @pytest.mark.parametrize("name", sorted(drv.CELLS))
    def test_frame_rate_and_model_value(self, name: str) -> None:
        cell = drv.CELLS[name]
        op = {50.0: "adopted", 20.0: "relaxed"}[cell.lam]
        fmt, rung = cell.label.split("/")
        row = self.LADDER[(op, fmt, rung)]
        assert cell.frame_bytes == round(float(row["frame_bytes"]))
        assert cell.batch == int(row["batch"]) and cell.lam == float(row["lambda_rec_per_s"])
        assert cell.model_n == int(row["n_max_v95"])

    def test_the_registered_six_are_unchanged(self) -> None:
        """Committed data-free in 6f82599; the prediction is only a prediction if these stay."""
        assert {k: (c.frame_bytes, c.batch, c.lam, c.model_n) for k, c in drv.CELLS.items()
                if k in "ABCDEF"} == {
            "A": (174, 1, 50.0, 31), "B": (300, 4, 50.0, 97), "C": (146, 1, 50.0, 34),
            "D": (173, 4, 50.0, 142), "E": (565, 4, 50.0, 49), "F": (372, 4, 50.0, 80)}


class TestTheCommittedSummaryIsTheCommittedRuns:
    RUNS = drv.read_runs(RAW / "ns3_nmax_direct_runs.csv")
    SUMMARY = _rows(RAW / "ns3_nmax_direct.csv")

    def test_summary_equals_summarise_of_runs(self) -> None:
        rebuilt = drv.summarise(self.RUNS, 30)
        fields = list(self.SUMMARY[0])
        assert [{k: str(r.get(k, "")) for k in fields} for r in rebuilt] == self.SUMMARY

    def test_every_summarised_point_has_thirty_seeds_numbered_1_to_30(self) -> None:
        def point(r: dict[str, str]) -> tuple[str, ...]:
            return (r["cell"], r["jitter_ms"], r.get("skew_ppm") or "0", r["n_nodes"])

        seeds: dict[tuple, set[int]] = {}
        for r in self.RUNS:
            seeds.setdefault(point(r), set()).add(int(r["seed"]))
        points = {point(r) for r in self.SUMMARY if r["n_nodes"] != "CROSSING"}
        assert points and all(seeds[p] == set(range(1, 31)) for p in points)

    def test_every_run_is_a_possible_simulator_output(self) -> None:
        for r in self.RUNS:
            cell = drv.CELLS[r["cell"]]
            n, tx, rx = int(r["n_nodes"]), int(r["tx_frames"]), int(r["rx_frames"])
            assert int(r["frame_bytes"]) == cell.frame_bytes
            assert float(r["frames_per_s"]) == cell.fps
            assert 0 < rx <= tx * (n - 1)
            assert float(r["delivered_frac"]) == pytest.approx(rx / (tx * (n - 1)), abs=1e-6)
            # each node sends for sim_time seconds at fps; the first frame leaves one period in
            expected = n * cell.fps * float(r["sim_time_s"])
            assert expected - 2 * n <= tx <= expected
