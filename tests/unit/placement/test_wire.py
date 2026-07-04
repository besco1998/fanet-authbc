"""Wire format A–D: covered_bytes boundaries, encode/decode round-trip, build+verify+tamper."""

from __future__ import annotations

import cbor2

from authbc.bench import telemgen
from authbc.crypto.bls import BlsScheme
from authbc.crypto.ed25519 import Ed25519Scheme
from authbc.ledger.chain import Chain
from authbc.ledger.record import canonical_bytes
from authbc.placement import wire
from authbc.placement.wire import Placement

_TELEMETRY = ("lat", "lon", "alt", "vel_x", "vel_y", "vel_z", "battery", "mode")
_ED = Ed25519Scheme()
_BLS = BlsScheme()


def _records(src: int, seed: int, n: int):
    chain = Chain(src=src)
    for i, r in enumerate(telemgen.samples(seed=seed, n=n)):
        chain.append({k: getattr(r, k) for k in _TELEMETRY}, ts=i)
    return chain.records()


# --------------------------------------------------------------------------- covered_bytes
def test_covered_bytes_boundaries() -> None:
    recs = _records(src=1, seed=1, n=4)
    a = wire.covered_bytes(recs, Placement.A)
    assert isinstance(a, list) and a == [r.canonical() for r in recs]  # per-record
    b = wire.covered_bytes(recs, Placement.B)
    assert isinstance(b, bytes) and b == canonical_bytes([r.to_map() for r in recs])  # whole array
    # B's covered bytes are the CBOR array encoding, NOT the concatenation of per-record bytes
    assert b != b"".join(a)
    # C mirrors A (per-record); D mirrors B (whole array)
    assert wire.covered_bytes(recs, Placement.C) == a
    assert wire.covered_bytes(recs, Placement.D) == b


def test_covered_bytes_changes_with_any_record() -> None:
    recs = _records(src=1, seed=2, n=3)
    base_b = wire.covered_bytes(recs, Placement.B)
    tampered = list(recs)
    tampered[1] = wire.Record(src=recs[1].src, seq=recs[1].seq, ts=recs[1].ts,
                              prev_hash=recs[1].prev_hash,
                              pl={**dict(recs[1].pl), "alt": recs[1].pl["alt"] + 1})
    assert wire.covered_bytes(tampered, Placement.B) != base_b
    assert wire.covered_bytes(tampered, Placement.A)[1] != wire.covered_bytes(recs, Placement.A)[1]


# --------------------------------------------------------------------------- encode/decode
def test_encode_decode_round_trip_all_placements() -> None:
    recs = _records(src=9, seed=3, n=3)
    sk, _ = _ED.keygen(seed=bytes(range(32)))
    bls_sks = [_BLS.keygen(seed=bytes([i]) * 32)[0] for i in range(3)]
    frames = [
        wire.build_A(recs, sk),
        wire.build_B(recs, sk),
        wire.build_C(recs, bls_sks),
        wire.build_D(recs, sk, block_id=1, frag_idx=0, frag_total=2),
    ]
    for f in frames:
        data = wire.encode_frame(f)
        # canonical: re-encoding the decoded frame is byte-identical (no indefinite lengths)
        assert wire.encode_frame(wire.decode_frame(data)) == data
        back = wire.decode_frame(data)
        assert back.t == f.t and back.n == f.n == 3
        assert [r.to_map() for r in back.recs] == [r.to_map() for r in f.recs]


def test_canonical_no_indefinite_lengths() -> None:
    recs = _records(src=2, seed=4, n=2)
    sk, _ = _ED.keygen(seed=bytes(range(32)))
    data = wire.encode_frame(wire.build_B(recs, sk))
    # Our frames ARE canonical: re-encoding the decoded object under canonical=True reproduces
    # the exact bytes. Canonical CBOR (RFC 8949 §4.2) uses only definite-length items, so an
    # indefinite-length item anywhere would make this idempotence fail. (A raw byte *value*
    # scan is wrong — hash/int data bytes routinely equal 0x9f/0xbf.)
    assert cbor2.dumps(cbor2.loads(data), canonical=True) == data


# --------------------------------------------------------------------------- build + verify
def test_A_build_verify_and_tamper() -> None:
    recs = _records(src=1, seed=5, n=4)
    sk, pk = _ED.keygen(seed=bytes(range(32)))
    frame = wire.build_A(recs, sk)
    assert wire.verify_A(frame, [pk] * frame.n) is True
    bad = wire.Frame(t=Placement.A, src=frame.src, base_seq=frame.base_seq,
                     recs=(*frame.recs[:1], wire.Record(src=recs[1].src, seq=recs[1].seq,
                           ts=recs[1].ts + 1, prev_hash=recs[1].prev_hash, pl=dict(recs[1].pl)),
                           *frame.recs[2:]), auth=frame.auth)
    assert wire.verify_A(bad, [pk] * bad.n) is False


def test_B_build_verify_and_tamper() -> None:
    recs = _records(src=1, seed=6, n=5)
    sk, pk = _ED.keygen(seed=bytes(range(32)))
    frame = wire.build_B(recs, sk)
    assert wire.verify_B(frame, pk) is True
    last = recs[-1]
    new_pl = {**dict(last.pl), "battery": (last.pl["battery"] + 1) % 101}
    tampered_rec = wire.Record(src=last.src, seq=last.seq, ts=last.ts,
                               prev_hash=last.prev_hash, pl=new_pl)
    tampered = wire.Frame(t=Placement.B, src=frame.src, base_seq=frame.base_seq,
                          recs=(*frame.recs[:-1], tampered_rec), auth=frame.auth)
    assert wire.verify_B(tampered, pk) is False


def test_C_cross_signer_aggregate_verify_and_tamper() -> None:
    # records from DIFFERENT originators, each BLS-signs its own record
    recs = [_records(src=10 + i, seed=7 + i, n=1)[0] for i in range(3)]
    sks = [_BLS.keygen(seed=bytes([i + 1]) * 32)[0] for i in range(3)]
    frame = wire.build_C(recs, sks)
    assert len(frame.auth["agg"]) == 96 and len(frame.auth["signers"]) == 3
    assert wire.verify_C(frame) is True
    tampered = wire.Frame(t=Placement.C, src=frame.src, base_seq=frame.base_seq,
                          recs=(wire.Record(src=recs[0].src, seq=recs[0].seq, ts=recs[0].ts + 9,
                                prev_hash=recs[0].prev_hash, pl=dict(recs[0].pl)), *frame.recs[1:]),
                          auth=frame.auth)
    assert wire.verify_C(tampered) is False


def test_D_block_verify_and_tamper() -> None:
    recs = _records(src=1, seed=11, n=6)
    sk, pk = _ED.keygen(seed=bytes(range(32)))
    frame = wire.build_D(recs, sk, block_id=42, frag_idx=1, frag_total=3)
    assert frame.auth["block_id"] == 42 and frame.auth["frag_total"] == 3
    assert wire.verify_D(frame, pk) is True
    tampered = wire.Frame(t=Placement.D, src=frame.src, base_seq=frame.base_seq,
                          recs=frame.recs[:-1], auth=frame.auth)  # drop a record from the block
    assert wire.verify_D(tampered, pk) is False


def test_encode_rejects_n_mismatch() -> None:
    recs = _records(src=1, seed=12, n=2)
    sk, _ = _ED.keygen(seed=bytes(range(32)))
    good = wire.build_B(recs, sk)
    bad = wire.Frame(t=Placement.B, src=good.src, base_seq=good.base_seq, recs=good.recs,
                     auth=good.auth, v=999)
    # unsupported version must be rejected on decode
    import pytest
    with pytest.raises(ValueError):
        wire.decode_frame(wire.encode_frame(bad))
