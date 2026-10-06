"""One definition of an authenticated frame, and what follows from it (docs/02 T3', T6').

A frame that verifies alone has to carry four things::

    header  +  chain link  +  signature(s)  +  at least one record that decodes alone

The byte, verifiability and exclusion results are this one sum evaluated at different batch sizes
and link payloads. They used to be three separate pieces of arithmetic that disagreed with each
other (audit F45–F47): the byte model amortised a keyframe across frames the verifiability model
assumed independent, and the exclusion test charged neither the chain link nor a record that could
be decoded without its predecessor.

Two layouts are described here.

* `FlatLayout` — the byte model of the FIRST format (`placement/wire.py` header, text keys, a
  chain link inside every record). It is a model: no frame carrying delta records in that header
  was ever emitted. Its constants are the measured ones the published results always used.
* `lean_frame_bytes` — the exact length of a `wire_v2` frame. Not a model of the lean format but
  its arithmetic, and `tests/unit/models/test_frame.py` holds it equal to emitted frames.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

LINK_FIELD_BYTES: int = 35       # wire_v2: one-byte key + two-byte length prefix + 32-byte hash
_MAP_AND_KEYS: int = 1 + 8       # CBOR map header + eight one-byte integer keys


def cbor_uint_bytes(value: int) -> int:
    """Bytes canonical CBOR spends on an unsigned integer (RFC 8949 §3)."""
    if value < 0:
        raise ValueError("unsigned integers only")
    for limit, width in ((24, 1), (2**8, 2), (2**16, 3), (2**32, 5)):
        if value < limit:
            return width
    return 9


def cbor_prefix_bytes(length: int) -> int:
    """Bytes of the length prefix in front of a byte string or array of `length` items."""
    return cbor_uint_bytes(length)


def lean_frame_bytes(*, src: int, base_seq: int, n: int, stream_bytes: int,
                     sig_bytes: int = 64, inline: bool = False) -> int:
    """Exact length of a `wire_v2` frame carrying `n` records in a `stream_bytes` record stream.

    `inline=True` is the one-signature-per-record frame (type 0); otherwise one signature.
    """
    fixed = (_MAP_AND_KEYS + 1 + 1 + cbor_uint_bytes(src) + cbor_uint_bytes(base_seq)
             + cbor_uint_bytes(n))                      # map, keys, v, t, src, base_seq, n
    link = LINK_FIELD_BYTES - 1                         # its key is already in `_MAP_AND_KEYS`
    recs = cbor_prefix_bytes(stream_bytes) + stream_bytes
    one_sig = cbor_prefix_bytes(sig_bytes) + sig_bytes
    auth = cbor_prefix_bytes(n) + n * one_sig if inline else one_sig
    return fixed + link + recs + auth


def lean_header_bytes(*, src: int, base_seq: int, n: int, stream_bytes: int,
                      sig_bytes: int = 64) -> int:
    """H_f of a self-batch lean frame: everything that is not link, record stream or signature.

    The same definition docs/01 §2a uses for v1 (`frame − records − signature`), with the chain
    link — which v1 keeps inside each record — separated out as its own term.
    """
    return (lean_frame_bytes(src=src, base_seq=base_seq, n=n, stream_bytes=stream_bytes,
                             sig_bytes=sig_bytes)
            - LINK_FIELD_BYTES - stream_bytes - sig_bytes)


def first_header_fields(*, src: int, base_seq: int, n: int,
                        sig_bytes: int = 64) -> dict[str, int]:
    """H_f of the first format (`placement/wire.py`) field by field.

    Each field is a CBOR text key (one byte plus its length) and then its value, or for `recs`
    and `auth` the length prefix of what follows. The seven key names alone are 29 B.
    """
    def key(name: str) -> int:
        return 1 + len(name)

    return {
        "map": 1,
        "v": key("v") + 1,
        "t": key("t") + 1,
        "src": key("src") + cbor_uint_bytes(src),
        "base_seq": key("base_seq") + cbor_uint_bytes(base_seq),
        "n": key("n") + cbor_uint_bytes(n),
        "recs": key("recs") + cbor_prefix_bytes(n),
        "auth": key("auth") + cbor_prefix_bytes(sig_bytes),
    }


def lean_header_fields(*, src: int, base_seq: int, n: int, stream_bytes: int,
                       sig_bytes: int = 64) -> dict[str, int]:
    """H_f of a self-batch lean frame field by field; every key is one byte.

    The chain link is not here: its key, prefix and 32 B are `LINK_FIELD_BYTES`, a separate term.
    """
    return {
        "map": 1,
        "v": 1 + 1,
        "t": 1 + 1,
        "src": 1 + cbor_uint_bytes(src),
        "base_seq": 1 + cbor_uint_bytes(base_seq),
        "n": 1 + cbor_uint_bytes(n),
        "recs": 1 + cbor_prefix_bytes(stream_bytes),
        "auth": 1 + cbor_prefix_bytes(sig_bytes),
    }


@dataclass(frozen=True)
class FlatLayout:
    """Byte model of a format whose sizes add without framing: H_f + L + signatures + records."""

    name: str
    header_bytes: float            # H_f
    link_bytes: float              # chain link carried once per frame; 0 if each record has its own
    key_record_bytes: float        # a record that decodes alone
    delta_record_bytes: float      # a record coded against its predecessor

    def __post_init__(self) -> None:
        if min(self.header_bytes, self.link_bytes, self.delta_record_bytes) < 0:
            raise ValueError("sizes must be ≥ 0")
        if self.key_record_bytes < self.delta_record_bytes:
            raise ValueError("a self-contained record cannot be smaller than a dependent one")

    @property
    def stateless(self) -> bool:
        """True when every record decodes alone (JSON, CBOR, MessagePack)."""
        return self.key_record_bytes == self.delta_record_bytes

    def frame_bytes(self, sig_bytes: float, batch: int, *, self_contained: bool = True,
                    inline: bool = False) -> float:
        """One frame of `batch` records; `self_contained` makes its first record a keyframe."""
        if batch < 1:
            raise ValueError(f"batch must be ≥ 1, got {batch}")
        first = self.key_record_bytes if self_contained else self.delta_record_bytes
        sigs = batch if inline else 1
        return (self.header_bytes + self.link_bytes + sigs * sig_bytes
                + first + (batch - 1) * self.delta_record_bytes)

    def mean_frame_bytes(self, sig_bytes: float, batch: int, ref_interval: int = 1, *,
                         inline: bool = False) -> float:
        """Mean frame when one frame in `ref_interval` is self-contained."""
        _require_interval(ref_interval)
        dependent = self.frame_bytes(sig_bytes, batch, self_contained=False, inline=inline)
        return dependent + (self.key_record_bytes - self.delta_record_bytes) / ref_interval

    def bytes_per_record(self, sig_bytes: float, batch: int, ref_interval: int = 1, *,
                         inline: bool = False) -> float:
        return self.mean_frame_bytes(sig_bytes, batch, ref_interval, inline=inline) / batch

    def max_batch(self, sig_bytes: float, payload_bytes: float) -> int:
        """Largest self-contained self-batch frame that fits `payload_bytes`; 0 if none does."""
        room = payload_bytes - self.frame_bytes(sig_bytes, 1)
        if room < 0:
            return 0
        if self.delta_record_bytes == 0:
            raise ValueError("a zero-byte record has no largest batch")
        return 1 + int(room // self.delta_record_bytes)

    def exclusion(self, sig_bytes: float, payload_bytes: float) -> str | None:
        """Why a link of `payload_bytes` cannot carry even one self-contained frame, or None.

        The tiers are nested and each names what a redesign would have to change: the signature
        scheme, the header, the on-air chain link, or the record encoding.
        """
        need = sig_bytes
        if payload_bytes < need:
            return "signature"
        need += self.header_bytes
        if payload_bytes < need:
            return "header"
        need += self.link_bytes
        if payload_bytes < need:
            return "chain link"
        if payload_bytes < need + self.key_record_bytes:
            return "record"
        return None


def _require_interval(ref_interval: int) -> None:
    if ref_interval < 1:
        raise ValueError(f"ref_interval must be ≥ 1 frame, got {ref_interval}")


def verifiability(p_loss: float, ref_interval: int = 1) -> float:
    """V — probability that a sent record can be decoded AND verified at a receiver (T3').

    One frame in `ref_interval` decodes alone; the j-th frame of a group needs all j frames up to
    and including itself, so under independent loss ``V = (1/R)·Σ_{j=1..R} (1−p)^j``.
    ``R = 1`` is the frame-independent case and gives the T3 value ``1 − p``.
    """
    if not 0.0 <= p_loss <= 1.0:
        raise ValueError(f"p_loss must be in [0, 1], got {p_loss}")
    _require_interval(ref_interval)
    q = 1.0 - p_loss
    return sum(q ** j for j in range(1, ref_interval + 1)) / ref_interval


def verifiability_gilbert(p_mean: float, mean_burst_frames: float, ref_interval: int = 1) -> float:
    """V under two-state (Gilbert) burst loss with the same MEAN loss and a mean burst length.

    Loss happens exactly in the bad state. With bad→good probability ``r = 1/mean_burst`` and
    good→bad probability ``a = p̄·r/(1−p̄)``, a run of j received frames has probability
    ``(1−p̄)·(1−a)^{j−1}``, so ``V = (1−p̄)/R · Σ_{j=1..R} (1−a)^{j−1}``.

    ``mean_burst_frames = 1/(1−p̄)`` reproduces independent loss. Longer bursts RAISE V for R > 1
    at the same mean loss, because losses that cluster break fewer groups — so independent loss
    is the conservative case, and V never exceeds ``1 − p̄`` for any R.
    """
    if not 0.0 <= p_mean < 1.0:
        raise ValueError(f"p_mean must be in [0, 1), got {p_mean}")
    if mean_burst_frames < 1.0:
        raise ValueError("a loss burst is at least one frame long")
    _require_interval(ref_interval)
    a = p_mean / (mean_burst_frames * (1.0 - p_mean))
    if a > 1.0:
        raise ValueError("no Gilbert chain has that mean loss with bursts that short")
    return (1.0 - p_mean) * sum((1.0 - a) ** (j - 1) for j in range(1, ref_interval + 1)) \
        / ref_interval


def max_ref_interval(p_loss: float, epsilon: float, candidates: Sequence[int]) -> int:
    """Largest candidate interval that still meets V ≥ 1−ε, or 0 if even R = 1 does not.

    V falls monotonically with R, so the choice is a threshold. At ``p = ε`` only R = 1 passes:
    a design evaluated at its own loss budget has no room for cross-frame dependency.
    """
    if not 0.0 < epsilon < 1.0:
        raise ValueError(f"epsilon must be in (0, 1), got {epsilon}")
    # Compared exactly, with no tolerance: at R = 1 `verifiability` returns the same double
    # `1.0 − p` that `1.0 − epsilon` is when p = ε, so the boundary case passes as T3 says.
    return max((r for r in candidates if verifiability(p_loss, r) >= 1.0 - epsilon), default=0)
