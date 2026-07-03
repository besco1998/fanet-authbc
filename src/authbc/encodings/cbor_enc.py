"""Canonical CBOR encoder (RFC 8949 §4.2) via cbor2 (docs/01 §1, docs/06 §5).

Encodes the record as a schema-implied **array** (no field names on the wire) — for a fixed
telemetry schema the field names are ~42 B/record of pure overhead (measured), so a compact
CBOR ledger drops them. ``cbor2.dumps(arr, canonical=True)`` gives deterministic core encoding
(shortest int/length forms); ``prev_hash`` rides as a native CBOR byte string. cbor2 is pinned
to 5.8.0 (docs/03 §2) because 5.8.1 regressed canonical output.
"""

from __future__ import annotations

import cbor2

from authbc.bench.telemgen import TelemetryRecord
from authbc.encodings.base import Encoder, array_to_record, record_to_array


class CborEncoder(Encoder):
    name = "cbor"
    deterministic = True

    def encode(self, rec: TelemetryRecord) -> bytes:
        return cbor2.dumps(record_to_array(self._validated(rec)), canonical=True)

    def decode(self, data: bytes) -> TelemetryRecord:
        return array_to_record(cbor2.loads(data))
