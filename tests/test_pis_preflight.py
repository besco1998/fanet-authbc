"""The Pi-only preflight (`analysis/pis_preflight.py`): today's verdicts, and each rule alone."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(REPO / "analysis"), str(REPO / "tests")]

import pis_preflight as pf  # noqa: E402

import hw_synth  # noqa: E402

HW = REPO / "results" / "hw" / "channel24"


@pytest.mark.parametrize(("folder", "verdict"), [
    ("w1pqr_2026-11-22_pre1", "GO"),        # 08:10 boot, yet 1 Mb/s
    ("w1q_2026-11-22_pre", "RETRY"),        # after the 15:57 power cut: 1 666 us, the offered rate
    ("w1q_2026-11-22_pre2", "GO"),          # the same boards, warm
])
def test_the_verdicts_given_at_the_boards_on_2026_11_22(folder: str, verdict: str) -> None:
    assert pf.check(HW / folder).verdict == verdict


def _session(tmp_path: Path, cycle_us: dict[int, float] | None = None,
             frameburst: tuple[str, str] = ("0", "0"), throttled: str = "0x0") -> Path:
    cycle_us = cycle_us or {}
    windows = []
    for s in pf.NODES:
        n = 600
        step_ns = 1e3 * cycle_us.get(s, 2050.0)
        others = [r for r in pf.NODES if r != s]
        windows.append(hw_synth.Window(
            label=f"R{s}", rate=600, senders=(s,), times={s: [k * step_ns for k in range(n)]},
            got={(s, r): set(range(n)) for r in others}, throttled=throttled))
    return hw_synth.write_session(tmp_path / "pre", pf.NODES, windows,
                                  stamp=lambda r, t: int(t),
                                  rssi=lambda r, w: {"any": "-50", "peers": {}},
                                  frameburst=frameburst)


class TestTheRules:
    def test_every_cycle_in_band_is_go(self, tmp_path: Path) -> None:
        r = pf.check(_session(tmp_path))
        assert r.verdict == "GO" and len(r.cycles) == 3

    def test_only_too_fast_is_one_retry(self, tmp_path: Path) -> None:
        r = pf.check(_session(tmp_path, {1: 1666.0, 2: 1666.0}))
        assert r.verdict == "RETRY" and len(r.too_fast) == 2 and not r.failing

    def test_too_slow_is_no_go(self, tmp_path: Path) -> None:
        assert pf.check(_session(tmp_path, {3: 2700.0})).verdict == "NO-GO"

    def test_too_fast_with_another_fault_is_no_go(self, tmp_path: Path) -> None:
        r = pf.check(_session(tmp_path, {1: 1666.0}, throttled="0x50005"))
        assert r.verdict == "NO-GO" and r.too_fast

    @pytest.mark.parametrize("fb", [("1", "0"), ("0", "1"), ("0", "missing")])
    def test_frame_burst_not_off_before_and_after_is_no_go(self, tmp_path: Path,
                                                           fb: tuple[str, str]) -> None:
        assert pf.check(_session(tmp_path, frameburst=fb)).verdict == "NO-GO"

    def test_a_board_without_its_files_is_no_go(self, tmp_path: Path) -> None:
        session = _session(tmp_path)
        for f in (session / "node2").iterdir():
            f.unlink()
        r = pf.check(session)
        assert r.verdict == "NO-GO" and r.failing == ["node 2: no session.log"]
