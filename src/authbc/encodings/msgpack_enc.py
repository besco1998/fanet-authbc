"""MessagePack encoder (docs/01 §1 "Encodings e").

MessagePack has no canonical mode, so determinism is enforced by emitting keys in sorted
order. ``prev_hash`` rides as a native bin (``use_bin_type=True``); ``raw=False`` on decode
keeps str keys as str and bin as bytes.
"""

from __future__ import annotations

import msgpack

from authbc.bench.telemgen import TelemetryRecord
from authbc.encodings.base import Encoder, obj_to_record, record_to_obj


class MsgpackEncoder(Encoder):
    name = "msgpack"
    deterministic = True

    def encode(self, rec: TelemetryRecord) -> bytes:
        obj = record_to_obj(self._validated(rec))
        ordered = {k: obj[k] for k in sorted(obj)}
        return msgpack.packb(ordered, use_bin_type=True)

    def decode(self, data: bytes) -> TelemetryRecord:
        obj = msgpack.unpackb(data, raw=False)
        return obj_to_record(obj)
