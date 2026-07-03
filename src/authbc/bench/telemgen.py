"""Seeded synthetic telemetry generator (docs/04 §1, docs/01 §1 "Traffic").

Produces INTEGER-ONLY records — floats break canonical-CBOR determinism across platforms
(docs/06 §5), so every telemetry quantity is fixed-point. Records form a coherent, seeded
random-walk trajectory so the delta encoder (encodings/delta_enc) sees realistic small
field-to-field deltas rather than noise. Deterministic: same seed ⇒ identical stream.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from random import Random

# Field bounds — single source of truth for schema validation. Telemetry uses fixed-point
# integers with the scales documented in docs/01 §1 and the P1 prompt.
U8: tuple[int, int] = (0, 2**8 - 1)
U16: tuple[int, int] = (0, 2**16 - 1)
U32: tuple[int, int] = (0, 2**32 - 1)
I16: tuple[int, int] = (-(2**15), 2**15 - 1)
I32: tuple[int, int] = (-(2**31), 2**31 - 1)

LAT_RANGE: tuple[int, int] = (-900_000_000, 900_000_000)  # ±90.0° at 1e-7 deg (fits i32)
LON_RANGE: tuple[int, int] = (-1_800_000_000, 1_800_000_000)  # ±180.0° at 1e-7 deg (fits i32)
ALT_RANGE: tuple[int, int] = (-50_000, 5_000_000)  # cm: −500 m … 50 km
VEL_RANGE: tuple[int, int] = (-3_000, 3_000)  # cm/s: ±30 m/s (well within i16)
BATTERY_RANGE: tuple[int, int] = (0, 100)  # percent
N_MODES: int = 8  # flight-mode enum cardinality (mode ∈ [0, N_MODES-1])

PREV_HASH_LEN: int = 32  # SHA-256 output width (bytes)
TS_STEP_MS: int = 50  # nominal 20 rec/s inter-arrival (docs/01 §1 default Λ = 20 rec/s)

# Canonical field order — used by the delta encoder and by every determinism check.
FIELD_ORDER: tuple[str, ...] = (
    "src",
    "seq",
    "ts",
    "prev_hash",
    "lat",
    "lon",
    "alt",
    "vel_x",
    "vel_y",
    "vel_z",
    "battery",
    "mode",
)

# Integer fields only (everything except the 32-byte prev_hash), in canonical order — this
# is exactly the set the delta encoder takes zigzag-varint deltas over.
INT_FIELD_ORDER: tuple[str, ...] = tuple(f for f in FIELD_ORDER if f != "prev_hash")

_RANGES: dict[str, tuple[int, int]] = {
    "src": U16,
    "seq": U32,
    "ts": U32,
    "lat": LAT_RANGE,
    "lon": LON_RANGE,
    "alt": ALT_RANGE,
    "vel_x": I16,
    "vel_y": I16,
    "vel_z": I16,
    "battery": BATTERY_RANGE,
    "mode": (0, N_MODES - 1),
}


@dataclass(frozen=True, slots=True)
class TelemetryRecord:
    """One UAV telemetry record (docs/01 §1). All quantities are integers; ``prev_hash`` is
    exactly 32 bytes (SHA-256 of the previous record — the real chain is built in P2; here it
    is seeded random so encoders see a realistic incompressible field)."""

    src: int
    seq: int
    ts: int
    prev_hash: bytes
    lat: int
    lon: int
    alt: int
    vel_x: int
    vel_y: int
    vel_z: int
    battery: int
    mode: int

    def as_dict(self) -> dict[str, int | bytes]:
        """Field→value mapping in canonical order (drives encoders + determinism checks)."""
        return {f: getattr(self, f) for f in FIELD_ORDER}


def _clamp(value: int, bounds: tuple[int, int]) -> int:
    lo, hi = bounds
    return lo if value < lo else hi if value > hi else value


def validate(rec: TelemetryRecord) -> None:
    """Raise ``ValueError``/``TypeError`` if ``rec`` violates the integer schema (docs/01 §1).

    Used by the property test and as a cheap invariant guard; keeps floats and out-of-range
    values from silently entering the encoders/benchmarks.
    """
    if not isinstance(rec.prev_hash, bytes) or len(rec.prev_hash) != PREV_HASH_LEN:
        raise ValueError(f"prev_hash must be {PREV_HASH_LEN} bytes, got {rec.prev_hash!r}")
    for field, bounds in _RANGES.items():
        val = getattr(rec, field)
        if isinstance(val, bool) or not isinstance(val, int):  # bool is an int subclass
            raise TypeError(f"{field} must be a non-bool int, got {type(val).__name__}")
        lo, hi = bounds
        if not (lo <= val <= hi):
            raise ValueError(f"{field}={val} out of range [{lo}, {hi}]")


def stream(seed: int, n: int, *, src: int = 1) -> Iterator[TelemetryRecord]:
    """Yield ``n`` schema-valid records as a seeded random-walk trajectory from ``src``.

    The walk takes small per-step increments (realistic UAV motion) so consecutive records
    differ by small deltas; ``seq`` increments by 1 and ``ts`` by ~50 ms. ``prev_hash`` is
    fresh seeded-random 32 bytes per record (incompressible — encoders must carry it fully).
    """
    if n < 0:
        raise ValueError("n must be >= 0")
    if not (U16[0] <= src <= U16[1]):
        raise ValueError(f"src out of u16 range: {src}")
    rng = Random(seed)

    lat = rng.randint(LAT_RANGE[0] // 2, LAT_RANGE[1] // 2)
    lon = rng.randint(LON_RANGE[0] // 2, LON_RANGE[1] // 2)
    alt = rng.randint(0, ALT_RANGE[1] // 10)
    vel_x = rng.randint(-500, 500)
    vel_y = rng.randint(-500, 500)
    vel_z = rng.randint(-200, 200)
    battery = 100
    mode = rng.randint(0, N_MODES - 1)
    ts = rng.randint(0, 10_000)

    for i in range(n):
        # integrate velocity (cm/s) over ~50 ms and jitter it slightly — small, realistic deltas
        lat = _clamp(lat + vel_x // 20 + rng.randint(-2, 2), LAT_RANGE)
        lon = _clamp(lon + vel_y // 20 + rng.randint(-2, 2), LON_RANGE)
        alt = _clamp(alt + vel_z // 20 + rng.randint(-1, 1), ALT_RANGE)
        vel_x = _clamp(vel_x + rng.randint(-10, 10), VEL_RANGE)
        vel_y = _clamp(vel_y + rng.randint(-10, 10), VEL_RANGE)
        vel_z = _clamp(vel_z + rng.randint(-5, 5), VEL_RANGE)
        battery = _clamp(battery - (1 if rng.random() < 0.02 else 0), BATTERY_RANGE)
        if rng.random() < 0.01:
            mode = rng.randint(0, N_MODES - 1)
        ts = _clamp(ts + TS_STEP_MS + rng.randint(-3, 3), U32)

        rec = TelemetryRecord(
            src=src,
            seq=i,
            ts=ts,
            prev_hash=bytes(rng.randrange(256) for _ in range(PREV_HASH_LEN)),
            lat=lat,
            lon=lon,
            alt=alt,
            vel_x=vel_x,
            vel_y=vel_y,
            vel_z=vel_z,
            battery=battery,
            mode=mode,
        )
        yield rec


def samples(seed: int, n: int, *, src: int = 1) -> list[TelemetryRecord]:
    """Materialize ``stream`` into a list (convenience for encoders/benchmarks)."""
    return list(stream(seed, n, src=src))
