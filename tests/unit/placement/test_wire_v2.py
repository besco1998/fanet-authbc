"""Wire format v2 — the lean frame as a real, decodable, verifiable object (docs/01 §4b, F45).

These tests exist because the design this project headlined was, until 2026-10-06, a sum of sizes
that no decoder had ever received. Each class below pins one property that a *composition* could
not show and a *frame* must have.
"""

from __future__ import annotations

import cbor2
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from authbc.bench import telemgen
from authbc.crypto.ed25519 import Ed25519Scheme
from authbc.ledger.chain import Chain
from authbc.ledger.record import Record
from authbc.placement import wire, wire_v2
from authbc.placement.wire_v2 import (
    DesyncError,
    FrameType,
    FrameV2,
    build_A_v2,
    build_B_v2,
    decode_frame_v2,
    encode_frame_v2,
    frame_src,
    verify_v2,
)

_ED = Ed25519Scheme()
_SK, _PK = _ED.keygen(seed=bytes(range(32)))


def _chain(n: int, *, src: int = 7, seed: int = 3, base_ts: int = 1_000) -> list[Record]:
    """`n` chained ledger records carrying real generator telemetry."""
    chain = Chain(src=src)
    for i, r in enumerate(telemgen.samples(seed=seed, n=n)):
        chain.append({k: getattr(r, k) for k in wire_v2.PAYLOAD_FIELDS}, ts=base_ts + 20 * i)
    return chain.records()


class TestRoundTrip:
    @pytest.mark.parametrize("b", [1, 2, 4, 8, 23, 24, 64])
    def test_a_self_contained_self_batch_frame_round_trips(self, b: int) -> None:
        recs = _chain(b)
        frame = build_B_v2(recs, _SK)
        back = decode_frame_v2(encode_frame_v2(frame))
        assert back == frame
        assert back.t is FrameType.B_KEY
        assert verify_v2(back, _PK)

    @pytest.mark.parametrize("b", [1, 2, 4, 8])
    def test_an_inline_frame_round_trips(self, b: int) -> None:
        recs = _chain(b)
        frame = build_A_v2(recs, _SK)
        back = decode_frame_v2(encode_frame_v2(frame))
        assert back == frame
        assert back.t is FrameType.A_KEY and len(back.auth) == b
        assert verify_v2(back, _PK)

    def test_a_dependent_frame_round_trips_given_its_predecessor(self) -> None:
        recs = _chain(8)
        frame = build_B_v2(recs[4:], _SK, prev=recs[3])
        assert frame.t is FrameType.B_DELTA
        back = decode_frame_v2(encode_frame_v2(frame, prev=recs[3]), prev=recs[3])
        assert back == frame
        assert verify_v2(back, _PK)

    def test_the_decoder_rebuilds_seq_src_and_every_prev_hash(self) -> None:
        recs = _chain(4, src=40_000)
        back = decode_frame_v2(encode_frame_v2(build_B_v2(recs, _SK)))
        assert [r.seq for r in back.recs] == [0, 1, 2, 3]
        assert {r.src for r in back.recs} == {40_000}
        assert [r.prev_hash for r in back.recs] == [r.prev_hash for r in recs]

    def test_encoding_is_deterministic(self) -> None:
        recs = _chain(4)
        assert encode_frame_v2(build_B_v2(recs, _SK)) == encode_frame_v2(build_B_v2(recs, _SK))


class TestADependentFrameNeedsItsPredecessor:
    """The loss-propagation case: the property a byte model could not show (F46)."""

    def test_without_the_predecessor_the_frame_is_undecodable(self) -> None:
        recs = _chain(8)
        data = encode_frame_v2(build_B_v2(recs[4:], _SK, prev=recs[3]), prev=recs[3])
        with pytest.raises(DesyncError):
            decode_frame_v2(data)

    def test_the_wrong_predecessor_is_refused_rather_than_decoded_wrongly(self) -> None:
        recs = _chain(8)
        data = encode_frame_v2(build_B_v2(recs[4:], _SK, prev=recs[3]), prev=recs[3])
        with pytest.raises(DesyncError):
            decode_frame_v2(data, prev=recs[2])            # one record too early
        other = _chain(8, src=8)
        with pytest.raises(DesyncError):
            decode_frame_v2(data, prev=other[3])           # right seq, wrong sender

    def test_a_self_contained_frame_ignores_whatever_the_receiver_holds(self) -> None:
        recs = _chain(8)
        data = encode_frame_v2(build_B_v2(recs[4:], _SK))
        assert decode_frame_v2(data).recs == tuple(recs[4:])
        assert decode_frame_v2(data, prev=recs[0]).recs == tuple(recs[4:])

    def test_desync_is_not_reported_as_a_malformed_frame(self) -> None:
        assert not issubclass(DesyncError, wire.WireDecodeError)


class TestWhatTheSignatureCovers:
    def test_it_is_the_same_bytes_v1_signs(self) -> None:
        recs = _chain(4)
        v1 = wire.build_B(recs, _SK)
        assert build_B_v2(recs, _SK).auth == v1.auth

    def test_a_frame_signed_by_someone_else_does_not_verify(self) -> None:
        other_sk, _ = _ED.keygen(seed=b"\x55" * 32)
        frame = decode_frame_v2(encode_frame_v2(build_B_v2(_chain(4), other_sk)))
        assert not verify_v2(frame, _PK)

    def test_a_substituted_chain_link_breaks_the_signature(self) -> None:
        recs = _chain(8)
        data = encode_frame_v2(build_B_v2(recs[4:], _SK))
        obj = cbor2.loads(data)
        obj[wire_v2.F_LINK] = b"\x00" * 32
        forged = decode_frame_v2(cbor2.dumps(obj, canonical=True))
        assert not verify_v2(forged, _PK)

    def test_a_shifted_base_seq_breaks_the_signature(self) -> None:
        data = encode_frame_v2(build_B_v2(_chain(4), _SK))
        obj = cbor2.loads(data)
        obj[wire_v2.F_BASE_SEQ] += 1
        assert not verify_v2(decode_frame_v2(cbor2.dumps(obj, canonical=True)), _PK)

    def test_an_inline_frame_fails_if_any_one_signature_is_wrong(self) -> None:
        frame = build_A_v2(_chain(4), _SK)
        sigs = list(frame.auth)
        sigs[2] = bytes(64)
        bad = FrameV2(t=frame.t, src=frame.src, base_seq=frame.base_seq, link=frame.link,
                      recs=frame.recs, auth=tuple(sigs))
        assert not verify_v2(decode_frame_v2(encode_frame_v2(bad)), _PK)

    @settings(max_examples=200, deadline=None)
    @given(pos=st.integers(min_value=0, max_value=10_000), bit=st.integers(0, 7))
    def test_no_single_bit_flip_yields_different_records_that_verify(self, pos: int,
                                                                    bit: int) -> None:
        recs = _chain(4)
        data = bytearray(encode_frame_v2(build_B_v2(recs, _SK)))
        data[pos % len(data)] ^= 1 << bit
        try:
            frame = decode_frame_v2(bytes(data))
        except wire.WireDecodeError:
            return
        if verify_v2(frame, _PK):
            # the flip landed in a byte the records do not depend on (a non-canonical length
            # prefix cbor2 still accepts); what matters is that the RECORDS are the signed ones
            assert frame.recs == tuple(recs)


class TestTheSenderRefusesFramesTheReceiverWouldRebuildDifferently:
    def test_records_that_do_not_chain(self) -> None:
        recs = _chain(4)
        broken = Record(src=recs[2].src, seq=recs[2].seq, ts=recs[2].ts,
                        prev_hash=b"\x22" * 32, pl=dict(recs[2].pl))
        frame = FrameV2(t=FrameType.B_KEY, src=7, base_seq=0, link=recs[0].prev_hash,
                        recs=(recs[0], recs[1], broken, recs[3]), auth=bytes(64))
        with pytest.raises(ValueError, match="does not chain"):
            encode_frame_v2(frame)

    def test_non_consecutive_or_foreign_records(self) -> None:
        recs = _chain(4)
        frame = FrameV2(t=FrameType.B_KEY, src=7, base_seq=0, link=recs[0].prev_hash,
                        recs=(recs[0], recs[2]), auth=bytes(64))
        with pytest.raises(ValueError, match="consecutive"):
            encode_frame_v2(frame)

    def test_a_dependent_frame_without_or_with_the_wrong_predecessor(self) -> None:
        recs = _chain(8)
        frame = build_B_v2(recs[4:], _SK, prev=recs[3])
        with pytest.raises(ValueError, match="needs `prev`"):
            encode_frame_v2(frame)
        with pytest.raises(ValueError, match="immediately before"):
            encode_frame_v2(frame, prev=recs[2])

    def test_a_self_contained_frame_must_not_be_given_a_predecessor(self) -> None:
        recs = _chain(8)
        with pytest.raises(ValueError, match="needs `prev`"):
            encode_frame_v2(build_B_v2(recs[4:], _SK), prev=recs[3])

    def test_an_empty_frame_and_an_oversized_one(self) -> None:
        recs = _chain(1)
        empty = FrameV2(t=FrameType.B_KEY, src=7, base_seq=0, link=bytes(32), recs=(),
                        auth=bytes(64))
        with pytest.raises(ValueError, match="1..255"):
            encode_frame_v2(empty)
        short_link = FrameV2(t=FrameType.B_KEY, src=7, base_seq=0, link=bytes(31),
                             recs=tuple(recs), auth=bytes(64))
        with pytest.raises(ValueError, match="link must be"):
            encode_frame_v2(short_link)

    def test_a_payload_outside_the_fixed_schema(self) -> None:
        rec = Chain(src=7).append({"a": 1}, ts=1)
        frame = FrameV2(t=FrameType.B_KEY, src=7, base_seq=0, link=rec.prev_hash, recs=(rec,),
                        auth=bytes(64))
        with pytest.raises(ValueError, match="fixed telemetry schema"):
            encode_frame_v2(frame)


class TestMalformedInputNeverCrashesTheDecoder:
    def _good(self) -> bytes:
        return encode_frame_v2(build_B_v2(_chain(4), _SK))

    @pytest.mark.parametrize("mutate", [
        lambda o: o.pop(wire_v2.F_LINK),
        lambda o: o.update({99: 1}),
        lambda o: o.update({wire_v2.F_V: 1}),
        lambda o: o.update({wire_v2.F_T: 9}),
        lambda o: o.update({wire_v2.F_N: 0}),
        lambda o: o.update({wire_v2.F_N: 5}),
        lambda o: o.update({wire_v2.F_N: True}),
        lambda o: o.update({wire_v2.F_SRC: "7"}),
        lambda o: o.update({wire_v2.F_SRC: 70_000}),
        lambda o: o.update({wire_v2.F_LINK: b"\x00" * 31}),
        lambda o: o.update({wire_v2.F_RECS: "text"}),
        lambda o: o.update({wire_v2.F_RECS: o[wire_v2.F_RECS][:-1]}),
        lambda o: o.update({wire_v2.F_RECS: o[wire_v2.F_RECS] + b"\x00"}),
        lambda o: o.update({wire_v2.F_AUTH: [b"\x00" * 64]}),
        lambda o: o.update({wire_v2.F_AUTH: 5}),
    ])
    def test_each_structural_defect_is_a_wire_decode_error(self, mutate) -> None:
        obj = cbor2.loads(self._good())
        mutate(obj)
        with pytest.raises(wire.WireDecodeError):
            decode_frame_v2(cbor2.dumps(obj, canonical=True))

    def test_an_inline_frame_with_the_wrong_number_of_signatures(self) -> None:
        obj = cbor2.loads(encode_frame_v2(build_A_v2(_chain(4), _SK)))
        obj[wire_v2.F_AUTH] = obj[wire_v2.F_AUTH][:3]
        with pytest.raises(wire.WireDecodeError):
            decode_frame_v2(cbor2.dumps(obj, canonical=True))

    @pytest.mark.parametrize("junk", [b"", b"\x00", b"\xff" * 40, cbor2.dumps([1, 2, 3]),
                                      cbor2.dumps({0: 2})])
    def test_non_frames(self, junk: bytes) -> None:
        with pytest.raises(wire.WireDecodeError):
            decode_frame_v2(junk)

    @settings(max_examples=300, deadline=None)
    @given(st.binary(max_size=400))
    def test_arbitrary_bytes_raise_only_the_documented_errors(self, data: bytes) -> None:
        try:
            decode_frame_v2(data)
        except (wire.WireDecodeError, DesyncError):
            pass

    @settings(max_examples=200, deadline=None)
    @given(cut=st.integers(min_value=0, max_value=400))
    def test_every_truncation_is_rejected(self, cut: int) -> None:
        good = self._good()
        with pytest.raises(wire.WireDecodeError):
            decode_frame_v2(good[: cut % len(good)])

    def test_frame_src_reads_the_sender_without_decoding_records(self) -> None:
        assert frame_src(encode_frame_v2(build_B_v2(_chain(4, src=31_000), _SK))) == 31_000
        for junk in (b"", b"\xff", cbor2.dumps([1]), cbor2.dumps({2: "x"}), cbor2.dumps({2: True})):
            with pytest.raises(wire.WireDecodeError):
                frame_src(junk)


class TestTheTwoFormatsDoNotAcceptEachOther:
    def test_v1_rejects_a_v2_frame(self) -> None:
        with pytest.raises(wire.WireDecodeError):
            wire.decode_frame(encode_frame_v2(build_B_v2(_chain(4), _SK)))

    def test_v2_rejects_a_v1_frame(self) -> None:
        with pytest.raises(wire.WireDecodeError):
            decode_frame_v2(wire.encode_frame(wire.build_B(_chain(4), _SK)))

    def test_v1_is_untouched(self) -> None:
        assert wire.WIRE_VERSION == 1 and wire_v2.WIRE_VERSION_2 == 2
