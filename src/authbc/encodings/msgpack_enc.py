"""MessagePack encoder (docs/01 §1 "Encodings e").

Like the CBOR encoder, serializes the record as a schema-implied **array** (no field names) —
the compact binary form for a fixed schema. A fixed-order array is inherently deterministic
(no map-key ordering to canonicalize). ``prev_hash`` rides as a native bin (``use_bin_type=
True``); ``raw=False`` on decode keeps bin as bytes.
"""

from __future__ import annotations

import msgpack

from authbc.bench.telemgen import TelemetryRecord
from authbc.encodings.base import Encoder, array_to_record, record_to_array


class MsgpackEncoder(Encoder):
    name = "msgpack"
    deterministic = True

    def encode(self, rec: TelemetryRecord) -> bytes:
        return msgpack.packb(record_to_array(self._validated(rec)), use_bin_type=True)

    def decode(self, data: bytes) -> TelemetryRecord:
        return array_to_record(msgpack.unpackb(data, raw=False))
