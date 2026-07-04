"""End-to-end macro through the emulator: golden counters (p=0), determinism, V ≈ 1−p."""

from __future__ import annotations

import pytest

from authbc.bench.macro import MacroConfig, run_macro


def test_golden_through_emulator_p0() -> None:
    """p=0: every frame delivered, every record verified, each receiver stores all others'.

    3 UAVs × 10 records; each of the 3 receivers stores the other 2 senders' 10 records ⇒
    total_stored = 3·2·10 = 60; broadcast = verified = 60; V = 1.
    """
    cfg = MacroConfig(placement="B", n_uav=3, records_per_uav=10, b=5, p=0.0, seed=1)
    out = run_macro(cfg)
    assert out["broadcast_instances"] == 60
    assert out["verified_instances"] == 60
    assert out["total_stored"] == 60
    assert out["V"] == pytest.approx(1.0)
    assert out["total_airtime_us"] > 0.0


def test_macro_deterministic() -> None:
    cfg = MacroConfig(placement="B", n_uav=4, records_per_uav=20, b=6, p=0.1, seed=42)
    assert run_macro(cfg) == run_macro(cfg)


def test_V_tracks_1_minus_p_placement_B() -> None:
    """B is loss-local: a delivered frame verifies all its records ⇒ V ≈ (1−p)."""
    cfg = MacroConfig(placement="B", n_uav=3, records_per_uav=2000, b=8, p=0.05, seed=9)
    out = run_macro(cfg)
    assert out["V"] == pytest.approx(0.95, abs=0.02)


def test_placement_A_end_to_end_p0() -> None:
    cfg = MacroConfig(placement="A", n_uav=3, records_per_uav=6, b=3, p=0.0, seed=2)
    out = run_macro(cfg)
    assert out["V"] == pytest.approx(1.0) and out["total_stored"] == 36  # 3·2·6
