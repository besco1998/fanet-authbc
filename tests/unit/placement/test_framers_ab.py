"""Placement A/B framers + b_max formula (docs/02 §6, P3 step 1)."""

from __future__ import annotations

from authbc.bench import telemgen
from authbc.crypto.ed25519 import Ed25519Scheme
from authbc.ledger.chain import Chain
from authbc.ledger.record import Record
from authbc.placement.framer import b_max, b_max_inline
from authbc.placement.inline import InlineFramer
from authbc.placement.self_batch import SelfBatchFramer

_TELEMETRY = ("lat", "lon", "alt", "vel_x", "vel_y", "vel_z", "battery", "mode")
_ED = Ed25519Scheme()


def _records(src, seed, n):
    chain = Chain(src=src)
    for i, r in enumerate(telemgen.samples(seed=seed, n=n)):
        chain.append({k: getattr(r, k) for k in _TELEMETRY}, ts=i)
    return chain.records()


def test_b_max_formula_against_inlined() -> None:
    """⌊(M−H_f−g_a)/s⌋ with M=1500, H_f=40 (docs/02 T2)."""
    assert b_max(130, 48) == 10   # 1412/130 = 10.86
    assert b_max(358, 48) == 3    # 1412/358 = 3.94
    assert b_max(40, 48) == 35    # 1412/40  = 35.3
    assert b_max(40, 64) == 34    # 1396/40  = 34.9
    # Reference outlier: the P3 prompt lists CBOR s=130,g_a=64 → 9, but the formula gives 10
    # (10·130 + 40 + 64 = 1404 ≤ 1500 < 1534 = 11·130+104). The formula is arithmetically
    # correct; the inlined "9" is an off-by-one in the reference (recorded in audits/p3.md).
    assert b_max(130, 64) == 10


def test_b_max_measured_sizes_sane() -> None:
    """With the measured P1 sizes + BLS g_a=96 (superseding the archive)."""
    assert b_max(69, 96) == 19    # CBOR through a BLS cross-signer frame
    assert b_max(45, 96) == 30    # delta
    assert b_max_inline(69) == 10  # placement A: ⌊(1500−40)/(69+64)⌋ = 1460/133 = 10.9


def test_inline_A_pack_unpack_and_per_record_tamper() -> None:
    recs = _records(src=1, seed=1, n=10)
    sk, pk = _ED.keygen(seed=bytes(range(32)))
    framer = InlineFramer(sk)
    frames = framer.pack(recs, b=4)  # 4,4,2
    assert [f.n for f in frames] == [4, 4, 2]
    for f in frames:
        out, mask = framer.unpack(f, pk=pk)
        assert out == list(f.recs) and mask == [True] * f.n
    # tamper one record in the first frame → only its mask entry is False
    f0 = frames[0]
    bad_rec = Record(src=f0.recs[2].src, seq=f0.recs[2].seq, ts=f0.recs[2].ts + 1,
                     prev_hash=f0.recs[2].prev_hash, pl=dict(f0.recs[2].pl))
    from authbc.placement.wire import Frame, Placement
    tampered = Frame(t=Placement.A, src=f0.src, base_seq=f0.base_seq,
                     recs=(*f0.recs[:2], bad_rec, *f0.recs[3:]), auth=f0.auth)
    _, mask = framer.unpack(tampered, pk=pk)
    assert mask == [True, True, False, True]


def test_self_batch_B_all_or_nothing() -> None:
    recs = _records(src=1, seed=2, n=9)
    sk, pk = _ED.keygen(seed=bytes(range(32)))
    framer = SelfBatchFramer(sk)
    frames = framer.pack(recs, b=5)  # 5,4
    assert [f.n for f in frames] == [5, 4]
    for f in frames:
        out, mask = framer.unpack(f, pk=pk)
        assert out == list(f.recs) and mask == [True] * f.n
    # any tamper ⇒ the whole frame's mask is False (one signature covers all)
    f0 = frames[0]
    bad = Record(src=f0.recs[0].src, seq=f0.recs[0].seq, ts=f0.recs[0].ts,
                 prev_hash=f0.recs[0].prev_hash,
                 pl={**dict(f0.recs[0].pl), "alt": f0.recs[0].pl["alt"] + 1})
    from authbc.placement.wire import Frame, Placement
    tampered = Frame(t=Placement.B, src=f0.src, base_seq=f0.base_seq,
                     recs=(bad, *f0.recs[1:]), auth=f0.auth)
    _, mask = framer.unpack(tampered, pk=pk)
    assert mask == [False] * f0.n
