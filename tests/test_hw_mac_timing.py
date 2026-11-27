"""C1's timing analysis (`analysis/hw_mac_timing.py`) on synthetic frames whose answer is known: a
known slot, DIFS, uniform window and share sent with no backoff; a missed frame excluded by its
sequence numbers; the airtime slope and intercept; the lattice's harmonic."""
from __future__ import annotations

import random
import sys
from pathlib import Path

import pytest

sys.path[:0] = [str(Path(__file__).resolve().parents[1] / "analysis")]

import hw_mac_timing as m  # noqa: E402
import pcap_frames as pf  # noqa: E402

DIFS, SLOT, W = 50, 20, 16


def _frames(gaps: list[float], payload: int = 145, drop: set[int] | None = None,
            t0: int = 4_000_000_000) -> list[pf.Frame]:
    """A sender's frames with the given gaps after each, TSFT at each start, some dropped."""
    out, t = [], float(t0)
    for seq in range(len(gaps) + 1):
        if not drop or seq not in drop:
            out.append(pf.Frame(index=seq, host_ns=int(t * 1000), tsft_us=int(t) % (1 << 32),
                                rate_mbps=1.0, short_preamble=False, bad_fcs=False,
                                signal_dbm=-45, freq_mhz=2462, length=payload + 60,
                                src="aa", src_ip="10.0.0.1", seq=seq, udp_len=payload + 8))
        if seq < len(gaps):
            t += m.airtime_us(payload) + gaps[seq]
    return out


def _backoff_gaps(n: int, no_backoff: float, seed: int = 1) -> list[float]:
    rng = random.Random(seed)
    return [float(DIFS if rng.random() < no_backoff else DIFS + SLOT * rng.randrange(W))
            for _ in range(n)]


class TestTheGaps:
    def test_floor_lattice_window_and_the_share_with_no_backoff(self) -> None:
        gaps = _backoff_gaps(20_000, no_backoff=0.5)
        s = m.gap_stats(gaps)
        assert s["gap_floor_us"] == DIFS and s["lattice_us"] == SLOT
        assert s["w_minus_1"] == W - 1
        assert s["share_no_backoff"] == pytest.approx(0.5 + 0.5 / W, abs=0.01)

    def test_a_plain_uniform_backoff_has_its_share_at_one_over_w(self) -> None:
        s = m.gap_stats(_backoff_gaps(20_000, no_backoff=0.0))
        assert s["share_k0"] == pytest.approx(1 / W, abs=0.01) and s["w_minus_1"] == W - 1

    def test_the_harmonic_does_not_win_the_lattice(self) -> None:
        # only even slots populated: the 2σ peak is as high as σ's would be; σ = 40 is right here
        rng = random.Random(3)
        gaps = [float(DIFS + 2 * SLOT * rng.randrange(8)) for _ in range(10_000)]
        assert m.lattice_us(gaps) == 2 * SLOT
        # all slots populated: σ = 20, though 40 also peaks
        assert m.lattice_us(_backoff_gaps(10_000, 0.0)) == SLOT


class TestTheIntervals:
    def test_a_missed_frame_removes_both_pairs_it_touches(self) -> None:
        gaps = [100.0] * 10
        d = m.intervals(_frames(gaps, drop={5}))
        assert len(d) == 10 - 2 and set(d) == {m.airtime_us(145) + 100.0}

    def test_strict_also_removes_the_pairs_next_to_a_miss(self) -> None:
        # 8 pairs survive the miss; strict drops the 2 beside it and the 2 at the window's ends,
        # whose outer neighbours were never sent
        gaps = [100.0] * 10
        assert len(m.intervals(_frames(gaps, drop={5}), strict=True)) == 8 - 2 - 2

    def test_the_tsf_wrap_is_crossed(self) -> None:
        fr = _frames([60.0] * 5, t0=(1 << 32) - 5000)
        assert set(m.intervals(fr)) == {m.airtime_us(145) + 60.0}


class TestTheAirtime:
    def test_the_slope_and_intercept_come_back(self) -> None:
        pts = [(p, m.airtime_us(p) + DIFS) for p in (145, 300, 600, 1000)]
        fit = m.airtime_fit(pts)
        assert fit["slope_us_per_byte"] == pytest.approx(8.0)
        assert fit["intercept_us"] == pytest.approx(m.PREAMBLE_LONG_US + DIFS)

    def test_145_bytes_is_1864_us(self) -> None:
        assert m.airtime_us(145) == 1864.0
