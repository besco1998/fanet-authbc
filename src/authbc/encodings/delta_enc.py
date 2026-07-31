"""Delta-CBOR-style encoder (docs/03 §3 encodings/, docs/06 §5).

Stateful, per-src: a keyframe every ``K=16`` records carries absolute field values; the
15 records in between carry **zigzag-varint deltas vs the previous record**. ``src`` is
carried absolutely in every frame (it names the stream, so the decoder can pick per-src
state); ``prev_hash`` (incompressible) is carried raw in every frame so the encoding
round-trips standalone (the real chain that would let the decoder recompute it is P2).

Loss model: a lost frame desyncs a src until its next keyframe — the decoder raises
:class:`DeltaDesyncError` for a delta frame it has no state for and bumps ``desync_count``
(docs/03 §3: "re-sync at next keyframe").
"""

from __future__ import annotations

from authbc.bench.telemgen import INT_FIELD_ORDER, PREV_HASH_LEN, TelemetryRecord
from authbc.encodings.base import (
    Encoder,
    svarint_decode,
    svarint_encode,
    uvarint_decode,
    uvarint_encode,
)

KEYFRAME = 0x00
DELTA = 0x01
K = 16  # keyframe interval (docs/01 §1, docs/03 §3)

# src is carried absolutely; everything else (seq, ts, lat, lon, alt, vel_*, battery, mode)
# is delta-coded against the previous record for the same src.
DELTA_FIELDS: tuple[str, ...] = tuple(f for f in INT_FIELD_ORDER if f != "src")


class DeltaDesyncError(Exception):
    """A delta frame arrived before any keyframe for its src (lost-frame desync)."""


class DeltaEncoder(Encoder):
    name = "delta"
    deterministic = True

    def __init__(self, keyframe_interval: int = K) -> None:
        if keyframe_interval < 1:
            raise ValueError("keyframe_interval must be >= 1")
        self.keyframe_interval = keyframe_interval
        self._enc_count: dict[int, int] = {}
        self._enc_prev: dict[int, list[int]] = {}
        self._dec_prev: dict[int, list[int]] = {}
        self.desync_count = 0

    @staticmethod
    def _delta_vals(rec: TelemetryRecord) -> list[int]:
        return [getattr(rec, f) for f in DELTA_FIELDS]

    def encode(self, rec: TelemetryRecord) -> bytes:
        self._validated(rec)
        src = rec.src
        count = self._enc_count.get(src, 0)
        cur = self._delta_vals(rec)
        out = bytearray()
        if count % self.keyframe_interval == 0:
            out.append(KEYFRAME)
            out += uvarint_encode(src)
            for v in cur:
                out += svarint_encode(v)
        else:
            out.append(DELTA)
            out += uvarint_encode(src)
            prev = self._enc_prev[src]
            for c, p in zip(cur, prev, strict=True):
                out += svarint_encode(c - p)
        out += rec.prev_hash
        self._enc_prev[src] = cur
        self._enc_count[src] = count + 1
        return bytes(out)

    def decode(self, data: bytes) -> TelemetryRecord:
        ftype = data[0]
        src, pos = uvarint_decode(data, 1)
        if ftype == KEYFRAME:
            vals: list[int] = []
            for _ in DELTA_FIELDS:
                v, pos = svarint_decode(data, pos)
                vals.append(v)
            self._dec_prev[src] = vals
        elif ftype == DELTA:
            prev = self._dec_prev.get(src)
            if prev is None:
                self.desync_count += 1
                raise DeltaDesyncError(f"delta frame for src={src} before any keyframe")
            vals = []
            for p in prev:
                d, pos = svarint_decode(data, pos)
                vals.append(p + d)
            self._dec_prev[src] = vals
        else:  # pragma: no cover - defensive
            raise ValueError(f"unknown delta frame type {ftype:#x}")
        prev_hash = data[pos : pos + PREV_HASH_LEN]
        if len(prev_hash) != PREV_HASH_LEN:
            raise ValueError("truncated delta frame: missing prev_hash")
        fields = dict(zip(DELTA_FIELDS, vals, strict=True))
        return TelemetryRecord(src=src, prev_hash=prev_hash, **fields)
