"""The airtime line's arithmetic (docs/NMAX_DIRECT_EXPECTATIONS.md, follow-up F2).

The registration fixes a procedure; these hold the script to it. Whether the line *predicts*
anything is a question for the simulator, answered in that document, not here.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "ns3"))
_spec = importlib.util.spec_from_file_location("nmax_airtime_line",
                                               REPO / "analysis" / "nmax_airtime_line.py")
assert _spec and _spec.loader
line = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(line)


class TestArithmetic:
    def test_the_constant_is_twice_the_preamble_detection_period_and_is_not_fitted(self) -> None:
        assert line.C_S == pytest.approx(2 * 4e-6)

    def test_a_crossing_by_hand(self) -> None:
        # 100 nodes at 12.5 frames/s, a frame holding the medium 300 µs:
        # 0.05 / 1250 = 40 µs per frame-second; minus 8 µs; over 300 µs
        assert line.a_of(100, 12.5, 300e-6) == pytest.approx((40e-6 - 8e-6) / 300e-6)

    def test_the_line_returns_the_crossing_it_was_calibrated_on(self) -> None:
        a = line.a_of(123.4, 12.5, 338e-6)
        assert line.n_line(a, 12.5, 338e-6) == pytest.approx(123.4)

    def test_a_longer_frame_or_a_faster_sender_lowers_the_crossing(self) -> None:
        base = line.n_line(0.075, 12.5, 300e-6)
        assert line.n_line(0.075, 12.5, 600e-6) < base
        assert line.n_line(0.075, 50.0, 300e-6) == pytest.approx(base / 4)

    @pytest.mark.parametrize("args", [(0, 12.5, 3e-4), (100, 0, 3e-4), (100, 12.5, 0)])
    def test_bad_inputs_are_refused(self, args: tuple[float, float, float]) -> None:
        with pytest.raises(ValueError):
            line.a_of(*args)


class TestTheRegisteredProcedure:
    def test_six_cells_calibrate_and_seven_are_held_out(self) -> None:
        assert line.CALIBRATION == tuple("ABCDEF")
        assert line.HELD_OUT == ("G", "H", "I", "RA", "RB", "RC", "RD")
        assert set(line.DIAGNOSTIC) <= set(line.HELD_OUT) and len(line.DIAGNOSTIC) == 5
        assert line.TOLERANCE == 0.06

    def test_the_stage_one_slope_reproduces_from_the_strictly_periodic_crossings(self) -> None:
        """a = 0.0749, 'mean of six; 0.0719–0.0764', as the registration states it."""
        a, per_cell = line.calibrate(line.crossings("0"))
        assert a == pytest.approx(0.0749, abs=5e-5)
        assert min(per_cell.values()) == pytest.approx(0.0719, abs=5e-5)
        assert max(per_cell.values()) == pytest.approx(0.0764, abs=5e-5)

    def test_the_registered_predictions_reproduce_with_that_slope(self) -> None:
        """The seven predictions committed before any held-out cell was run, to the digit given.
        They were computed with the slope unrounded; 0.0749 exactly moves two of them by 0.1."""
        registered = {"G": 74.9, "H": 105.8, "I": 89.5, "RA": 75.1, "RB": 217.9, "RC": 81.7,
                      "RD": 300.2}
        a, _ = line.calibrate(line.crossings("0"))
        got = line.predictions(a)
        for cell, n in registered.items():
            assert round(got[cell], 1) == n, cell


class TestTheHeldOutTestAsScored:
    """F2's outcome, on the grids it was registered on (docs/NMAX_DIRECT_EXPECTATIONS.md).

    Finer grids were run round the same crossings afterwards; they must not move this.
    """

    SCORED = {"G": 76.25, "H": 108.89, "I": 91.34, "RA": 78.35, "RB": 219.83, "RC": 85.52,
              "RD": 308.06}

    def test_the_registered_grids_have_seven_node_counts_each(self) -> None:
        assert set(line.F2_GRIDS) == set(line.HELD_OUT)
        assert all(len(g) == 7 and list(g) == sorted(g) for g in line.F2_GRIDS.values())

    def test_the_crossings_are_the_ones_recorded_in_the_outcome(self) -> None:
        got = line.held_out_crossings()
        assert {c: round(v[0], 2) for c, v in got.items()} == self.SCORED

    def test_every_held_out_cell_is_inside_the_tolerance_of_the_line(self) -> None:
        a, _ = line.calibrate(line.crossings("period"))
        predicted = line.predictions(a)
        for cell, (measured, lo, hi) in line.held_out_crossings().items():
            band = (predicted[cell] * (1 - line.TOLERANCE), predicted[cell] * (1 + line.TOLERANCE))
            assert band[0] <= lo <= measured <= hi <= band[1], cell

    def test_the_line_beats_the_single_ceiling_in_every_diagnostic_cell(self) -> None:
        import run_nmax_direct as drv
        a, _ = line.calibrate(line.crossings("period"))
        predicted = line.predictions(a)
        got = line.held_out_crossings()
        for cell in line.DIAGNOSTIC:
            measured = got[cell][0]
            assert abs(measured - predicted[cell]) / predicted[cell] < \
                abs(measured - drv.CELLS[cell].model_n) / drv.CELLS[cell].model_n, cell

    def test_it_also_holds_with_the_slope_as_first_registered(self) -> None:
        a, _ = line.calibrate(line.crossings("0"))
        predicted = line.predictions(a)
        for cell, (measured, _, _) in line.held_out_crossings().items():
            assert abs(measured - predicted[cell]) / predicted[cell] <= line.TOLERANCE, cell


class TestTheStreamBaselinesAsScored:
    """F3's outcome: five cells that were predicted, committed, then simulated.

    The slope is the one calibrated before F2; nothing was re-fitted for these.
    """

    SCORED = {"SM": 42.15, "ST": 40.44, "SG": 39.44, "SE": 34.81, "SW": 29.00}
    REGISTERED_LINE = {"SM": 40.6, "ST": 38.8, "SG": 38.0, "SE": 33.6, "SW": 28.0}

    def test_all_five_cells_are_scored(self) -> None:
        """The first scoring silently had four: the EMSS cell's period is not a round number of
        milliseconds and was looked up by its exact value (F56)."""
        assert set(line.stream_scores()) == set(line.STREAM)

    def test_the_predictions_are_the_ones_that_were_registered(self) -> None:
        got = {c: round(s["line"], 1) for c, s in line.stream_scores().items()}
        assert got == self.REGISTERED_LINE

    def test_the_crossings_are_the_ones_recorded_in_the_outcome(self) -> None:
        assert {c: round(s["measured"], 2) for c, s in line.stream_scores().items()} == self.SCORED

    def test_every_cell_is_inside_the_registered_tolerance_interval_and_all(self) -> None:
        for cell, s in line.stream_scores().items():
            lo, hi = s["line"] * (1 - line.TOLERANCE), s["line"] * (1 + line.TOLERANCE)
            assert lo <= s["lo"] <= s["measured"] <= s["hi"] <= hi, cell

    def test_all_five_sit_above_the_line_by_what_was_expected_at_this_frame_rate(self) -> None:
        """Recorded beforehand as an expectation, not a prediction: about +3.5 %, because the two
        calibration cells at 50 frames/s sat 3.4 and 3.8 % above the line."""
        deviations = [s["vs_line_pct"] for s in line.stream_scores().values()]
        assert all(3.0 < d < 4.5 for d in deviations), deviations

