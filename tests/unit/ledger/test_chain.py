"""Hash-chain correctness (docs/01 §1): 1000-append verify + independent prev_hash recompute."""

from __future__ import annotations

import hashlib

import cbor2
import pytest

from authbc.bench import telemgen
from authbc.ledger.chain import Chain
from authbc.ledger.record import GENESIS_PH, Record

_TELEMETRY = ("lat", "lon", "alt", "vel_x", "vel_y", "vel_z", "battery", "mode")


def _payloads(seed: int, n: int) -> list[dict[str, int]]:
    return [{k: getattr(r, k) for k in _TELEMETRY} for r in telemgen.samples(seed=seed, n=n)]


def _independent_hash(rec: Record) -> bytes:
    """Recompute a record's hash by a separate path (NOT rec.record_hash())."""
    m = {"src": rec.src, "seq": rec.seq, "ts": rec.ts, "ph": rec.prev_hash, "pl": dict(rec.pl)}
    return hashlib.sha256(cbor2.dumps(m, canonical=True)).digest()


def test_1000_append_chain_verifies() -> None:
    chain = Chain(src=7)
    for i, pl in enumerate(_payloads(seed=1, n=1000)):
        rec = chain.append(pl, ts=1000 + i)
        assert rec.seq == i and rec.src == 7
    assert len(chain) == 1000
    assert chain.verify() is True


def test_genesis_prev_hash_is_zero() -> None:
    chain = Chain(src=3)
    first = chain.append(_payloads(1, 1)[0], ts=0)
    assert first.prev_hash == GENESIS_PH


def test_prev_hash_independent_recompute() -> None:
    chain = Chain(src=9)
    for i, pl in enumerate(_payloads(seed=2, n=200)):
        chain.append(pl, ts=i)
    recs = chain.records()
    assert recs[0].prev_hash == GENESIS_PH
    for i in range(1, len(recs)):
        assert recs[i].prev_hash == _independent_hash(recs[i - 1]), f"chain break at {i}"


def test_tamper_breaks_chain() -> None:
    chain = Chain(src=1)
    for i, pl in enumerate(_payloads(seed=3, n=50)):
        chain.append(pl, ts=i)
    recs = chain.records()
    # tamper record 20's payload → its hash changes → record 21's prev_hash no longer matches
    bad = Record(src=recs[20].src, seq=recs[20].seq, ts=recs[20].ts, prev_hash=recs[20].prev_hash,
                 pl={**dict(recs[20].pl), "battery": (recs[20].pl["battery"] + 1) % 101})
    assert bad.record_hash() != recs[20].record_hash()
    assert recs[21].prev_hash != bad.record_hash()  # the chain would detect the swap


def test_record_rejects_float_and_bad_hash() -> None:
    good_pl = _payloads(5, 1)[0]
    with pytest.raises(TypeError):
        Record(src=1, seq=0, ts=0, prev_hash=GENESIS_PH, pl={**good_pl, "lat": 1.5})
    with pytest.raises(ValueError):
        Record(src=1, seq=0, ts=0, prev_hash=b"\x00" * 16, pl=good_pl)
    with pytest.raises(ValueError):
        Record(src=70000, seq=0, ts=0, prev_hash=GENESIS_PH, pl=good_pl)


def test_determinism_same_payload_same_hash() -> None:
    pl = _payloads(6, 1)[0]
    a = Record(src=2, seq=5, ts=99, prev_hash=GENESIS_PH, pl=pl)
    b = Record(src=2, seq=5, ts=99, prev_hash=GENESIS_PH, pl=dict(pl))
    assert a.canonical() == b.canonical()
    assert a.record_hash() == b.record_hash()
