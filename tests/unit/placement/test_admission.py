"""Admission before verification (revision A7; placement/admission.py).

Held here: the group MAC refuses an outsider's frame and passes a member's; the cheap checks
refuse what is too short, unparseable, from an unknown sender, replayed or too far ahead, and
pass honest frames; the plan's worst case — a well-formed frame naming a real sender with a
newer sequence number and a wrong signature — passes every cheap check and costs the receiver
a verification; the rate cap holds an impostor to the sender's own rate.
"""

from __future__ import annotations

from authbc.bench import telemgen
from authbc.crypto.ed25519 import Ed25519Scheme
from authbc.ledger.chain import Chain
from authbc.placement import wire_v2
from authbc.placement.admission import AdmissionReceiver, GroupMac, Policy, Refused
from authbc.placement.session_v2 import LeanReceiver, LeanSender, Receipt

_ED = Ed25519Scheme()
SK, PK = _ED.keygen(seed=bytes(range(32)))
B = 4


def _frames(n: int, sk=SK) -> list[bytes]:
    chain = Chain(src=7)
    for i, r in enumerate(telemgen.samples(seed=3, n=n * B)):
        chain.append({k: getattr(r, k) for k in wire_v2.PAYLOAD_FIELDS}, ts=1_000 + 20 * i)
    recs = chain.records()
    sender = LeanSender(sk)
    return [sender.frame(recs[i:i + B]) for i in range(0, len(recs), B)]


def _rx(policy: Policy) -> AdmissionReceiver:
    return AdmissionReceiver(LeanReceiver({7: PK}), policy, frozenset({7}))


class TestGroupMac:
    def test_a_member_passes_and_an_outsider_does_not(self) -> None:
        mac = GroupMac(b"swarm key")
        rx = _rx(Policy(group_mac=mac))
        f = _frames(1)[0]
        assert rx.receive(mac.wrap(f)).receipt is Receipt.ACCEPTED       # type: ignore[union-attr]
        assert rx.receive(GroupMac(b"other").wrap(f)) is Refused.MAC
        assert len(mac.wrap(f)) == len(f) + 8


class TestCheapChecks:
    def test_honest_frames_pass(self) -> None:
        rx = _rx(Policy(cheap_checks=True))
        assert all(rx.receive(f).receipt is Receipt.ACCEPTED            # type: ignore[union-attr]
                   for f in _frames(4))

    def test_short_garbage_unknown_and_replayed_frames_are_refused_cheaply(self) -> None:
        rx = _rx(Policy(cheap_checks=True))
        frames = _frames(3)
        rx.receive(frames[0])
        rx.receive(frames[1])
        assert rx.receive(b"\x00" * 10) is Refused.SHAPE
        assert rx.receive(b"\xff" * 200) is Refused.SHAPE
        assert rx.receive(frames[0]) is Refused.SEQ_WINDOW                # replayed
        stranger = AdmissionReceiver(LeanReceiver({8: PK}), Policy(cheap_checks=True),
                                     frozenset({8}))
        assert stranger.receive(frames[2]) is Refused.UNKNOWN

    def test_a_forged_newer_frame_passes_every_cheap_check_and_costs_a_verification(self) -> None:
        rx = _rx(Policy(cheap_checks=True))
        rx.receive(_frames(1)[0])
        other_sk, _ = _ED.keygen(seed=b"\x01" * 32)
        forged = _frames(2, sk=other_sk)[1]                                # newer seq, wrong key
        assert rx.receive(forged).receipt is Receipt.BAD_SIGNATURE        # type: ignore[union-attr]


class TestRateCap:
    def test_an_impostor_is_held_to_the_senders_own_rate(self) -> None:
        rx = _rx(Policy(rate_cap=12.5, slack=0.0, burst=2.0))
        frame = _frames(1)[0]
        got = [rx.receive(frame, t_s=0.001 * i) for i in range(20)]       # 1 000 frames/s
        assert sum(r is Refused.RATE for r in got) >= 17
