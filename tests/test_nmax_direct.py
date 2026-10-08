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


class TestThePlanIsWhatWasRun:
    """The node counts simulated are a committed file, so the campaign can be run again."""

    PLAN = REPO / "experiments" / "nmax-direct" / "plan.txt"

    def test_a_plan_is_recovered_from_runs(self) -> None:
        runs = _runs("A", {29: [0.9], 31: [0.9]}) \
            + _runs("A", {30: [0.9]}, jitter="20") \
            + _runs("D", {120: [0.9]}, jitter="0.1", skew="5000")
        assert drv.plan_of(runs) == [("A", "0", [29, 31]), ("A", "period", [30]),
                                     ("D", "0.1/5000", [120])]

    def test_a_jitter_of_one_period_is_written_as_the_word(self) -> None:
        # cell D sends 12.5 frames/s: one period is 80 ms, and 20 ms is not
        runs = _runs("D", {120: [0.9]}, jitter="80") + _runs("D", {121: [0.9]}, jitter="20")
        assert drv.plan_of(runs) == [("D", "20", [121]), ("D", "period", [120])]

    def test_a_period_six_figures_cannot_hold_is_still_one_period(self) -> None:
        """EMSS sends 50.5 frames/s: one period is 19.80198… ms, written as 19.802 (F56).

        Compared with the exact value it is no longer "one period": the plan would name it as a
        number, a resumed campaign would run it all again, and three readers dropped the cell.
        """
        from authbc.bench import provenance

        exact = 1000.0 / drv.CELLS["SE"].fps
        assert f"{exact:g}" == "19.802" and float("19.802") != exact
        assert provenance.as_written(exact) == float("19.802")
        runs = _runs("SE", {34: [0.9]}, jitter="19.802")
        assert drv.plan_of(runs) == [("SE", "period", [34])]

    def test_every_cell_run_at_one_period_is_summarised_as_one_period(self) -> None:
        from authbc.bench import provenance

        crossings = [r for r in _rows(RAW / "ns3_nmax_direct.csv")
                     if r["n_nodes"] == "CROSSING" and r["skew_ppm"] == "0"]

        def period(r: dict[str, str]) -> float:
            return 1000.0 / drv.CELLS[r["cell"]].fps

        near = {r["cell"] for r in crossings
                if abs(float(r["jitter_ms"]) - period(r)) < 1e-3 * period(r)}
        matched = {r["cell"] for r in crossings
                   if float(r["jitter_ms"]) == provenance.as_written(period(r))}
        assert matched == near and {"SM", "ST", "SG", "SE", "SW"} <= matched

    def test_the_committed_plan_names_exactly_the_points_on_file(self) -> None:
        runs = drv.read_runs(RAW / "ns3_nmax_direct_runs.csv")
        assert drv.read_plan(self.PLAN) == drv.plan_of(runs)

    def test_reading_back_a_written_plan_gives_the_same_plan(self, tmp_path) -> None:
        plan = [("A", "0", [29, 31]), ("RD", "period", [240, 300]), ("D", "0.1/5000", [120])]
        out = tmp_path / "plan.txt"
        out.write_text(drv.render_plan(plan))
        assert drv.read_plan(out) == plan


class TestWhichRunsAPlanStillNeeds:
    def test_seeds_run_from_one_by_default(self) -> None:
        todo = drv.pending([("A", "0", [29])], set(), seeds=3)
        assert [t[-1] for t in todo] == [1, 2, 3]

    def test_a_fresh_sample_starts_where_it_is_told_to(self) -> None:
        todo = drv.pending([("A", "0", [29, 31])], set(), seeds=2, first_seed=31)
        assert [(t[3], t[4]) for t in todo] == [(29, 31), (29, 32), (31, 31), (31, 32)]

    def test_runs_on_file_are_not_run_again(self) -> None:
        done = {drv._run_key(r) for r in _runs("A", {29: [0.9, 0.9]})}        # seeds 1 and 2
        assert [t[-1] for t in drv.pending([("A", "0", [29])], done, seeds=4)] == [3, 4]

    def test_a_run_whose_period_six_figures_cannot_hold_is_recognised_on_file(self) -> None:
        """Before F56 a resumed campaign would have run every EMSS point again."""
        done = {drv._run_key(r) for r in _runs("SE", {34: [0.9]}, jitter="19.802")}
        assert drv.pending([("SE", "period", [34])], done, seeds=1) == []

    def test_the_exact_jitter_is_what_the_simulator_is_given(self) -> None:
        ((_, jitter, _, _, _),) = drv.pending([("SE", "period", [34])], set(), seeds=1)
        assert jitter == 1000.0 / drv.CELLS["SE"].fps


class TestTheScenarioIsInvokedAsPublishedUnlessToldOtherwise:
    BASE = ["--nNodes=29", "--framesPerSec=50.0", "--frameSize=174", "--simTime=20.0",
            "--seed=1", "--outPrefix=p"]

    def test_defaults_add_no_argument(self) -> None:
        assert drv.scenario_args(174, 50.0, 29, 1, 20.0, Path("p")) == self.BASE

    def test_each_option_adds_its_own_argument_and_only_that(self) -> None:
        def extra(**kw: float) -> list[str]:
            return drv.scenario_args(174, 50.0, 29, 1, 20.0, Path("p"), **kw)[len(self.BASE):]

        assert extra(jitter_ms=20.0) == ["--txJitterMs=20.0"]
        assert extra(jitter_ms=0.1, skew_ppm=5000.0) == ["--txJitterMs=0.1", "--txSkewPpm=5000.0"]
        assert extra(cw_min=31) == ["--cwMin=31"]


class TestCellsAreTheLaddersFrames:
    """A cell that simulated a frame the ladder does not list would validate nothing."""

    LADDER = {(r["op"], r["format"], r["rung"]): r for r in _rows(RAW / "design_ladder.csv")
              if r["scheme"] == "ed25519"}
    STREAM = {r["scheme"]: r for r in _rows(RAW / "stream_baselines.csv")}

    @pytest.mark.parametrize("name", sorted(k for k, c in drv.CELLS.items()
                                            if c.label.startswith("stream/")))
    def test_a_stream_cell_is_the_frame_and_rate_of_the_stream_table(self, name: str) -> None:
        cell = drv.CELLS[name]
        row = self.STREAM[cell.label.removeprefix("stream/")]
        assert cell.frame_bytes == round(float(row["frame_bytes"]))
        assert (cell.batch, cell.fps) == (1, float(row["frames_per_s"]))

    @pytest.mark.parametrize("name", sorted(k for k, c in drv.CELLS.items()
                                            if not c.label.startswith("stream/")))
    def test_frame_rate_and_model_value(self, name: str) -> None:
        cell = drv.CELLS[name]
        op = {50.0: "adopted", 20.0: "relaxed"}[cell.lam]
        fmt, rung = cell.label.split("/")
        row = self.LADDER[(op, fmt, rung)]
        assert cell.frame_bytes == round(float(row["frame_bytes"]))
        assert cell.batch == int(row["batch"]) and cell.lam == float(row["lambda_rec_per_s"])
        # `model_n` is what the single load ceiling predicted — the figure the search tests
        assert cell.model_n == int(row["n_max_load_ceiling"])

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
            # each node sends for sim_time seconds at fps; the first frame leaves one period in.
            # A rate offset of s ppm lets a node send that much more or less than nominal.
            expected = n * cell.fps * float(r["sim_time_s"])
            skew = float(r["skew_ppm"]) * 1e-6
            assert expected * (1 - skew) - 2 * n <= tx <= expected * (1 + skew)


class TestOnePeriodOfJitterIsAcceptedByTheScenario:
    """⚠️ Added 2026-10-09. The scenario refuses a jitter above one period, comparing
    `txJitterMs * 1e-3 > 1.0 / framesPerSec`. At 116 frames/s, 1000/116 fails that by one unit in
    the last place and ns-3 aborted. It had never happened because every earlier rate passes."""

    @staticmethod
    def _guard_accepts(jitter_ms: float, fps: float) -> bool:
        return not (jitter_ms < 0.0 or jitter_ms * 1e-3 > 1.0 / fps)

    def test_the_rate_that_aborted(self) -> None:
        assert not self._guard_accepts(1000.0 / 116, 116)          # the defect, as found
        assert self._guard_accepts(drv.one_period_ms(116), 116)
        assert drv.one_period_ms(116) == pytest.approx(1000.0 / 116, rel=1e-12)

    def test_every_rate_used_before_is_unchanged(self) -> None:
        for fps in sorted({c.fps for c in drv.CELLS.values()}):
            assert drv.one_period_ms(fps) == 1000.0 / fps, fps
            assert drv.source_of("period", fps) == (1000.0 / fps, 0.0)

    def test_a_sweep_of_rates_never_trips_the_guard(self) -> None:
        for fps in [x / 2 for x in range(2, 1000)]:
            assert self._guard_accepts(drv.one_period_ms(fps), fps), fps
