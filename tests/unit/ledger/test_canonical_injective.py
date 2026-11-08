"""The signed encoding is injective: the assumption of the proofs, discharged (W6(b); docs/02 §11).

The paper's proofs model a frame's signed bytes as a free term, which Tamarin treats as injective;
the paper said "we assume canonical encoding to be injective". The encoding is
σ_A(r) = CBOR(m(r)) per record (inline placements) and σ_B(r₁…r_n) = CBOR([m(r₁), …, m(r_n)]) per
frame (batched placements), CBOR in its deterministic form (`ledger.record.canonical_bytes`). The
proof in docs/02 §11 rests on three facts, each held here over the whole record domain, not only
the telemetry schema:

1. `Record.from_map ∘ cbor2.loads` is a left inverse of σ_A, and its list form of σ_B — so neither
   can send two different inputs to the same bytes;
2. the encoding is deterministic: re-encoding what was decoded gives the same bytes, with map keys
   in the order RFC 8949 §4.2.1 fixes;
3. σ_A's bytes always begin a map (major type 5) and σ_B's an array (major type 4): a signature
   over one placement's bytes is never a signature over another's.

A counterexample found here is a finding (Failure Report), not a reason to narrow the domain.
"""
from __future__ import annotations

import cbor2
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from authbc.ledger.record import PREV_HASH_LEN, Record, canonical_bytes
from authbc.placement.wire import Placement, covered_bytes

U16, U32 = 2**16 - 1, 2**32 - 1

# The whole domain `Record` admits: any text keys, any non-bool int values, big ones included
# (CBOR carries those as tagged bignums).
_payload = st.dictionaries(st.text(max_size=12), st.integers(), max_size=10)
records = st.builds(Record, src=st.integers(0, U16), seq=st.integers(0, U32),
                    ts=st.integers(0, U32),
                    prev_hash=st.binary(min_size=PREV_HASH_LEN, max_size=PREV_HASH_LEN),
                    pl=_payload)
frames = st.lists(records, min_size=1, max_size=8)

FAST = settings(max_examples=300, deadline=None)


def _major(data: bytes) -> int:
    return data[0] >> 5


class TestALeftInverseExists:
    @FAST
    @given(records)
    def test_one_record(self, r: Record) -> None:
        assert Record.from_map(cbor2.loads(r.canonical())) == r

    @FAST
    @given(frames)
    def test_a_frame_of_records(self, recs: list[Record]) -> None:
        signed = covered_bytes(recs, Placement.B)
        assert [Record.from_map(m) for m in cbor2.loads(signed)] == recs


class TestDistinctInputsGiveDistinctBytes:
    @FAST
    @given(records, records)
    def test_two_records(self, a: Record, b: Record) -> None:
        assert (a == b) == (a.canonical() == b.canonical())

    @FAST
    @given(frames, frames)
    def test_two_frames(self, a: list[Record], b: list[Record]) -> None:
        assert (a == b) == (covered_bytes(a, Placement.B) == covered_bytes(b, Placement.B))

    @FAST
    @given(records, st.sampled_from(["src", "seq", "ts", "prev_hash", "pl"]))
    def test_one_field_changed(self, r: Record, field: str) -> None:
        changed = {"src": dict(src=(r.src + 1) % (U16 + 1)),
                   "seq": dict(seq=(r.seq + 1) % (U32 + 1)),
                   "ts": dict(ts=(r.ts + 1) % (U32 + 1)),
                   "prev_hash": dict(prev_hash=bytes([r.prev_hash[0] ^ 1]) + r.prev_hash[1:]),
                   "pl": dict(pl={**r.pl, "__extra__": 0} if "__extra__" not in r.pl
                              else {k: v for k, v in r.pl.items() if k != "__extra__"})}[field]
        other = Record(**{"src": r.src, "seq": r.seq, "ts": r.ts, "prev_hash": r.prev_hash,
                          "pl": dict(r.pl), **changed})
        assert other != r and other.canonical() != r.canonical()


class TestTheEncodingIsDeterministic:
    @FAST
    @given(records)
    def test_re_encoding_gives_the_same_bytes(self, r: Record) -> None:
        data = r.canonical()
        assert canonical_bytes(cbor2.loads(data)) == data

    @FAST
    @given(_payload)
    def test_map_keys_in_rfc8949_order(self, pl: dict[str, int]) -> None:
        # RFC 8949 §4.2.1: keys sorted by the bytewise order of their encodings. For text keys
        # alone this is also RFC 7049's length-first order, so either reading gives these bytes.
        encoded = [canonical_bytes(k) for k in cbor2.loads(canonical_bytes(pl))]
        assert encoded == sorted(encoded)


class TestPlacementsCannotBeConfused:
    @FAST
    @given(records, frames)
    def test_a_record_is_a_map_and_a_frame_is_an_array(self, r: Record,
                                                        recs: list[Record]) -> None:
        assert _major(r.canonical()) == 5
        assert _major(covered_bytes(recs, Placement.B)) == 4
        assert all(_major(b) == 5 for b in covered_bytes(recs, Placement.A))


class TestTheDomainIsWhatTheProofAssumes:
    def test_a_boolean_is_refused(self) -> None:
        # Python takes True for 1; CBOR does not (0xf5 against 0x01). Admitting bools would let
        # two equal Records encode differently, so the record refuses them.
        with pytest.raises(TypeError):
            Record(src=0, seq=0, ts=0, prev_hash=b"\0" * PREV_HASH_LEN, pl={"a": True})

    def test_a_short_chain_link_is_refused(self) -> None:
        with pytest.raises(ValueError):
            Record(src=0, seq=0, ts=0, prev_hash=b"\0" * 31, pl={})
