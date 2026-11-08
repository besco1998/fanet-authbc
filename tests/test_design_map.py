"""Revision A2: the design map (predictions/A2.md, analysis/design_map.py).

Held here: the arithmetic the registration states as computed (b*, the infeasible cells, the
gain region, the MTU), that the map's frames at the paper's point are the ladder's emitted
frames, that the cells handed to ns-3 are the registered ones, and that nothing is scored from
an unfinished campaign.
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
_spec = importlib.util.spec_from_file_location("design_map", REPO / "analysis" / "design_map.py")
assert _spec and _spec.loader
dm = importlib.util.module_from_spec(_spec)
sys.modules["design_map"] = dm
_spec.loader.exec_module(dm)

import run_nmax_direct as drv  # noqa: E402


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(ln for ln in fh if not ln.startswith("#")))


MAP = {(int(r["lambda_rec_per_s"]), int(r["d_max_ms"])): r for r in _rows(dm.MAP)}
T_CH, T_V = dm.budget()


class TestTheBatchTheDeadlineAdmits:
    @pytest.mark.parametrize(("lam", "d", "b"), [(50, 100, 4), (20, 250, 4), (100, 100, 9),
                                                  (10, 40, 0), (40, 40, 1), (100, 500, 49)])
    def test_b_star(self, lam: int, d: int, b: int) -> None:
        assert dm.b_star(lam, d, T_CH, T_V) == b

    def test_the_budget_is_the_freshness_tables(self) -> None:
        assert (T_CH, T_V) == (3.4907, 0.2595)

    def test_six_cells_admit_no_frame_at_all(self) -> None:
        assert sorted(k for k, r in MAP.items() if r["feasible"] == "0") == [
            (10, 40), (10, 60), (10, 80), (10, 100), (20, 40), (25, 40)]

    def test_on_this_grid_a_batch_needs_exactly_lambda_times_deadline_above_two(self) -> None:
        for (lam, d), r in MAP.items():
            if r["feasible"] == "1":
                assert (int(r["b_star"]) >= 2) == (lam * d / 1000 > 2), (lam, d)

    def test_a_cell_with_one_record_per_frame_gains_nothing(self) -> None:
        for r in MAP.values():
            if r["b_star"] == "1":
                assert float(r["model_ratio"]) == 1.0
                assert r["design_frame_bytes"] == r["base_frame_bytes"]


class TestTheFramesAreEmitted:
    def test_at_the_papers_point_the_map_has_the_ladders_frames(self) -> None:
        ladder = {r["rung"]: r for r in _rows(RAW / "design_ladder.csv")
                  if r["op"] == "adopted" and r["format"] == "lean" and r["scheme"] == "ed25519"}
        r = MAP[(50, 100)]
        assert float(r["design_frame_bytes"]) == pytest.approx(
            float(ladder["batch-delta"]["frame_bytes"]), abs=1e-3)
        assert float(r["base_frame_bytes"]) == pytest.approx(
            float(ladder["inline-1"]["frame_bytes"]), abs=1e-3)

    def test_the_mtu_never_binds_in_a_cell(self) -> None:
        assert all(r["fits_mtu"] == "1" for r in MAP.values() if r["feasible"] == "1")
        assert {int(r["mtu_records"]) for k, r in MAP.items() if k[0] >= 20} == {151}
        assert {int(r["mtu_records"]) for k, r in MAP.items() if k[0] == 10} == {135}

    def test_the_models_ratio_does_not_fall_as_the_batch_grows(self) -> None:
        for lam in dm.LAMBDAS:
            cells = sorted((int(r["b_star"]), float(r["model_ratio"])) for (la, _), r in
                           MAP.items() if la == lam and r["feasible"] == "1")
            assert [x for _, x in cells] == sorted(x for _, x in cells), lam


class TestWhatIsHandedToNs3:
    REG = _rows(dm.PREDICTIONS)

    def test_the_plans_ten_cells_and_one_more(self) -> None:
        cells = {(int(r["lambda_rec_per_s"]), int(r["d_max_ms"]), r["in_plan"]) for r in self.REG}
        assert {(lam, d) for lam, d, _ in cells} == set(dm.VALIDATION + dm.EXTRA)
        assert {(lam, d) for lam, d, flag in cells if flag == "0"} == {(100, 100)}

    def test_every_registered_cell_is_the_drivers_cell(self) -> None:
        for r in self.REG:
            c = drv.CELLS[r["ns3_cell"]]
            assert (c.frame_bytes, c.batch, c.fps) == (
                int(r["frame_bytes"]), int(r["batch"]),
                pytest.approx(float(r["frames_per_s"]), abs=1e-4)), r

    def test_the_plan_runs_exactly_the_registered_grids(self) -> None:
        plan = {cell: ns for cell, spec, ns in
                drv.read_plan(REPO / "experiments" / "design-map" / "plan.txt")}
        reg = {r["ns3_cell"]: [int(x) for x in r["ns3_grid"].split()] for r in self.REG}
        assert plan == reg
        assert all(spec == "period" for _, spec, _ in
                   drv.read_plan(REPO / "experiments" / "design-map" / "plan.txt"))


class TestNothingIsScoredEarly:
    def test_no_runs_no_score(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(dm, "RAW", tmp_path)
        assert dm.score() == []
