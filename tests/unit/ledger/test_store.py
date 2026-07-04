"""Store replay/equivocation/tamper behaviour + tamper-detection property test (docs/01 §1)."""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from authbc.bench import telemgen
from authbc.crypto.registry import get_scheme
from authbc.ledger.chain import Chain
from authbc.ledger.record import GENESIS_PH, Record
from authbc.ledger.store import Outcome, Store

_TELEMETRY = ("lat", "lon", "alt", "vel_x", "vel_y", "vel_z", "battery", "mode")
_SCHEME = get_scheme("ed25519")


def _pl(seed: int, i: int = 0) -> dict[str, int]:
    r = telemgen.samples(seed=seed, n=i + 1)[i]
    return {k: getattr(r, k) for k in _TELEMETRY}


def _signed(chain: Chain, pl: dict[str, int], ts: int, sk):
    rec = chain.append(pl, ts=ts)
    return rec, _SCHEME.sign(sk, rec.canonical())


def test_store_accepts_valid_chain() -> None:
    sk, pk = _SCHEME.keygen(seed=bytes(range(32)))
    chain, store = Chain(src=1), Store()
    for i in range(20):
        rec, sig = _signed(chain, _pl(1, i), ts=i, sk=sk)
        assert store.ingest(rec, scheme=_SCHEME, pk=pk, sig=sig) is Outcome.STORED
    assert store.counters["stored"] == 20
    assert store.counters["replay"] == 0
    assert store.counters["equivocation"] == 0
    assert store.counters["tampered"] == 0


def test_replay_rejected() -> None:
    chain, store = Chain(src=1), Store()
    rec = chain.append(_pl(2), ts=0)
    assert store.ingest(rec) is Outcome.STORED
    assert store.ingest(rec) is Outcome.REPLAY  # exact duplicate
    assert store.counters["replay"] == 1


def test_equivocation_flagged_with_evidence() -> None:
    store = Store()
    c1, c2 = Chain(src=5), Chain(src=5)
    r1 = c1.append(_pl(3, 0), ts=0)
    r2 = c2.append(_pl(4, 0), ts=0)  # same (src,seq)=(5,0), different payload ⇒ different hash
    assert store.ingest(r1) is Outcome.STORED
    assert store.ingest(r2) is Outcome.EQUIVOCATION
    assert store.counters["equivocation"] == 1
    assert store.equivocations == [(r1, r2)]  # evidence retained


def test_bad_signature_is_tampered() -> None:
    sk, pk = _SCHEME.keygen(seed=bytes(range(32)))
    _, pk2 = _SCHEME.keygen(seed=bytes(range(1, 33)))
    chain, store = Chain(src=1), Store()
    rec, sig = _signed(chain, _pl(5), ts=0, sk=sk)
    assert store.ingest(rec, scheme=_SCHEME, pk=pk2, sig=sig) is Outcome.TAMPERED  # wrong pk
    assert store.counters["tampered"] == 1


def test_seq_wraparound_rejected_as_replay() -> None:
    """u32 wrap (seq back to a low value) must be rejected, not silently accepted."""
    store = Store()
    hi = Record(src=2, seq=1000, ts=0, prev_hash=GENESIS_PH, pl=_pl(6))
    assert store.ingest(hi) is Outcome.STORED
    low = Record(src=2, seq=0, ts=1, prev_hash=GENESIS_PH, pl=_pl(6))
    assert store.ingest(low) is Outcome.REPLAY
    assert store.counters["replay"] == 1


def test_gap_is_allowed() -> None:
    """A missed predecessor (loss) is a robustness event, not a security failure — accept it."""
    store = Store()
    r0 = Record(src=3, seq=0, ts=0, prev_hash=GENESIS_PH, pl=_pl(7))
    r5 = Record(src=3, seq=5, ts=5, prev_hash=b"\x11" * 32, pl=_pl(7))  # gap; predecessor unknown
    assert store.ingest(r0) is Outcome.STORED
    assert store.ingest(r5) is Outcome.STORED


def test_forged_contiguous_link_is_tampered() -> None:
    store = Store()
    r0 = Record(src=4, seq=0, ts=0, prev_hash=GENESIS_PH, pl=_pl(8))
    assert store.ingest(r0) is Outcome.STORED
    forged = Record(src=4, seq=1, ts=1, prev_hash=b"\x22" * 32, pl=_pl(8))  # wrong prev_hash
    assert store.ingest(forged) is Outcome.TAMPERED


@settings(max_examples=200)
@given(
    seed=st.integers(0, 2**31 - 1),
    field=st.sampled_from(_TELEMETRY),
    delta=st.sampled_from([1, -1, 2]),
)
def test_any_field_tamper_breaks_signature(seed: int, field: str, delta: int) -> None:
    """Any change to any signed field flips the canonical bytes ⇒ signature fails (docs/01 §1)."""
    sk, pk = _SCHEME.keygen(seed=bytes(range(32)))
    pl = _pl(seed)
    rec = Record(src=1, seq=0, ts=0, prev_hash=GENESIS_PH, pl=pl)
    sig = _SCHEME.sign(sk, rec.canonical())
    tampered_pl = {**pl, field: pl[field] + delta}
    if tampered_pl == pl:  # no-op change (shouldn't happen with these deltas)
        return
    tampered = Record(src=1, seq=0, ts=0, prev_hash=GENESIS_PH, pl=tampered_pl)
    assert _SCHEME.verify(pk, tampered.canonical(), sig) is False
    store = Store()
    assert store.ingest(tampered, scheme=_SCHEME, pk=pk, sig=sig) is Outcome.TAMPERED
