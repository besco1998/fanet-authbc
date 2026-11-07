"""The rig self-test (hw/rig_selftest.py, hw/rig_check.py) and the window validity test.

Finding F78. On 2026-10-09 the board's ground had come loose from the meter's: the sync line
worked, the current read correctly, and the voltage reading moved by 0.29 V with the state of
the sync line. These tests hold the check that would have refused that rig — on captures made
up to have exactly one thing wrong each — and that the limits it prints are the limits it uses.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "hw"))


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, REPO / "hw" / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


energy_loop = _load("energy_loop")
rig_selftest = _load("rig_selftest")
rig_check = _load("rig_check")


def capture(*, line_shift_v: float = 0.0, source_ohm: float = 0.47, open_v: float = 5.24,
            idle_ma: float = 380.0, one_core_ma: float = 150.0, all_cores_ma: float = 570.0,
            drift_v: float = 0.0, sync: bool = True, board_channel: int = 1
            ) -> list[dict[str, str]]:
    """The self-test sequence as a meter would log it, 50 samples a second."""
    rows: list[dict[str, str]] = []
    ms = 1000
    total = sum(s for s, _h, _c in rig_selftest.SEQUENCE)
    for seconds, high, cores in rig_selftest.SEQUENCE:
        extra = {0: 0.0, 1: one_core_ma, -1: all_cores_ma}[cores]
        for _ in range(int(seconds * 50)):
            amps = (idle_ma + extra) / 1000.0
            volts = (open_v - source_ohm * amps + (line_shift_v if high and sync else 0.0)
                     + drift_v * (ms - 1000) / (1000.0 * total))
            board = (f"{volts:.3f}", f"{1000 * amps:.1f}", f"{volts * amps:.4f}")
            idle_other = ("5.215", "415.0", f"{5.215 * 0.415:.4f}")
            first, second = (board, idle_other) if board_channel == 1 else (idle_other, board)
            rows.append({"ms": str(ms), "window": "1" if high and sync else "0", "wtrans": "0",
                         "V1": first[0], "I1_mA": first[1], "P1_W": first[2],
                         "V2": second[0], "I2_mA": second[1], "P2_W": second[2]})
            ms += 20
    return rows


def verdicts(rows: list[dict[str, str]], channel: int = 1, manifest: dict | None = None
             ) -> dict[str, bool | None]:
    return {c.name: c.ok for c in rig_check.assess(rows, channel, manifest)}


GROUND = "the voltage does not move with the sync line"


class TestTheSequence:
    def test_three_marked_windows_idle_then_one_core_then_every_core(self) -> None:
        high = [(s, c) for s, h, c in rig_selftest.SEQUENCE if h]
        assert high == [(5.0, 0), (5.0, 1), (5.0, -1)]
        assert all(not h for _s, h, _c in rig_selftest.SEQUENCE[::2])     # low between and around
        assert rig_check.WINDOW_S == 5.0


class TestTheJudge:
    def test_a_rig_like_julys_passes_every_check(self) -> None:
        got = verdicts(capture())
        assert False not in got.values() and got[GROUND] is True
        assert sum(v is None for v in got.values()) == 4           # four values reported only

    def test_a_loose_ground_fails(self) -> None:
        """The fault of 2026-10-09: −0.29 V whenever the line is high. The supply then reads low
        as well, since every loaded window has the line high; nothing else is touched."""
        failed = {k for k, v in verdicts(capture(line_shift_v=-0.29)).items() if v is False}
        assert GROUND in failed
        assert failed <= {GROUND, "supply with one core busy", "supply with every core busy"}

    def test_a_small_ground_error_fails_that_check_and_no_other(self) -> None:
        got = verdicts(capture(line_shift_v=-0.05))
        assert [k for k, v in got.items() if v is False] == [GROUND]

    def test_julys_few_millivolts_pass(self) -> None:
        assert verdicts(capture(line_shift_v=-0.004))[GROUND] is True

    def test_an_idle_voltage_that_wanders_fails(self) -> None:
        got = verdicts(capture(drift_v=0.08))
        assert got["idle voltage is the same before and after"] is False

    def test_the_wrong_channel_fails(self) -> None:
        got = verdicts(capture(board_channel=2), channel=1)
        assert got["this channel is the board under test"] is False
        assert verdicts(capture(board_channel=2), channel=2)[
            "this channel is the board under test"] is True

    def test_a_supply_that_holds_one_core_and_not_four_fails_on_four(self) -> None:
        got = verdicts(capture(source_ohm=0.76))
        assert got["supply with one core busy"] is True
        assert got["supply with every core busy"] is False

    def test_a_dead_sync_line_stops_the_check_at_the_first_line(self) -> None:
        got = verdicts(capture(sync=False))
        assert got == {"the sync line marks three windows of 5 s": False}

    def test_an_under_voltage_during_the_test_fails_even_if_the_meter_looks_fine(self) -> None:
        state = {"undervoltage_events": "1", "governor": "performance"}
        name = "no under-voltage logged by the board during the test"
        assert verdicts(capture(), manifest={"before": state, "after": state})[name] is True
        moved = {"before": state, "after": {**state, "undervoltage_events": "2"}}
        assert verdicts(capture(), manifest=moved)[name] is False
        unread = {"before": {**state, "undervoltage_events": "NA"}, "after": state}
        assert verdicts(capture(), manifest=unread)[name] is False

    def test_the_limits_printed_in_the_table_are_the_limits_used(self) -> None:
        doc = rig_check.__doc__ or ""
        assert f"within {1000 * rig_check.LINE_SHIFT_MAX_V:.0f} mV" in doc
        assert f"within {1000 * rig_check.IDLE_DRIFT_MAX_V:.0f} mV" in doc
        assert f"+{1000 * rig_check.ONE_CORE_MIN_A:.0f} mA or more" in doc
        assert f"{rig_check.ONE_CORE_MIN_V} V or more" in doc
        assert f"{rig_check.ALL_CORES_MIN_V} V or more" in doc
        assert "that the sensor's gain is right" in doc           # what passing does not show


class TestAWindowIsCleanOnlyIfNothingHappenedInIt:
    def test_the_firmware_bits_as_before(self) -> None:
        clean = energy_loop.window_is_clean
        assert clean("throttled=0x0", "throttled=0x0")
        assert not clean("throttled=0x0", "throttled=0x50000")      # it happened in the window
        assert not clean("throttled=0x50005", "throttled=0x50005")  # it is happening now
        assert clean("throttled=0x50000", "throttled=0x50000")      # history, by these bits alone

    def test_once_the_bits_are_set_the_kernels_count_decides(self) -> None:
        clean = energy_loop.window_is_clean
        assert clean("throttled=0x50000", "throttled=0x50000", "1", "1")
        assert not clean("throttled=0x50000", "throttled=0x50000", "1", "2")
        assert clean("throttled=0x50000", "throttled=0x50000", "NA", "2")   # unreadable: bits only

    @pytest.mark.parametrize(("returncode", "stdout", "stderr", "expected"), [
        (0, "Oct 09 06:03:32 host kernel: hwmon hwmon1: Undervoltage detected!\n", "", "1"),
        (1, "", "", "0"),                       # journalctl: no line matched
        (1, "", "No journal files were found.", "NA"),
        (2, "", "", "NA"),
    ])
    def test_counting_the_kernels_lines(self, monkeypatch: pytest.MonkeyPatch, returncode: int,
                                        stdout: str, stderr: str, expected: str) -> None:
        monkeypatch.setattr(energy_loop.subprocess, "run", lambda *a, **k: SimpleNamespace(
            returncode=returncode, stdout=stdout, stderr=stderr))
        assert energy_loop.undervoltage_events() == expected

    def test_a_board_without_the_journal_reads_as_unknown_not_as_zero(
            self, monkeypatch: pytest.MonkeyPatch) -> None:
        def missing(*_a: object, **_k: object) -> None:
            raise FileNotFoundError("journalctl")
        monkeypatch.setattr(energy_loop.subprocess, "run", missing)
        assert energy_loop.undervoltage_events() == "NA"


class TestTheSyncPinOnAFreshlyBootedBoard:
    """The first export of a pin after a boot is writable only a moment later (2026-10-09)."""

    class _Attribute:
        def __init__(self, refusals: int) -> None:
            self.refusals, self.written = refusals, None

        def write_text(self, text: str) -> None:
            if self.refusals:
                self.refusals -= 1
                raise PermissionError("not yet handed to the gpio group")
            self.written = text

    def test_it_waits_for_the_permission_instead_of_giving_up(self) -> None:
        attribute = self._Attribute(refusals=3)
        energy_loop.write_when_permitted(attribute, "out", patience_s=2.0)   # type: ignore[arg-type]
        assert attribute.written == "out" and attribute.refusals == 0

    def test_a_pin_that_never_becomes_writable_is_still_an_error(self) -> None:
        attribute = self._Attribute(refusals=10_000)
        with pytest.raises(PermissionError):
            energy_loop.write_when_permitted(attribute, "out", patience_s=0.2)   # type: ignore[arg-type]
