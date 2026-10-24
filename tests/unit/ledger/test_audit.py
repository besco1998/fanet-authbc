"""The post-mission audit (revision A16; src/authbc/ledger/audit.py).

Held here: an honest mission audits clean with a deterministic Merkle root; an equivocating
sender is caught from two receivers' uploads; a forged frame planted in a neighbour's upload
is caught; a gap and a broken link in a sender's own chain are reported; the auditor's
signature covers the findings.
"""

from __future__ import annotations

from authbc.bench import telemgen
from authbc.crypto.ed25519 import Ed25519Scheme
from authbc.ledger.audit import Upload, audit, merkle_root
from authbc.ledger.chain import Chain
from authbc.ledger.record import Record
from authbc.placement import wire_v2
from authbc.placement.session_v2 import LeanReceiver, LeanSender

_ED = Ed25519Scheme()
B = 4
KEYS = {u: _ED.keygen(seed=bytes([u]) * 32) for u in (1, 2, 3)}
PKS = {u: pk for u, (_, pk) in KEYS.items()}


def _records(src: int, n: int, seed: int) -> list[Record]:
    chain = Chain(src=src)
    for i, r in enumerate(telemgen.samples(seed=seed, n=n)):
        chain.append({k: getattr(r, k) for k in wire_v2.PAYLOAD_FIELDS}, ts=1_000 + 20 * i)
    return chain.records()


def _frames(src: int, n_frames: int) -> list[bytes]:
    recs = _records(src, n_frames * B, seed=src)
    sender = LeanSender(KEYS[src][0])
    return [sender.frame(recs[i:i + B]) for i in range(0, len(recs), B)]


def _held(rx: LeanReceiver) -> tuple[bytes, ...]:
    return tuple(dict.fromkeys(rx._frames.values()))


def _honest(lost: dict[tuple[int, int], set[int]]) -> list[Upload]:
    """Three UAVs, eight frames each; `lost[(src, rx)]` are the frame indices rx misses."""
    own = {u: _frames(u, 8) for u in KEYS}
    uploads = []
    for rx_id in KEYS:
        rx = LeanReceiver(PKS)
        for src in KEYS:
            if src == rx_id:
                continue
            for i, f in enumerate(own[src]):
                if i not in lost.get((src, rx_id), set()):
                    rx.receive(f)
        uploads.append(Upload(rx_id, tuple(own[rx_id]), _held(rx)))
    return uploads


class TestAnHonestMission:
    def test_audits_clean_even_with_losses(self) -> None:
        report = audit(_honest({(1, 2): {3}, (3, 1): {0, 5}}), PKS)
        assert report.clean()
        assert report.frames_audited == 3 * 8 + (2 * 8 * 3 - 3)

    def test_the_root_does_not_depend_on_upload_order(self) -> None:
        ups = _honest({})
        assert audit(ups, PKS).merkle_root == audit(ups[::-1], PKS).merkle_root

    def test_the_auditor_signs_the_root_and_the_findings(self) -> None:
        sk, pk = _ED.keygen(seed=b"\x09" * 32)
        report = audit(_honest({}), PKS, auditor=(_ED, sk))
        assert _ED.verify(pk, report.merkle_root + repr(tuple([] for _ in range(6))).encode(),
                          report.signature)


class TestFaults:
    def test_an_equivocating_sender_is_caught(self) -> None:
        recs = _records(1, 8, seed=1)
        honest = LeanSender(KEYS[1][0])
        frames = [honest.frame(recs[i:i + B]) for i in range(0, 8, B)]
        # UAV 1 signs a second, different second frame and shows it to UAV 3 only
        other = list(recs[4:])
        other[1] = Record(src=1, seq=other[1].seq, ts=other[1].ts + 1, prev_hash=other[1].prev_hash,
                          pl=other[1].pl)
        for i in range(2, 4):
            other[i] = Record(src=1, seq=other[i].seq, ts=other[i].ts,
                              prev_hash=other[i - 1].record_hash(), pl=other[i].pl)
        forked = wire_v2.encode_frame_v2(wire_v2.build_B_v2(other, KEYS[1][0]))
        rx2, rx3 = LeanReceiver(PKS), LeanReceiver(PKS)
        for f in frames:
            rx2.receive(f)
        rx3.receive(frames[0])
        rx3.receive(forked)
        report = audit([Upload(1, tuple(frames)), Upload(2, (), _held(rx2)),
                        Upload(3, (), _held(rx3))], PKS)
        assert (1, recs[5].seq) in report.equivocations
        assert any(holder == 3 for holder, _, _ in report.mismatches)

    def test_a_forged_frame_in_a_neighbours_upload_is_caught(self) -> None:
        ups = _honest({(1, 2): {3}})
        recs = _records(1, 16, seed=1)[12:16]           # the frame UAV 2 lost
        fake = wire_v2.encode_frame_v2(wire_v2.build_B_v2(recs, KEYS[2][0]))   # wrong key
        ups[1] = Upload(2, ups[1].own, ups[1].held + (fake,))
        report = audit(ups, PKS)
        assert report.forgeries == [(2, len(ups[1].held) - 1)]

    def test_a_gap_in_a_senders_own_chain_is_reported(self) -> None:
        frames = _frames(1, 4)
        report = audit([Upload(1, (frames[0], frames[2], frames[3]))], PKS)
        assert report.gaps == [(1, 3, 8)]          # records 4..7 went with the second frame

    def test_a_link_that_skips_a_frame_is_a_broken_link(self) -> None:
        recs = _records(1, 12, seed=1)
        first = wire_v2.encode_frame_v2(wire_v2.build_B_v2(recs[0:4], KEYS[1][0]))
        # frame 2 signed with a link to frame 0's last record: it skips frame 1's records
        bad = [Record(src=1, seq=r.seq, ts=r.ts, prev_hash=r.prev_hash, pl=r.pl)
               for r in recs[4:8]]
        bad[0] = Record(src=1, seq=bad[0].seq, ts=bad[0].ts, prev_hash=recs[2].record_hash(),
                        pl=bad[0].pl)
        for i in range(1, 4):
            bad[i] = Record(src=1, seq=bad[i].seq, ts=bad[i].ts,
                            prev_hash=bad[i - 1].record_hash(), pl=bad[i].pl)
        second = wire_v2.encode_frame_v2(wire_v2.build_B_v2(bad, KEYS[1][0]))
        report = audit([Upload(1, (first, second))], PKS)
        assert report.broken_links == [(1, recs[4].seq)]


def test_merkle_root_of_one_leaf_and_of_none() -> None:
    assert merkle_root([b"x"]) != merkle_root([])
    assert merkle_root([b"a", b"b", b"c"]) != merkle_root([b"a", b"b"])
