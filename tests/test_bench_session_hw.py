"""The bench session of 2026-10-09 on the Raspberry Pi 4 (hw/BENCH_SESSION.md steps 1 and 5).

Finding F77. Held here: the files are what the documents quote; the ranges written down before
the measurement are compared with what came out — two of them were missed, on the fast side,
and stay recorded as missed; and the run's validity rests on evidence that is in the
repository (the same session's signature timings against the reference board's, and the
kernel's under-voltage record).
"""
from __future__ import annotations

import csv
import hashlib
import math
import re
import subprocess
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
# The afternoon's session (audit F81): the receiver as it was, then the receiver that keeps frames
CONTROL = {(r["op"], int(r["agg_b"])): float(r["median_ns"]) / 1e6
           for r in _rows(HW / "p1_lean.authbc-pi4b.control-20261009.csv")}
KEPT = {(r["op"], int(r["agg_b"])): float(r["median_ns"]) / 1e6
        for r in _rows(HW / "p1_lean.authbc-pi4b.frames-kept.csv")}
RETIMING_REGISTERED = "61a4b4f"


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
        """The sender's are the morning's, which the energy runs were registered against; the
        receiver's are of the receiver that keeps frames (1.41 and 0.65 ms before it did)."""
        assert NUMBERS["leanSendMs"] == f"{LEAN[('frame_send', 4)]:.2f}" == "0.87"
        assert NUMBERS["leanSendOneMs"] == f"{LEAN[('frame_send', 1)]:.2f}" == "0.38"
        assert NUMBERS["leanRecvMs"] == f"{KEPT[('frame_receive', 4)]:.2f}" == "1.43"
        assert NUMBERS["leanRecvOneMs"] == f"{KEPT[('frame_receive', 1)]:.2f}" == "0.66"
        assert (f"{LEAN[('frame_receive', 4)]:.2f}", f"{LEAN[('frame_receive', 1)]:.2f}") == \
            ("1.41", "0.65")

    def test_the_lean_rows_model_is_the_timed_frame_at_the_metered_power(self) -> None:
        """The "model" column of the lean rows: the frame's time on the board times the power
        of the energy table. Until the runs of 2026-10-09 it was printed as an estimate of the
        energy; it is now what the meter is set beside (tests/test_energy_runs.py)."""
        paper = re.sub(r"\s+", " ", (REPO / "paper" / "main.tex").read_text(encoding="utf-8"))
        for b, macro in ((4, "leanSendUj"), (1, "leanSendOneUj")):
            assert NUMBERS[macro] == f"{0.749 * LEAN[('frame_send', b)] * 1e3 / b:.0f}"
        assert (NUMBERS["leanSendUj"], NUMBERS["leanSendOneUj"]) == ("163", "284")
        assert "whose model is its timed frame (\\leanSendMs\\,ms for four records) at that " \
               "power" in paper
        assert "in this prototype, the slower to run" in paper
        assert "the time of one whole frame on the board (\\leanSendMs\\,ms for four records) " \
               "at that same power, written down before the meter was read" in CODESIGN

    def test_neither_document_still_says_the_lean_codec_is_untimed(self) -> None:
        paper = (REPO / "paper" / "main.tex").read_text(encoding="utf-8")
        assert "has not been timed" not in paper and "has not been timed" not in CODESIGN

    def test_the_first_formats_comparison_is_described_as_a_test_of_times(self) -> None:
        """Its model's power is the median of the metered runs themselves."""
        paper = re.sub(r"\s+", " ", (REPO / "paper" / "main.tex").read_text(encoding="utf-8"))
        assert "the median over these same metered runs, so the comparison tests the times" in paper
        assert "That comparison tests the times, not the power" in CODESIGN
        method = re.sub(r"\s+", " ", (REPO / "thesis" / "ch06_methodology.tex").read_text())
        assert "it cannot test the power" in method

    def test_the_receiver_costs_five_times_its_verification(self) -> None:
        verify_ms = _crypto("p1_crypto.authbc-pi4b.frames-kept.csv")[("ed25519", "verify")] / 1e6
        assert NUMBERS["leanRecvOverVerify"] == f"{KEPT[('frame_receive', 4)] / verify_ms:.1f}"
        assert 5.0 < float(NUMBERS["leanRecvOverVerify"]) < 6.0

    def test_one_core_of_the_prototype_serves_57_nodes_and_the_design_needs_two_cores(self) -> None:
        per_neighbour_s = 50 / 4 * KEPT[("frame_receive", 4)] / 1e3      # 12.5 frames a second
        assert NUMBERS["ncpuProto"] == str(1 + math.floor(1 / per_neighbour_s)) == "57"
        n_max = int(NUMBERS["nmaxLeanDesign"])
        assert NUMBERS["cpuProtoCores"] == f"{(n_max - 1) * per_neighbour_s:.1f}" == "2.2"
        assert int(NUMBERS["ncpuProto"]) < n_max < int(NUMBERS["ncpuBatch"])
        assert "for the prototype on one core the processor binds first" in CODESIGN


class TestTheReceiverThatKeepsFramesWasTimedAgainstAControl:
    """Audit F81. The receiver was changed to keep every accepted frame; its time is in the
    paper. Two runs in one session on the same board: the receiver as it was, then the new one.
    What each should show was committed before either (hw/BENCH_SESSION.md, 61a4b4f)."""

    @staticmethod
    def _git(*args: str) -> str:
        return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True,
                              check=True).stdout

    def test_the_expectation_was_committed_before_the_new_receiver_and_before_its_timing(
            self) -> None:
        sheet = self._git("show", f"{RETIMING_REGISTERED}:hw/BENCH_SESSION.md")
        for needle in ("**1.383–1.439 ms** (four records), **0.640–0.666 ms** (one)",
                       "between **1.00 and 1.02 times the control**",
                       "**57** while t ≤ 1.4286 ms",
                       "the code is not tuned to get under"):
            assert needle in sheet, needle
        files = self._git("ls-tree", "-r", "--name-only", RETIMING_REGISTERED)
        assert "frames-kept" not in files and "control-20261009" not in files
        receiver = self._git("show",
                             f"{RETIMING_REGISTERED}:src/authbc/placement/session_v2.py")
        assert "frame_of" not in receiver and "proves_equivocation" not in receiver

    def test_the_receiver_in_the_repository_is_the_one_that_was_timed(self) -> None:
        """Read on the board after the run, by SHA-256. If one of these files changes, the
        receive time in the paper is of code that no longer exists: time it again on the board
        (hw/BENCH_SESSION.md) and record the new hashes with the new file."""
        timed = {
            "src/authbc/placement/session_v2.py":
                "42f954ad58cdeeb98e1b3b00da057c7a7bc8aa0a13a64172102bed90997fae8a",
            "src/authbc/ledger/store.py":
                "5fc6c4a98a8b4b14021b04192b9178e8e598abd553eb055bf3f8024a31dd2ff2",
            "src/authbc/placement/wire_v2.py":
                "6edf42a8af07c83e96f34e34b4ecac3104ed71e75dec0a5f360ddb7eddb94db0",
        }
        for path, digest in timed.items():
            assert hashlib.sha256((REPO / path).read_bytes()).hexdigest() == digest, path
            assert digest in BENCH, path

    def test_both_runs_were_valid_and_on_the_same_board(self) -> None:
        for name in ("control-20261009", "frames-kept"):
            head = _header(HW / f"p1_lean.authbc-pi4b.{name}.csv")
            assert head["device_host"] == "authbc-pi4b" and head["python"] == "3.12.13"
            assert head["device_governor"] == "performance"
            assert head["device_throttled_before"] == head["device_throttled_after"] == "0x0"
        runs = [_header(HW / f"p1_lean.authbc-pi4b.{n}.csv")["run_utc"]
                for n in ("control-20261009", "frames-kept")]
        assert runs == sorted(runs) and runs[0][:8] == runs[1][:8] == "20261009"

    def test_all_three_runs_computed_the_same_thing(self) -> None:
        def sums(name: str) -> dict[tuple[str, str], str]:
            return {(r["op"], r["agg_b"]): r["checksum"] for r in _rows(HW / name)}
        assert sums("p1_lean.authbc-pi4b.csv") == sums("p1_lean.authbc-pi4b.control-20261009.csv") \
            == sums("p1_lean.authbc-pi4b.frames-kept.csv")

    def test_the_control_reproduces_the_morning_within_two_percent(self) -> None:
        for b, (lo, hi) in ((4, (1.383, 1.439)), (1, (0.640, 0.666))):
            assert lo <= CONTROL[("frame_receive", b)] <= hi
        assert abs(CONTROL[("frame_receive", 4)] / LEAN[("frame_receive", 4)] - 1) < 0.005

    def test_keeping_frames_costs_under_one_percent_where_two_were_allowed(self) -> None:
        for b in (1, 4):
            ratio = KEPT[("frame_receive", b)] / CONTROL[("frame_receive", b)]
            assert 1.00 <= ratio <= 1.02
            assert ratio < 1.01
        added_us = 1e3 * (KEPT[("frame_receive", 4)] - CONTROL[("frame_receive", 4)])
        assert 3.0 <= added_us <= 12.0                       # the figure expected beforehand
        assert NUMBERS["leanRecvKeepUs"] == f"{added_us:.0f}" == "10"
        assert NUMBERS["leanRecvKeepPct"] == "0.7"

    def test_the_senders_time_did_not_move(self) -> None:
        for b in (1, 4):
            assert abs(KEPT[("frame_send", b)] / CONTROL[("frame_send", b)] - 1) < 0.01

    def test_fifty_seven_nodes_stand_by_two_parts_in_a_thousand(self) -> None:
        """Said so in the thesis: the count is one frame-time step from 56."""
        bound_ms = 1e3 / (12.5 * 56)
        assert f"{bound_ms:.4f}" == "1.4286"
        margin = 1 - KEPT[("frame_receive", 4)] / bound_ms
        assert 0.001 < margin < 0.003
        assert "by a margin of two parts in a thousand" in CODESIGN


class TestTheMultiCoreMeasurementScript:
    """`hw/multicore_receive.py` (audit F84): K receivers on K cores at once."""

    def test_its_self_test_runs_two_workers_and_writes_nothing(self, tmp_path: Path) -> None:
        import sys
        done = subprocess.run([sys.executable, str(REPO / "hw" / "multicore_receive.py"),
                               "--check", "--workers", "1", "2"], cwd=tmp_path,
                              capture_output=True, text=True, timeout=120)
        assert done.returncode == 0, done.stderr
        assert "OK: multicore_receive.py --check ran 2 runs" in done.stdout
        assert not list(tmp_path.iterdir())

    def test_a_neighbour_is_charged_twelve_and_a_half_frames_a_second(self) -> None:
        text = (REPO / "hw" / "multicore_receive.py").read_text(encoding="utf-8")
        assert "FRAMES_PER_NODE_S = 50.0 / BATCH" in text and "BATCH = 4" in text
        assert '"nodes_served": 1 + int(total // FRAMES_PER_NODE_S)' in text
