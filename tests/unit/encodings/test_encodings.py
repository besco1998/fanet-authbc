"""Round-trip + delta-recovery tests for all encoders (docs/03 §3, docs/06 §5)."""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from authbc.bench import telemgen
from authbc.encodings.delta_enc import DeltaDesyncError, DeltaEncoder
from authbc.encodings.registry import ENCODER_CLASSES, new_encoder

ENCODER_NAMES = list(ENCODER_CLASSES)


@pytest.mark.parametrize("name", ENCODER_NAMES)
def test_round_trip_stream_1000(name: str) -> None:
    """Encode a 1000-record stream then decode it back — must be identical (all encoders)."""
    recs = telemgen.samples(seed=11, n=1000)
    enc = new_encoder(name)
    dec = new_encoder(name)
    frames = [enc.encode(r) for r in recs]
    out = [dec.decode(f) for f in frames]
    assert out == recs


@pytest.mark.parametrize("name", ENCODER_NAMES)
@settings(max_examples=200)
@given(seed=st.integers(0, 2**31 - 1), n=st.integers(1, 40))
def test_round_trip_property(name: str, seed: int, n: int) -> None:
    recs = telemgen.samples(seed=seed, n=n)
    enc, dec = new_encoder(name), new_encoder(name)
    out = [dec.decode(enc.encode(r)) for r in recs]
    assert out == recs


def test_delta_keyframe_cadence() -> None:
    """First frame and every K-th frame are keyframes; the rest are deltas."""
    recs = telemgen.samples(seed=7, n=40)
    enc = DeltaEncoder()
    frames = [enc.encode(r) for r in recs]
    for i, f in enumerate(frames):
        expected = 0x00 if i % enc.keyframe_interval == 0 else 0x01
        assert f[0] == expected


def test_delta_loss_then_keyframe_recovery() -> None:
    """Dropping delta frames desyncs the decoder until the next keyframe re-syncs it."""
    recs = telemgen.samples(seed=9, n=48)  # 3 keyframes at indices 0,16,32
    enc = DeltaEncoder()
    frames = [enc.encode(r) for r in recs]

    dec = DeltaEncoder()
    # Drop frames 5..15 (deltas after the first keyframe). Decoder should decode 0..4,
    # desync on 6..15 would-be frames (they're gone), then re-sync at keyframe 16.
    delivered = [(i, f) for i, f in enumerate(frames) if not (5 <= i < 16)]
    decoded: dict[int, telemgen.TelemetryRecord] = {}
    for i, f in delivered:
        try:
            decoded[i] = dec.decode(f)
        except DeltaDesyncError:
            pass
    # frames 0..4 decode against the first keyframe; 16.. decode after re-sync.
    for i in list(range(0, 5)) + list(range(16, 48)):
        assert decoded[i] == recs[i]
    assert dec.desync_count == 0  # dropped frames never reached the decoder

    # Now feed a delta frame with NO prior keyframe → explicit desync bump.
    fresh = DeltaEncoder()
    with pytest.raises(DeltaDesyncError):
        fresh.decode(frames[1])  # a delta frame, no keyframe seen first
    assert fresh.desync_count == 1


def test_deterministic_flag_true_for_all() -> None:
    for name in ENCODER_NAMES:
        assert new_encoder(name).deterministic is True
