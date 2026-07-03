"""Canonical CBOR encoder (RFC 8949 §4.2) via cbor2 (docs/01 §1, docs/06 §5).

``cbor2.dumps(obj, canonical=True)`` gives deterministic core encoding: sorted keys, shortest
int/length forms. ``prev_hash`` rides as a native CBOR byte string. cbor2 is pinned to 5.8.0
(docs/03 §2) because 5.8.1 regressed canonical output.
"""

from __future__ import annotations

import cbor2

from authbc.bench.telemgen import TelemetryRecord
from authbc.encodings.base import Encoder, obj_to_record, record_to_obj


class CborEncoder(Encoder):
    name = "cbor"
    deterministic = True

    def encode(self, rec: TelemetryRecord) -> bytes:
        return cbor2.dumps(record_to_obj(self._validated(rec)), canonical=True)

    def decode(self, data: bytes) -> TelemetryRecord:
        return obj_to_record(cbor2.loads(data))
