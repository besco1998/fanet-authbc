"""Boundary-value correctness for every encoder (docs/03 §3).

Exercises the extreme field values of the integer schema (min/max of each width, ±full-range
coordinate deltas, 0x00.../0xff... hashes) through encode→decode. Catches int-width, varint,
zigzag, and byte-string edge bugs that random sampling might miss.
"""

from __future__ import annotations

import pytest

from authbc.bench.telemgen import (
    ALT_RANGE,
    BATTERY_RANGE,
    I16,
    LAT_RANGE,
    LON_RANGE,
    N_MODES,
    U16,
    U32,
    TelemetryRecord,
    validate,
)
from authbc.encodings.registry import ENCODER_CLASSES, new_encoder

ENCODER_NAMES = list(ENCODER_CLASSES)


def _rec(src, seq, ts, ph, lat, lon, alt, vx, vy, vz, bat, mode) -> TelemetryRecord:
    r = TelemetryRecord(src, seq, ts, ph, lat, lon, alt, vx, vy, vz, bat, mode)
    validate(r)  # every boundary record must itself be schema-valid
    return r


MIN_REC = _rec(U16[0], U32[0], U32[0], b"\x00" * 32, LAT_RANGE[0], LON_RANGE[0], ALT_RANGE[0],
               I16[0], I16[0], I16[0], BATTERY_RANGE[0], 0)
MAX_REC = _rec(U16[1], U32[1], U32[1], b"\xff" * 32, LAT_RANGE[1], LON_RANGE[1], ALT_RANGE[1],
               I16[1], I16[1], I16[1], BATTERY_RANGE[1], N_MODES - 1)
MID_REC = _rec(1234, 42, 1_000_000, bytes(range(32)), -1, 1, -12345, -1, 1, 0, 55, 3)

BOUNDARY_RECS = [MIN_REC, MAX_REC, MID_REC]


@pytest.mark.parametrize("name", ENCODER_NAMES)
@pytest.mark.parametrize("rec", BOUNDARY_RECS, ids=["min", "max", "mid"])
def test_boundary_round_trip(name: str, rec: TelemetryRecord) -> None:
    enc, dec = new_encoder(name), new_encoder(name)
    assert dec.decode(enc.encode(rec)) == rec


@pytest.mark.parametrize("name", ENCODER_NAMES)
def test_extreme_delta_stream(name: str) -> None:
    """min→max→min in one stream forces the largest possible deltas (delta encoder)."""
    stream = [MIN_REC, MAX_REC, MIN_REC, MAX_REC]
    # keep a single src so the delta encoder chains them (MIN/MAX share src only if equal;
    # rebuild with a common src so delta state is one chain)
    common = [_rec(7, r.seq, r.ts, r.prev_hash, r.lat, r.lon, r.alt, r.vel_x, r.vel_y, r.vel_z,
                   r.battery, r.mode) for r in stream]
    enc, dec = new_encoder(name), new_encoder(name)
    out = [dec.decode(enc.encode(r)) for r in common]
    assert out == common
