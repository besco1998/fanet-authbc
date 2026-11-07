"""Schema-conformance + determinism tests for the seeded telemetry generator (docs/04 §1)."""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from authbc.bench import telemgen
from authbc.bench.telemgen import PREV_HASH_LEN, TelemetryRecord, validate


def test_1000_samples_conform() -> None:
    """The 1000-sample schema check mandated by the P1 prompt (step 1)."""
    recs = telemgen.samples(seed=1, n=1000, src=7)
    assert len(recs) == 1000
    for i, rec in enumerate(recs):
        validate(rec)  # raises on any schema violation
        assert rec.seq == i
        assert rec.src == 7
        assert isinstance(rec.prev_hash, bytes) and len(rec.prev_hash) == PREV_HASH_LEN


def test_determinism_same_seed() -> None:
    """Same seed ⇒ byte-identical stream (a determinism failure here is a STOP, Law 3)."""
    a = telemgen.samples(seed=42, n=500)
    b = telemgen.samples(seed=42, n=500)
    assert a == b
    assert a[0].prev_hash == b[0].prev_hash


def test_different_seeds_differ() -> None:
    a = telemgen.samples(seed=1, n=100)
    b = telemgen.samples(seed=2, n=100)
    assert a != b


def test_walk_deltas_are_small() -> None:
    """Consecutive lat/lon deltas stay small — this is what makes delta-encoding pay (T1)."""
    recs = telemgen.samples(seed=3, n=1000)
    max_dlat = max(abs(recs[i + 1].lat - recs[i].lat) for i in range(len(recs) - 1))
    assert max_dlat < 10_000  # « the ~1.8e9 lon span → deltas are tiny varints


@settings(max_examples=200)
@given(seed=st.integers(min_value=0, max_value=2**31 - 1), n=st.integers(min_value=0, max_value=64))
def test_property_all_conform(seed: int, n: int) -> None:
    recs = telemgen.samples(seed=seed, n=n)
    assert len(recs) == n
    for rec in recs:
        validate(rec)


def test_validate_rejects_float_and_out_of_range() -> None:
    good = telemgen.samples(seed=5, n=1)[0]
    validate(good)
    # bool is an int subclass — must be rejected
    bad_bool = TelemetryRecord(**{**good.as_dict(), "mode": True})  # type: ignore[arg-type]
    try:
        validate(bad_bool)
    except TypeError:
        pass
    else:  # pragma: no cover
        raise AssertionError("bool mode should be rejected")
    bad_range = TelemetryRecord(**{**good.as_dict(), "battery": 250})  # type: ignore[arg-type]
    try:
        validate(bad_range)
    except ValueError:
        pass
    else:  # pragma: no cover
        raise AssertionError("battery=250 should be rejected")
    bad_hash = TelemetryRecord(**{**good.as_dict(), "prev_hash": b"\x00" * 16})  # type: ignore[arg-type]
    try:
        validate(bad_hash)
    except ValueError:
        pass
    else:  # pragma: no cover
        raise AssertionError("16-byte prev_hash should be rejected")


# --------------------------------------------------------------------------- record spacing
# Added 2026-10-08. Every published size comes from records 50 ms apart, the spacing of the
# 20 records/s point the generator was written for, while the adopted operating point is
# 50 records/s — 20 ms. The paper says the delta record is no larger there. These tests are
# that sentence.
def test_the_default_stream_is_unchanged_by_the_spacing_parameter() -> None:
    """Digest of the first 200 records of seed 1, taken from the generator before `step_ms`."""
    import dataclasses
    import hashlib

    fields = [dataclasses.astuple(r) for r in telemgen.samples(1, 200)]
    assert hashlib.sha256(repr(fields).encode()).hexdigest() == (
        "1366282c6710386ad0aa2e8e82c2149ebd597a592e4149b48c0a6bee71e24755")
    assert telemgen.samples(1, 200) == telemgen.samples(1, 200, step_ms=telemgen.TS_STEP_MS)


def _lean_delta_sizes(step_ms: int) -> set[int]:
    from authbc.ledger.record import Record
    from authbc.placement import wire_v2

    sizes: set[int] = set()
    for seed in range(1, 31):
        raw = telemgen.samples(seed, 1000, step_ms=step_ms)
        recs = [Record(src=40_000, seq=180_000 + i, ts=3_600_000 + r.ts - raw[0].ts,
                       prev_hash=bytes(32), pl={k: getattr(r, k) for k in wire_v2.PAYLOAD_FIELDS})
                for i, r in enumerate(raw)]
        sizes |= {len(wire_v2.record_stream([r], p)) for p, r in zip(recs, recs[1:], strict=False)}
    return sizes


def test_the_delta_record_is_at_the_floor_at_the_published_spacing() -> None:
    assert _lean_delta_sizes(50) == {9}


def test_the_delta_record_is_no_larger_at_the_spacing_of_the_operating_point() -> None:
    """20 ms: 50 records/s. Nine fields, one byte each — the floor of the format."""
    assert _lean_delta_sizes(20) == {9}


def test_spacing_must_be_a_sensible_number_of_milliseconds() -> None:
    import pytest

    for bad in (0, -5, 1001):
        with pytest.raises(ValueError, match="step_ms"):
            next(telemgen.stream(1, 1, step_ms=bad))
