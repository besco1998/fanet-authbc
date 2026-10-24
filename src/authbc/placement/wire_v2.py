"""Wire format v2 — the lean frame, built as ONE decodable, verifiable object (docs/01 §4b).

**Why this module exists (audit F45, 2026-10-06).** Until now the design the paper headlines was a
*sum of sizes measured separately*: a delta record size from `encodings/delta_enc.py`, a header
measured on canonical-CBOR frames by `placement/wire.py`, and a signature length. No frame carrying
delta records was ever encoded, sent or decoded, so three composition errors stayed invisible —
delta records that could not be decoded after a lost frame (F46), an exclusion test that never
charged the chain link (F47), and a record size taken at the wrong sampling interval (F48). This
module is the object those numbers described. Every size the lean design reports is now the length
of a byte string this module emitted and decoded again.

**v1 is not touched.** `placement/wire.py` is frozen (⚠️ D6); its vectors and every artifact
derived from them are bit-identical. v2 is additive.

Frame := canonical CBOR map with INTEGER keys (the COSE / SenML convention)::

    0 v         2
    1 t         FrameType: 0 inline (one signature per record) · 1 self-batch, decodes alone ·
                2 self-batch, first record coded against the previous frame's last record
    2 src       u16
    3 base_seq  u32, sequence number of the first record
    4 n         records in the frame, 1..255
    5 link      bytes(32): prev_hash of the first record — the ONE chain link a frame carries
    6 recs      bytes: the record stream
    7 auth      self-batch: bytes(64) · inline: array of n bytes(64)

Record stream := rec_0 ‖ … ‖ rec_{n−1}; each record is nine LEB128 varints in `STREAM_FIELDS` order.
A KEY record carries absolute values (`ts`, `battery`, `mode` unsigned, the rest zig-zag signed); a
DELTA record carries zig-zag differences from the record before it. rec_0 is KEY in types 0 and 1
and DELTA in type 2; every later record is DELTA. `src` and `seq` are not repeated per record:
every record of the frame has the frame's `src`, and its `seq` is `base_seq + i`.

**What is signed is unchanged from v1** (`wire.covered_bytes`): the canonical CBOR of the ledger
records, each with its own `prev_hash`. A receiver therefore has to REBUILD the records before it
can verify — which is the point. A frame it cannot decode is a frame it cannot verify, and the
verifiability model (`models/frame.py`) now says so.

**The chain link is never omitted.** `prev_hash_0 = link` and
`prev_hash_i = SHA-256(canonical(rec_{i−1}))`.
Without the link a frame that follows a lost one could not be rebuilt, hence not verified, so "one
link per frame" is the floor (docs/02 §9b), not an optimisation that can be taken further.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import IntEnum
from typing import Any

import cbor2

from authbc.crypto.ed25519 import Ed25519Scheme
from authbc.encodings.base import svarint_decode, svarint_encode, uvarint_decode, uvarint_encode
from authbc.ledger.record import PREV_HASH_LEN, Record, canonical_bytes
from authbc.placement.wire import Placement, WireDecodeError, covered_bytes

WIRE_VERSION_2 = 2
SIG_LEN = 64
MAX_RECORDS = 255

F_V, F_T, F_SRC, F_BASE_SEQ, F_N, F_LINK, F_RECS, F_AUTH = range(8)

# The telemetry payload is a FIXED schema, so its field names never travel (the same argument that
# made the v1 CBOR encoder a schema-implied array). Names match the ledger payload used since P2.
PAYLOAD_FIELDS: tuple[str, ...] = (
    "lat", "lon", "alt", "vel_x", "vel_y", "vel_z", "battery", "mode")
STREAM_FIELDS: tuple[str, ...] = ("ts", *PAYLOAD_FIELDS)
# Fields that cannot be negative are sent unsigned in a KEY record: zig-zag would double them and
# push `battery` (0..100) from one byte to two for nothing.
_UNSIGNED: frozenset[str] = frozenset({"ts", "battery", "mode"})

_ED = Ed25519Scheme()


class FrameType(IntEnum):
    """What the frame's `t` field says about its signatures and its first record."""

    A_KEY = 0     # inline: one signature per record; decodes alone
    B_KEY = 1     # self-batch: one signature; decodes alone
    B_DELTA = 2   # self-batch: one signature; needs the previous frame's last record


class DesyncError(Exception):
    """A type-2 frame arrived without the record it is coded against.

    Deliberately NOT a `WireDecodeError`: the frame is well formed. It is undecodable *by this
    receiver, now*, because an earlier frame was lost — the loss-propagation case the verifiability
    model has to count (docs/02 T3').
    """


@dataclass(frozen=True)
class FrameV2:
    t: FrameType
    src: int
    base_seq: int
    link: bytes
    recs: tuple[Record, ...]
    auth: Any   # bytes for self-batch; tuple[bytes, ...] for inline

    @property
    def n(self) -> int:
        return len(self.recs)


# --------------------------------------------------------------------------- record stream
def _values(rec: Record) -> tuple[int, ...]:
    """The nine stream values of a record, in `STREAM_FIELDS` order."""
    if set(rec.pl) != set(PAYLOAD_FIELDS):
        raise ValueError(
            f"wire v2 carries the fixed telemetry schema {PAYLOAD_FIELDS}; got {sorted(rec.pl)}")
    return (rec.ts, *(rec.pl[f] for f in PAYLOAD_FIELDS))


def _key_bytes(vals: Sequence[int]) -> bytes:
    out = bytearray()
    for name, v in zip(STREAM_FIELDS, vals, strict=True):
        out += uvarint_encode(v) if name in _UNSIGNED else svarint_encode(v)
    return bytes(out)


def _delta_bytes(vals: Sequence[int], prev: Sequence[int]) -> bytes:
    out = bytearray()
    for cur, old in zip(vals, prev, strict=True):
        out += svarint_encode(cur - old)
    return bytes(out)


def _read_key(data: bytes, pos: int) -> tuple[tuple[int, ...], int]:
    vals: list[int] = []
    for name in STREAM_FIELDS:
        v, pos = (uvarint_decode if name in _UNSIGNED else svarint_decode)(data, pos)
        vals.append(v)
    return tuple(vals), pos


def _read_delta(data: bytes, pos: int, prev: Sequence[int]) -> tuple[tuple[int, ...], int]:
    vals: list[int] = []
    for old in prev:
        d, pos = svarint_decode(data, pos)
        vals.append(old + d)
    return tuple(vals), pos


def record_stream(recs: Sequence[Record], prev: Record | None) -> bytes:
    """The `recs` field: KEY-then-DELTA when `prev` is None, all-DELTA when it is given."""
    out = bytearray()
    last = _values(prev) if prev is not None else None
    for rec in recs:
        vals = _values(rec)
        out += _key_bytes(vals) if last is None else _delta_bytes(vals, last)
        last = vals
    return bytes(out)


# --------------------------------------------------------------------------- encode
def _check_encodable(frame: FrameV2, prev: Record | None) -> None:
    """Refuse to emit a frame the receiver would rebuild into different records.

    The receiver derives `src`, `seq` and every `prev_hash` after the first, so any record that
    disagrees with those derivations would decode cleanly and then fail its signature — a silent
    self-inflicted loss. Better to fail here, at the sender.
    """
    if not 1 <= frame.n <= MAX_RECORDS:
        raise ValueError(f"a frame carries 1..{MAX_RECORDS} records, got {frame.n}")
    if len(frame.link) != PREV_HASH_LEN:
        raise ValueError(f"link must be {PREV_HASH_LEN} bytes")
    expected_ph = frame.link
    for i, rec in enumerate(frame.recs):
        if rec.src != frame.src or rec.seq != frame.base_seq + i:
            raise ValueError("records must share the frame's src and have consecutive seq")
        if rec.prev_hash != expected_ph:
            raise ValueError(f"record {i} does not chain: its prev_hash is not derivable")
        expected_ph = rec.record_hash()
    dependent = frame.t is FrameType.B_DELTA
    if dependent != (prev is not None):
        raise ValueError("a B_DELTA frame needs `prev`; every other type must not be given one")
    if prev is not None and (prev.src != frame.src or prev.seq != frame.base_seq - 1
                             or prev.record_hash() != frame.link):
        raise ValueError("`prev` must be the record immediately before the frame's first")


def encode_frame_v2(frame: FrameV2, *, prev: Record | None = None) -> bytes:
    """Serialise a frame. `prev` is the record before `recs[0]`, required for B_DELTA only."""
    _check_encodable(frame, prev)
    auth = list(frame.auth) if frame.t is FrameType.A_KEY else frame.auth
    return canonical_bytes({
        F_V: WIRE_VERSION_2, F_T: int(frame.t), F_SRC: frame.src, F_BASE_SEQ: frame.base_seq,
        F_N: frame.n, F_LINK: frame.link, F_RECS: record_stream(frame.recs, prev),
        F_AUTH: auth,
    })


# --------------------------------------------------------------------------- decode
def _rebuild(src: int, base_seq: int, n: int, link: bytes, stream: bytes,
             prev_vals: tuple[int, ...] | None) -> tuple[Record, ...]:
    """Records from the stream, with `seq` and every `prev_hash` re-derived (never read)."""
    recs: list[Record] = []
    pos, last, ph = 0, prev_vals, link
    for i in range(n):
        vals, pos = _read_key(stream, pos) if last is None else _read_delta(stream, pos, last)
        rec = Record(src=src, seq=base_seq + i, ts=vals[0], prev_hash=ph,
                     pl=dict(zip(PAYLOAD_FIELDS, vals[1:], strict=True)))
        recs.append(rec)
        last, ph = vals, rec.record_hash()
    if pos != len(stream):
        raise ValueError("trailing bytes after the last record")
    return tuple(recs)


def _auth_ok(t: FrameType, auth: Any, n: int) -> bool:
    b = (bytes, bytearray)
    if t is FrameType.A_KEY:
        return isinstance(auth, list) and len(auth) == n and all(isinstance(s, b) for s in auth)
    return isinstance(auth, b)


def frame_src(data: bytes) -> int:
    """The `src` of a frame, read without decoding its records.

    A receiver needs it first: the sender decides which key verifies the frame and which decoder
    state a type-2 frame is coded against.
    """
    try:
        obj = cbor2.loads(data)
        src = obj[F_SRC]
        if isinstance(src, bool) or not isinstance(src, int):
            raise ValueError("src must be an integer")
        return src
    except (cbor2.CBORDecodeError, KeyError, IndexError, TypeError, ValueError) as e:
        raise WireDecodeError(f"malformed frame: {e}") from e


def decode_frame_v2(data: bytes, *, prev: Record | None = None) -> FrameV2:
    """Decode and structurally validate a frame.

    `prev` is the receiver's copy of the record before the frame's first; it is consulted only for
    a B_DELTA frame. Malformed input raises `WireDecodeError`; a well-formed B_DELTA frame whose
    predecessor the receiver does not hold raises `DesyncError`.
    """
    try:
        obj = cbor2.loads(data)
        if not isinstance(obj, dict) or set(obj) != set(range(8)):
            raise ValueError("frame must be a CBOR map with keys 0..7")
        if obj[F_V] != WIRE_VERSION_2:
            raise ValueError(f"unsupported wire version {obj[F_V]!r}")
        t = FrameType(obj[F_T])
        src, base_seq, n = obj[F_SRC], obj[F_BASE_SEQ], obj[F_N]
        link, stream, auth = obj[F_LINK], obj[F_RECS], obj[F_AUTH]
        for name, val in (("src", src), ("base_seq", base_seq), ("n", n)):
            if isinstance(val, bool) or not isinstance(val, int):
                raise ValueError(f"{name} must be an integer")
        if not 1 <= n <= MAX_RECORDS:
            raise ValueError(f"n out of range: {n}")
        if not isinstance(link, bytes) or len(link) != PREV_HASH_LEN:
            raise ValueError("link must be 32 bytes")
        if not isinstance(stream, bytes) or not _auth_ok(t, auth, n):
            raise ValueError("recs must be bytes and auth must match the frame type")
        prev_vals: tuple[int, ...] | None = None
        if t is FrameType.B_DELTA:
            if prev is None or prev.src != src or prev.seq != base_seq - 1:
                raise DesyncError(
                    f"frame src={src} base_seq={base_seq} is coded against a record not held")
            prev_vals = _values(prev)
        recs = _rebuild(src, base_seq, n, link, stream, prev_vals)
        return FrameV2(t=t, src=src, base_seq=base_seq, link=link, recs=recs,
                       auth=tuple(bytes(s) for s in auth) if t is FrameType.A_KEY else bytes(auth))
    except (DesyncError, WireDecodeError):
        raise
    except (cbor2.CBORDecodeError, KeyError, IndexError, TypeError, ValueError, OverflowError,
            AttributeError) as e:
        raise WireDecodeError(f"malformed frame: {e}") from e


# --------------------------------------------------------------------------- build / verify
def build_B_v2(recs: Sequence[Record], sk: Any, *, prev: Record | None = None) -> FrameV2:
    """Self-batch: one Ed25519 signature over the canonical records (same bytes v1 signs).

    Give `prev` to code the first record against it (a dependent, type-2 frame); omit it for a
    frame that decodes alone.
    """
    t = FrameType.B_KEY if prev is None else FrameType.B_DELTA
    return FrameV2(t=t, src=recs[0].src, base_seq=recs[0].seq, link=recs[0].prev_hash,
                   recs=tuple(recs), auth=_ED.sign(sk, covered_bytes(list(recs), Placement.B)))


def build_A_v2(recs: Sequence[Record], sk: Any) -> FrameV2:
    """Inline: every record signed on its own, the frame merely shares the header."""
    return FrameV2(t=FrameType.A_KEY, src=recs[0].src, base_seq=recs[0].seq,
                   link=recs[0].prev_hash, recs=tuple(recs),
                   auth=tuple(_ED.sign(sk, r.canonical()) for r in recs))


def verify_v2(frame: FrameV2, pk: Any) -> bool:
    """True iff every signature in the frame verifies over the REBUILT records."""
    if frame.t is FrameType.A_KEY:
        return len(frame.auth) == frame.n and all(
            _ED.verify(pk, r.canonical(), sig)
            for r, sig in zip(frame.recs, frame.auth, strict=True))
    return _ED.verify(pk, covered_bytes(list(frame.recs), Placement.B), frame.auth)
