"""Encoder ABC + shared record⇄object mapping and varint helpers (docs/03 §3 encodings/).

Every encoder converts a :class:`~authbc.bench.telemgen.TelemetryRecord` to/from ``bytes``.
Stateless encoders (JSON/CBOR/MessagePack) implement pure ``encode``/``decode``; the delta
encoder keeps per-src state (docs/06 §5) but honours the same interface. ``deterministic``
advertises whether two encodes of the same record are byte-identical — a determinism test
(two subprocesses, SHA-256 of the concatenation) enforces it for the deterministic ones.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from authbc.bench.telemgen import FIELD_ORDER, INT_FIELD_ORDER, TelemetryRecord, validate

# Compact canonical wire keys (short, to keep CBOR near the docs/02 T1 anchor). Order is
# FIELD_ORDER so serialized key order is deterministic regardless of dict insertion.
KEYS: dict[str, str] = {
    "src": "src",
    "seq": "seq",
    "ts": "ts",
    "prev_hash": "ph",
    "lat": "lat",
    "lon": "lon",
    "alt": "alt",
    "vel_x": "vx",
    "vel_y": "vy",
    "vel_z": "vz",
    "battery": "bat",
    "mode": "md",
}
_INV_KEYS: dict[str, str] = {v: k for k, v in KEYS.items()}


def record_to_obj(rec: TelemetryRecord) -> dict[str, int | bytes]:
    """Record → plain dict keyed by the compact wire keys, in canonical field order."""
    d = rec.as_dict()
    return {KEYS[f]: d[f] for f in FIELD_ORDER}


def obj_to_record(obj: dict) -> TelemetryRecord:
    """Inverse of :func:`record_to_obj`. ``prev_hash`` is coerced to ``bytes``."""
    fields = {_INV_KEYS[k]: v for k, v in obj.items()}
    ph = fields["prev_hash"]
    fields["prev_hash"] = bytes(ph) if not isinstance(ph, bytes) else ph
    return TelemetryRecord(**fields)  # type: ignore[arg-type]


def record_to_array(rec: TelemetryRecord) -> list:
    """Record → fixed-order list of values (NO field names on the wire).

    For a known, fixed telemetry schema, transmitting field names every record is pure
    overhead (~42 B/record in canonical CBOR — measured); the binary encoders (CBOR,
    MessagePack) therefore serialize this schema-implied array. Field order is FIELD_ORDER,
    so decoding is unambiguous (docs/01 §1 fixes the schema).
    """
    d = rec.as_dict()
    return [d[f] for f in FIELD_ORDER]


def array_to_record(arr: list) -> TelemetryRecord:
    """Inverse of :func:`record_to_array`. ``prev_hash`` is coerced to ``bytes``."""
    fields = dict(zip(FIELD_ORDER, arr, strict=True))
    ph = fields["prev_hash"]
    fields["prev_hash"] = bytes(ph) if not isinstance(ph, bytes) else ph
    return TelemetryRecord(**fields)  # type: ignore[arg-type]


# --------------------------------------------------------------------------- varint helpers
def zigzag(n: int) -> int:
    """Map a signed int to an unsigned one (small |n| ⇒ small result); 64-bit shift is safe
    for our field deltas which fit well within int64."""
    return (n << 1) ^ (n >> 63)


def unzigzag(u: int) -> int:
    return (u >> 1) ^ -(u & 1)


def uvarint_encode(u: int) -> bytes:
    """LEB128 unsigned varint."""
    if u < 0:
        raise ValueError("uvarint_encode expects a non-negative int")
    out = bytearray()
    while True:
        b = u & 0x7F
        u >>= 7
        if u:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)


def uvarint_decode(data: bytes, pos: int = 0) -> tuple[int, int]:
    """Decode one LEB128 varint at ``data[pos:]`` → ``(value, next_pos)``."""
    result = 0
    shift = 0
    while True:
        b = data[pos]
        pos += 1
        result |= (b & 0x7F) << shift
        if not (b & 0x80):
            return result, pos
        shift += 7


def svarint_encode(n: int) -> bytes:
    return uvarint_encode(zigzag(n))


def svarint_decode(data: bytes, pos: int = 0) -> tuple[int, int]:
    u, pos = uvarint_decode(data, pos)
    return unzigzag(u), pos


class Encoder(ABC):
    """Record encoder (docs/03 §3). Subclasses set ``name`` and ``deterministic``."""

    name: str
    deterministic: bool

    @abstractmethod
    def encode(self, rec: TelemetryRecord) -> bytes:
        """Serialize one record to bytes (stateful encoders advance internal state)."""

    @abstractmethod
    def decode(self, data: bytes) -> TelemetryRecord:
        """Inverse of :meth:`encode` (stateful decoders advance internal state)."""

    def encode_stream(self, recs: list[TelemetryRecord]) -> list[bytes]:
        return [self.encode(r) for r in recs]

    def _validated(self, rec: TelemetryRecord) -> TelemetryRecord:
        validate(rec)
        return rec


__all__ = [
    "FIELD_ORDER",
    "INT_FIELD_ORDER",
    "KEYS",
    "Encoder",
    "array_to_record",
    "obj_to_record",
    "record_to_array",
    "record_to_obj",
    "svarint_decode",
    "svarint_encode",
    "unzigzag",
    "uvarint_decode",
    "uvarint_encode",
    "zigzag",
]
