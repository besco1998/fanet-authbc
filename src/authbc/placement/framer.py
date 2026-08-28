"""Framer ABC + MTU/batch helpers (docs/01 §1 placements, docs/02 §6-7).

A ``Framer`` packs records into wire frames (reusing the frozen P2 ``wire`` builders) and
unpacks a received frame back to ``(records, ok_mask)`` where ``ok_mask[i]`` says whether
record i verified. Placement B/C/D are all-or-nothing per frame (one auth object); A is
per-record. ``b_max`` is the byte-budget batch limit (docs/02 T2).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator, Sequence
from typing import Any

from authbc.ledger.record import Record
from authbc.placement.wire import Frame

M_MTU = 1500  # application MTU budget (docs/01 §1, docs/02 §6)
H_F = 44      # ledger frame header bytes — MEASURED from wire.py (B1, docs/01 §2a)


def b_max(s: float, g_a: int, *, mtu: int = M_MTU, h_f: int = H_F) -> int:
    """Max single-auth records per frame: ⌊(M − H_f − g_a)/s⌋ (docs/02 T2 §, B/C/D).

    ``s`` is a float because encoded sizes are measured means; the floor is taken on the
    quotient, not on ``s``, so flooring the size first would give a different answer.
    """
    if s <= 0:
        raise ValueError("record size s must be positive")
    return int((mtu - h_f - g_a) // s)


def b_max_inline(s: float, g_record: int = 64, *, mtu: int = M_MTU, h_f: int = H_F) -> int:
    """Max per-record-signed (placement A) records: ⌊(M − H_f)/(s + g_record)⌋."""
    if s <= 0:
        raise ValueError("record size s must be positive")
    return int((mtu - h_f) // (s + g_record))


def _chunks(records: Sequence[Record], b: int) -> Iterator[list[Record]]:
    if b < 1:
        raise ValueError("batch size b must be >= 1")
    for i in range(0, len(records), b):
        yield list(records[i : i + b])


class Framer(ABC):
    """Pack records into frames / unpack a frame to (records, ok_mask)."""

    @abstractmethod
    def pack(
        self,
        records: Sequence[Record],
        *,
        b: int,
        sigs: Sequence[bytes] | None = None,
        pks: Sequence[Any] | None = None,
    ) -> list[Frame]:
        """Pack records into frames of at most ``b`` records each.

        ``sigs``/``pks`` exist only for placement C, which aggregates signatures made by
        *different* senders and therefore cannot produce them itself — the relay is given
        already-signed records. A, B and D sign internally and ignore both. As with
        ``unpack``, they are optional here and checked in C so that substitutability holds.
        """
        ...

    @abstractmethod
    def unpack(self, frame: Frame, *, pk: Any = None) -> tuple[list[Record], list[bool]]:
        """Verify a frame → (records, ok_mask).

        ``pk`` is optional because the placements genuinely differ: A, B and D verify
        against a sender key supplied by the caller, while C (cross-signer aggregation)
        carries its own public keys inside the frame and ignores it. Subclasses that
        need a key raise ``ValueError`` when it is absent — declaring it optional here
        and required there would break substitutability (LSP).
        """
        ...


# --------------------------------------------------------------------------- H_f is a RANGE
# ⚠️ 2026-08-28 math audit. `H_F` above is a single constant, and docs/01 §2a reports it as
# "44 B ... at every batch 1 ≤ b ≤ 23, stepping to 46 B at b ≥ 24" — constant in b. It IS
# constant in b. It is NOT constant in the magnitudes of `src` and `base_seq`, because canonical
# CBOR encodes an integer 0..23 in one byte and one ≥ 65536 in five. Measured:
#
#     src=0     base_seq=0        ->  H_f = 38 B     (first records of a flight, low node id)
#     src=24    base_seq=24       ->  H_f = 39 B
#     src=256   base_seq=256      ->  H_f = 40 B
#     src=40000 base_seq=180000   ->  H_f = 44 B     (1 h into flight at 50 Hz — the documented
#                                                     value, and the top of the range)
#
# WHY THIS MATTERS, and it is not the byte model. T6's exclusion bound is s_max = M − H_f − g_a,
# so a LARGER H_f makes exclusion MORE likely. DR3 (M=115, g_a=64, s_min=13) is excluded for
# H_f ≥ 39 and FEASIBLE at H_f ≤ 38 — at which point the paper's headline goes from "four of
# seven EU868 rates excluded" to three. docs/01 §2a analyses the direction of bias for the byte
# comparison (where 44 B is conservative) and never for T6, where the sign is opposite.
#
# The constant is left at 44 deliberately: it is the steady-state value for any realistic flight,
# every frozen artifact depends on it, and it is the conservative choice for the byte results.
# What changes is that the range is now measurable rather than assumed.
def measure_frame_header_bytes(batch: int = 4, *, src: int = 40_000,
                               base_seq: int = 180_000) -> int:
    """H_f measured from the implemented wire format at a given (batch, src, base_seq).

    H_f = len(encode_frame(F)) − Σ len(record canonical bytes) − len(auth), exactly the
    definition in docs/01 §2a. Defaults reproduce the documented 44 B.
    """
    from authbc.ledger.record import Record
    from authbc.placement.wire import Frame, Placement, encode_frame

    recs = tuple(Record(src=src, seq=base_seq + i, ts=1_000 + i,
                        prev_hash=b"\x11" * 32, pl={"a": 1})
                 for i in range(batch))
    frame = Frame(t=Placement.B, src=src, base_seq=base_seq, recs=recs, auth=b"\x00" * 64)
    return len(encode_frame(frame)) - sum(len(r.canonical()) for r in recs) - 64


def frame_header_bytes_range(batch: int = 4) -> tuple[int, int]:
    """(min, max) H_f over the legal (src, base_seq) domain at a given batch size."""
    lo = measure_frame_header_bytes(batch, src=0, base_seq=0)
    hi = measure_frame_header_bytes(batch, src=65_535, base_seq=4_294_967_000)
    return lo, hi
