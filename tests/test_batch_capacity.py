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
