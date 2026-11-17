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
