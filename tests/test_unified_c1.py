"""U-C1's classifier (analysis/unified_c1.py), on a trace made up by hand.

Held here, as predictions/UC1.md fixes them:
* overlapping frames whose starts differ → detection window;
* starts at one instant, every frame having drawn a backoff → same-slot tie;
* starts at one instant, one frame without a draw → zero-backoff start after a busy period;
* a frame alone is not lost; shares are over all frames sent;
* a counts frames enqueued inside a busy period (sensed from start + 4 µs); K the other frames
  still held when that period ends.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "analysis"))
spec = importlib.util.spec_from_file_location("unified_c1", REPO / "analysis" / "unified_c1.py")
assert spec and spec.loader
c1 = importlib.util.module_from_spec(spec)
sys.modules["unified_c1"] = c1
spec.loader.exec_module(c1)

US = 1_000
T = 300 * US


def _frame(e: int, b: int) -> dict[str, int]:
    return {"E": e, "B": b, "F": b + T}


def _trace():
    fr = {
        (0, 1): _frame(0, 34 * US),                      # alone: not lost
        # a tie: 1 and 2 both drew backoffs and start at one instant
        (1, 2): _frame(100 * US, 1_000 * US), (2, 3): _frame(110 * US, 1_000 * US),
        # zero backoff after busy: 3 drew, 4 did not (pre-empted, zero slots)
        (3, 4): _frame(2_000 * US, 3_000 * US), (4, 5): _frame(2_100 * US, 3_000 * US),
        # detection window: starts 2 µs apart
        (5, 6): _frame(5_000 * US, 5_034 * US), (6, 7): _frame(5_001 * US, 5_036 * US),
    }
    draws = {1: [100 * US], 2: [110 * US], 3: [2_000 * US]}
    return fr, draws


def test_each_class_and_the_shares() -> None:
    r = c1.classify(*_trace())
    assert r["tie"] == pytest.approx(2 / 7)
    assert r["zero_backoff_after_busy"] == pytest.approx(2 / 7)
    assert r["detection_window"] == pytest.approx(2 / 7)
    assert r["p"] == pytest.approx(6 / 7)


def test_a_and_k() -> None:
    fr = {(0, 1): _frame(0, 34 * US),                    # busy from 38 µs to 334 µs
          (1, 2): _frame(100 * US, 400 * US),            # arrives busy; held at 334 µs with 3
          (2, 3): _frame(200 * US, 800 * US)}            # arrives busy; held at 334 µs with 2
    r = c1.classify(fr, {1: [100 * US], 2: [200 * US]})
    assert r["a"] == pytest.approx(2 / 3)
    assert r["K"] == pytest.approx(1.0)                  # each waits alongside one other


# U-D's D3 table (predictions/UD.md): the classifier's predictions at 802.11b, 1 Mb/s.
D3 = {("Pb1B", 5): (0.00564, 0.00030, 0.00212, 0.00807, 0.3275, 0.5605),
      ("Pb1B", 11): (0.10730, 0.00183, 0.00710, 0.11623, 0.7742, 5.1482),
      ("Pb1D", 17): (0.00767, 0.00033, 0.00219, 0.01019, 0.3701, 0.6770),
      ("Pb1D", 35): (0.08866, 0.00145, 0.00596, 0.09607, 0.7525, 4.2737)}


@pytest.mark.parametrize(("cell", "n"), sorted(D3))
def test_predictions_at_80211b_are_the_registered_ones(cell: str, n: int) -> None:
    got = c1.predictions(cell, n)
    for q, want in zip(c1.QUANTITIES, D3[(cell, n)], strict=True):
        assert round(got[q], 5 if q not in ("a", "K") else 4) == want, q


def test_80211a_predictions_unchanged() -> None:
    got = c1.predictions("C", 34)                       # predictions/UC1.md, row C 34
    assert round(got["tie"], 5) == 0.02603 and round(got["K"], 4) == 1.0452
