"""W4(a): the record-size bounds (analysis/worst_case_records.py; predictions/W4a.md).

What is held here, before any capacity: that the bound frames are real (encoded, decoded back to
their records and verified), that their lengths are the hand arithmetic of the registration, and
that every value the bounds use lies inside the schema's ranges. The capacities are held after the
run, beside the outcome.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("worst_case_records",
                                               REPO / "analysis" / "worst_case_records.py")
assert _spec and _spec.loader
w4a = importlib.util.module_from_spec(_spec)
sys.modules["worst_case_records"] = w4a
_spec.loader.exec_module(w4a)

CASES = {r["case"]: r for r in w4a.cases()}      # builds, decodes and verifies every frame
RANGES = {"lat": w4a.telemgen.LAT_RANGE, "lon": w4a.telemgen.LON_RANGE,
          "alt": w4a.telemgen.ALT_RANGE, "vel_x": w4a.telemgen.VEL_RANGE,
          "vel_y": w4a.telemgen.VEL_RANGE, "vel_z": w4a.telemgen.VEL_RANGE,
          "battery": w4a.telemgen.BATTERY_RANGE, "mode": (0, w4a.telemgen.N_MODES - 1),
          "ts": (0, w4a.U32_MAX)}


class TestTheBoundsAreInsideTheSchema:
    @pytest.mark.parametrize("values", [w4a.schema_values(4), w4a.physical_values(4)])
    def test_every_value(self, values: list[dict[str, int]]) -> None:
        for v in values:
            for k, (lo, hi) in RANGES.items():
                assert lo <= v[k] <= hi, (k, v[k])

    def test_the_schema_deltas_are_full_spans(self) -> None:
        for k, (lo, hi) in RANGES.items():
            assert abs(w4a.A[k] - w4a.B[k]) == hi - lo, k


class TestTheFrameLengthsAreTheRegistrations:
    def test_the_lengths(self) -> None:
        got = {k: CASES[k]["frame_bytes"] for k in CASES if "published" not in k}
        assert got == {"AUTHBC, schema bound": 233, "AUTHBC, physical bound": 188,
                       "per-record, schema bound": 150, "per-record, smallest": 125}

    def test_the_hand_arithmetic(self) -> None:
        # key: ts, lat, lon 5 B each, alt 4, three velocities 2 each, battery and mode 1 each
        assert CASES["AUTHBC, schema bound"]["key_record_bytes"] == 5 + 5 + 5 + 4 + 2 * 3 + 1 + 1
        # schema delta: battery's ±100 zig-zagged needs two bytes
        assert CASES["AUTHBC, schema bound"]["delta_record_bytes"] == 5 + 5 + 5 + 4 + 2 * 3 + 2 + 1
        # physical delta: ts, lat 1 B; lon 2; alt 1; velocities 2 each; battery, mode 1
        assert CASES["AUTHBC, physical bound"]["delta_record_bytes"] == 1 + 1 + 2 + 1 + 6 + 1 + 1
        assert CASES["per-record, smallest"]["key_record_bytes"] == 9

    def test_the_published_means(self) -> None:
        assert CASES["AUTHBC, published mean"]["frame_bytes"] == pytest.approx(173.0, abs=0.01)
        assert CASES["per-record, published mean"]["frame_bytes"] == pytest.approx(146.76,
                                                                                   abs=0.01)


# --------------------------------------------------------------------- after the run, 2026-11-05
REGISTRATION = "1dc2301"            # predictions/W4a.md, tag prereg-W4a


def _scored() -> dict[str, dict[str, str]]:
    import csv
    path = REPO / "results" / "raw" / "w4a_worst_case.csv"
    return {r["case"]: r for r in csv.DictReader(ln for ln in path.read_text().splitlines()
                                                 if not ln.startswith("#"))}


class TestTheOutcome:
    def test_the_scored_code_is_the_registered_code(self) -> None:
        import subprocess
        then = subprocess.run(["git", "show", f"{REGISTRATION}:analysis/worst_case_records.py"],
                              cwd=REPO, capture_output=True, text=True, check=True).stdout
        assert then == (REPO / "analysis" / "worst_case_records.py").read_text()

    @pytest.mark.parametrize("pair,at_least", [
        ("AUTHBC, physical bound / per-record, published mean", 3.3),
        ("AUTHBC, schema bound / per-record, published mean", 2.5),
        ("AUTHBC, schema bound / per-record, smallest", 2.0)])
    def test_the_registered_ratios(self, pair: str, at_least: float) -> None:
        assert float(_scored()[f"ratio: {pair}"]["model_crossing"]) >= at_least

    def test_no_telemetry_of_the_schema_reverses_the_ordering(self) -> None:
        even = _scored()["break-even against per-record at its smallest"]
        assert float(even["delta_record_bytes"]) > 28 * 7          # eight times the schema's
