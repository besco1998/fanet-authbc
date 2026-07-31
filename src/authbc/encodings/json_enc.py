"""JSON encoder — stdlib, the Pillar-1 baseline (docs/01 §1 "Encodings e").

Deterministic via ``sort_keys=True`` + compact separators. ``prev_hash`` (bytes) is carried
as a lowercase hex string since JSON has no byte type — this is what makes JSON the largest
encoding in the T1 table.
"""

from __future__ import annotations

import json

from authbc.bench.telemgen import TelemetryRecord
from authbc.encodings.base import Encoder, obj_to_record, record_to_obj


class JsonEncoder(Encoder):
    name = "json"
    deterministic = True

    def encode(self, rec: TelemetryRecord) -> bytes:
        src = record_to_obj(self._validated(rec))
        ph = src["ph"]
        assert isinstance(ph, bytes), "prev_hash must be bytes before hex-encoding"
        # JSON cannot carry raw bytes, so the wire dict is a *different* type from the
        # record dict: ph becomes a hex string. Build it rather than mutating in place.
        obj: dict[str, int | str] = {k: v for k, v in src.items() if k != "ph"}  # type: ignore[misc]
        obj["ph"] = ph.hex()
        return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")

    def decode(self, data: bytes) -> TelemetryRecord:
        obj = json.loads(data.decode("utf-8"))
        obj["ph"] = bytes.fromhex(obj["ph"])
        return obj_to_record(obj)
