"""The compiled sender's energy run reads the Python lean rows' records (revision A8).

`hw/validate_energy_e2e.py --format rust` meters `authbc-rx sendloop` on a records file it
writes. Held here: that file is the Python lean pipeline's stream (seed 1, 4 000 chained
records) in the format `authbc-rx` reads, so the two energy rows differ in implementation only.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

from authbc.bench import leanframes
from authbc.placement import wire_v2

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "hw"))
_spec = importlib.util.spec_from_file_location("validate_energy_e2e",
                                               REPO / "hw" / "validate_energy_e2e.py")
assert _spec and _spec.loader
ve = importlib.util.module_from_spec(_spec)
sys.modules["validate_energy_e2e"] = ve
_spec.loader.exec_module(ve)


def test_the_records_file_is_the_lean_pipelines_stream(tmp_path: Path) -> None:
    lines = ve.rust_records(tmp_path / "r.jsonl").read_text().splitlines()
    recs = leanframes.chained_records(1, 4000)
    assert len(lines) == len(recs) == 4000
    for line, r in zip(lines[:50] + lines[-50:], recs[:50] + recs[-50:], strict=True):
        row = json.loads(line)
        assert (row["src"], row["seq"], row["ts"]) == (r.src, r.seq, r.ts)
        assert bytes.fromhex(row["ph"]) == r.prev_hash
        assert row["pl"] == [r.pl[f] for f in wire_v2.PAYLOAD_FIELDS]


def test_the_key_is_the_lean_pipelines() -> None:
    import hashlib
    assert ve.LEAN_KEY_SEED == hashlib.sha256(b"g9:lean").digest()
