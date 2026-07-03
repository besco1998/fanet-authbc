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
