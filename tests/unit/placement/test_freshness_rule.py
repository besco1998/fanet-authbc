"""The time window against delayed frames (revision A5; src/authbc/placement/freshness_rule.py).

Held here: the window's arithmetic as the plan writes it, the worst-case drift of two clocks,
that a delayed frame is refused before verification and never stored, that a timestamp altered
to look fresh still fails its signature, and that the rule stands aside, saying so, when the
window has outgrown its limit or a frame's times cannot be read alone.
"""

from __future__ import annotations

import pytest

from authbc.bench import telemgen
from authbc.crypto.ed25519 import Ed25519Scheme
from authbc.ledger.chain import Chain
from authbc.ledger.record import Record
from authbc.placement import wire_v2
from authbc.placement.freshness_rule import TimedReceiver, TimeVerdict, TimeWindow, accepted
from authbc.placement.session_v2 import LeanReceiver, LeanSender, Receipt

_ED = Ed25519Scheme()
_SK, _PK = _ED.keygen(seed=bytes(range(32)))
B = 4
# The plan's A5 numbers: b = 4 at 50 records/s, worst channel delay, one verification; the
# guard that makes Δ_acc = 150 ms at σ = 10 ms.
WINDOW = TimeWindow(batch=4, lam=50.0, t_ch_ms=3.49, t_v_ms=0.26, sigma_clk_ms=10.0,
                    guard_ms=46.25)


def _records(n: int) -> list[Record]:
    chain = Chain(src=7)
    for i, r in enumerate(telemgen.samples(seed=3, n=n)):
        chain.append({k: getattr(r, k) for k in wire_v2.PAYLOAD_FIELDS}, ts=1_000 + 20 * i)
    return chain.records()


def _frames(n_frames: int, ref_interval: int = 1) -> tuple[list[bytes], list[int]]:
    """Frames and the timestamp of each frame's newest record."""
    recs = _records(n_frames * B)
    sender = LeanSender(_SK, ref_interval=ref_interval)
    frames = [sender.frame(recs[i:i + B]) for i in range(0, len(recs), B)]
    return frames, [recs[i + B - 1].ts for i in range(0, len(recs), B)]


def _rx(max_window_ms: float = 1_000.0) -> TimedReceiver:
    return TimedReceiver(LeanReceiver({7: _PK}), WINDOW, max_window_ms)


class TestTheWindow:
    def test_the_plans_window_is_150_ms(self) -> None:
        assert WINDOW.accept_ms == pytest.approx(150.0)

    def test_two_clocks_at_20_ppm_drift_apart_by_144_ms_an_hour(self) -> None:
        """Each clock 72 ms an hour, in opposite directions: 144 ms, not 72."""
        assert WINDOW.widened(3_600.0) - WINDOW.accept_ms == pytest.approx(144.0)

    def test_how_long_an_outage_a_limit_allows(self) -> None:
        assert WINDOW.longest_outage_s(150.0 + 144.0) == pytest.approx(3_600.0)
        with pytest.raises(ValueError):
            WINDOW.longest_outage_s(100.0)
        with pytest.raises(ValueError):
            WINDOW.widened(-1.0)


class TestDelayedFrames:
    def test_an_honest_stream_is_accepted(self) -> None:
        rx = _rx()
        frames, newest = _frames(8)
        assert all(accepted(rx.receive(f, t + 3.75)) for f, t in zip(frames, newest, strict=True))
        assert rx.counters["fresh"] == 8

    def test_a_frame_held_back_past_the_window_is_refused_and_never_stored(self) -> None:
        rx = _rx()
        frames, newest = _frames(3)
        rx.receive(frames[0], newest[0] + 3.75)
        late = rx.receive(frames[1], newest[1] + 3.75 + 250.0)
        assert late.verdict is TimeVerdict.STALE and late.received is None
        assert len(rx.inner.store.records()) == B
        # sequence numbers alone would have taken it: the next frame is still accepted
        assert accepted(rx.receive(frames[2], newest[2] + 3.75))

    def test_the_same_delay_is_accepted_without_the_rule(self) -> None:
        """What the rule closes: the receiver alone stores a frame however late it comes."""
        plain = LeanReceiver({7: _PK})
        frames, _ = _frames(2)
        assert plain.receive(frames[0]).receipt is Receipt.ACCEPTED
        assert plain.receive(frames[1]).receipt is Receipt.ACCEPTED

    def test_a_timestamp_moved_forward_to_look_fresh_fails_the_signature(self) -> None:
        recs = _records(B)
        # The forger re-chains the altered records, or the encoder refuses them; the
        # signature it keeps is the honest frame's.
        forged: list[Record] = []
        for r in recs:
            link = forged[-1].record_hash() if forged else r.prev_hash
            forged.append(Record(src=r.src, seq=r.seq, ts=r.ts + 10_000, prev_hash=link,
                                 pl=r.pl))
        honest = LeanSender(_SK).frame(recs)
        f = wire_v2.decode_frame_v2(honest)
        tampered = wire_v2.encode_frame_v2(
            wire_v2.FrameV2(t=f.t, src=f.src, base_seq=f.base_seq, link=f.link,
                            recs=tuple(forged), auth=f.auth))
        got = _rx().receive(tampered, recs[-1].ts + 10_000 + 3.75)
        assert got.verdict is TimeVerdict.FRESH
        assert got.received is not None and got.received.receipt is Receipt.BAD_SIGNATURE


class TestWhereTheRuleStandsAside:
    def test_past_its_limit_the_window_gives_way_to_sequence_numbers(self) -> None:
        rx = _rx(max_window_ms=200.0)
        frames, newest = _frames(1)
        got = rx.receive(frames[0], newest[0] + 3.75 + 5_000, outage_s=3_600.0)
        assert got.verdict is TimeVerdict.TIME_UNVERIFIED and accepted(got)

    def test_a_dependent_frame_is_passed_on_unchecked_and_counted(self) -> None:
        rx = _rx()
        frames, newest = _frames(2, ref_interval=2)
        assert rx.receive(frames[0], newest[0] + 3.75).verdict is TimeVerdict.FRESH
        got = rx.receive(frames[1], newest[1] + 3.75)
        assert got.verdict is TimeVerdict.NOT_CHECKED and accepted(got)
        assert rx.counters["not_checked"] == 1
