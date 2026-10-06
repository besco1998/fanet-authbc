"""Measured components of the lean frame (docs/04 §2 E6; docs/01 §4b; audit F45, F48).

Every size the lean design reports comes from here, and every one is the length of a `wire_v2`
frame or record stream that was actually encoded. Nothing in this module is a model.

Three conventions are fixed here so that they are stated once.

* **Where in a flight.** Canonical CBOR integers and varints grow with magnitude, so a header or a
  keyframe has no single size (audit F43b). Sizes are reported at the point docs/01 §2a already
  used for the v1 header — sender id 40 000, one hour into a 50 Hz flight (sequence number
  180 000, timestamp 3.6·10⁶ ms) — which is the top of the realistic range, and the low end
  (everything zero) is reported beside it.
* **Which records.** The standard 30-seed × 1000-record protocol (audit F4), unchanged.
* **How far apart.** The generator emits a record every 50 ms. A `stride` of k keeps every k-th
  record, i.e. records 50·k ms apart. A delta is a difference, so its size depends on that spacing;
  measuring it at 50 ms and using it for a link that sends a record every few seconds was audit
  finding F48.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from functools import cache
from statistics import mean

from authbc.bench import telemgen
from authbc.bench.framesizes import RECORDS_PER_SEED, SIZE_SEEDS
from authbc.encodings.delta_enc import DeltaEncoder
from authbc.ledger.record import Record
from authbc.models import frame as frame_model
from authbc.placement import wire_v2

CONVENTION_SRC: int = 40_000
CONVENTION_BASE_SEQ: int = 180_000
CONVENTION_TS0_MS: int = 3_600_000
SIG_BYTES: int = 64


@dataclass(frozen=True)
class SizeStats:
    """Mean and range of a set of byte lengths."""

    mean: float
    lo: int
    hi: int
    n: int

    @classmethod
    def of(cls, sizes: Sequence[int]) -> SizeStats:
        return cls(mean=mean(sizes), lo=min(sizes), hi=max(sizes), n=len(sizes))


_STREAMS: dict[int, list[telemgen.TelemetryRecord]] = {}


def generator_records(seed: int, n: int) -> list[telemgen.TelemetryRecord]:
    """The first `n` records of the seeded generator stream.

    The generator is sequential, so a shorter stream is a prefix of a longer one from the same
    seed (`tests/unit/bench/test_leanframes.py` holds this). Sweeping the record spacing asks for
    the same thirty streams at many lengths; each is generated once, at the longest length asked
    for so far, and sliced.
    """
    have = _STREAMS.get(seed, [])
    if len(have) < n:
        have = _STREAMS[seed] = telemgen.samples(seed=seed, n=max(n, 2 * len(have)))
    return have[:n]


def chained_records(seed: int, n: int, *, src: int = CONVENTION_SRC,
                    base_seq: int = CONVENTION_BASE_SEQ, ts0: int = CONVENTION_TS0_MS,
                    stride: int = 1) -> list[Record]:
    """`n` consecutive chained ledger records from the seeded generator, mid-flight.

    The telemetry is the generator's; `src`, `seq` and the time origin are placed where the caller
    asks, because a `Chain` can only start at sequence number zero and the sizes of interest are
    the ones an hour into a flight.
    """
    if stride < 1:
        raise ValueError(f"stride must be ≥ 1, got {stride}")
    return list(_chained(seed, n, src, base_seq, ts0, stride))


@cache
def _chained(seed: int, n: int, src: int, base_seq: int, ts0: int,
             stride: int) -> tuple[Record, ...]:
    # Cached: every measurement of one stream needs the same n SHA-256 chain links, and the
    # frame-size sweeps ask for the same thirty streams a dozen times over.
    raw = generator_records(seed, n * stride)[::stride]
    t_first = raw[0].ts
    recs: list[Record] = []
    ph = bytes(32)
    for i, r in enumerate(raw):
        rec = Record(src=src, seq=base_seq + i, ts=ts0 + (r.ts - t_first), prev_hash=ph,
                     pl={k: getattr(r, k) for k in wire_v2.PAYLOAD_FIELDS})
        recs.append(rec)
        ph = rec.record_hash()
    return tuple(recs)


def lean_record_sizes(seeds: Sequence[int] = SIZE_SEEDS, n: int = RECORDS_PER_SEED, *,
                      stride: int = 1, ts0: int = CONVENTION_TS0_MS
                      ) -> tuple[SizeStats, SizeStats]:
    """(keyframe, delta) record-stream bytes of the lean format, pooled over `seeds`.

    Every record is measured both ways: alone, as a self-contained record, and against the record
    before it.
    """
    key: list[int] = []
    delta: list[int] = []
    for seed in seeds:
        recs = chained_records(seed, n, stride=stride, ts0=ts0)
        key.extend(len(wire_v2.record_stream([r], None)) for r in recs)
        delta.extend(len(wire_v2.record_stream([r], p))
                     for p, r in zip(recs, recs[1:], strict=False))
    return SizeStats.of(key), SizeStats.of(delta)


def v1_delta_record_sizes(seeds: Sequence[int] = SIZE_SEEDS, n: int = RECORDS_PER_SEED, *,
                          stride: int = 1) -> tuple[SizeStats, SizeStats]:
    """(keyframe, delta) record bytes of the FIRST format's delta encoder, each with its 32 B link.

    The same records as `lean_record_sizes`, through `encodings/delta_enc.py` — the encoder whose
    16-record mean (45.0 B) the published byte results used.
    """
    key: list[int] = []
    delta: list[int] = []
    for seed in seeds:
        raw = generator_records(seed, n * stride)[::stride]
        all_keys = DeltaEncoder(keyframe_interval=1)
        key.extend(len(all_keys.encode(r)) for r in raw)
        one_key = DeltaEncoder(keyframe_interval=len(raw) + 1)
        delta.extend([len(one_key.encode(r)) for r in raw][1:])
    return SizeStats.of(key), SizeStats.of(delta)


def lean_frame_sizes(batch: int, ref_interval: int = 1, *, inline: bool = False,
                     seeds: Sequence[int] = SIZE_SEEDS, n: int = RECORDS_PER_SEED,
                     stride: int = 1, src: int = CONVENTION_SRC,
                     base_seq: int = CONVENTION_BASE_SEQ, ts0: int = CONVENTION_TS0_MS,
                     sig_bytes: int = SIG_BYTES) -> SizeStats:
    """Lengths of emitted lean frames of `batch` records, one self-contained frame per interval.

    The signature is `sig_bytes` of zeros: a frame's length does not depend on the signature's
    value, and signing 30 000 records would only measure the signer
    (`tests/unit/bench/test_leanframes.py` holds that a signed frame has the same length).
    """
    if batch < 1 or ref_interval < 1:
        raise ValueError("batch and ref_interval must be ≥ 1")
    if inline and ref_interval != 1:
        raise ValueError("an inline frame is always self-contained")
    sizes: list[int] = []
    for seed in seeds:
        recs = chained_records(seed, n - n % batch, stride=stride, src=src, base_seq=base_seq,
                               ts0=ts0)
        for k, start in enumerate(range(0, len(recs), batch)):
            chunk = recs[start:start + batch]
            prev = recs[start - 1] if k % ref_interval else None
            sizes.append(_frame_len(chunk, prev, inline=inline, sig_bytes=sig_bytes))
    return SizeStats.of(sizes)


def _frame_len(chunk: Sequence[Record], prev: Record | None, *, inline: bool,
               sig_bytes: int) -> int:
    auth: bytes | tuple[bytes, ...]
    if inline:
        t, auth = wire_v2.FrameType.A_KEY, tuple(bytes(sig_bytes) for _ in chunk)
    else:
        t = wire_v2.FrameType.B_DELTA if prev is not None else wire_v2.FrameType.B_KEY
        auth = bytes(sig_bytes)
    f = wire_v2.FrameV2(t=t, src=chunk[0].src, base_seq=chunk[0].seq, link=chunk[0].prev_hash,
                        recs=tuple(chunk), auth=auth)
    return len(wire_v2.encode_frame_v2(f, prev=prev))


def lean_layout(*, stride: int = 1) -> frame_model.FlatLayout:
    """The lean format as additive components, for searches over batch size and link payload.

    Header at the documented flight point for a multi-record frame; records as the measured means.
    A search needs sizes that add, and CBOR length prefixes do not quite: this layout is exact for
    frames whose record stream is 24–255 B (batches of 2 to about 27) and one byte high for a
    single-record frame. Reported sizes come from `lean_frame_sizes`, never from this.
    """
    key, delta = lean_record_sizes(stride=stride)
    header = frame_model.lean_header_bytes(src=CONVENTION_SRC, base_seq=CONVENTION_BASE_SEQ,
                                           n=4, stream_bytes=50)
    return frame_model.FlatLayout("lean", header_bytes=header,
                                  link_bytes=frame_model.LINK_FIELD_BYTES,
                                  key_record_bytes=key.mean, delta_record_bytes=delta.mean)


def v1_delta_layout(*, stride: int = 1, header_bytes: float = 44.0) -> frame_model.FlatLayout:
    """Byte model of the first format with delta records: text-keyed header, a link per record."""
    key, delta = v1_delta_record_sizes(stride=stride)
    return frame_model.FlatLayout("v1/delta", header_bytes=header_bytes, link_bytes=0,
                                  key_record_bytes=key.mean, delta_record_bytes=delta.mean)
