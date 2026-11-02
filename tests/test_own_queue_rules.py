"""G27's analysis (analysis/own_queue_rules.py; predictions/G27.md): data, bands and parameters.

What is held here: that the readers give the numbers the findings quote from the boards' files
(F73's pooled table, F74's spacings, F76's saturated runs); that each band is the registered rule
applied to those files; that every parameter follows from the measured spacing by its closed
form; and that stage A — one simulated sender gives the closed form's gap — passed for every set.
The scores themselves are held after the run, beside the outcome.
"""
from __future__ import annotations

import csv
import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("own_queue_rules",
                                               REPO / "analysis" / "own_queue_rules.py")
assert _spec and _spec.loader
g27 = importlib.util.module_from_spec(_spec)
sys.modules["own_queue_rules"] = g27
_spec.loader.exec_module(g27)


def _rows(name: str) -> list[dict[str, str]]:
    path = REPO / "results" / "raw" / name
    return list(csv.DictReader(ln for ln in path.read_text().splitlines()
                               if not ln.startswith("#")))


class TestTheMeasurements:
    def test_the_spacings_of_f74_and_f75(self) -> None:
        gaps = g27.measured_gaps_s()
        assert 1e6 * gaps["on"]["mean"] == pytest.approx(44.77, abs=0.01)    # 4 windows
        assert 1e6 * gaps["off"]["mean"] == pytest.approx(73.80, abs=0.01)   # 2 windows
        assert 1e6 * gaps["on"]["lowest"] == pytest.approx(42.6)
        assert 1e6 * gaps["on"]["highest"] == pytest.approx(50.5)
        # reading B: frames the receiver missed never went on air, so the gaps are longer
        assert gaps["on"]["reading_B"] > gaps["on"]["mean"]
        assert gaps["off"]["reading_B"] > gaps["off"]["mean"]

    def test_what_one_sender_loses_alone(self) -> None:
        # F76: "0.5–0.9 % of the frames its receiver spans"
        assert 100 * g27.one_sender_loss_max() == pytest.approx(0.919, abs=0.001)

    def test_f73s_pooled_table(self) -> None:
        # docs/audits/model_provenance.md F73: 0.330 (±0.046), 0.504 (±0.066), 0.778 (±0.130)
        bands = g27.window_bands()["pooled"]
        for fps, mean, half in ((124, 0.330, 0.046), (174, 0.504, 0.066), (211, 0.778, 0.130)):
            m, lo, hi, n = bands[fps]
            assert n == 12
            assert 100 * m == pytest.approx(mean, abs=0.0005)
            assert 100 * (hi - m) == pytest.approx(half, abs=0.0005)

    def test_the_windows_per_state(self) -> None:
        bands = g27.window_bands()
        assert [bands["on"][f][3] for f in g27.LOADS] == [8, 8, 8]
        assert [bands["off"][f][3] for f in g27.LOADS] == [4, 4, 4]

    def test_f76s_saturated_runs(self) -> None:
        b = g27.saturated_bands()
        assert 100 * b["off"]["loss"] == pytest.approx(12.40, abs=0.005)
        assert 100 * b["on"]["loss"] == pytest.approx(12.14, abs=0.005)
        assert b["off"]["rate"] == pytest.approx(525.34, abs=0.01)
        assert b["on"]["rate"] == pytest.approx(529.59, abs=0.01)
        for state in ("on", "off"):
            assert b[state]["windows"] == 4
            assert b[state]["loss_lo"] < b[state]["loss"] < b[state]["loss_hi"]
            assert b[state]["rate_lo"] < b[state]["rate"] < b[state]["rate_hi"]


class TestTheParameters:
    @pytest.mark.parametrize("state,expected", [
        ("on", {"R1": "W=3", "R2": "q=0.84", "R3": "q=0.663", "R4": "W=3",
                "R5": "slot=1.44us"}),
        ("off", {"R1": "W=10", "R2": "q=0.41", "R3": "q=0.324", "R4": "W=10",
                 "R5": "slot=5.31us"})])
    def test_the_registered_values(self, state: str, expected: dict[str, str]) -> None:
        rules = g27.candidates(g27.measured_gaps_s()[state]["mean"])
        assert {r.name: g27.parameter(r) for r in rules} == expected

    @pytest.mark.parametrize("state", ["on", "off"])
    def test_each_closed_form_returns_the_measured_gap(self, state: str) -> None:
        gap = g27.measured_gaps_s()[state]["mean"]
        for rule in g27.candidates(gap):
            # R1 and R4 round the window to a whole number of slots: within half a slot
            tol = g27.frozen.SLOT_S / 2 if rule.name in ("R1", "R4") else 0.1e-6
            assert g27.closed_gap_s(rule) == pytest.approx(gap, abs=tol), rule.name

    def test_r4_differs_from_r1_only_in_contention(self) -> None:
        r1, _r2, _r3, r4, _r5 = g27.candidates(g27.measured_gaps_s()["off"]["mean"])
        assert r1.w_post == r4.w_post and r4.w_defer == g27.frozen.W0 and r4.redraw_on_defer

    def test_the_standard_is_the_standards_gap(self) -> None:
        assert 1e6 * g27.closed_gap_s(g27.oq.STANDARD) == pytest.approx(101.5)


class TestStageA:
    def test_every_set_passed(self) -> None:
        rows = _rows("g27_calibration.csv")
        assert len(rows) == 2 * len(g27.CALIBRATIONS) * 6
        assert all(r["stage_A_pass"] == "True" for r in rows)
        for r in rows:
            assert abs(float(r["simulated_gap_us"]) - float(r["closed_form_gap_us"])) < 1.0


class TestTheFrozenModelsDefect:
    """F114: a station colliding with itself, measured from the frozen model's own groups."""

    def test_no_capacity_cell_moves(self) -> None:
        for r in _rows("g27_frozen_defect.csv"):
            if r["point"].startswith("cell"):
                assert abs(float(r["relative_change"])) < 0.001, r["point"]

    def test_at_the_hardware_loads_it_is_one_to_two_percent(self) -> None:
        rows = {r["point"]: r for r in _rows("g27_frozen_defect.csv")}
        for fps in (174, 211):
            assert -0.025 < float(rows[f"F73 2 boards {fps}/s"]["relative_change"]) < -0.01
        sat = rows["F76 2 boards saturated 400/s"]
        assert float(sat["loss"]) == pytest.approx(0.119, abs=0.0005)    # F76: "11.9 %"
        assert float(sat["loss_without_the_defect"]) == pytest.approx(2 / 17, abs=0.001)
