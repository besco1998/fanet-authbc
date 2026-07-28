"""B1 — H_f is MEASURED from the wire format, not assumed (docs/01 §2a).

Before 2026-07-29 the models carried an undocumented `H_f = 40 B`. It feeds T2, T2a, T6, `b_max`,
channel utilisation and the energy model, and nothing anywhere derived it. Measuring the frame
`placement/wire.py` actually serialises gives **44 B**.

These tests are the standing link between the model constant and the implementation: if the wire
format changes, the model constant must change with it, and this file fails until it does. That is
the F1-class staleness the frozen gate exists to prevent, applied to a constant instead of a CSV.
"""

from __future__ import annotations

import cbor2
import pytest

from authbc.ledger.record import Record
from authbc.placement import wire
from authbc.placement.framer import H_F


def _record(i: int) -> Record:
    """A realistic telemetry record: u16 src, mid-range u32 seq/ts, 8 integer payload fields."""
    return Record(src=1234, seq=100_000 + i, ts=3_600_000 + 50 * i, prev_hash=bytes(32),
                  pl={"lat": 123_456_789, "lon": 87_654_321, "alt": 1200,
                      "vx": 15, "vy": 3, "vz": 1, "batt": 87, "mode": 4})


def _framing_overhead(placement: wire.Placement, batch: int, auth: object,
                      auth_bytes: int) -> int:
    """H_f = len(frame) − Σ len(record bytes) − len(auth) — the definition in docs/01 §2a."""
    recs = [_record(i) for i in range(batch)]
    frame = wire.Frame(t=placement, src=recs[0].src, base_seq=recs[0].seq,
                       recs=tuple(recs), auth=auth)
    return len(wire.encode_frame(frame)) - sum(len(r.canonical()) for r in recs) - auth_bytes


def test_the_model_constant_equals_the_measured_wire_overhead() -> None:
    """The whole point of B1: `framer.H_F` must be what the wire format actually costs."""
    assert H_F == 44
    assert _framing_overhead(wire.Placement.B, 4, bytes(64), 64) == H_F


@pytest.mark.parametrize("batch", [1, 2, 3, 4, 5, 8, 16, 23])
def test_self_batch_overhead_is_flat_at_44_bytes_through_b23(batch: int) -> None:
    """Placement B — the optimized configuration — is a flat 44 B while CBOR lengths stay short."""
    assert _framing_overhead(wire.Placement.B, batch, bytes(64), 64) == 44


def test_overhead_steps_to_46_bytes_at_b24_where_cbor_lengths_widen() -> None:
    """CBOR encodes lengths 0..23 in the initial byte and needs a following byte from 24 up.

    So H_f is a *step* function of b, not a constant — the model's single value is exact at the
    operating point (b=4) and 2 B optimistic for large batches. Recorded, not hidden.
    """
    assert _framing_overhead(wire.Placement.B, 23, bytes(64), 64) == 44
    assert _framing_overhead(wire.Placement.B, 24, bytes(64), 64) == 46
    assert _framing_overhead(wire.Placement.B, 31, bytes(64), 64) == 46


def test_inline_placement_a_overhead_grows_with_the_batch() -> None:
    """A carries b separate signatures, each with its own CBOR byte-string header (~2 B).

    Using the flat 44 B for A therefore *understates* the A baseline, which makes every reported
    improvement over it slightly CONSERVATIVE. Direction of bias stated in docs/01 §2a.
    """
    at_1 = _framing_overhead(wire.Placement.A, 1, [bytes(64)], 64)
    at_4 = _framing_overhead(wire.Placement.A, 4, [bytes(64)] * 4, 4 * 64)
    assert at_1 == 45
    assert at_4 == 51
    assert at_4 > at_1, "A's framing must grow with b — one byte-string header per signature"
    assert at_1 >= H_F, "the A baseline is never cheaper to frame than the optimized B frame"


def test_block_placement_d_overhead_is_much_larger_and_the_bias_is_conservative() -> None:
    """D adds block_id / frag_idx / frag_total keys *and* their names: 81 B measured.

    The model charges D only 44 B, so it FLATTERS D by 37 B. D is already rejected on
    verifiability (T3), so a truer model would reject it harder — the simplification cannot
    manufacture the T3 result.
    """
    auth = {"sig": bytes(64), "block_id": 7, "frag_idx": 0, "frag_total": 1}
    assert _framing_overhead(wire.Placement.D, 4, auth, 64) == 81
    assert 81 > H_F


def test_most_of_the_header_is_cbor_text_keys() -> None:
    """43 of the 44 B is the empty skeleton, and the text keys dominate it.

    Stated so the thesis does not claim a tuned wire format: an integer-keyed profile would be
    materially smaller, and that optimisation is explicitly not part of this work.
    """
    skeleton = cbor2.dumps({"v": 1, "t": 1, "src": 1234, "base_seq": 100_000,
                            "n": 0, "recs": [], "auth": b""}, canonical=True)
    assert len(skeleton) == 43
    key_names = ("v", "t", "src", "base_seq", "n", "recs", "auth")
    # each text key costs 1 length byte + its characters
    assert sum(1 + len(k) for k in key_names) == 29
    assert 29 / len(skeleton) > 0.65, "text keys should dominate the skeleton"
