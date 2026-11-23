"""The gate S0's scorer (`analysis/s0.py`) on synthetic sessions whose answer is known: a sniffer
that records everything, one that misses frames, one without TSFT, one whose signal does not follow
the set power; the TSF wrap; the plan."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(REPO / "analysis"), str(REPO / "tests"), str(REPO / "src")]

import s0  # noqa: E402

import hw_synth  # noqa: E402
from pcap_synth import data_frame, pcap, radiotap_realtek  # noqa: E402

T0 = 1_795_400_000_000_000_000           # ns
CYCLE_NS = 2_050_000                      # a saturated sender alone: 2 050 µs
POWER = {"P15": 15, "P12": 12, "P9": 9, "P6": 6}


def _windows() -> list[hw_synth.Window]:
    out = []
    t = T0
    for label in s0.plan()[2:]:
        name, rate, _b, senders, sec = label.split()[:5]
        nodes = tuple(int(x) for x in senders.split(","))
        n = {"G": 1000, "R": 400, "P": 120, "X": 300, "W": 50}[name[0]]
        step = CYCLE_NS if float(rate) == 600 else 20_000_000
        times = {s: [t + k * step + 7_000 * i for k in range(n)] for i, s in enumerate(nodes)}
        got = {(s, r): set(range(n)) for s in nodes for r in (1, 2, 3) if r != s}
        out.append(hw_synth.Window(label=name, rate=float(rate), senders=nodes,
                                   seconds=int(sec), times=times, got=got))
        t += (int(sec) + 5) * 1_000_000_000
    return out


def _session(tmp: Path, miss_every: int = 0, tsft: bool = True,
             signal_of: dict[int, int] | None = None) -> Path:
    windows = _windows()
    s = hw_synth.write_session(tmp / "s", (1, 2, 3), windows, stamp=lambda r, t: int(t),
                               rssi=lambda r, w: {"any": "-50", "peers": {}})
    records = []
    signal_of = signal_of or {15: -40, 12: -43, 9: -46, 6: -49}
    for w in windows:
        level = POWER.get(w.label, 15)
        for src, times in w.times.items():
            for seq, t in enumerate(times):
                if miss_every and src == 1 and w.label == "G1" and seq % miss_every == 0:
                    continue
                rt = radiotap_realtek(int(t // 1000) if tsft else None, signal_of[level])
                records.append((int(t) + 300_000,
                                rt + data_frame(seq, src_ip=f"10.0.0.{src}") + b"FCS!"))
    records.sort()
    (s / "sniffer").mkdir()
    (s / "sniffer" / "sniff_bbb2_1.pcap").write_bytes(pcap(records))
    return s


def _row(rows: list[dict], what: str, item: str | None = None) -> dict:
    return next(r for r in rows if r["what"] == what and (item is None or r["item"] == item))


class TestTheGate:
    def test_a_sniffer_that_records_everything_passes(self, tmp_path: Path) -> None:
        rows = s0.score(_session(tmp_path))
        assert _row(rows, "capture completeness", "node 1, 1000 sent")["held"] is True
        assert _row(rows, "TSFT present")["held"] is True
        s2s = [r for r in rows if r["what"] == "TSFT start-to-start"]
        assert len(s2s) == 6 and all(r["held"] for r in s2s)
        assert all(r["held"] for r in rows if r["what"] == "signal follows set power")
        assert _row(rows, "every frame at 1 Mb/s")["held"] is True
        assert _row(rows, "bad-checksum frames passed")["measured"] == "no"

    def test_missing_one_frame_in_fifty_fails_completeness(self, tmp_path: Path) -> None:
        rows = s0.score(_session(tmp_path, miss_every=50))
        row = _row(rows, "capture completeness", "node 1, 1000 sent")
        assert row["measured"] == 0.98 and row["held"] is False

    def test_without_tsft_the_gate_says_so_and_checks_no_intervals(self, tmp_path: Path
                                                                   ) -> None:
        rows = s0.score(_session(tmp_path, tsft=False))
        assert _row(rows, "TSFT present")["held"] is False
        assert not [r for r in rows if r["what"] == "TSFT start-to-start"]
        # host times here are the true times + 0.3 ms: a constant offset, no jitter
        assert _row(rows, "host-time jitter, sniffer against pi-B (us)")["measured"] == 0.0

    def test_a_signal_that_does_not_follow_the_power_fails(self, tmp_path: Path) -> None:
        rows = s0.score(_session(tmp_path, signal_of={15: -40, 12: -41, 9: -42, 6: -43}))
        steps = [r for r in rows if r["what"] == "signal follows set power"]
        assert [r["measured"] for r in steps] == [1.0, 2.0, 3.0]
        assert not any(r["held"] for r in steps)


class TestTheHelpers:
    def test_the_tsf_wrap_is_undone(self) -> None:
        w = s0.TSF_WRAP
        assert s0.unwrap_tsft([w - 2000, w - 1000, 500, 2500]) == [w - 2000, w - 1000, w + 500,
                                                                   w + 2500]

    @pytest.mark.parametrize(("levels", "steps"), [({15: -40, 12: -43}, {3: 3})])
    def test_steps_are_falls_from_15_dbm(self, levels: dict[int, float], steps: dict) -> None:
        assert s0.signal_steps(levels) == steps


class TestThePlan:
    def test_it_parses_and_puts_the_wl18xx_window_last_before_the_checks(self, tmp_path: Path
                                                                          ) -> None:
        plan = tmp_path / "p.txt"
        plan.write_text("\n".join(s0.plan()) + "\n")
        run = subprocess.run(["bash", str(REPO / "hw" / "channel" / "run_window_plan2.sh"), "1",
                              "0", str(plan)], env={"DRY": "1", "PATH": "/usr/bin:/bin"},
                             capture_output=True, text=True, check=True)
        labels = [ln.split()[2] for ln in run.stdout.splitlines() if ln.startswith("window ")]
        assert labels == ["R1", "R2", "R3", "G1", "G2", "G3", "P15", "P12", "P9", "P6", "X",
                          "W", "R1", "R2", "R3"]
        assert int(run.stdout.splitlines()[-1].split()[1]) - 120 < 10 * 60
