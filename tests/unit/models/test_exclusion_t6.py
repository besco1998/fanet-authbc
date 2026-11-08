"""T6' — which links cannot carry one self-contained authenticated frame (docs/02 §10).

T6 is the low-rate arm's theorem: it says *when a link cannot carry authenticated, hash-chained
telemetry at all*, and it does so without simulating anything. Its size half is the one frame
definition of `models/frame.py`; its other half is the fragmentation bound, which stays in
`models/optimizer.py`.

⚠️ **What this file used to assert, kept visible (audit F47, 2026-10).** Until then T6 was
``s_max = M − H_f − g_a`` compared with a 13 B "smallest record", and these tests held that DR3
"misses by six bytes" (115 − 44 − 64 = 7 < 13) and — in `tests/test_wire_profile.py`, now removed —
that an integer-keyed header "rescues" it (115 − 22 − 64 = 29 ≥ 13). Two things were never
charged: the chain link that per-frame chaining puts in every frame, and a record that decodes
without its predecessor (13 B was the *mean delta* record with its link subtracted). Charged, DR3
is excluded under either header, and not narrowly. `TestTheWithdrawnArithmetic` pins the old
numbers beside the frames that contradict them, so the calculation cannot quietly come back.

Expected values are hand-computed from RP002-1.0.3 payload limits and CBOR encoding rules, and
checked against frames the encoder actually emits (Law 6).
"""

from __future__ import annotations

import math

import pytest

from authbc.bench import leanframes
from authbc.crypto.ed25519 import Ed25519Scheme
from authbc.ledger.record import Record
from authbc.models import lora
from authbc.models.frame import LINK_FIELD_BYTES, FlatLayout, lean_frame_bytes
from authbc.models.optimizer import max_fragments
from authbc.placement import wire_v2

G_A = 64                 # Ed25519 / ECDSA-P256
# The lean format with every integer at its minimum width: node 0, sequence 0, one record of
# zeros. Header = map 1 + five one-byte keys and values 10 + `recs` key and prefix 2 + `auth` key
# and prefix 3 = 16 B. No telemetry and no moment of a flight produces a smaller frame.
LEAN_FLOOR = FlatLayout("lean, floor", header_bytes=16, link_bytes=LINK_FIELD_BYTES,
                        key_record_bytes=9, delta_record_bytes=9)
SIGNATURE_ALONE = {0, 1, 2, 8, 10}       # payload 50 or 51 B
BY_COMPOSITION = {3, 9, 11}              # payload 115 B
FEASIBLE = {4, 5, 6, 7}                  # payload 222 or 242 B


# --- the fragmentation escape is closed by T3 -------------------------------------------------
def test_no_fragmentation_when_epsilon_equals_p() -> None:
    """The load-bearing step: at ε = p the whole verifiability budget is spent on ONE frame.

    V = (1−p)^n ≥ 1−ε with ε = p = 0.05 needs 0.95^n ≥ 0.95, i.e. n ≤ 1. So an oversized auth
    object cannot be split across frames and still verify — which is what makes T6 an exclusion
    rather than an inconvenience. It is also T6's first scope condition: at p well below ε the
    bound loosens (see the next test) and fragmentation is an escape again.
    """
    assert max_fragments(epsilon=0.05, p_loss=0.05) == 1
    assert 0.95**1 >= 0.95 and 0.95**2 < 0.95


def test_fragment_bound_matches_the_closed_form() -> None:
    """n_max = ⌊ln(1−ε)/ln(1−p)⌋, hand-checked at a looser target and at a cleaner link."""
    assert math.floor(math.log(0.90) / math.log(0.95)) == 2
    assert max_fragments(epsilon=0.10, p_loss=0.05) == 2
    assert max_fragments(epsilon=0.05, p_loss=0.01) == 5     # ε ≫ p: the exclusion's scope ends
    assert max_fragments(epsilon=0.05, p_loss=0.10) == 0     # unreachable at any n


def test_lossless_link_does_not_bound_fragments() -> None:
    assert max_fragments(epsilon=0.05, p_loss=0.0) > 1_000_000


@pytest.mark.parametrize(("eps", "p"), [(0.05, 1.0), (0.0, 0.05), (1.0, 0.05), (0.05, -0.1)])
def test_fragment_bound_rejects_out_of_range_probabilities(eps: float, p: float) -> None:
    with pytest.raises(ValueError):
        max_fragments(epsilon=eps, p_loss=p)


# --- the size half ----------------------------------------------------------------------------
class TestTheSmallestFrameTheFormatCanEmit:
    def test_the_floor_layout_is_the_arithmetic_of_a_real_frame(self) -> None:
        assert LEAN_FLOOR.frame_bytes(G_A, 1) == 124 == lean_frame_bytes(
            src=0, base_seq=0, n=1, stream_bytes=9)

    def test_and_that_frame_is_emitted_signed_and_verified(self) -> None:
        sk, pk = Ed25519Scheme().keygen(seed=bytes(32))
        zero = Record(src=0, seq=0, ts=0, prev_hash=bytes(32),
                      pl=dict.fromkeys(wire_v2.PAYLOAD_FIELDS, 0))
        data = wire_v2.encode_frame_v2(wire_v2.build_B_v2([zero], sk))
        assert len(data) == 124 and wire_v2.verify_v2(wire_v2.decode_frame_v2(data), pk)

    def test_header_link_and_signature_alone_are_the_whole_115_byte_payload(self) -> None:
        """16 + 35 + 64 = 115: on DR3, DR9 and DR11 not one byte is left for a record."""
        assert LEAN_FLOOR.header_bytes + LEAN_FLOOR.link_bytes + G_A == 115
        assert LEAN_FLOOR.exclusion(G_A, 115) == "record"
        assert LEAN_FLOOR.exclusion(G_A, 123) == "record" and LEAN_FLOOR.exclusion(G_A, 124) is None

    def test_at_any_real_header_the_chain_link_already_overflows(self) -> None:
        """One byte of node id or sequence number beyond the floor, and the link no longer fits."""
        real = FlatLayout("lean", header_bytes=17, link_bytes=LINK_FIELD_BYTES,
                          key_record_bytes=19, delta_record_bytes=9)
        assert real.exclusion(G_A, 115) == "chain link"


class TestTwelveDataRates:
    """RP002-1.0.3 Tables 12 and 13 define twelve EU863-870 data rates, not the seven of SF7–12."""

    def test_the_payload_limits(self) -> None:
        limits = {dr: lim.n_not_repeater for dr, lim in lora.EU868_PAYLOAD_LIMITS.items()}
        assert {dr for dr, n in limits.items() if n in (50, 51)} == SIGNATURE_ALONE
        assert {dr for dr, n in limits.items() if n == 115} == BY_COMPOSITION
        assert {dr for dr, n in limits.items() if n == 242} == FEASIBLE
        assert len(limits) == 12

    def test_a_64_byte_signature_alone_overflows_five(self) -> None:
        """The strongest form: it holds with a zero-byte header and no record at all."""
        empty = FlatLayout("nothing but a signature", 0, 0, 0, 0)
        for dr in SIGNATURE_ALONE:
            limit = lora.EU868_PAYLOAD_LIMITS[dr].n_not_repeater
            assert limit < G_A and empty.exclusion(G_A, limit) == "signature"
            assert LEAN_FLOOR.exclusion(96, limit) == "signature"       # BLS, 96 B: worse

    def test_three_more_are_excluded_by_what_a_frame_must_contain(self) -> None:
        for dr in BY_COMPOSITION:
            limit = lora.EU868_PAYLOAD_LIMITS[dr].n_not_repeater
            assert LEAN_FLOOR.exclusion(G_A, limit) == "record"
            assert LEAN_FLOOR.frame_bytes(G_A, 1) - limit == 9

    def test_four_are_feasible_under_either_payload_table(self) -> None:
        for dr in FEASIBLE:
            lim = lora.EU868_PAYLOAD_LIMITS[dr]
            assert (lim.n_not_repeater, lim.n_repeater) == (242, 222)
            assert LEAN_FLOOR.exclusion(G_A, lim.n_repeater) is None
        assert leanframes.lean_frame_sizes(1).hi <= 222       # every emitted one-record frame

    def test_the_count_is_eight_of_twelve(self) -> None:
        excluded = {dr for dr, lim in lora.EU868_PAYLOAD_LIMITS.items()
                    if LEAN_FLOOR.exclusion(G_A, lim.n_not_repeater) is not None}
        assert excluded == SIGNATURE_ALONE | BY_COMPOSITION and len(excluded) == 8


class TestWhatEachRelaxationBuys:
    def test_taking_the_chain_link_off_the_air_frees_the_115_byte_rates_only(self) -> None:
        unchained = FlatLayout("lean, no on-air link", 16, 0, 9, 9)
        assert unchained.frame_bytes(G_A, 1) == 124 - LINK_FIELD_BYTES == 89
        assert unchained.exclusion(G_A, 115) is None
        assert unchained.exclusion(G_A, 51) == "signature"

    def test_the_smallest_standard_signature_fits_51_bytes_and_leaves_three(self) -> None:
        """48 B (BLS12-381, minimal-signature-size) clears the signature tier and no other."""
        assert LEAN_FLOOR.exclusion(48, 51) == "header" and 51 - 48 == 3

    def test_with_it_a_frame_of_zeros_would_fit_115_bytes_but_real_telemetry_does_not(self) -> None:
        """⚠️ A three-byte miss is not an exclusion; it is recorded as what it is."""
        assert LEAN_FLOOR.frame_bytes(48, 1) == 108 <= 115
        assert leanframes.lean_frame_sizes(1, src=0, base_seq=0, ts0=0, sig_bytes=48).lo == 118

    def test_a_chained_frame_does_not_fit_51_bytes_under_any_authenticator(self) -> None:
        """Header and link are 51 B before any tag or record: chaining itself is excluded there."""
        assert LEAN_FLOOR.header_bytes + LEAN_FLOOR.link_bytes == 51
        for tag in (13, 8, 1):
            assert LEAN_FLOOR.exclusion(tag, 51) in ("header", "chain link")


class TestTheWithdrawnArithmetic:
    """The calculation F47 retracts, held beside the frames that contradict it."""

    def test_the_old_bound_and_what_it_left_out(self) -> None:
        old_room_first, old_room_lean, old_smallest_record = 115 - 44 - 64, 115 - 22 - 64, 13
        assert (old_room_first, old_room_lean) == (7, 29)
        # the old verdicts: excluded "by six bytes" under the first header, feasible under a lean
        assert old_room_first < old_smallest_record <= old_room_lean
        # what was left out: the link every frame must carry, and a record that decodes alone
        key, delta = leanframes.lean_record_sizes()
        assert delta.lo == 9 and key.lo == 21                 # a keyframe is not a 13 B record
        assert old_room_lean - LINK_FIELD_BYTES < 0           # the link alone overruns the room

    def test_no_emitted_frame_of_either_format_fits_115_bytes(self) -> None:
        lean = leanframes.lean_frame_sizes(1, src=0, base_seq=0, ts0=0)
        assert lean.lo == 134 > 115
        key, _ = leanframes.v1_delta_record_sizes()
        assert 38 + G_A + key.lo == 158 > 115                 # first format, smallest header

    def test_the_first_format_misses_without_any_header_at_all(self) -> None:
        """So its exclusion never turned on H_f, as the audit of 2026-08 believed (A3, F43)."""
        key, _ = leanframes.v1_delta_record_sizes()
        assert G_A + key.lo == 120 > 115
