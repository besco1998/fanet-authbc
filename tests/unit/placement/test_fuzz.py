"""Fuzz gate (P2 step 6): 1000 byte-mutations of valid frames → zero crashes/hangs.

Every mutation must either (a) decode+verify (rare — only if the mutation missed the signed
region) or (b) be cleanly rejected: a ``WireDecodeError`` on decode, or ``verify → False``.
NO unhandled exception may escape decode/verify, and each op is O(bytes) so it cannot hang.
"""

from __future__ import annotations

import random

from authbc.bench import telemgen
from authbc.crypto.bls import BlsScheme
from authbc.crypto.ed25519 import Ed25519Scheme
from authbc.ledger.chain import Chain
from authbc.placement import wire
from authbc.placement.wire import Placement, WireDecodeError

_TELEMETRY = ("lat", "lon", "alt", "vel_x", "vel_y", "vel_z", "battery", "mode")
_ED = Ed25519Scheme()
_BLS = BlsScheme()
_ED_SEED = bytes(range(32))


def _records(src, seed, n):
    chain = Chain(src=src)
    for i, r in enumerate(telemgen.samples(seed=seed, n=n)):
        chain.append({k: getattr(r, k) for k in _TELEMETRY}, ts=i)
    return chain.records()


def _valid_frames() -> list[wire.Frame]:
    ed_sk, _ = _ED.keygen(seed=_ED_SEED)
    recs = _records(1, 1, 3)
    cross = [_records(10 + j, 20 + j, 1)[0] for j in range(3)]
    bls_sks = [_BLS.keygen(seed=bytes([30 + j]) * 32)[0] for j in range(3)]
    return [
        wire.build_A(recs, ed_sk),
        wire.build_B(recs, ed_sk),
        wire.build_C(cross, bls_sks),
        wire.build_D(recs, ed_sk, block_id=1, frag_idx=0, frag_total=1),
    ]


def _verify(frame: wire.Frame, ed_pk) -> bool:
    if frame.t is Placement.A:
        return wire.verify_A(frame, [ed_pk] * frame.n)
    if frame.t is Placement.B:
        return wire.verify_B(frame, ed_pk)
    if frame.t is Placement.C:
        return wire.verify_C(frame)
    return wire.verify_D(frame, ed_pk)


def _mutate(rng: random.Random, data: bytes) -> bytes:
    b = bytearray(data)
    kind = rng.randrange(4)
    if not b:
        return bytes([rng.randrange(256)])
    if kind == 0:  # flip a byte
        i = rng.randrange(len(b))
        b[i] ^= 1 << rng.randrange(8)
    elif kind == 1:  # truncate
        b = b[: rng.randrange(len(b))]
    elif kind == 2:  # insert a byte
        b.insert(rng.randrange(len(b) + 1), rng.randrange(256))
    else:  # delete a byte
        del b[rng.randrange(len(b))]
    return bytes(b)


def test_fuzz_1000_mutations_no_crash() -> None:
    _, ed_pk = _ED.keygen(seed=_ED_SEED)
    valid = [wire.encode_frame(f) for f in _valid_frames()]
    rng = random.Random(2024)
    malformed = decoded = verified_true = 0
    for _ in range(1000):
        mutated = _mutate(rng, rng.choice(valid))
        try:
            frame = wire.decode_frame(mutated)
        except WireDecodeError:
            malformed += 1
            continue
        # decoded cleanly → verify must return a bool, never raise
        ok = _verify(frame, ed_pk)
        assert ok in (True, False)
        decoded += 1
        verified_true += int(ok)
    assert malformed + decoded == 1000
    assert malformed > 0  # the vast majority of mutations are structurally invalid


def test_valid_frame_survives_reencode() -> None:
    """Sanity: an unmutated frame decodes, re-encodes byte-identically, and verifies."""
    _, ed_pk = _ED.keygen(seed=_ED_SEED)
    for frame in _valid_frames():
        data = wire.encode_frame(frame)
        assert wire.encode_frame(wire.decode_frame(data)) == data
        assert _verify(wire.decode_frame(data), ed_pk) is True
