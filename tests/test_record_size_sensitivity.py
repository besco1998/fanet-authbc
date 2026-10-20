"""Revision A9's size code against the lean format itself (predictions/A9.md).

`analysis/record_size_sensitivity.py` codes records of 9, 15 and 25 fields the way `wire_v2`
codes its own nine. On nine fields it must BE `wire_v2`: the same record-stream bytes, and frame
lengths equal to the encoded frames'. Then a difference at 15 or 25 fields is a difference in the
record, not in the arithmetic.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

from authbc.bench import leanframes
from authbc.crypto.ed25519 import Ed25519Scheme
from authbc.ledger.record import Record
from authbc.placement import wire_v2

REPO = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "record_size_sensitivity", REPO / "analysis" / "record_size_sensitivity.py")
assert _spec and _spec.loader
rs = importlib.util.module_from_spec(_spec)
sys.modules["record_size_sensitivity"] = rs
_spec.loader.exec_module(rs)

_ED = Ed25519Scheme()
_SK, _ = _ED.keygen(seed=bytes(range(32)))


def _as_dict(r: Record) -> dict[str, int]:
    return {"ts": r.ts, **r.pl}


@pytest.fixture(scope="module")
def recs() -> list[Record]:
    """Generator telemetry on the exact 20 ms grid the flight logs are sampled on, re-chained."""
    out: list[Record] = []
    ph = bytes(32)
    for i, r in enumerate(leanframes.chained_records(seed=7, n=40, step_ms=rs.SPACING_MS)):
        rec = Record(src=r.src, seq=r.seq, ts=leanframes.CONVENTION_TS0_MS + rs.SPACING_MS * i,
                     prev_hash=ph, pl=r.pl)
        out.append(rec)
        ph = rec.record_hash()
    return out


def test_nine_fields_are_the_lean_format_s_nine(recs: list[Record]) -> None:
    assert rs.FIELDS_9 == wire_v2.STREAM_FIELDS
    assert rs.UNSIGNED & set(rs.FIELDS_9) == wire_v2._UNSIGNED


def test_record_stream_bytes_equal_wire_v2(recs: list[Record]) -> None:
    d = [_as_dict(r) for r in recs]
    assert rs.key_bytes(d[0], rs.FIELDS_9) == len(wire_v2.record_stream(recs[:1], None))
    for i in range(1, len(recs)):
        assert rs.delta_bytes(d[i], d[i - 1], rs.FIELDS_9) == len(
            wire_v2.record_stream(recs[i:i + 1], recs[i - 1]))


@pytest.mark.parametrize("b", [1, 2, 3, 4])
def test_frame_lengths_equal_encoded_frames(recs: list[Record], b: int) -> None:
    d = [_as_dict(r) for r in recs]
    want = [len(wire_v2.encode_frame_v2(wire_v2.build_B_v2(recs[i:i + b], _SK)))
            for i in range(0, len(recs) - b + 1, b)]
    assert rs.frames(d, rs.FIELDS_9, b) == want


def test_a_group_across_a_gap_is_not_a_frame() -> None:
    base = {f: 1 for f in rs.FIELDS_25}
    d = [{**base, "ts": t} for t in (0, 20, 40, 100, 120, 140, 160)]
    # pairs: (0,20) ok, (40,100) straddles the gap, (120,140) ok
    assert len(rs.frames(d, rs.FIELDS_9, 2)) == 2
    assert len(rs.frames(d, rs.FIELDS_9, 1)) == 7


def test_more_fields_never_shrink_a_record(recs: list[Record]) -> None:
    extra = {"roll": -1200, "pitch": 300, "yaw": 17_000, "p": -40, "q": 12, "r": 3, "fix": 3,
             "sats": 14, "eph": 80, "epv": 120, "airspeed": 0, "wind_n": -150, "wind_e": 90,
             "mission": 2, "status": 32, "thrust": 450}
    d = [{**_as_dict(r), **extra} for r in recs]
    k = [rs.key_bytes(d[0], rs.SETS[n]) for n in (9, 15, 25)]
    assert k[0] < k[1] < k[2]
