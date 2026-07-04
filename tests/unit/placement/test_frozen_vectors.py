"""FROZEN wire vectors (⚠️ D6) — byte-identity forever (docs/01 §4, P2 step 4).

The build logic here is the SINGLE source for both emitting the vectors (run this file as a
script) and checking them (pytest), so the two can never drift. Ed25519 and BLS AugScheme
signing are deterministic, and keygen is seeded, so every frame is byte-reproducible.

After the freeze commit, any change to these bytes is a ⚠️ D6 event needing Mohamed.
Regenerate ONLY with explicit approval:  python tests/unit/placement/test_frozen_vectors.py
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from authbc.bench import telemgen
from authbc.crypto.bls import BlsScheme
from authbc.crypto.ed25519 import Ed25519Scheme
from authbc.ledger.chain import Chain
from authbc.placement import wire

VECTORS = Path(__file__).resolve().parents[2] / "vectors" / "wire"
_TELEMETRY = ("lat", "lon", "alt", "vel_x", "vel_y", "vel_z", "battery", "mode")
_ED = Ed25519Scheme()
_BLS = BlsScheme()
_ED_SEED = bytes(range(32))


def _records(src: int, seed: int, n: int):
    chain = Chain(src=src)
    for i, r in enumerate(telemgen.samples(seed=seed, n=n)):
        chain.append({k: getattr(r, k) for k in _TELEMETRY}, ts=1000 + i)
    return chain.records()


def build_vectors() -> dict[str, wire.Frame]:
    """Deterministically build ≥3 frames per placement (fixed seeds/keys/payloads)."""
    ed_sk, _ = _ED.keygen(seed=_ED_SEED)
    vecs: dict[str, wire.Frame] = {}
    for i in range(3):
        recs = _records(src=100 + i, seed=i, n=2 + i)  # 2,3,4 records
        vecs[f"A_{i}"] = wire.build_A(recs, ed_sk)
        vecs[f"B_{i}"] = wire.build_B(recs, ed_sk)
        vecs[f"D_{i}"] = wire.build_D(recs, ed_sk, block_id=i, frag_idx=0, frag_total=1)
    for i in range(3):
        m = 2 + i
        recs = [_records(src=200 + i * 10 + j, seed=50 + i * 10 + j, n=1)[0] for j in range(m)]
        sks = [_BLS.keygen(seed=bytes([60 + i * 10 + j]) * 32)[0] for j in range(m)]
        vecs[f"C_{i}"] = wire.build_C(recs, sks)
    return vecs


def _covered_digest(frame: wire.Frame) -> str:
    cov = wire.covered_bytes(frame.recs, frame.t)
    blob = b"".join(cov) if isinstance(cov, list) else cov
    return hashlib.sha256(blob).hexdigest()


def _emit() -> None:
    VECTORS.mkdir(parents=True, exist_ok=True)
    expected: dict[str, dict] = {}
    for name, frame in build_vectors().items():
        data = wire.encode_frame(frame)
        (VECTORS / f"{name}.bin").write_bytes(data)
        expected[name] = {
            "placement": frame.t.name,
            "n": frame.n,
            "frame_sha256": hashlib.sha256(data).hexdigest(),
            "covered_sha256": _covered_digest(frame),
            "nbytes": len(data),
        }
    meta = {"ed_seed_hex": _ED_SEED.hex(),
            "note": "FROZEN at P2 (D6); do not edit without Mohamed"}
    (VECTORS / "expected.json").write_text(
        json.dumps({"meta": meta, "vectors": expected}, indent=2))
    print(f"emitted {len(expected)} vectors to {VECTORS}")


# --------------------------------------------------------------------------- tests
def _load_expected() -> dict:
    return json.loads((VECTORS / "expected.json").read_text())["vectors"]


def test_build_is_deterministic() -> None:
    a = {k: wire.encode_frame(v) for k, v in build_vectors().items()}
    b = {k: wire.encode_frame(v) for k, v in build_vectors().items()}
    assert a == b  # Ed25519 + BLS signing are deterministic ⇒ byte-identical rebuilds


def test_frozen_bytes_match() -> None:
    """The committed .bin bytes must equal a fresh rebuild — the D6 freeze anchor."""
    expected = _load_expected()
    rebuilt = build_vectors()
    assert set(rebuilt) == set(expected), "vector set changed"
    for name, frame in rebuilt.items():
        data = wire.encode_frame(frame)
        frozen = (VECTORS / f"{name}.bin").read_bytes()
        assert data == frozen, f"{name}: bytes drifted from frozen vector (D6)"
        assert hashlib.sha256(data).hexdigest() == expected[name]["frame_sha256"]
        assert _covered_digest(frame) == expected[name]["covered_sha256"]


def test_frozen_vectors_verify() -> None:
    """Every frozen frame must still verify under its scheme (decode from bytes)."""
    ed_sk, ed_pk = _ED.keygen(seed=_ED_SEED)
    for name in _load_expected():
        frame = wire.decode_frame((VECTORS / f"{name}.bin").read_bytes())
        if frame.t is wire.Placement.A:
            assert wire.verify_A(frame, [ed_pk] * frame.n) is True
        elif frame.t is wire.Placement.B:
            assert wire.verify_B(frame, ed_pk) is True
        elif frame.t is wire.Placement.C:
            assert wire.verify_C(frame) is True
        else:
            assert wire.verify_D(frame, ed_pk) is True


if __name__ == "__main__":
    _emit()
