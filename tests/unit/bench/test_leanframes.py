"""Measured components of the lean frame (docs/04 §2 E6; audit F45, F48)."""

from __future__ import annotations

import pytest

from authbc.bench import leanframes, telemgen
from authbc.crypto.ed25519 import Ed25519Scheme
from authbc.models import frame as frame_model
from authbc.placement import wire_v2

_ED = Ed25519Scheme()
_SK, _ = _ED.keygen(seed=bytes(range(32)))
SEEDS = (1, 2, 3)


class TestTheGeneratorStreamIsSlicedNotRegenerated:
    def test_a_shorter_stream_is_a_prefix_of_a_longer_one(self) -> None:
        """The cache in `generator_records` is only sound because of this."""
        long, short = telemgen.samples(seed=7, n=400), telemgen.samples(seed=7, n=150)
        assert long[:150] == short

    def test_the_cached_stream_equals_a_fresh_one_whatever_was_asked_first(self) -> None:
        leanframes.generator_records(11, 300)          # warm with a longer request
        assert leanframes.generator_records(11, 120) == telemgen.samples(seed=11, n=120)
        assert leanframes.generator_records(11, 700) == telemgen.samples(seed=11, n=700)


class TestChainedRecords:
    def test_they_form_a_valid_chain_at_the_requested_place_in_a_flight(self) -> None:
        recs = leanframes.chained_records(1, 20)
        assert recs[0].src == 40_000 and recs[0].seq == 180_000 and recs[0].ts == 3_600_000
        for prev, cur in zip(recs, recs[1:], strict=False):
            assert cur.seq == prev.seq + 1 and cur.prev_hash == prev.record_hash()

    def test_a_stride_keeps_every_kth_record_of_the_same_stream(self) -> None:
        every = leanframes.chained_records(1, 60)
        third = leanframes.chained_records(1, 20, stride=3)
        assert [dict(r.pl) for r in third] == [dict(r.pl) for r in every[::3]]

    def test_a_stride_below_one_is_refused(self) -> None:
        with pytest.raises(ValueError, match="stride"):
            leanframes.chained_records(1, 10, stride=0)


class TestRecordSizes:
    def test_the_lean_record_is_about_24_bytes_alone_and_9_as_a_difference(self) -> None:
        key, delta = leanframes.lean_record_sizes()
        assert key.mean == pytest.approx(24.0, abs=0.05) and (key.lo, key.hi) == (21, 25)
        assert (delta.mean, delta.lo, delta.hi) == (9.0, 9, 9)
        assert key.n == 30_000 and delta.n == 29_970

    def test_the_first_formats_delta_encoder_reproduces_its_published_sizes(self) -> None:
        """59.85 and 44.0 average to the 45.0 B the byte results used (K = 16)."""
        key, delta = leanframes.v1_delta_record_sizes()
        assert key.mean == pytest.approx(59.85, abs=0.01) and delta.mean == 44.0
        assert (key.mean + 15 * delta.mean) / 16 == pytest.approx(45.0, abs=0.01)

    def test_a_delta_grows_with_the_time_between_records(self) -> None:
        """The defect behind F48: a difference is not a constant of the encoder."""
        sizes = [leanframes.lean_record_sizes(SEEDS, 64, stride=k)[1].mean
                 for k in (1, 2, 20, 110, 330)]
        assert sizes == sorted(sizes) and sizes[0] == 9.0 and sizes[-1] > 15.0

    def test_a_keyframe_does_not(self) -> None:
        sizes = [leanframes.lean_record_sizes(SEEDS, 64, stride=k)[0].mean for k in (1, 20, 330)]
        assert max(sizes) - min(sizes) < 0.5

    def test_a_keyframe_grows_with_the_flight_through_its_timestamp(self) -> None:
        """A millisecond timestamp is a 2-byte varint in the first 16 s and 4 bytes after 35 min.

        (The 30-seed protocol runs 50 s per stream, so its time-zero keyframe mixes 2- and 3-byte
        timestamps and sits 1.3 B, not 2 B, under the one-hour figure.)
        """
        early, _ = leanframes.lean_record_sizes(SEEDS, 200, ts0=0)      # first 10 s
        late, _ = leanframes.lean_record_sizes(SEEDS, 200)             # one hour in
        assert 2.0 <= late.mean - early.mean < 2.1


class TestFrameSizes:
    def test_the_design_frame_is_173_bytes_and_the_one_record_frame_146(self) -> None:
        assert leanframes.lean_frame_sizes(4).mean == pytest.approx(173.0, abs=0.01)
        assert leanframes.lean_frame_sizes(1).mean == pytest.approx(145.77, abs=0.01)

    def test_a_frame_has_the_same_length_whatever_its_signature_says(self) -> None:
        recs = leanframes.chained_records(1, 4)
        signed = len(wire_v2.encode_frame_v2(wire_v2.build_B_v2(recs, _SK)))
        assert signed == leanframes.lean_frame_sizes(4, seeds=(1,), n=4).lo

    def test_a_longer_reference_interval_shrinks_the_mean_frame_only(self) -> None:
        alone = leanframes.lean_frame_sizes(4, 1, seeds=SEEDS, n=160)
        grouped = leanframes.lean_frame_sizes(4, 4, seeds=SEEDS, n=160)
        assert grouped.mean < alone.mean and grouped.hi == alone.hi
        # three frames in four swap a keyframe for a 9 B delta
        key, delta = leanframes.lean_record_sizes(SEEDS, 160)
        assert alone.mean - grouped.mean == pytest.approx(0.75 * (key.mean - delta.mean), abs=0.2)

    def test_inline_frames_cost_a_signature_and_its_framing_per_record(self) -> None:
        batch = leanframes.lean_frame_sizes(4, seeds=SEEDS, n=160).mean
        inline = leanframes.lean_frame_sizes(4, inline=True, seeds=SEEDS, n=160).mean
        assert inline - batch == pytest.approx(3 * 64 + 7, abs=0.01)

    def test_guards(self) -> None:
        with pytest.raises(ValueError, match="≥ 1"):
            leanframes.lean_frame_sizes(0)
        with pytest.raises(ValueError, match="self-contained"):
            leanframes.lean_frame_sizes(4, 2, inline=True)


class TestTheAdditiveLayout:
    def test_it_matches_emitted_frames_for_batches_of_two_and_more(self) -> None:
        layout = leanframes.lean_layout()
        for b in (2, 4, 5, 8):
            assert layout.frame_bytes(64, b) == pytest.approx(
                leanframes.lean_frame_sizes(b).mean, abs=0.01)

    def test_it_is_within_a_byte_for_a_single_record_and_never_low(self) -> None:
        """A stream under 24 B takes a one-byte length prefix; the layout assumes two."""
        gap = leanframes.lean_layout().frame_bytes(64, 1) - leanframes.lean_frame_sizes(1).mean
        assert 0.0 <= gap < 1.0

    def test_its_header_and_link_are_the_wire_formats(self) -> None:
        layout = leanframes.lean_layout()
        assert layout.header_bytes == 23 and layout.link_bytes == frame_model.LINK_FIELD_BYTES

    def test_the_first_formats_layout_carries_no_separate_link(self) -> None:
        layout = leanframes.v1_delta_layout()
        assert layout.header_bytes == 44 and layout.link_bytes == 0
        assert layout.frame_bytes(64, 4) == pytest.approx(299.85, abs=0.01)
