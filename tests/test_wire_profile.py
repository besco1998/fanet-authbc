"""M5/F44 — the exclusion bound depends on a header this thesis declines to optimise.

⚠️ This file exists to make one uncomfortable consequence unmissable: `docs/01 §2a` has always
said the frame header is mostly CBOR text key names and that an integer-keyed profile "would
shrink substantially", while `docs/02` T6 claims an exclusion bound that *depends on that header*.
Putting the two together costs the paper its fourth excluded EU868 data rate.

Expected values are hand-derived from canonical CBOR encoding rules, not by calling the module
back on itself (docs/05 §9): an unsigned integer 0..23 encodes in one byte; a text string of
length n encodes in 1 + n bytes.
"""

from __future__ import annotations

import pytest

from authbc.models import lora
from authbc.models.optimizer import exclusion_tier, max_record_bytes
from authbc.placement import framer
from authbc.placement import wire_profile as wp

G_A = 64.0                 # Ed25519 / ECDSA-P256
DR3_PAYLOAD = 115          # RP002-1.0.3 Table 13
S_MIN_PUBLISHED = 13.0     # the 45 B delta record minus its 32 B chain link (docs/02 §9b)


class TestKeyNamesAreTheHeader:
    def test_text_keys_cost_29_bytes_and_integer_keys_cost_7(self) -> None:
        """Hand-derived: 'v'->2, 't'->2, 'src'->4, 'base_seq'->9, 'n'->2, 'recs'->5, 'auth'->5."""
        assert 2 + 2 + 4 + 9 + 2 + 5 + 5 == 29
        assert wp.key_name_cost() == (29, 7)

    def test_that_saving_is_most_of_the_header(self) -> None:
        cur = wp.current_profile(4)
        assert cur.h_f == framer.H_F == 44
        text, ints = wp.key_name_cost()
        assert (text - ints) / cur.h_f > 0.45, "key names are less than half the header"


class TestTheLeanProfileHalvesTheHeader:
    def test_integer_keys_alone_take_h_f_from_44_to_22(self) -> None:
        assert wp.current_profile(4).h_f == 44
        assert wp.lean_profile(4, elide_redundant=False).h_f == 22

    def test_eliding_redundant_fields_saves_ten_bytes_per_record(self) -> None:
        """`src` and `seq` are derivable from the frame's `src` and `base_seq` + index in B."""
        keep = wp.lean_profile(4, elide_redundant=False)
        elide = wp.lean_profile(4)
        assert keep.h_f == elide.h_f == 22, "eliding record fields must not move H_f"
        per_record = (keep.record_bytes_total - elide.record_bytes_total) / 4
        assert per_record == 10.0

    def test_the_two_mechanisms_are_attributed_separately(self) -> None:
        """Reported as two numbers, not one lump, so each can be argued with on its own."""
        cur, keys, lean = (wp.current_profile(4),
                           wp.lean_profile(4, elide_redundant=False),
                           wp.lean_profile(4))
        assert cur.bytes_per_record > keys.bytes_per_record > lean.bytes_per_record


class TestTheHeadlineMovesFromFourToThree:
    """⚠️ THE finding. Read the reasoning before changing any expected value here."""

    def test_dr3_is_excluded_under_the_published_profile(self) -> None:
        h_f = wp.current_profile(4).h_f
        assert max_record_bytes(DR3_PAYLOAD, G_A, h_f) == 7.0
        assert exclusion_tier(DR3_PAYLOAD, G_A, h_f, S_MIN_PUBLISHED) == "encoding"

    def test_dr3_becomes_FEASIBLE_under_integer_keys_alone(self) -> None:
        """Not even the record elision is needed — halving the header is enough."""
        h_f = wp.lean_profile(4, elide_redundant=False).h_f
        assert max_record_bytes(DR3_PAYLOAD, G_A, h_f) == 29.0
        assert exclusion_tier(DR3_PAYLOAD, G_A, h_f, S_MIN_PUBLISHED) is None

    def test_the_count_goes_from_four_of_seven_to_three_of_seven(self) -> None:
        def excluded(h_f: float, s_min: float) -> int:
            return sum(1 for dr in range(7)
                       if exclusion_tier(lora.EU868_DATA_RATES[dr].max_app_payload,
                                         G_A, h_f, s_min))

        assert excluded(wp.current_profile(4).h_f, S_MIN_PUBLISHED) == 4
        assert excluded(wp.lean_profile(4, elide_redundant=False).h_f, S_MIN_PUBLISHED) == 3
        assert excluded(wp.lean_profile(4).h_f, float(wp.smallest_record_bytes())) == 3


class TestWhatSurvivesRegardless:
    """The half of the claim no framing work can touch — and the half worth leading with."""

    @pytest.mark.parametrize("h_f", [0, 10, 22, 38, 44, 100])
    @pytest.mark.parametrize("dr", [0, 1, 2])
    def test_dr0_to_dr2_stay_excluded_at_any_header_and_a_one_byte_record(
            self, h_f: int, dr: int) -> None:
        """M = 51 B < g_a = 64 B: the SIGNATURE ALONE overflows the payload."""
        m = lora.EU868_DATA_RATES[dr].max_app_payload
        assert m == 51
        assert exclusion_tier(m, G_A, h_f, 1.0) == "signature"

    def test_even_the_smallest_standardised_signature_barely_fits(self) -> None:
        """48 B compressed BLS12-381 G1 (draft-irtf-cfrg-bls-signature-05) at 126-bit security."""
        assert exclusion_tier(51, 48.0, 0.0, 1.0) is None
        assert max_record_bytes(51, 48.0, 0.0) == 3.0

    def test_dr4_to_dr6_were_never_in_question(self) -> None:
        for dr in (4, 5, 6):
            m = lora.EU868_DATA_RATES[dr].max_app_payload
            assert exclusion_tier(m, G_A, 44.0, S_MIN_PUBLISHED) is None


class TestTheFrozenFormatIsUntouched:
    """⚠️ D6. This module measures an alternative; it must never become the shipped format."""

    def test_the_model_constant_and_the_shipped_wire_are_unchanged(self) -> None:
        assert framer.H_F == 44
        assert framer.measure_frame_header_bytes(4) == 44
        assert wp.current_profile(4).h_f == 44

    def test_the_lean_profile_is_not_importable_from_the_wire_module(self) -> None:
        from authbc.placement import wire
        assert not hasattr(wire, "lean_profile")
