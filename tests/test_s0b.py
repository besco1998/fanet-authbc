"""S0b's scorer (`analysis/s0b.py`) on synthetic sessions with two captures of the same frames:
an AR9271 that passes, one that misses frames, one whose signal steps disagree with the TP-Link's,
and Mohamed's diagnostic rule both ways."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(REPO / "analysis"), str(REPO / "tests"), str(REPO / "src")]

import s0b  # noqa: E402

import hw_synth  # noqa: E402
from pcap_synth import data_frame, pcap, radiotap_realtek  # noqa: E402

T0 = 1_795_400_000_000_000_000
PLAN = REPO / "experiments" / "channel24" / "plan_s0b.txt"


def _windows() -> list[hw_synth.Window]:
    out, t = [], T0
    for line in PLAN.read_text().splitlines():
        if line.startswith("#"):
            continue
        name, rate, _b, senders, sec = line.split()[:5]
        nodes = tuple(int(x) for x in senders.split(","))
        n = {"G": 1000, "R": 400, "P": 120, "X": 300}[name[0]]
        step = 2_050_000 if float(rate) == 600 else 20_000_000
        times = {s: [t + k * step + 7_000 * i for k in range(n)] for i, s in enumerate(nodes)}
        got = {(s, r): set(range(n)) for s in nodes for r in (1, 2, 3) if r != s}
        out.append(hw_synth.Window(label=name, rate=float(rate), senders=nodes,
                                   seconds=int(sec), times=times, got=got))
        t += (int(sec) + 5) * 1_000_000_000
    return out


def _signal(label: str, slope: float) -> int:
    """dBm for a window: the set power from the label, each dB set giving `slope` dB received."""
    p = int(label[2:]) if label[:2] in ("PA", "PB", "PC") else 15
    return round(-40 - slope * (15 - p))


def _session(tmp: Path, ar_miss: dict[int, int] | None = None, ar_slope_a: float = 0.7,
             tp_slope_a: float = 0.7, slope_bc: float = 1.0) -> Path:
    windows = _windows()
    s = hw_synth.write_session(tmp / "s", (1, 2, 3), windows, stamp=lambda r, t: int(t),
                               rssi=lambda r, w: {"any": "-50", "peers": {}})
    ar, tp = [], []
    for w in windows:
        for src, times in w.times.items():
            slope_ar = ar_slope_a if src == 1 else slope_bc
            slope_tp = tp_slope_a if src == 1 else slope_bc
            for seq, t in enumerate(times):
                body = data_frame(seq, src_ip=f"10.0.0.{src}") + b"FCS!"
                miss = (ar_miss or {}).get(src)
                tsft = int(t // 1000)
                if not (miss and w.label.startswith("G") and seq % miss == 0):
                    rt = radiotap_realtek(tsft, _signal(w.label, slope_ar))
                    ar.append((int(t) + 200_000, rt + body))
                tp.append((int(t) + 300_000, radiotap_realtek(tsft, _signal(w.label, slope_tp))
                           + body))
    for folder, recs, module in (("sniffer_ar", ar, "ath9k_htc"), ("sniffer", tp, "8188eu")):
        (s / folder).mkdir()
        (s / folder / "sniff.pcap").write_bytes(pcap(sorted(recs)))
        (s / folder / "sniffer.log").write_text(f"[t] env: kernel x | module {module} AB\n")
    return s


def _held(rows: list[dict], what: str) -> list:
    return [r["held"] for r in rows if r["what"] == what]


class TestTheGate:
    def test_an_ar9271_that_records_everything_passes(self, tmp_path: Path) -> None:
        rows = s0b.score(_session(tmp_path))
        for what in ("the sniffer under test is ath9k_htc", "capture completeness (AR9271)",
                     "TSFT present (AR9271)", "TSFT start-to-start (AR9271)",
                     "signal step: AR9271 against TP-Link, same frames",
                     "every frame at 1 Mb/s (AR9271)"):
            assert _held(rows, what) and all(_held(rows, what)), what

    def test_missing_one_frame_in_fifty_of_pi_b_fails(self, tmp_path: Path) -> None:
        rows = s0b.score(_session(tmp_path, ar_miss={2: 50}))
        assert _held(rows, "capture completeness (AR9271)") == [True, False, True]

    def test_a_reading_that_disagrees_with_the_tp_link_fails(self, tmp_path: Path) -> None:
        rows = s0b.score(_session(tmp_path, ar_slope_a=1.0, tp_slope_a=0.7))
        # falls of 3/6/9 against 2.1/4.2/6.3: within 1 dB at 3 dB only
        assert _held(rows, "signal step: AR9271 against TP-Link, same frames") == [True, False,
                                                                                  False]


class TestTheDiagnostic:
    def test_linear_steps_of_pi_b_and_the_pi_3_point_at_pi_a(self, tmp_path: Path) -> None:
        rows = s0b.score(_session(tmp_path, slope_bc=1.0))
        verdict = next(r for r in rows if r["what"] == "diagnostic: who compresses")["measured"]
        assert verdict.startswith("the AR9271 is linear")

    def test_compressed_steps_cannot_be_separated(self, tmp_path: Path) -> None:
        rows = s0b.score(_session(tmp_path, slope_bc=0.7))
        verdict = next(r for r in rows if r["what"] == "diagnostic: who compresses")["measured"]
        assert "cannot be separated" in verdict and "HackRF" in verdict


def test_the_plan_parses_in_about_eleven_minutes() -> None:
    run = subprocess.run(["bash", str(REPO / "hw" / "channel" / "run_window_plan2.sh"), "1", "0",
                          str(PLAN)], env={"DRY": "1", "PATH": "/usr/bin:/bin"},
                         capture_output=True, text=True, check=True)
    assert len([ln for ln in run.stdout.splitlines() if ln.startswith("window ")]) == 22
    assert int(run.stdout.splitlines()[-1].split()[1]) - 120 < 12 * 60
