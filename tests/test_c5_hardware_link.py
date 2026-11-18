"""C5's hardware link (analysis/c5_hardware_link.py): the size line runs through W3a's two
measured record frames, the loss is a straight line between measured sizes and never extrapolated,
and feasible batches are reported as the runs they are."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("c5_hw", REPO / "analysis" / "c5_hardware_link.py")
assert spec and spec.loader
hw = importlib.util.module_from_spec(spec)
sys.modules["c5_hw"] = hw
spec.loader.exec_module(hw)


def test_frame_size_passes_through_the_measured_frames() -> None:
    assert hw.frame_bytes(1) == 147 and hw.frame_bytes(4) == 173
    assert hw.frame_bytes(hw.B_MAX) <= 1028


def test_loss_is_interpolated_not_extrapolated() -> None:
    pts = {147: 0.03, 173: 0.04, 1028: 0.06}
    assert hw.interpolate(pts, 160) == pytest.approx(0.035)
    assert hw.interpolate(pts, 600.5) == pytest.approx(0.05)
    with pytest.raises(ValueError):
        hw.interpolate(pts, 1100)


def test_ranges() -> None:
    assert hw.ranges([1, 2, 3, 7, 8, 10]) == "1-3, 7-8, 10"
    assert hw.ranges([]) == ""
