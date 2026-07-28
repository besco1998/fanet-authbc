"""T6 — the authentication-exclusion threshold (guards optimizer.max_fragments /
max_record_bytes / exclusion_tier, docs/02 §10).

T6 is the LoRa arm's theorem: it says *when a link cannot carry authenticated telemetry at all*,
and it does so without simulating anything. Every expected value below is hand-computed from the
primary constants (RP002-1.0.3 Table 13 payload limits; 64 B Ed25519/ECDSA signatures; the 40 B
AUTHBC frame header, docs/01 §2) rather than by calling the module back on itself (Law 6).
"""

from __future__ import annotations

import math

import pytest

from authbc.models import lora
from authbc.models.optimizer import (
    exclusion_tier,
    max_fragments,
    max_record_bytes,
)

H_F = 44        # AUTHBC frame header — MEASURED from wire.py (B1, docs/01 §2a)
G_A = 64        # Ed25519 / ECDSA-P256 signature (both 64 B; the E1/E3 measured schemes)
S_DELTA_PER_RECORD = 45.0    # measured delta record, 802.11 wire format (E1)
S_DELTA_PER_FRAME = 13.0     # same record minus the 32 B chain hash (F5, adopted on LoRa)


# --- the fragmentation escape is closed by T3 -------------------------------------------------
def test_no_fragmentation_when_epsilon_equals_p() -> None:
    """The load-bearing step: at ε = p the whole verifiability budget is spent on ONE frame.

    V = (1−p)^n ≥ 1−ε with ε = p = 0.05 needs 0.95^n ≥ 0.95, i.e. n ≤ 1. So an oversized auth
    object cannot be split across frames and still verify — which is what makes T6 an exclusion
    rather than an inconvenience.
    """
    assert max_fragments(epsilon=0.05, p_loss=0.05) == 1
    assert 0.95**1 >= 0.95 and 0.95**2 < 0.95


def test_fragment_bound_matches_the_closed_form() -> None:
    """n_max = ⌊ln(1−ε)/ln(1−p)⌋, hand-checked at a looser target."""
    assert math.floor(math.log(0.90) / math.log(0.95)) == 2
    assert max_fragments(epsilon=0.10, p_loss=0.05) == 2
    assert max_fragments(epsilon=0.05, p_loss=0.10) == 0    # unreachable at any n


def test_lossless_link_does_not_bound_fragments() -> None:
    assert max_fragments(epsilon=0.05, p_loss=0.0) > 1_000_000


@pytest.mark.parametrize(("eps", "p"), [(0.05, 1.0), (0.0, 0.05), (1.0, 0.05), (0.05, -0.1)])
def test_fragment_bound_rejects_out_of_range_probabilities(eps: float, p: float) -> None:
    with pytest.raises(ValueError):
        max_fragments(epsilon=eps, p_loss=p)


# --- the threshold itself ---------------------------------------------------------------------
def test_max_record_bytes_is_the_payload_left_after_header_and_signature() -> None:
    assert max_record_bytes(1500, G_A, H_F) == 1500 - 44 - 64          # 802.11: 1392 B of room
    assert max_record_bytes(242, G_A, H_F) == 134                      # LoRa DR4-6
    assert max_record_bytes(115, G_A, H_F) == 7                        # LoRa DR3 — 7 B
    assert max_record_bytes(51, G_A, H_F) == -57                       # LoRa DR0-2 — negative


def test_tier_1_signature_exclusion_on_the_three_longest_range_lora_rates() -> None:
    """DR0/DR1/DR2 carry 51 B (RP002 Table 13); a 64 B signature alone overflows that.

    This is the strongest form of the result: it holds with a **zero-byte header and a zero-byte
    record**, so no encoding, batching, chain placement or framing change can rescue it.
    """
    for dr in (0, 1, 2):
        m = lora.EU868_DATA_RATES[dr].max_app_payload
        assert m == 51
        assert m < G_A, "the signature alone must overflow the frame"
        assert exclusion_tier(m, G_A, H_F, S_DELTA_PER_FRAME) == "signature"
        # and it stays excluded even with a free header and a free record
        assert exclusion_tier(m, G_A, frame_hdr_bytes=0, min_record_bytes=0.0) == "signature"


def test_tier_1_also_excludes_bls_which_is_larger_still() -> None:
    """BLS as measured in P1 is 96 B — worse, not better, on a payload-starved link."""
    assert exclusion_tier(51, auth_bytes=96, frame_hdr_bytes=H_F,
                          min_record_bytes=S_DELTA_PER_FRAME) == "signature"


def test_tier_2_framing_exclusion_is_the_best_case_for_the_smallest_signature() -> None:
    """The cryptographic floor at 128-bit security is a 48 B compressed BLS12-381 G1 point.

    48 B *does* fit DR0-2's 51 B — so tier 1 is escapable in principle — but it leaves **3 B** for
    the header AND the record together. The exclusion moves from "cryptographically impossible" to
    "possible only with a 3-byte frame", which is the honest statement of how tight this is.
    """
    assert exclusion_tier(51, auth_bytes=48, frame_hdr_bytes=H_F,
                          min_record_bytes=S_DELTA_PER_FRAME) == "framing"
    assert max_record_bytes(51, 48, frame_hdr_bytes=0) == 3


def test_tier_3_encoding_exclusion_at_dr3_misses_by_six_bytes() -> None:
    """DR3 (115 B) leaves 7 B for a record; the smallest AUTHBC record is 13 B. Excluded.

    This is the only tier compression can attack, and DR3 is where it comes closest: six bytes.
    """
    m = lora.EU868_DATA_RATES[3].max_app_payload
    assert m == 115
    assert max_record_bytes(m, G_A, H_F) == 7.0
    assert exclusion_tier(m, G_A, H_F, S_DELTA_PER_FRAME) == "encoding"
    assert exclusion_tier(m, G_A, H_F, S_DELTA_PER_RECORD) == "encoding"
    # a 7 B record would clear it — the threshold is exact, not approximate
    assert exclusion_tier(m, G_A, H_F, 7.0) is None


def test_the_fast_lora_rates_and_80211_are_not_excluded() -> None:
    for dr in (4, 5, 6):
        m = lora.EU868_DATA_RATES[dr].max_app_payload
        assert exclusion_tier(m, G_A, H_F, S_DELTA_PER_FRAME) is None
        assert exclusion_tier(m, G_A, H_F, S_DELTA_PER_RECORD) is None
    assert exclusion_tier(1500, G_A, H_F, S_DELTA_PER_RECORD) is None


def test_exclusion_is_exactly_what_the_lora_optimizer_finds_independently() -> None:
    """Cross-check (Law 6): the closed form must agree with the enumerated design space.

    `lora.max_batch_for_mtu` counts how many records actually fit; T6 predicts zero on precisely
    the excluded rates. Two independent routes to the same partition of DR0-6.
    """
    excluded = {dr for dr in range(7)
                if exclusion_tier(lora.EU868_DATA_RATES[dr].max_app_payload, G_A, H_F,
                                  S_DELTA_PER_FRAME) is not None}
    enumerated = {dr for dr in range(7)
                  if lora.max_batch_for_mtu(S_DELTA_PER_FRAME, G_A, H_F, dr) == 0}
    assert excluded == enumerated == {0, 1, 2, 3}
