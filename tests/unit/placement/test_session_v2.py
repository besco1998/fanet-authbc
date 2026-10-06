"""The lean frame under loss, replay and forgery (docs/01 §4b, audit F45/F46).

The paper used to say "each frame verifies alone" for a design whose records were delta-coded
across frames, and "replay protection" appeared nowhere. Both are now properties of running code,
and these tests are where they are held.
"""

from __future__ import annotations

import cbor2
import pytest

from authbc.bench import telemgen
from authbc.crypto.ed25519 import Ed25519Scheme
from authbc.ledger.chain import Chain
from authbc.ledger.record import Record
from authbc.placement import wire_v2
from authbc.placement.session_v2 import LeanReceiver, LeanSender, Receipt

_ED = Ed25519Scheme()
_SK, _PK = _ED.keygen(seed=bytes(range(32)))
B = 4


def _records(n: int, *, src: int = 7, seed: int = 3) -> list[Record]:
    chain = Chain(src=src)
    for i, r in enumerate(telemgen.samples(seed=seed, n=n)):
        chain.append({k: getattr(r, k) for k in wire_v2.PAYLOAD_FIELDS}, ts=1_000 + 20 * i)
    return chain.records()


def _frames(n_frames: int, *, ref_interval: int, src: int = 7, sk=_SK) -> list[bytes]:
    recs = _records(n_frames * B, src=src)
    sender = LeanSender(sk, ref_interval=ref_interval)
    return [sender.frame(recs[i:i + B]) for i in range(0, len(recs), B)]


class TestALossFreeStream:
    @pytest.mark.parametrize("ref", [1, 2, 4, 8])
    def test_every_frame_is_accepted_and_the_ledger_is_complete(self, ref: int) -> None:
        rx = LeanReceiver({7: _PK})
        receipts = [rx.receive(f).receipt for f in _frames(16, ref_interval=ref)]
        assert receipts == [Receipt.ACCEPTED] * 16
        assert len(rx.store.records()) == 16 * B
        assert rx.counters["accepted"] == 16

    def test_the_stored_records_are_the_senders_records_byte_for_byte(self) -> None:
        recs = _records(8)
        sender, rx = LeanSender(_SK, ref_interval=2), LeanReceiver({7: _PK})
        for i in range(0, 8, B):
            rx.receive(sender.frame(recs[i:i + B]))
        assert [r.canonical() for r in rx.store.records()] == [r.canonical() for r in recs]


class TestWhatALostFrameCosts:
    def test_with_every_frame_self_contained_a_loss_costs_exactly_that_frame(self) -> None:
        frames = _frames(8, ref_interval=1)
        rx = LeanReceiver({7: _PK})
        receipts = [rx.receive(f).receipt for i, f in enumerate(frames) if i != 3]
        assert receipts == [Receipt.ACCEPTED] * 7

    def test_with_a_reference_interval_of_four_a_loss_costs_the_rest_of_the_group(self) -> None:
        frames = _frames(8, ref_interval=4)          # frames 0 and 4 decode alone
        rx = LeanReceiver({7: _PK})
        receipts = [rx.receive(f).receipt for i, f in enumerate(frames) if i != 1]
        #            frame:   0                 2               3               4..7
        assert receipts == ([Receipt.ACCEPTED] + [Receipt.DESYNC] * 2 + [Receipt.ACCEPTED] * 4)

    def test_losing_the_self_contained_frame_costs_the_whole_group(self) -> None:
        frames = _frames(8, ref_interval=4)
        rx = LeanReceiver({7: _PK})
        receipts = [rx.receive(f).receipt for f in frames[1:]]
        assert receipts == [Receipt.DESYNC] * 3 + [Receipt.ACCEPTED] * 4

    def test_a_frame_after_a_gap_is_stored_and_its_link_names_the_missing_record(self) -> None:
        recs = _records(12)
        sender, rx = LeanSender(_SK), LeanReceiver({7: _PK})
        frames = [sender.frame(recs[i:i + B]) for i in range(0, 12, B)]
        rx.receive(frames[0])
        out = rx.receive(frames[2])                  # frame 1 never arrived
        assert out.receipt is Receipt.ACCEPTED
        assert out.records[0].prev_hash == recs[7].record_hash()
        assert [r.seq for r in rx.store.records()] == [0, 1, 2, 3, 8, 9, 10, 11]


class TestReplayAndForgery:
    def test_a_replayed_frame_is_refused_and_stores_nothing(self) -> None:
        frames = _frames(4, ref_interval=1)
        rx = LeanReceiver({7: _PK})
        for f in frames:
            rx.receive(f)
        assert rx.receive(frames[1]).receipt is Receipt.REPLAY
        assert len(rx.store.records()) == 4 * B

    def test_a_replayed_self_contained_frame_cannot_desynchronise_the_stream(self) -> None:
        """The attack the state-commit rule exists for.

        Frames 0 and 4 decode alone; 1-3 and 5-7 are dependent. Replaying frame 0 in the middle of
        the second group would, if the decoder's state followed whatever DECODED, rewind it to
        record 3 and make the honest frame 6 undecodable.
        """
        frames = _frames(8, ref_interval=4)
        rx = LeanReceiver({7: _PK})
        for f in frames[:6]:
            assert rx.receive(f).receipt is Receipt.ACCEPTED
        assert rx.receive(frames[0]).receipt is Receipt.REPLAY
        assert rx.receive(frames[6]).receipt is Receipt.ACCEPTED
        assert rx.receive(frames[7]).receipt is Receipt.ACCEPTED

    def test_a_frame_from_an_impostor_is_refused_and_changes_no_state(self) -> None:
        impostor_sk, _ = _ED.keygen(seed=b"\x66" * 32)
        honest = _frames(8, ref_interval=4)
        forged = _frames(8, ref_interval=4, sk=impostor_sk)
        rx = LeanReceiver({7: _PK})
        for f in honest[:2]:
            rx.receive(f)
        assert rx.receive(forged[4]).receipt is Receipt.BAD_SIGNATURE   # self-contained forgery
        assert rx.receive(honest[2]).receipt is Receipt.ACCEPTED        # stream still in step
        assert len(rx.store.records()) == 3 * B

    def test_an_unknown_sender_and_a_malformed_frame(self) -> None:
        rx = LeanReceiver({7: _PK})
        assert rx.receive(_frames(1, ref_interval=1, src=9)[0]).receipt is Receipt.UNKNOWN_SENDER
        assert rx.receive(b"\xff\x00").receipt is Receipt.MALFORMED
        assert rx.counters["unknown_sender"] == 1 and rx.counters["malformed"] == 1

    def test_two_different_signed_records_for_one_sequence_number_are_kept_as_evidence(
            self) -> None:
        recs = _records(B)
        other = _records(B, seed=99)                 # same src and seq, different telemetry
        rx = LeanReceiver({7: _PK})
        assert rx.receive(LeanSender(_SK).frame(recs)).receipt is Receipt.ACCEPTED
        assert rx.receive(LeanSender(_SK).frame(other)).receipt is Receipt.EQUIVOCATION
        assert len(rx.store.equivocations) == 1

    def test_a_signed_frame_whose_link_contradicts_the_stored_chain_is_tampering(self) -> None:
        recs = _records(2 * B)
        rx = LeanReceiver({7: _PK})
        rx.receive(LeanSender(_SK).frame(recs[:B]))
        # the sender signs a second frame that claims a different predecessor
        fork = Chain(src=7)
        for r in _records(B, seed=5):
            fork.append(dict(r.pl), ts=r.ts)
        moved = [fork.append(dict(r.pl), ts=r.ts) for r in recs[B:]]
        assert rx.receive(LeanSender(_SK).frame(moved)).receipt is Receipt.TAMPERED
        assert len(rx.store.records()) == B


class TestSeveralSenders:
    def test_streams_are_decoded_against_their_own_state(self) -> None:
        sk2, pk2 = _ED.keygen(seed=b"\x02" * 32)
        a = _frames(4, ref_interval=4, src=7)
        b = _frames(4, ref_interval=4, src=8, sk=sk2)
        rx = LeanReceiver({7: _PK, 8: pk2})
        receipts = [rx.receive(f).receipt for pair in zip(a, b, strict=True) for f in pair]
        assert receipts == [Receipt.ACCEPTED] * 8

    def test_one_senders_loss_does_not_desynchronise_another(self) -> None:
        sk2, pk2 = _ED.keygen(seed=b"\x02" * 32)
        a = _frames(4, ref_interval=4, src=7)
        b = _frames(4, ref_interval=4, src=8, sk=sk2)
        rx = LeanReceiver({7: _PK, 8: pk2})
        rx.receive(a[0])
        rx.receive(b[0])
        assert rx.receive(a[2]).receipt is Receipt.DESYNC      # a[1] lost
        assert rx.receive(b[1]).receipt is Receipt.ACCEPTED


class TestSenderGuards:
    def test_a_reference_interval_below_one_is_refused(self) -> None:
        with pytest.raises(ValueError, match="ref_interval"):
            LeanSender(_SK, ref_interval=0)

    def test_the_first_frame_of_each_group_is_the_only_self_contained_one(self) -> None:
        types = [cbor2.loads(f)[wire_v2.F_T] for f in _frames(8, ref_interval=4)]
        assert types == [1, 2, 2, 2, 1, 2, 2, 2]
