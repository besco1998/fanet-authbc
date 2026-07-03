"""Encoder registry + a stream-digest helper used by the determinism test (docs/03 §3).

``stream_digest`` is importable so a *subprocess* can recompute the SHA-256 of an encoded
1000-record stream; two subprocesses must agree (determinism release gate, docs/06 §5).
"""

from __future__ import annotations

import hashlib

from authbc.bench import telemgen
from authbc.encodings.base import Encoder
from authbc.encodings.cbor_enc import CborEncoder
from authbc.encodings.delta_enc import DeltaEncoder
from authbc.encodings.json_enc import JsonEncoder
from authbc.encodings.msgpack_enc import MsgpackEncoder

ENCODER_CLASSES: dict[str, type[Encoder]] = {
    "json": JsonEncoder,
    "cbor": CborEncoder,
    "msgpack": MsgpackEncoder,
    "delta": DeltaEncoder,
}


def new_encoder(name: str) -> Encoder:
    return ENCODER_CLASSES[name]()


def new_encoders() -> list[Encoder]:
    return [cls() for cls in ENCODER_CLASSES.values()]


def stream_digest(name: str, seed: int, n: int) -> str:
    """SHA-256 (hex) of the concatenated encoding of an ``n``-record seeded stream."""
    enc = new_encoder(name)
    h = hashlib.sha256()
    for rec in telemgen.stream(seed, n):
        h.update(enc.encode(rec))
    return h.hexdigest()
