"""Broadcast emulator: lossless delivery, MTU, sender-only airtime, determinism, loss rate."""

from __future__ import annotations

import pytest

from authbc.channel.airtime import airtime_broadcast
from authbc.channel.emulator import BroadcastChannel


def test_p0_all_receive_and_airtime_is_sender_only() -> None:
    ch = BroadcastChannel(node_ids=[1, 2, 3], p=0.0, seed=1)
    frame = b"x" * 200
    got = ch.broadcast(sender=1, frame_bytes=frame)
    assert sorted(got) == [2, 3]  # every other node receives
    assert ch.metrics[1].frames_tx == 1 and ch.metrics[1].frames_rx == 0
    assert ch.metrics[2].frames_rx == 1 and ch.metrics[3].frames_rx == 1
    # sender charged one frame's airtime; receivers charged none (no double-count)
    assert ch.metrics[1].airtime_us == pytest.approx(airtime_broadcast(200))
    assert ch.metrics[2].airtime_us == 0.0 and ch.metrics[3].airtime_us == 0.0
    assert ch.total_airtime_us() == pytest.approx(airtime_broadcast(200))


def test_mtu_enforced() -> None:
    ch = BroadcastChannel(node_ids=[1, 2], p=0.0, seed=1)
    with pytest.raises(ValueError):
        ch.broadcast(sender=1, frame_bytes=b"z" * 1501)


def test_determinism_same_seed_identical_metrics() -> None:
    def run():
        ch = BroadcastChannel(node_ids=[1, 2, 3, 4], p=0.1, seed=2024)
        for i in range(500):
            ch.broadcast(sender=1 + (i % 4), frame_bytes=b"f" * 300)
        return ch.metrics_rows()

    assert run() == run()  # byte-identical metrics across identical seeds


def test_receive_fraction_near_1_minus_p() -> None:
    """Over many frames the per-receiver receive fraction ≈ (1−p) (full Binomial check: audit)."""
    p = 0.1
    ch = BroadcastChannel(node_ids=[1, 2], p=p, seed=7)
    n = 20000
    for _ in range(n):
        ch.broadcast(sender=1, frame_bytes=b"f" * 100)
    frac = ch.metrics[2].frames_rx / n
    assert frac == pytest.approx(1 - p, abs=0.01)  # ~0.9 ± 0.01


def test_p1_drops_everything() -> None:
    ch = BroadcastChannel(node_ids=[1, 2], p=1.0, seed=3)
    assert ch.broadcast(sender=1, frame_bytes=b"a" * 50) == []
    assert ch.metrics[2].frames_rx == 0
