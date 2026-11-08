"""How long the time window holds without GNSS (W6(a), docs/02 §12).

Held here: that A5's outcome depends on an outage only through the separation of the two clocks,
which is what makes the holdover exactly inversely proportional to the oscillator's offset; the
thresholds docs/02 §12 reads from A5's file; and the table's scaling.
"""
from __future__ import annotations

import csv
from pathlib import Path

import pytest

from authbc.placement.freshness_rule import TimeWindow

REPO = Path(__file__).resolve().parents[3]
A5 = REPO / "results" / "raw" / "replay_window.csv"
LOMBARDI_TCXO, LOMBARDI_OCXO_WORST = 1e-6, 1e-8          # Table 17.5, offset after warm-up


def _outage_rows(policy: str) -> list[dict[str, str]]:
    with A5.open(encoding="utf-8") as fh:
        return [r for r in csv.DictReader(ln for ln in fh if not ln.startswith("#"))
                if r["study"] == "outage" and r["policy"] == policy]


def _thresholds(policy: str) -> tuple[float, float]:
    """The last clock separation with false rejection below 10⁻⁴ (A5's criterion), and the first
    above it (ms)."""
    rows = sorted(_outage_rows(policy), key=lambda r: float(r["clock_apart_ms"]))
    ok = [float(r["clock_apart_ms"]) for r in rows if float(r["false_rejection"]) < 1e-4]
    bad = [float(r["clock_apart_ms"]) for r in rows if float(r["false_rejection"]) >= 1e-4]
    return max(ok), min(bad)


class TestTheOutageEntersOnlyAsASeparation:
    def test_a5s_separation_is_two_offsets_times_the_outage(self) -> None:
        for r in _outage_rows("fixed150"):
            assert float(r["clock_apart_ms"]) == pytest.approx(
                2 * 20e-6 * float(r["outage_min"]) * 60 * 1000, abs=1e-6)

    @pytest.mark.parametrize("ppm,outage_s", [(20.0, 3600.0), (1.0, 72_000.0), (0.01, 7.2e6)])
    def test_the_widened_window_depends_on_the_product(self, ppm: float, outage_s: float) -> None:
        # 20 ppm for an hour, 1 ppm for 20 h, 0.01 ppm for 2 000 h: the same separation
        base = TimeWindow(batch=4, lam=50.0, t_ch_ms=3.0, t_v_ms=0.75, sigma_clk_ms=10.0,
                          guard_ms=10.0, drift_ppm=20.0)
        other = TimeWindow(batch=4, lam=50.0, t_ch_ms=3.0, t_v_ms=0.75, sigma_clk_ms=10.0,
                           guard_ms=10.0, drift_ppm=ppm)
        assert other.widened(outage_s) == pytest.approx(base.widened(3600.0))


class TestTheTableOfDocs02Section12:
    def test_the_thresholds_read_from_a5(self) -> None:
        assert _thresholds("fixed150") == (72.0, 108.0)
        assert _thresholds("fixed250") == (180.0, 216.0)

    @pytest.mark.parametrize("policy,hours", [("fixed150", (10.0, 15.0)),
                                              ("fixed250", (25.0, 30.0))])
    def test_a_tcxo(self, policy: str, hours: tuple[float, float]) -> None:
        last, first = _thresholds(policy)
        got = tuple(s / 1000 / (2 * LOMBARDI_TCXO) / 3600 for s in (last, first))
        assert got == pytest.approx(hours)

    def test_an_ocxo(self) -> None:
        last, first = _thresholds("fixed150")
        got = tuple(s / 1000 / (2 * LOMBARDI_OCXO_WORST) / 3600 for s in (last, first))
        assert got == pytest.approx((1000.0, 1500.0))
