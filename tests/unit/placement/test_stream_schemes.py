"""The stream-signing schemes, implemented (revision A10; placement/stream_schemes.py).

Held here: each authenticates honest packets, refuses a forged one, and does so at the moment
its definition says — TESLA when the key arrives and only for packets that came before their key
could be known, EMSS when a signature packet links back to the packet, Wong–Lam on arrival —
and each adds the bytes Table 5 charged it.
"""

from __future__ import annotations

from authbc.crypto.ed25519 import Ed25519Scheme
from authbc.placement import stream_schemes as ss

_ED = Ed25519Scheme()
SK, PK = _ED.keygen(seed=b"\x05" * 32)
P = 82                      # the lean one-record frame without its signature


def _payload(i: int) -> bytes:
    return i.to_bytes(4, "big") * (P // 4) + bytes(P % 4)


class TestTesla:
    def _pair(self, d: int = 1) -> tuple[ss.TeslaSender, ss.TeslaReceiver]:
        keys = ss.tesla_chain(b"seed", 64)
        return (ss.TeslaSender(keys, interval_ms=20.0, delay=d),
                ss.TeslaReceiver(keys[0], interval_ms=20.0, delay=d, payload_bytes=P))

    def test_a_packet_is_authenticated_when_its_key_arrives(self) -> None:
        tx, rx = self._pair()
        first = tx.packet(_payload(1), 5.0)               # interval 1
        assert len(first) == P + 24                       # Table 5: 10 + 10 + 4
        assert rx.receive(first, 6.0) == []               # its key is not known yet
        assert rx.receive(tx.packet(_payload(2), 25.0), 26.0) == [_payload(1)]

    def test_a_forged_mac_is_refused(self) -> None:
        tx, rx = self._pair()
        bad = bytearray(tx.packet(_payload(1), 5.0))
        bad[P + 4] ^= 1
        rx.receive(bytes(bad), 6.0)
        assert rx.receive(tx.packet(_payload(2), 25.0), 26.0) == []

    def test_a_packet_that_arrives_after_its_key_could_be_known_is_unsafe(self) -> None:
        tx, rx = self._pair()
        late = tx.packet(_payload(1), 5.0)
        rx.receive(tx.packet(_payload(2), 25.0), 26.0)
        assert rx.receive(late, 30.0) == [] and rx.unsafe == 1

    def test_a_lost_disclosure_is_recovered_from_a_later_key(self) -> None:
        tx, rx = self._pair()
        rx.receive(tx.packet(_payload(1), 5.0), 6.0)
        tx.packet(_payload(2), 25.0)                      # lost: it carried K_1
        assert rx.receive(tx.packet(_payload(3), 45.0), 46.0) == [_payload(1)]


class TestEmss:
    def test_packets_are_authenticated_by_the_next_signature_packet(self) -> None:
        tx, rx = ss.EmssSender(SK, period=4), ss.EmssReceiver(PK, payload_bytes=P)
        got: list[bytes] = []
        for i in range(4):
            for pkt in tx.packets(_payload(i)):
                got += rx.receive(pkt)
        assert sorted(got) == sorted(_payload(i) for i in range(4))

    def test_one_lost_packet_does_not_cut_the_chain(self) -> None:
        tx, rx = ss.EmssSender(SK, period=4), ss.EmssReceiver(PK, payload_bytes=P)
        got: list[bytes] = []
        for i in range(4):
            for pkt in tx.packets(_payload(i)):
                if not (i == 2 and pkt[:1] == b"D"):
                    got += rx.receive(pkt)
        assert sorted(got) == sorted(_payload(i) for i in (0, 1, 3))

    def test_a_tampered_packet_is_never_authenticated(self) -> None:
        tx, rx = ss.EmssSender(SK, period=4), ss.EmssReceiver(PK, payload_bytes=P)
        got: list[bytes] = []
        for i in range(4):
            for pkt in tx.packets(_payload(i)):
                if i == 1 and pkt[:1] == b"D":
                    pkt = pkt[:5] + bytes([pkt[5] ^ 1]) + pkt[6:]
                got += rx.receive(pkt)
        assert _payload(1) not in got and _payload(1)[:4] not in [g[:4] for g in got]


class TestWongLam:
    def test_each_packet_verifies_alone_and_carries_129_bytes(self) -> None:
        packets = ss.wong_lam_block([_payload(i) for i in range(4)], SK)
        assert all(len(p) == P + 129 for p in packets)
        assert [ss.wong_lam_verify(p, PK, P) for p in packets] == [_payload(i) for i in range(4)]

    def test_a_tampered_packet_fails(self) -> None:
        p = bytearray(ss.wong_lam_block([_payload(i) for i in range(4)], SK)[2])
        p[0] ^= 1
        assert ss.wong_lam_verify(bytes(p), PK, P) is None
