"""The compiled codec's golden vectors (revision A8; analysis/rust_identity.py).

Sixteen frames that the Python codec and `hw/rust_receiver` emitted byte for byte are kept in
`tests/vectors/rust_identity/`. CI has no Rust toolchain, so what is held here is that the
vectors still decode and verify with the Python codec, and that the recorded gate passed in
full: a change to `wire_v2` that broke byte-identity would break these frames.
"""
from __future__ import annotations

import csv
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from authbc.placement.session_v2 import verified_records

REPO = Path(__file__).resolve().parents[1]
VECTORS = REPO / "tests" / "vectors" / "rust_identity"


def _frames() -> list[bytes]:
    data, out, pos = (VECTORS / "frames.bin").read_bytes(), [], 0
    while pos + 4 <= len(data):
        n = int.from_bytes(data[pos:pos + 4], "big")
        out.append(data[pos + 4:pos + 4 + n])
        pos += 4 + n
    return out


def test_the_golden_frames_verify_with_the_python_codec() -> None:
    pk_hex = (VECTORS / "README.md").read_text().split("Public key: ")[1].split()[0]
    pk = Ed25519PublicKey.from_public_bytes(bytes.fromhex(pk_hex))
    frames = _frames()
    assert len(frames) == 16
    assert all(verified_records(f, pk) is not None for f in frames)


def test_the_recorded_gate_passed_in_full() -> None:
    with (REPO / "results" / "raw" / "rust_identity.csv").open(encoding="utf-8") as fh:
        (row,) = list(csv.DictReader(ln for ln in fh if not ln.startswith("#")))
    assert row["frames"] == row["rust_frames"] == row["identical"] == "10000"
    assert row["rust_verifies_python"] == row["python_verifies_rust"] == "10000"
