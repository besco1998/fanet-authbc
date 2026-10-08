"""Records at the operating rate from PX4 software-in-the-loop (docs/PX4_LOGS_EXPECTATIONS.md).

The flight cannot be repeated by a test: it needs a built PX4. What is held is that the
analysis is the one applied to the public logs, that the artifacts are what it gives on the
flight's raw files (which are in the repository), and that the outcome recorded against the
registered predictions — including the two that were missed — is what the artifacts say.
"""

from __future__ import annotations

import csv
import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
RAW = REPO / "results" / "raw"
sys.path.insert(0, str(REPO / "analysis"))
_spec = importlib.util.spec_from_file_location("px4_sitl_sizes",
                                               REPO / "analysis" / "px4_sitl_sizes.py")
assert _spec and _spec.loader
sitl = importlib.util.module_from_spec(_spec)
sys.modules["px4_sitl_sizes"] = sitl
_spec.loader.exec_module(sitl)


def _rows(name: str) -> list[dict[str, str]]:
    return list(csv.DictReader(ln for ln in (RAW / name).read_text().splitlines()
                               if not ln.startswith("#")))


SIZES = {(r["part"], r["spacing_ms"]): r for r in _rows("px4_sitl_sizes.csv")}
TIMING = {r["quantity"]: r for r in _rows("px4_sitl_stream_timing.csv")}
PHASES = json.loads((sitl.FLIGHT / "phases.json").read_text())


class TestTheArithmetic:
    def test_a_phase_is_cut_from_runs_without_bridging_the_cut(self) -> None:
        run = [(t, 0, 0, 0, 0, 0, 0, 0, 0) for t in range(0, 400, 20)]
        (part,) = sitl.within([run], 100, 300)
        assert [r[0] for r in part] == list(range(100, 300, 20))
        assert sitl.within([run], 100, 180) == []            # too short to hold one frame + 1

    def test_intervals_are_differences_in_milliseconds(self) -> None:
        assert sitl._intervals([0, 20_000_000, 41_000_000], 1e6) == [20.0, 21.0]
        assert sitl._intervals([100, 116, 140], 1.0) == [16.0, 24.0]

    def test_interval_statistics(self) -> None:
        s = sitl._interval_stats("x", [16.0, 24.0] * 60)
        got = (s["n"], s["mean_ms"], s["sd_ms"], s["min_ms"], s["max_ms"])
        assert got == (120, 20.0, 4.0, 16.0, 24.0)
        assert s["half_p16_p84_ms"] == 4.0                   # half of 24 − 16

    def test_the_clock_ratio_is_autopilot_time_over_host_time(self) -> None:
        cap = {"time_boot_ms": [0, 9_400], "recv_mono_ns": [0, 10_000_000_000]}
        assert sitl._ratio(cap, "recv_mono_ns") == pytest.approx(0.94)


class TestTheFlightThatWasRegistered:
    def test_px4_release_and_airframe(self) -> None:
        assert (PHASES["px4"], PHASES["model"]) == ("v1.17.0", "sihsim_quadx")

    def test_the_five_parts_of_the_mission_in_order(self) -> None:
        phases = PHASES["phases_boot_ms"]
        assert list(phases) == ["takeoff", "square_5mps", "square_12mps", "hold", "land"]
        ends = [span[1] for span in phases.values()]
        assert ends == sorted(ends)
        assert phases["hold"][1] - phases["hold"][0] >= 60_000
        # four legs of 150 m at the commanded speed
        assert phases["square_5mps"][1] - phases["square_5mps"][0] == pytest.approx(120_000,
                                                                                    rel=0.01)
        assert phases["square_12mps"][1] - phases["square_12mps"][0] == pytest.approx(50_000,
                                                                                      rel=0.01)

    @pytest.mark.frozen
    def test_the_artifacts_are_the_analysis_of_the_raw_files(self) -> None:
        fresh = {(r["part"], str(r["spacing_ms"])): r for r in sitl.sizes(sitl.FLIGHT)}
        assert set(fresh) == set(SIZES)
        for key, row in fresh.items():
            assert {k: str(v) for k, v in row.items()} == SIZES[key], key
        timing = {r["quantity"]: r for r in sitl.timing(sitl.FLIGHT)}
        assert {q: {k: str(v) for k, v in r.items()} for q, r in timing.items()} == TIMING


class TestTheOutcomeAsRecorded:
    """docs/PX4_LOGS_EXPECTATIONS.md, "Outcome (2026-10-08)": each line against the artifacts."""

    DOC = (REPO / "docs" / "PX4_LOGS_EXPECTATIONS.md").read_text()
    WHOLE = SIZES[("whole flight", "20")]

    def test_every_delta_at_the_operating_rate_is_at_the_floor(self) -> None:
        for (part, spacing), r in SIZES.items():
            if spacing == "20":
                assert (r["lean_delta_mean"], r["lean_delta_min"], r["lean_delta_max"]) == \
                    ("9", "9", "9"), part
        assert self.WHOLE["records"] == "14317" and "14,317 in-flight records" in self.DOC

    def test_the_design_costs_less_than_the_generator_says(self) -> None:
        assert self.WHOLE["bytes_per_rec"] == "42.472" and "**42.47 B**" in self.DOC
        assert 42.3 <= float(self.WHOLE["bytes_per_rec"]) <= 43.8          # the registered range
        assert round(100 * (1 - 42.472 / 43.25), 1) == 1.8
        assert 20 <= float(self.WHOLE["lean_key_mean"]) <= 24

    def test_the_comparison_at_200_ms_missed_its_range_and_is_recorded_as_missed(self) -> None:
        r = SIZES[("whole flight", "200")]
        assert r["lean_delta_mean"] == "10.641" and float(r["lean_delta_mean"]) > 10.6
        assert "**missed, by 0.04 B**" in self.DOC

    def test_the_registered_timing_spread_is_reported_and_not_scored(self) -> None:
        raw = TIMING["flight: received, wall clock"]
        assert float(raw["sd_ms"]) > 50 and float(raw["min_ms"]) < -2000    # the clock steps
        assert abs(float(raw["mean_ms"]) - 20.0) <= 0.2                     # the mean held
        assert "not scored as registered" in self.DOC

    def test_the_spread_that_can_be_stated(self) -> None:
        flight = TIMING["flight: received, wall clock, clock steps removed"]
        ground = TIMING["ground: received, monotonic clock"]
        assert flight["half_p16_p84_ms"] == "0.3736" and ground["half_p16_p84_ms"] == "0.3699"
        assert (round(float(flight["sd_ms"]), 1), round(float(ground["sd_ms"]), 1)) == (1.2, 1.3)
        assert "14 intervals" in flight["note"]
        for needle in ("**±0.37 ms**", "| 1.2 ms |", "| 1.3 ms |"):
            assert needle in self.DOC, needle

    def test_the_stamps_inside_the_messages_alternate_16_and_24_ms(self) -> None:
        note = TIMING["flight: stamped (time_boot_ms)"]["note"]
        assert "49.9 % at 16 ms" in note and "50.0 % at 24 ms" in note and "0.0 % at 20 ms" in note
