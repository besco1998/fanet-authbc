#!/usr/bin/env python3
"""Revision A8's byte-identity gate: the compiled codec against the Python one (predictions/A8.md).

10 000 frames of four records (the generator's records, chained, at the sizing convention's
sender and sequence numbers) are encoded and signed by `wire_v2` in Python and by
`hw/rust_receiver` with the same key. Ed25519 signing is deterministic, so the two must be equal
byte for byte; and each side must verify every frame of the other.

    python analysis/rust_identity.py      # results/raw/rust_identity.csv; golden vectors in
                                          # tests/vectors/rust_identity/
"""
from __future__ import annotations

import csv
import io
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from authbc.bench import leanframes, provenance  # noqa: E402
from authbc.crypto.ed25519 import Ed25519Scheme  # noqa: E402
from authbc.placement import wire_v2  # noqa: E402
from authbc.placement.session_v2 import LeanSender, verified_records  # noqa: E402

EXE = REPO / "hw" / "rust_receiver" / "target" / "release" / "authbc-rx"
OUT = REPO / "results" / "raw" / "rust_identity.csv"
VECTORS = REPO / "tests" / "vectors" / "rust_identity"
FRAMES, BATCH = 10_000, 4
SEED = bytes(range(32))


def frames_file(frames: list[bytes]) -> bytes:
    return b"".join(len(f).to_bytes(4, "big") + f for f in frames)


def read_frames(data: bytes) -> list[bytes]:
    out, pos = [], 0
    while pos + 4 <= len(data):
        n = int.from_bytes(data[pos:pos + 4], "big")
        out.append(data[pos + 4:pos + 4 + n])
        pos += 4 + n
    return out


def main() -> None:
    sk, pk = Ed25519Scheme().keygen(seed=SEED)
    pk_hex = pk.public_bytes(Encoding.Raw, PublicFormat.Raw).hex()
    recs = []
    for seed in range(1, 11):                     # ten seeded streams of 4 000 records
        recs += leanframes.chained_records(seed, FRAMES * BATCH // 10)
    sender_frames: list[bytes] = []
    for s in range(10):
        chunk = recs[s * 4000:(s + 1) * 4000]
        sender = LeanSender(sk)
        sender_frames += [sender.frame(chunk[i:i + BATCH]) for i in range(0, 4000, BATCH)]
    with tempfile.TemporaryDirectory() as td:
        rec_path, py_path = Path(td) / "records.jsonl", Path(td) / "py.bin"
        rec_path.write_text("".join(json.dumps(
            {"src": r.src, "seq": r.seq, "ts": r.ts, "ph": r.prev_hash.hex(),
             "pl": [r.pl[f] for f in wire_v2.PAYLOAD_FIELDS]}) + "\n" for r in recs))
        py_path.write_bytes(frames_file(sender_frames))
        rust = read_frames(subprocess.run([str(EXE), "encode", str(rec_path), SEED.hex(),
                                           str(BATCH)], capture_output=True, check=True).stdout)
        rust_verifies = subprocess.run([str(EXE), "verify", str(py_path), pk_hex],
                                       capture_output=True, text=True, check=True).stdout
    identical = sum(a == b for a, b in zip(sender_frames, rust, strict=True))
    python_verifies = sum(verified_records(f, pk) is not None for f in rust)
    row = {"frames": len(sender_frames), "rust_frames": len(rust), "identical": identical,
           "rust_verifies_python": int(rust_verifies.split()[0]),
           "python_verifies_rust": python_verifies}
    buf = io.StringIO()
    for k, v in {**provenance.env_block(), "run": "rust_identity",
                 "config_hash": provenance.config_hash({"frames": FRAMES, "batch": BATCH})
                 }.items():
        buf.write(f"# {k}={v}\n")
    w = csv.DictWriter(buf, fieldnames=list(row), lineterminator="\n")
    w.writeheader()
    w.writerow(row)
    OUT.write_text(buf.getvalue())
    VECTORS.mkdir(parents=True, exist_ok=True)       # a few frames kept as golden vectors
    (VECTORS / "frames.bin").write_bytes(frames_file(sender_frames[:16]))
    (VECTORS / "README.md").write_text(
        "Sixteen lean frames (four records each, key seed bytes 0..31) emitted by the Python\n"
        "codec and, byte for byte, by `hw/rust_receiver` (`analysis/rust_identity.py`).\n"
        f"Public key: {pk_hex}\n")
    print(row)


if __name__ == "__main__":
    main()
