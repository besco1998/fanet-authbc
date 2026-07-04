"""Placement C — cross-signer aggregate: mixed originators verify; one bad signer fails all."""

from __future__ import annotations

from authbc.bench import telemgen
from authbc.crypto.bls import BlsScheme
from authbc.ledger.chain import Chain
from authbc.placement.relay_agg import RelayAggFramer

_TELEMETRY = ("lat", "lon", "alt", "vel_x", "vel_y", "vel_z", "battery", "mode")
_BLS = BlsScheme()


def _rec(src, seed):
    chain = Chain(src=src)
    r = telemgen.samples(seed=seed, n=1)[0]
    return chain.append({k: getattr(r, k) for k in _TELEMETRY}, ts=0)


def _originators(n):
    recs, sks, pks = [], [], []
    for i in range(n):
        rec = _rec(src=10 + i, seed=100 + i)
        sk, pk = _BLS.keygen(seed=bytes([20 + i]) * 32)
        recs.append(rec)
        sks.append(sk)
        pks.append(pk)
    return recs, sks, pks


def test_mixed_originator_frame_verifies() -> None:
    recs, sks, pks = _originators(4)
    sigs = [_BLS.sign(sk, r.canonical()) for sk, r in zip(sks, recs, strict=True)]
    framer = RelayAggFramer()
    frames = framer.pack(recs, sigs=sigs, pks=pks, b=4)
    assert len(frames) == 1 and len(frames[0].auth["agg"]) == 96
    out, mask = framer.unpack(frames[0])
    assert out == recs and mask == [True] * 4


def test_one_bad_inner_signature_fails_whole_aggregate() -> None:
    """BLS aggregate_verify is all-or-nothing; a single bad signer fails the entire frame."""
    recs, sks, pks = _originators(3)
    sigs = [_BLS.sign(sk, r.canonical()) for sk, r in zip(sks, recs, strict=True)]
    # corrupt ONE inner signature (originator 1 signs the WRONG message)
    sigs[1] = _BLS.sign(sks[1], b"not this record")
    framer = RelayAggFramer()
    frame = framer.pack(recs, sigs=sigs, pks=pks, b=3)[0]
    _, mask = framer.unpack(frame)
    assert mask == [False, False, False]  # cannot localize the bad signer — whole frame fails


def test_pack_chunks_by_b() -> None:
    recs, sks, pks = _originators(5)
    sigs = [_BLS.sign(sk, r.canonical()) for sk, r in zip(sks, recs, strict=True)]
    frames = RelayAggFramer().pack(recs, sigs=sigs, pks=pks, b=2)
    assert [f.n for f in frames] == [2, 2, 1]
