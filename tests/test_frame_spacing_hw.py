"""One saturated sender's frame spacing, read at the receiver (analysis/frame_spacing_hw.py).

docs/CONTENTION_HW_FRAMEBURST_EXPECTATIONS.md. Held here: the arithmetic; that the artifact is
what the script gives from the boards' files; and the three facts the thesis quotes from it —
the spacing with the driver's setting, the spacing with frame burst off, and that neither is
the standard's. It also pins the error of August 2026: the sender's own rate is not the rate
on air.
"""
from __future__ import annotations

import csv
import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("frame_spacing_hw",
                                               REPO / "analysis" / "frame_spacing_hw.py")
assert _spec and _spec.loader
fs = importlib.util.module_from_spec(_spec)
sys.modules["frame_spacing_hw"] = fs
_spec.loader.exec_module(fs)

ROWS = list(csv.DictReader(ln for ln in fs.OUT.read_text().splitlines()
                           if not ln.startswith("#")))


def _cycles(session: str, burst: str) -> list[float]:
    return [float(r["cycle_us"]) for r in ROWS
            if r["session"] == session and r["frame_burst"].startswith(burst)]


class TestTheArithmetic:
    def test_the_frame_and_the_standards_cycle(self) -> None:
        # 1400 B of UDP payload: 1464 B on air with IP, UDP, LLC, MAC header and FCS; at 6 Mb/s
        # that is 489 symbols of 4 µs behind a 20 µs preamble
        assert fs.ppdu_s() == pytest.approx(1976e-6, abs=1e-9)
        # DIFS 34 µs and the mean of a counter drawn from 0…15 slots of 9 µs
        assert fs.standard_cycle_s() == pytest.approx(2077.5e-6, abs=1e-9)

    def test_the_cycle_is_the_receivers_span_over_the_sequence_numbers_it_covers(self) -> None:
        row = fs.spacing({"sent": 1100, "achieved_fps": 550.0},
                         {"received_unique": 990, "min_seq": 10, "max_seq": 1010, "span_s": 2.0})
        assert row["frames_spanned"] == 1000 and row["cycle_us"] == pytest.approx(2000.0)
        assert row["air_fps"] == pytest.approx(500.0)
        assert row["gap_after_frame_us"] == pytest.approx(24.0, abs=0.05)
        # what the sender reports is recorded beside it, and is not the same thing
        assert row["sender_fps"] == 550.0 and row["first_seq_recorded"] is True

    def test_a_window_counts_only_if_the_sender_fell_short_of_what_it_was_asked(self) -> None:
        assert fs.saturated({"achieved_fps": 495.0}, 600)
        assert not fs.saturated({"achieved_fps": 400.1}, 400)


class TestTheArtifact:
    def test_the_file_is_what_the_script_gives(self) -> None:
        def as_text(r: dict) -> dict:
            return {k: str(v) for k, v in r.items()}
        assert [as_text(r) for r in fs.collect()] == ROWS

    def test_three_sessions_two_saturated_windows_each(self) -> None:
        assert [(r["session"], r["frame_burst"][:3], r["window"]) for r in ROWS] == [
            ("2026-08-05", "on ", "13_B_600fps"), ("2026-08-05", "on ", "14_B_900fps"),
            ("2026-10-09", "on ", "13_B_600fps"), ("2026-10-09", "on ", "14_B_900fps"),
            ("2026-10-09", "off", "13_B_600fps"), ("2026-10-09", "off", "14_B_900fps")]

    def test_with_the_drivers_setting_the_spacing_is_2019_us_and_august_agrees(self) -> None:
        assert _cycles("2026-08-05", "on") == [2018.6, 2019.1]
        assert _cycles("2026-10-09", "on")[0] == 2018.9

    def test_with_frame_burst_off_it_is_2050_us(self) -> None:
        assert _cycles("2026-10-09", "off") == [2049.5, 2050.1]

    def test_neither_is_the_standards(self) -> None:
        standard = 1e6 * fs.standard_cycle_s()
        assert all(float(r["cycle_us"]) < standard - 25.0 for r in ROWS)

    def test_the_prediction_registered_for_frame_burst_off_failed(self) -> None:
        """P1 of the follow-up: 2.070–2.095 ms. Kept as a test so that it stays visible."""
        assert not any(2070.0 <= c <= 2095.0 for c in _cycles("2026-10-09", "off"))

    def test_the_senders_own_rate_overstates_the_rate_on_air(self) -> None:
        """August's 1.995 ms was the reciprocal of the sender's rate: 1.2 % short of the cycle."""
        august = [r for r in ROWS if r["session"] == "2026-08-05"]
        assert [r["sender_ms_per_frame"] for r in august] == ["1.9953", "1.9957"]
        for r in august:
            assert float(r["sender_fps"]) > float(r["air_fps"]) + 5.0
            assert float(r["cycle_us"]) / (1e3 * float(r["sender_ms_per_frame"])) == \
                pytest.approx(1.012, abs=0.001)
