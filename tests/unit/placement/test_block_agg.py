"""Placement D — fragmentation, reorder tolerance, timeout, one-fragment-loss kills the block."""

from __future__ import annotations

from authbc.bench import telemgen
from authbc.crypto.ed25519 import Ed25519Scheme
from authbc.ledger.chain import Chain
from authbc.placement.block_agg import BlockAggFramer, BlockReassembler

_TELEMETRY = ("lat", "lon", "alt", "vel_x", "vel_y", "vel_z", "battery", "mode")
_ED = Ed25519Scheme()


def _records(src, seed, n):
    chain = Chain(src=src)
    for i, r in enumerate(telemgen.samples(seed=seed, n=n)):
        chain.append({k: getattr(r, k) for k in _TELEMETRY}, ts=i)
    return chain.records()


def test_fragmentation_and_verify() -> None:
    recs = _records(src=1, seed=1, n=6)
    sk, pk = _ED.keygen(seed=bytes(range(32)))
    frames = BlockAggFramer(sk).pack(recs, b=2)  # 3 fragments of 2
    assert [f.n for f in frames] == [2, 2, 2]
    assert {f.auth["frag_total"] for f in frames} == {3}
    # a single fragment does NOT verify on its own (its recs are only a slice)
    assert BlockAggFramer(sk).unpack(frames[0], pk=pk)[1] == [False, False]
    # reassemble in order → verifies
    rea = BlockReassembler()
    full = None
    for i, f in enumerate(frames):
        full = rea.offer(f, now_ms=i)
    out, mask = BlockAggFramer(sk).unpack(full, pk=pk)
    assert out == recs and mask == [True] * 6


def test_reorder_tolerance() -> None:
    recs = _records(src=1, seed=2, n=6)
    sk, pk = _ED.keygen(seed=bytes(range(32)))
    frames = BlockAggFramer(sk).pack(recs, b=2)
    rea = BlockReassembler()
    full = None
    for f in [frames[2], frames[0], frames[1]]:  # out of order
        full = rea.offer(f, now_ms=0) or full
    out, mask = BlockAggFramer(sk).unpack(full, pk=pk)
    assert out == recs and mask == [True] * 6


def test_timeout_discards_partial_block() -> None:
    recs = _records(src=1, seed=3, n=6)
    sk, _ = _ED.keygen(seed=bytes(range(32)))
    frames = BlockAggFramer(sk).pack(recs, b=2)
    rea = BlockReassembler(timeout_ms=500)
    assert rea.offer(frames[0], now_ms=0) is None  # only 1 of 3 fragments
    assert rea.offer(frames[1], now_ms=100) is None
    assert rea.sweep(now_ms=400) == 0  # within timeout
    assert rea.sweep(now_ms=601) == 1  # 601 - 0 > 500 ⇒ discard
    assert rea.discarded_partial == 1


def test_one_fragment_loss_kills_exactly_that_block() -> None:
    sk, pk = _ED.keygen(seed=bytes(range(32)))
    fa = BlockAggFramer(sk).pack(_records(src=1, seed=4, n=4), b=2)  # block A: 2 frags
    fb = BlockAggFramer(sk).pack(_records(src=2, seed=5, n=4), b=2)  # block B: 2 frags
    rea = BlockReassembler()
    # deliver both fragments of B, but only ONE of A (drop A's second)
    rea.offer(fa[0], now_ms=0)
    full_b = None
    for f in fb:
        full_b = rea.offer(f, now_ms=1) or full_b
    assert full_b is not None and BlockAggFramer(sk).unpack(full_b, pk=pk)[1] == [True] * 4
    rea.sweep(now_ms=600)
    assert rea.discarded_partial == 1  # exactly block A discarded
