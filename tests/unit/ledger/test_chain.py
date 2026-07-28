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


# --- F5: is the per-record prev_hash actually needed ON THE WIRE? --------------------------
def test_chain_reconstructs_from_one_link_per_frame() -> None:
    """A receiver can DERIVE every prev_hash in a frame except the first (audit F5).

    prev_hash_{i+1} = H(record_i), and record_i is fully known once its own prev_hash is known —
    so one transmitted link per frame seeds a recurrence that rebuilds the rest. This test pins
    the property that makes the wire-format saving possible: the reconstruction is BYTE-IDENTICAL
    to the original and the resulting stored chain still verifies.

    Saving, if adopted: 32·(b−1)/b bytes per record — 24 B at b=4, against a 45 B delta record.
    NOT adopted: the wire format is frozen under ⚠️ D6 and this is Mohamed's decision.
    """
    src, b, n = 7, 4, 12
    chain = Chain(src=src)
    for i in range(n):
        chain.append({"lat": 100 + i, "lon": 200 + i, "alt": 300 + i}, ts=1000 + i)
    original = chain.records()
    assert chain.verify()

    recovered: list[Record] = []
    for f in range(0, n, b):
        frame = original[f:f + b]
        # WIRE: the frame's first prev_hash, plus each record's body. No other hashes.
        first_ph = frame[0].prev_hash
        bodies = [(r.src, r.seq, r.ts, dict(r.pl)) for r in frame]

        ph = first_ph
        for rec_src, seq, ts, pl in bodies:
            rec = Record(src=rec_src, seq=seq, ts=ts, prev_hash=ph, pl=pl)
            recovered.append(rec)
            ph = rec.record_hash()          # derived, never transmitted

    assert len(recovered) == n
    assert all(a.canonical() == r.canonical() for a, r in zip(original, recovered, strict=True))

    rebuilt = Chain(src=src)
    for rec in recovered:
        rebuilt._records.append(rec)        # noqa: SLF001 — loading a received chain directly
    assert rebuilt.verify(), "the reconstructed ledger must satisfy the same chain invariant"


def test_omitting_the_frames_first_link_breaks_reconstruction() -> None:
    """The saving is 32·(b−1)/b, not 32·b: the first link per frame is NOT redundant.

    It is the only thing tying a frame to the previous one, so dropping it would let frames be
    reordered or dropped undetected.
    """
    chain = Chain(src=3)
    for i in range(4):
        chain.append({"lat": i}, ts=i)
    recs = chain.records()
    # Rebuilding from a WRONG first link yields a chain that is internally consistent but does
    # not match the original — which is exactly the cross-frame tamper-evidence being preserved.
    bogus = Record(src=3, seq=0, ts=0, prev_hash=b"\xff" * 32, pl=dict(recs[0].pl))
    assert bogus.canonical() != recs[0].canonical()
