"""The bench session of 2026-10-09 on the Raspberry Pi 4 (hw/BENCH_SESSION.md steps 1 and 5).

Finding F77. Held here: the files are what the documents quote; the ranges written down before
the measurement are compared with what came out — two of them were missed, on the fast side,
and stay recorded as missed; and the run's validity rests on evidence that is in the
repository (the same session's signature timings against the reference board's, and the
kernel's under-voltage record).
"""
from __future__ import annotations

import csv
import math
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
HW = REPO / "results" / "hw"
NUMBERS = dict(re.findall(r"\\newcommand\{\\(\w+)\}\{(.*)\}",
                          (REPO / "paper" / "numbers.tex").read_text(encoding="utf-8")))
BENCH = (REPO / "hw" / "BENCH_SESSION.md").read_text(encoding="utf-8")
CODESIGN = re.sub(r"\s+", " ", (REPO / "thesis" / "ch08_codesign.tex").read_text(encoding="utf-8"))


def _rows(path: Path) -> list[dict[str, str]]:
    return list(csv.DictReader(ln for ln in path.read_text().splitlines()
                               if not ln.startswith("#")))


def _header(path: Path) -> dict[str, str]:
    return dict(ln[2:].split("=", 1) for ln in path.read_text().splitlines()
                if ln.startswith("# ") and "=" in ln)


LEAN = {(r["op"], int(r["agg_b"])): float(r["median_ns"]) / 1e6       # milliseconds
        for r in _rows(HW / "p1_lean.authbc-pi4b.csv")}
DESKTOP = {(r["op"], int(r["agg_b"])): float(r["median_ns"]) / 1e6
           for r in _rows(REPO / "results" / "raw" / "p1_lean.x86-desktop.20261009.csv")}


def _crypto(name: str) -> dict[tuple[str, str], float]:
    return {(r["scheme"], r["op"]): float(r["median_ns"])
            for r in _rows(HW / name) if not r["agg_b"]}


class TestTheRunWasValid:
    def test_it_ran_on_the_board_with_the_reference_software(self) -> None:
        head = _header(HW / "p1_lean.authbc-pi4b.csv")
        assert head["device_model"].startswith("Raspberry Pi 4 Model B")
        assert head["device_governor"] == "performance" and head["python"] == "3.12.13"

    def test_the_same_sessions_signatures_time_as_the_reference_boards(self) -> None:
        """The other Pi 4 gave the timings every table uses; it has since been re-installed."""
        today, reference = _crypto("p1_crypto.authbc-pi4b.20261009.csv"), \
            _crypto("p1_crypto.authbc-pi4a.csv")
        for key in (("ed25519", "sign"), ("ed25519", "verify"), ("ecdsa_p256", "verify"),
                    ("bls", "verify")):
            assert abs(today[key] / reference[key] - 1) < 0.005, key

    def test_no_under_voltage_after_boot(self) -> None:
        """The firmware's flag read 0x50000 before and after: bits that stay set once raised.
        The kernel's log dates the one event to the boot, 250 s before the benchmark."""
        head = _header(HW / "p1_lean.authbc-pi4b.csv")
        assert head["device_throttled_before"] == head["device_throttled_after"] == "0x50000"
        log = (HW / "meta" / "authbc-pi4b-20261009T030746Z" / "undervoltage_events.txt").read_text()
        events = [float(t) for t in re.findall(r"\[\s*([\d.]+)\] .*Undervoltage detected", log)]
        assert events == [10.557687] and "from about 260 s to 585 s" in log

    def test_the_computation_is_the_one_the_desktop_runs(self) -> None:
        board = {(r["op"], r["agg_b"]): r["checksum"]
                 for r in _rows(HW / "p1_lean.authbc-pi4b.csv")}
        desk = {(r["op"], r["agg_b"]): r["checksum"]
                for r in _rows(REPO / "results" / "raw" / "p1_lean.x86-desktop.20261009.csv")}
        assert board == desk and len(board) == 4


class TestWhatWasWrittenDownBeforehand:
    def test_the_two_timing_ranges_were_missed_on_the_fast_side(self) -> None:
        assert "| Pi 4: lean **sender**, one 4-record frame | **1.0–2.5 ms** |" in BENCH
        assert "| Pi 4: lean **receiver**, one 4-record frame | **2–5 ms** |" in BENCH
        assert LEAN[("frame_send", 4)] < 1.0 and LEAN[("frame_receive", 4)] < 2.0
        assert "came in under what had been written down for them" in CODESIGN

    def test_the_desktop_figure_they_were_scaled_from_was_three_to_four_times_high(self) -> None:
        assert "0.42 ms on a loaded x86 desktop" in BENCH and "0.90 ms on the same desktop" in BENCH
        assert 3.0 < 0.42 / DESKTOP[("frame_send", 4)] < 4.0
        assert 3.0 < 0.90 / DESKTOP[("frame_receive", 4)] < 4.0
        assert "three to four times too high" in CODESIGN

    def test_the_board_is_six_to_seven_times_slower_on_interpreted_code_and_three_on_a_signature(
            self) -> None:
        for op in ("frame_send", "frame_receive"):
            assert 6.0 < LEAN[(op, 4)] / DESKTOP[(op, 4)] < 7.5
        desk = {(r["scheme"], r["op"]): float(r["median_ns"])
                for r in _rows(REPO / "results" / "raw" / "p1_crypto.csv") if not r["agg_b"]}
        board = _crypto("p1_crypto.authbc-pi4b.20261009.csv")
        assert 2.9 < board[("ed25519", "verify")] / desk[("ed25519", "verify")] < 3.4
        assert "six to seven times slower than the desktop" in CODESIGN

    def test_batch_verification_landed_inside_its_range(self) -> None:
        assert "| batch of 64 against one at a time, per signature | **0.45–0.60×** |" in BENCH
        cost = {int(r["batch"]): float(r["median_ns_per_sig"])
                for r in _rows(HW / "ed25519_batch.authbc-pi4b.csv")}
        assert 0.45 <= cost[64] / cost[1] <= 0.60
        assert f"{cost[64] / cost[1]:.2f}" == NUMBERS["edBatchRatio"] == "0.46"
        assert all(cost[a] > cost[b] for a, b in ((1, 4), (4, 8), (8, 16), (16, 32), (32, 64)))


class TestWhatTheDocumentsQuote:
    def test_the_times(self) -> None:
        assert NUMBERS["leanSendMs"] == f"{LEAN[('frame_send', 4)]:.2f}" == "0.87"
        assert NUMBERS["leanRecvMs"] == f"{LEAN[('frame_receive', 4)]:.2f}" == "1.41"
        assert NUMBERS["leanSendOneMs"] == f"{LEAN[('frame_send', 1)]:.2f}" == "0.38"
        assert NUMBERS["leanRecvOneMs"] == f"{LEAN[('frame_receive', 1)]:.2f}" == "0.65"

    def test_the_receiver_costs_five_times_its_verification(self) -> None:
        verify_ms = _crypto("p1_crypto.authbc-pi4b.20261009.csv")[("ed25519", "verify")] / 1e6
        assert NUMBERS["leanRecvOverVerify"] == f"{LEAN[('frame_receive', 4)] / verify_ms:.1f}"
        assert 5.0 < float(NUMBERS["leanRecvOverVerify"]) < 6.0

    def test_one_core_of_the_prototype_serves_57_nodes_and_the_design_needs_two_cores(self) -> None:
        per_neighbour_s = 50 / 4 * LEAN[("frame_receive", 4)] / 1e3      # 12.5 frames a second
        assert NUMBERS["ncpuProto"] == str(1 + math.floor(1 / per_neighbour_s)) == "57"
        n_max = int(NUMBERS["nmaxLeanDesign"])
        assert NUMBERS["cpuProtoCores"] == f"{(n_max - 1) * per_neighbour_s:.1f}" == "2.2"
        assert int(NUMBERS["ncpuProto"]) < n_max < int(NUMBERS["ncpuBatch"])
        assert "for the prototype on one core the processor binds first" in CODESIGN
