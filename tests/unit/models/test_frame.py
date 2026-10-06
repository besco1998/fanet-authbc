"""The single frame definition: sizes, verifiability, exclusion (docs/02 T3', T6'; F45–F47)."""

from __future__ import annotations

import cbor2
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from authbc.bench import telemgen
from authbc.crypto.ed25519 import Ed25519Scheme
from authbc.ledger.record import Record
from authbc.models import frame
from authbc.models.energy import Placement
from authbc.models.frame import FlatLayout
from authbc.models.optimizer import bytes_per_record
from authbc.placement import wire_v2
from authbc.placement.framer import measure_frame_header_bytes

_ED = Ed25519Scheme()
_SK, _ = _ED.keygen(seed=bytes(range(32)))

# The byte model of the first format, from the constants the published results always used:
# H_f = 44 B measured on `wire.py`; delta keyframe 59.85 B and delta record 44.0 B, both carrying
# their own 32 B chain link (results/raw/frame_components.csv re-derives the last two).
V1_DELTA = FlatLayout("v1/delta", header_bytes=44, link_bytes=0, key_record_bytes=59.85,
                      delta_record_bytes=44.0)
V1_CBOR = FlatLayout("v1/cbor", header_bytes=44, link_bytes=0, key_record_bytes=66.25,
                     delta_record_bytes=66.25)


def _chained(src: int, base_seq: int, n: int, seed: int) -> list[Record]:
    """`n` consecutive chained records starting at an ARBITRARY base_seq (a mid-flight frame)."""
    recs: list[Record] = []
    ph = bytes([seed % 251]) * 32
    for i, r in enumerate(telemgen.samples(seed=seed, n=n)):
        rec = Record(src=src, seq=base_seq + i, ts=1_000 + 20 * i, prev_hash=ph,
                     pl={k: getattr(r, k) for k in wire_v2.PAYLOAD_FIELDS})
        recs.append(rec)
        ph = rec.record_hash()
    return recs


class TestLeanFrameArithmeticEqualsEmittedFrames:
    """`lean_frame_bytes` is not a model of the lean format; it is its arithmetic."""

    @settings(max_examples=150, deadline=None)
    @given(src=st.integers(0, 65_535), base_seq=st.integers(0, 2**32 - 300),
           n=st.integers(1, 64), seed=st.integers(0, 500), inline=st.booleans())
    def test_for_any_sender_sequence_number_and_batch(self, src: int, base_seq: int, n: int,
                                                      seed: int, inline: bool) -> None:
        recs = _chained(src, base_seq, n, seed)
        built = wire_v2.build_A_v2(recs, _SK) if inline else wire_v2.build_B_v2(recs, _SK)
        data = wire_v2.encode_frame_v2(built)
        stream = len(cbor2.loads(data)[wire_v2.F_RECS])
        assert len(data) == frame.lean_frame_bytes(src=src, base_seq=base_seq, n=n,
                                                   stream_bytes=stream, inline=inline)

    @pytest.mark.parametrize("sig_bytes", [13, 48, 64, 96])
    def test_for_other_authentication_object_sizes(self, sig_bytes: int) -> None:
        recs = _chained(40_000, 180_000, 4, seed=1)
        f = wire_v2.build_B_v2(recs, _SK)
        resized = wire_v2.FrameV2(t=f.t, src=f.src, base_seq=f.base_seq, link=f.link,
                                  recs=f.recs, auth=bytes(sig_bytes))
        data = wire_v2.encode_frame_v2(resized)
        stream = len(cbor2.loads(data)[wire_v2.F_RECS])
        assert len(data) == frame.lean_frame_bytes(src=40_000, base_seq=180_000, n=4,
                                                   stream_bytes=stream, sig_bytes=sig_bytes)

    def test_the_link_field_is_thirty_five_bytes(self) -> None:
        assert len(cbor2.dumps({wire_v2.F_LINK: bytes(32)}, canonical=True)) - 1 \
            == frame.LINK_FIELD_BYTES


class TestTheLeanHeader:
    def test_it_is_23_bytes_where_v1_measures_44(self) -> None:
        """Same sender id and sequence number as the documented v1 measurement (docs/01 §2a)."""
        assert measure_frame_header_bytes(4, src=40_000, base_seq=180_000) == 44
        assert frame.lean_header_bytes(src=40_000, base_seq=180_000, n=4, stream_bytes=50) == 23

    def test_it_is_a_range_just_as_v1_is(self) -> None:
        lo = frame.lean_header_bytes(src=0, base_seq=0, n=4, stream_bytes=50)
        hi = frame.lean_header_bytes(src=65_535, base_seq=2**32 - 300, n=4, stream_bytes=50)
        assert (lo, hi) == (17, 23)

    def test_a_single_short_record_saves_one_more_prefix_byte(self) -> None:
        """CBOR spends one byte, not two, on the length of a stream under 24 bytes."""
        assert frame.lean_header_bytes(src=40_000, base_seq=180_000, n=1, stream_bytes=23) == 22
        assert frame.lean_header_bytes(src=40_000, base_seq=180_000, n=1, stream_bytes=24) == 23

    def test_cbor_integer_widths(self) -> None:
        assert [frame.cbor_uint_bytes(v) for v in (0, 23, 24, 255, 256, 65_535, 65_536,
                                                   2**32 - 1, 2**32)] == [1, 1, 2, 2, 3, 3, 5, 5, 9]
        with pytest.raises(ValueError):
            frame.cbor_uint_bytes(-1)


class TestHeaderFieldByField:
    """The paper's frame table is this breakdown, so it is held to the encoders."""

    @pytest.mark.parametrize(("src", "base_seq"), [(0, 0), (24, 24), (256, 256),
                                                   (40_000, 180_000), (65_535, 4_294_967_000)])
    def test_the_first_formats_fields_sum_to_the_measured_header(self, src: int,
                                                                 base_seq: int) -> None:
        fields = frame.first_header_fields(src=src, base_seq=base_seq, n=4)
        assert sum(fields.values()) == measure_frame_header_bytes(
            4, src=src, base_seq=base_seq)

    def test_the_lean_fields_sum_to_the_lean_header(self) -> None:
        for src, base_seq, n, stream in ((0, 0, 1, 9), (40_000, 180_000, 4, 50), (7, 300, 9, 400)):
            fields = frame.lean_header_fields(src=src, base_seq=base_seq, n=n,
                                                    stream_bytes=stream)
            assert sum(fields.values()) == frame.lean_header_bytes(
                src=src, base_seq=base_seq, n=n, stream_bytes=stream)

    def test_by_hand_at_the_documented_flight_point(self) -> None:
        """'v'→2, 't'→2, 'src'→4, 'base_seq'→9, 'n'→2, 'recs'→5, 'auth'→5 bytes of key name."""
        first = frame.first_header_fields(src=40_000, base_seq=180_000, n=4)
        assert first == {"map": 1, "v": 3, "t": 3, "src": 7, "base_seq": 14, "n": 3, "recs": 6,
                         "auth": 7}
        lean = frame.lean_header_fields(src=40_000, base_seq=180_000, n=4, stream_bytes=50)
        assert lean == {"map": 1, "v": 2, "t": 2, "src": 4, "base_seq": 6, "n": 2, "recs": 3,
                        "auth": 3}

    def test_key_names_are_29_of_the_first_headers_44_bytes_and_7_of_the_lean_23(self) -> None:
        """What `docs/01 §2a` said qualitatively since P3: the header is mostly key names."""
        assert sum(1 + len(k) for k in ("v", "t", "src", "base_seq", "n", "recs", "auth")) == 29
        first = frame.first_header_fields(src=40_000, base_seq=180_000, n=4)
        lean = frame.lean_header_fields(src=40_000, base_seq=180_000, n=4, stream_bytes=50)
        # same values, same prefixes: the whole difference is 22 B of key names less one byte
        # the lean `recs` prefix gains, because its records are a byte string, not an array
        assert sum(first.values()) - sum(lean.values()) == (29 - 7) - 1 == 21


class TestTheFirstFormatsByteModel:
    def test_it_reproduces_the_published_design_as_one_keyframe_per_four_frames(self) -> None:
        """K = 16 records at b = 4 is one self-contained frame in four: 72.0 B/record."""
        assert V1_DELTA.bytes_per_record(64, 4, ref_interval=4) == pytest.approx(71.99, abs=0.01)

    def test_a_self_contained_frame_costs_three_bytes_per_record_more(self) -> None:
        assert V1_DELTA.bytes_per_record(64, 4, ref_interval=1) == pytest.approx(74.96, abs=0.01)
        assert V1_DELTA.frame_bytes(64, 4) == pytest.approx(299.85)

    def test_a_stateless_encoding_matches_the_optimizers_formula(self) -> None:
        for b in (1, 2, 4, 8):
            assert V1_CBOR.bytes_per_record(64, b) == pytest.approx(
                bytes_per_record(Placement.B, b, 66.25, 64, 44, 1))
            assert V1_CBOR.bytes_per_record(64, b, inline=True) == pytest.approx(
                bytes_per_record(Placement.A, b, 66.25, 64, 44, 1))
        assert V1_CBOR.stateless and not V1_DELTA.stateless

    def test_the_reference_interval_does_not_change_a_stateless_encoding(self) -> None:
        assert V1_CBOR.bytes_per_record(64, 4, ref_interval=8) == V1_CBOR.bytes_per_record(64, 4)

    def test_guards(self) -> None:
        with pytest.raises(ValueError, match="batch"):
            V1_DELTA.frame_bytes(64, 0)
        with pytest.raises(ValueError, match="ref_interval"):
            V1_DELTA.mean_frame_bytes(64, 4, ref_interval=0)
        with pytest.raises(ValueError, match="≥ 0"):
            FlatLayout("x", -1, 0, 1, 1)
        with pytest.raises(ValueError, match="cannot be smaller"):
            FlatLayout("x", 1, 0, 1, 2)


class TestVerifiabilityCountsWhatCanBeDecoded:
    def test_one_self_contained_frame_per_frame_is_the_t3_value(self) -> None:
        for p in (0.0, 0.00023, 0.02, 0.05, 0.10):
            assert frame.verifiability(p, 1) == 1.0 - p

    def test_the_published_design_at_its_own_loss_budget(self) -> None:
        """0.95, 0.9025, 0.857375 and 0.81450625 average to 0.8811 — not 0.95."""
        assert frame.verifiability(0.05, 4) == pytest.approx(0.88109, abs=1e-5)

    def test_unbatched_delta_records_with_a_keyframe_every_sixteen(self) -> None:
        """Geometric sum by hand: 19·(1 − 0.95^16)/16 = 19·0.559873/16 = 0.664849."""
        assert frame.verifiability(0.05, 16) == pytest.approx(0.664849, abs=1e-5)

    def test_it_falls_with_the_interval_and_never_exceeds_one_minus_p(self) -> None:
        for p in (0.001, 0.02, 0.05, 0.2):
            vals = [frame.verifiability(p, r) for r in (1, 2, 4, 8, 16)]
            assert vals == sorted(vals, reverse=True)
            assert max(vals) == 1.0 - p

    def test_guards(self) -> None:
        with pytest.raises(ValueError, match="p_loss"):
            frame.verifiability(1.5)
        with pytest.raises(ValueError, match="ref_interval"):
            frame.verifiability(0.05, 0)


class TestBurstLoss:
    def test_bursts_of_the_memoryless_length_reproduce_independent_loss(self) -> None:
        for p in (0.02, 0.05, 0.10):
            for r in (1, 2, 4, 8):
                assert frame.verifiability_gilbert(p, 1.0 / (1.0 - p), r) == pytest.approx(
                    frame.verifiability(p, r), abs=1e-12)

    def test_the_mean_loss_alone_decides_a_frame_independent_design(self) -> None:
        for burst in (1.5, 4.0, 20.0):
            assert frame.verifiability_gilbert(0.05, burst, 1) == pytest.approx(0.95)

    def test_longer_bursts_cost_a_dependent_design_less_but_never_rescue_it(self) -> None:
        vals = [frame.verifiability_gilbert(0.05, burst, 4) for burst in (1.0 / 0.95, 2, 4, 16)]
        assert vals == sorted(vals)
        assert vals[0] == pytest.approx(0.88109, abs=1e-5)
        assert all(v < 0.95 for v in vals)

    def test_guards(self) -> None:
        with pytest.raises(ValueError, match="p_mean"):
            frame.verifiability_gilbert(1.0, 4.0)
        with pytest.raises(ValueError, match="at least one frame"):
            frame.verifiability_gilbert(0.05, 0.5)
        with pytest.raises(ValueError, match="no Gilbert chain"):
            frame.verifiability_gilbert(0.6, 1.0, 2)
        with pytest.raises(ValueError, match="ref_interval"):
            frame.verifiability_gilbert(0.05, 4.0, 0)


class TestTheLargestReferenceInterval:
    CANDIDATES = (1, 2, 4, 8, 16)

    def test_at_its_own_loss_budget_a_design_must_be_frame_independent(self) -> None:
        assert frame.max_ref_interval(0.05, 0.05, self.CANDIDATES) == 1

    def test_a_looser_loss_buys_a_longer_interval(self) -> None:
        assert frame.max_ref_interval(0.02, 0.05, self.CANDIDATES) == 4
        assert frame.max_ref_interval(0.01, 0.05, self.CANDIDATES) == 8
        assert frame.max_ref_interval(0.00023, 0.05, self.CANDIDATES) == 16

    def test_a_loss_above_the_budget_admits_nothing(self) -> None:
        assert frame.max_ref_interval(0.051, 0.05, self.CANDIDATES) == 0

    def test_guard(self) -> None:
        with pytest.raises(ValueError, match="epsilon"):
            frame.max_ref_interval(0.05, 0.0, self.CANDIDATES)


class TestExclusionChargesTheWholeFrame:
    LEAN = FlatLayout("lean", header_bytes=22, link_bytes=35, key_record_bytes=23,
                      delta_record_bytes=9)

    def test_the_tiers_are_nested_and_each_names_what_would_have_to_change(self) -> None:
        assert self.LEAN.exclusion(64, 51) == "signature"
        assert self.LEAN.exclusion(64, 80) == "header"
        assert self.LEAN.exclusion(64, 115) == "chain link"
        assert self.LEAN.exclusion(64, 130) == "record"
        assert self.LEAN.exclusion(64, 144) is None

    def test_the_first_format_fails_dr3_on_the_record_and_by_53_bytes_not_six(self) -> None:
        assert V1_DELTA.exclusion(64, 115) == "record"
        assert V1_DELTA.frame_bytes(64, 1) - 115 == pytest.approx(52.85)

    def test_max_batch(self) -> None:
        assert self.LEAN.max_batch(64, 143) == 0
        assert self.LEAN.max_batch(64, 144) == 1
        assert self.LEAN.max_batch(64, 242) == 1 + (242 - 144) // 9
        assert V1_DELTA.max_batch(64, 1500) == 1 + int((1500 - 167.85) // 44)
        with pytest.raises(ValueError, match="zero-byte record"):
            FlatLayout("x", 1, 0, 0, 0).max_batch(64, 500)
